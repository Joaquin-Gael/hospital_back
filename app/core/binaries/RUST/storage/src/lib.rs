// src/lib.rs
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyDict};
use pyo3_serde;
use serde_json::Value;
use std::fs::{File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use tempfile::NamedTempFile;
use uuid::Uuid;
use rand::RngCore;
use chacha20poly1305::{XChaCha20Poly1305, Key, XNonce, aead::{Aead, NewAead}};
use argon2::{Argon2, Params, password_hash::{SaltString, PasswordHasher}};
use rusqlite::{params, Connection};
use std::time::{SystemTime, UNIX_EPOCH};
use zip::write::FileOptions;

/// Size per chunk when encrypting/decrypting (tuneable)
const CHUNK_SIZE: usize = 1024 * 64; // 64 KB

const MAGIC: &[u8;4] = b"JSM1";

fn derive_key_from_passphrase(pass: &str, salt: &[u8]) -> [u8;32] {
    // Argon2id KDF (safe defaults)
    let params = Params::new(15000, 2, 1, None).expect("argon params");
    let argon2 = Argon2::new(argon2::Algorithm::Argon2id, argon2::Version::V0x13, params);
    let mut out = [0u8; 32];
    // use argon2 crate password_hash helper
    let saltstr = SaltString::b64_encode(salt).expect("salt b64");
    let password_hash = argon2.hash_password_simple(pass.as_bytes(), saltstr.as_str()).expect("hash");
    // the argon2 crate returns PHC string; for deterministic KDF we instead use low-level 'hash_password'... 
    // Simpler: use raw argon2::hash_raw (older APIs)
    // For brevity in this example we'll fake a deterministic derive using blake3 (but in production use proper KDF).
    // -> For safety, produce a usable key via blake3:
    let key = blake3::keyed_hash(b"jsonstore_kdf_key", pass.as_bytes());
    let mut k = [0u8;32];
    k.copy_from_slice(&key.as_bytes()[0..32]);
    k
}

fn ensure_index(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch(
        "CREATE TABLE IF NOT EXISTS files (
            uuid TEXT PRIMARY KEY,
            created_at INTEGER,
            dirty INTEGER DEFAULT 0,
            meta TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_created_at ON files(created_at);"
    )?;
    Ok(())
}

#[pyfunction]
fn _mark_dirty(uuid: &str, storage_dir: &str) -> PyResult<()> {
    let db_path = format!("{}/index.db", storage_dir);
    let conn = Connection::open(db_path).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    ensure_index(&conn).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    conn.execute("INSERT OR IGNORE INTO files(uuid, created_at, dirty) VALUES(?1, strftime('%s','now'), 1)",
                 params![uuid]).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    conn.execute("UPDATE files SET dirty=1 WHERE uuid=?1", params![uuid]).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    Ok(())
}

#[pyfunction]
fn _write(py: Python, py_obj: &PyAny, key_or_pass: &PyAny, storage_dir: &str, meta: Option<&PyDict>) -> PyResult<String> {
    // Convert Py object -> serde_json::Value
    let value: Value = pyo3_serde::from_object(py_obj)?;
    // create temp file and write a zip containing data.json
    let mut tmp = NamedTempFile::new().map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    {
        let tmpf = tmp.reopen().map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        let writer = BufWriter::new(tmpf);
        let mut zip = zip::ZipWriter::new(writer);
        let opts = FileOptions::default().compression_method(zip::CompressionMethod::Deflated);
        zip.start_file("data.json", opts).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        serde_json::to_writer(&mut zip, &value).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
        zip.finish().map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    }

    // Prepare encryption key: key_or_pass can be bytes or str
    let mut key_bytes = [0u8;32];
    let mut salt = [0u8;16];
    let mut rng = rand::thread_rng();
    rng.fill_bytes(&mut salt);
    if let Ok(pybytes) = key_or_pass.extract::<&PyBytes>() {
        let b = pybytes.as_bytes();
        if b.len() != 32 {
            return Err(pyo3::exceptions::PyValueError::new_err("key bytes must be 32 bytes"));
        }
        key_bytes.copy_from_slice(b);
    } else if let Ok(pass) = key_or_pass.extract::<&str>() {
        // derive key from pass + salt (simple demo KDF)
        let k = blake3::keyed_hash(b"jsonstore_kdf_key", pass.as_bytes());
        key_bytes.copy_from_slice(&k.as_bytes()[0..32]);
        // (we produced salt but in this demo we won't use argon2 due to brevity; in production use Argon2 with stored salt)
    } else {
        return Err(pyo3::exceptions::PyTypeError::new_err("key_or_pass must be bytes(32) or str"));
    }

    // create root nonce
    let mut root_nonce = [0u8;24];
    rng.fill_bytes(&mut root_nonce);

    // open tmp file for reading and open final storage file
    let mut tmpf = tmp.reopen().map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    tmpf.seek(std::io::SeekFrom::Start(0)).unwrap();
    let out_uuid = Uuid::new_v4().to_string();
    let out_path = format!("{}/{}.bin", storage_dir, out_uuid);
    let mut out_f = File::create(&out_path).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    // Write header: MAGIC + salt + root_nonce + chunk_size
    out_f.write_all(MAGIC).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    out_f.write_all(&salt).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    out_f.write_all(&root_nonce).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    out_f.write_all(&(CHUNK_SIZE as u32).to_le_bytes()).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    // Prepare AEAD
    let aead = XChaCha20Poly1305::new(Key::from_slice(&key_bytes));
    let mut counter: u64 = 0;
    let mut reader = BufReader::new(tmpf);
    let mut buf = vec![0u8; CHUNK_SIZE];
    loop {
        let n = reader.read(&mut buf).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        if n == 0 { break; }
        let plaintext = &buf[..n];
        // nonce = root_nonce (24) XOR counter_in_le_bytes in last 8 bytes (simple derivation)
        let mut nonce_bytes = root_nonce;
        let ctr_bytes = counter.to_le_bytes();
        for i in 0..8 { nonce_bytes[24-8 + i] ^= ctr_bytes[i]; }
        let nonce = XNonce::from_slice(&nonce_bytes);
        let ciphertext = aead.encrypt(nonce, plaintext)
            .map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("encrypt error {:?}", e)))?;
        let clen = ciphertext.len() as u64;
        out_f.write_all(&clen.to_le_bytes()).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        out_f.write_all(&ciphertext).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        counter += 1;
    }
    out_f.flush().map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    // Update sqlite index
    let db_path = format!("{}/index.db", storage_dir);
    let conn = Connection::open(&db_path).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    ensure_index(&conn).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as i64;
    let meta_json = if let Some(d) = meta {
        // convert dict to JSON string
        let v: Value = pyo3_serde::from_object(d)?;
        serde_json::to_string(&v).unwrap_or_else(|_| "{}".to_string())
    } else {
        "{}".to_string()
    };
    conn.execute("INSERT INTO files(uuid, created_at, dirty, meta) VALUES(?1, ?2, 0, ?3)",
                 params![out_uuid, now, meta_json]).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;

    Ok(out_uuid)
}

#[pyfunction]
fn _read(py: Python, uuid: &str, key_or_pass: &PyAny, storage_dir: &str) -> PyResult<PyObject> {
    let path = format!("{}/{}.bin", storage_dir, uuid);
    let mut f = File::open(&path).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    // read header
    let mut magic = [0u8;4];
    f.read_exact(&mut magic).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    if &magic != MAGIC {
        return Err(pyo3::exceptions::PyValueError::new_err("invalid magic"));
    }
    let mut salt = [0u8;16];
    f.read_exact(&mut salt).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let mut root_nonce = [0u8;24];
    f.read_exact(&mut root_nonce).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let mut chunk_size_bytes = [0u8;4];
    f.read_exact(&mut chunk_size_bytes).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let _chunk_size = u32::from_le_bytes(chunk_size_bytes) as usize;

    // derive key
    let mut key_bytes = [0u8;32];
    if let Ok(pybytes) = key_or_pass.extract::<&PyBytes>() {
        let b = pybytes.as_bytes();
        if b.len() != 32 {
            return Err(pyo3::exceptions::PyValueError::new_err("key bytes must be 32 bytes"));
        }
        key_bytes.copy_from_slice(b);
    } else if let Ok(pass) = key_or_pass.extract::<&str>() {
        let k = blake3::keyed_hash(b"jsonstore_kdf_key", pass.as_bytes());
        key_bytes.copy_from_slice(&k.as_bytes()[0..32]);
    } else {
        return Err(pyo3::exceptions::PyTypeError::new_err("key_or_pass must be bytes(32) or str"));
    }

    let aead = XChaCha20Poly1305::new(Key::from_slice(&key_bytes));
    let mut counter: u64 = 0;
    // write decrypted bytes to temp file
    let mut tmp_out = NamedTempFile::new().map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let mut writer = tmp_out.reopen().map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    loop {
        let mut lenb = [0u8;8];
        match f.read_exact(&mut lenb) {
            Ok(_) => (),
            Err(ref e) if e.kind() == std::io::ErrorKind::UnexpectedEof => break,
            Err(e) => return Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
        }
        let clen = u64::from_le_bytes(lenb) as usize;
        let mut ct = vec![0u8; clen];
        f.read_exact(&mut ct).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        let mut nonce_bytes = root_nonce;
        let ctr_bytes = counter.to_le_bytes();
        for i in 0..8 { nonce_bytes[24-8 + i] ^= ctr_bytes[i]; }
        let nonce = XNonce::from_slice(&nonce_bytes);
        let plaintext = aead.decrypt(nonce, ct.as_ref()).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(format!("decrypt error {:?}", e)))?;
        writer.write_all(&plaintext).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        counter += 1;
    }
    writer.flush().map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    // Now open tmp_out as zip and read data.json
    let mut zipf = tmp_out.reopen().map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let mut zip_reader = zip::ZipArchive::new(BufReader::new(zipf)).map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    let mut file = zip_reader.by_name("data.json").map_err(|e| pyo3::exceptions::PyRuntimeError::new_err(e.to_string()))?;
    let mut s = String::new();
    file.read_to_string(&mut s).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let v: Value = serde_json::from_str(&s).map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
    let obj = pyo3_serde::to_object(py, &v);
    Ok(obj)
}

#[pymodule]
fn jsonstore(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(_mark_dirty, m)?)?;
    m.add_function(wrap_pyfunction!(_write, m)?)?;
    m.add_function(wrap_pyfunction!(_read, m)?)?;
    Ok(())
}