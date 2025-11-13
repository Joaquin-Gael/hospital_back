use tokio::{self, io::{AsyncReadExt, AsyncWriteExt}};
use chacha20poly1305::{
    aead::{AeadMutInPlace, KeyInit},
    ChaCha20Poly1305, Nonce
};
use serde::{Serialize, Deserialize};
use serde_json::{self, Value};
use std::{collections::HashMap, env};
use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;
//use rusqlite::Connection;
use uuid::Uuid;
use chrono::Utc;
use chrono::Duration;

const KEY: &[u8; 32] = b"01234567890123456789012345678901";

const NONCE: &[u8; 12] = b"012345678901";

const DATA_TYPE: &str = "st";

#[derive(Debug, Serialize, Deserialize)]
enum Types {
    Sequence(String),
    Integer(i64),
    Boolean(bool)
}

#[derive(Debug, Serialize, Deserialize)]
struct Index {
    uuid_id: String,
    //created_at: i64,
    set_name: String,
    hash: String,
    items_count: u64
}

#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Item {
    #[pyo3(get, set)]
    pub uuid_id: String,
    #[pyo3(get, set)]
    pub set_name: String,
    #[pyo3(get, set)]
    pub item_name: String,
    #[pyo3(get, set)]
    pub content: String,
    #[pyo3(get, set)]
    pub created_at: i64,
    #[pyo3(get, set)]
    pub updated_at: i64,
    #[pyo3(get, set)]
    pub expired_at: i64,
    #[pyo3(get, set)]
    pub data_type: String
}

#[pyclass]
#[derive(Debug, Serialize, Deserialize)]
pub struct Set {
    #[pyo3(get, set)]
    pub name: String,
    #[pyo3(get, set)]
    pub content: Vec<Item>
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ItemInput {
    set_name: String,
    item_name: String,
    content: Value,
}

impl Item {
    pub async fn new(set_name: String, item_name: String, content: String) -> Self {
        let uuid_id = Uuid::new_v4().to_string();
        Self {
            uuid_id,
            set_name,
            item_name,
            content,
            created_at: Utc::now().timestamp(),
            updated_at: Utc::now().timestamp(),
            expired_at: Utc::now().timestamp() + Duration::days(30).num_seconds(),
            data_type: DATA_TYPE.to_string(),
        }
    }
    
    pub async fn write_dict(&mut self, data: HashMap<String, Types>) -> Result<(), Box<dyn std::error::Error>> {
        let mut json_data = HashMap::new();
        for (key, value) in data {
            match value {
                Types::Sequence(s) => json_data.insert(key, Types::Sequence(s)),
                Types::Integer(i) => json_data.insert(key, Types::Integer(i)),
                Types::Boolean(b) => json_data.insert(key, Types::Boolean(b)),
            };
        }
        let mut json_template = String::from("{\n");
        for (k, v) in json_data.iter() {
            json_template.push_str(&format!("\"{}\":", k));
            match v {
                Types::Sequence(s) => json_template.push_str(&format!("\"{}\",", s)),
                Types::Integer(i) => json_template.push_str(&format!("{},", i)),
                Types::Boolean(b) => json_template.push_str(&format!("{},", b)),
            }
        }
        json_template.push_str("}");
        self.content = json_template;
        Ok(())
    }

    pub async fn write_str(&mut self, data: String) -> Result<(), Box<dyn std::error::Error>> {
        self.content = data;
        Ok(())
    }

}

impl Set {
    pub async fn new(name: String) -> Self {
        Self {
            name,
            content: Vec::new(),
        }
    }

    pub async fn count_items(&self) -> u64 {
        self.content.len() as u64
    }

    pub async fn insert_item(&mut self, item: Item) -> Result<bool, Box<dyn std::error::Error>> {
        if let Some(i) = self.content.iter().find(|i| i.item_name == item.item_name) {
            if i.content == item.content {
                Err("Item already exists".into())
            } else {
                self.content.push(item);
                Ok(true)
            }
        } else {
            self.content.push(item);
            Ok(true)
        }
    }

    pub async fn get_item(&self, uuid_id: &str) -> Result<&Item, Box<dyn std::error::Error>> {
        let item = self.content.iter().find(|i| i.uuid_id == uuid_id).clone();
        match item {
            Some(i) => Ok(i),
            None => Err("Item not found".into()),
        }
    }

    pub async fn get_item_by_name(&self, name: &str) -> Result<&Item, Box<dyn std::error::Error>> {
        let item = self.content.iter().find(|i| i.item_name == name).clone();
        match item {
            Some(i) => Ok(i),
            None => Err("Item not found".into()),
        }
    }

    pub async fn delete_item_by_id(&mut self, uuid_id: &str) -> Result<(), Box<dyn std::error::Error>> {
        self.content.retain(|i| i.uuid_id != uuid_id);
        Ok(())
    }

    pub async fn delete_item_by_name(&mut self, name: &str) -> Result<(), Box<dyn std::error::Error>> {
        self.content.retain(|i| i.item_name != name.to_string());
        Ok(())
    }

    pub async fn update_item_by_id(&mut self, uuid_id: &str, item: Item) -> Result<(), Box<dyn std::error::Error>> {
        let index = self.content.iter().position(|i| i.uuid_id == uuid_id);
        match index {
            Some(i) => {
                self.content[i] = item;
                Ok(())
            },
            None => Err("Item not found".into()),
        }
    }

    pub async fn update_item_by_name(&mut self, name: &str, item: Item) -> Result<(), Box<dyn std::error::Error>> {
        let index = self.content.iter().position(|i| i.item_name == name.to_string());
        match index {
            Some(i) => {
                self.content[i] = item;
                Ok(())
            },
            None => Err("Item not found".into()),
        }
    }
}

pub async fn create_index() -> Result<bool, Box<dyn std::error::Error>> {
    let path = env::var("PATH_DIR").unwrap_or_else(|_| "storage".to_string());
    let path = format!("{}/index.{}", path, DATA_TYPE);
    match tokio::fs::File::create(path.clone()).await {
        Ok(_) => {
            Ok(tokio::fs::try_exists(path).await.unwrap_or(false))
        },
        Err(e) => return Err(e.into()),
    }
}

pub async fn create_set(set_name: String) -> Result<Set, Box<dyn std::error::Error>> {
    let set = Set::new(set_name).await;
    Ok(set)
}

pub async fn encript_json(json_data: String) -> Vec<u8> {
    let mut cipher = ChaCha20Poly1305::new(KEY.into());

    let mut buffer: Vec<u8> = Vec::new();
    buffer.extend_from_slice(json_data.as_bytes());

    cipher.encrypt_in_place(&Nonce::from_slice(NONCE), b"", &mut buffer).unwrap();

    buffer
}

pub async fn decrypt_json(encrypted_data: Vec<u8>) -> String {
    let mut cipher = ChaCha20Poly1305::new(KEY.into());
    //println!("Data Encrypted: {:?}", encrypted_data);
    let mut buffer: Vec<u8> = Vec::new();
    buffer.extend_from_slice(&encrypted_data);

    match cipher.decrypt_in_place(&Nonce::from_slice(NONCE), b"", &mut buffer) {
        Ok(_) => {
            return String::from_utf8_lossy(&buffer).to_string()
        },
        Err(e) => {
            //println!("Error decrypting data: {:?}", e.to_string());
            return String::from("")
        },
    };
}


pub async fn save_data(json: String, set_name: String) -> Result<bool, Box<dyn std::error::Error>> {    
    let path = env::var("PATH_DIR").unwrap_or_else(|_| "storage".to_string());
    let path = format!("{}/{}.{}", path, set_name, DATA_TYPE);
    match tokio::fs::try_exists(&path).await {
        Ok(exists) if !exists => {
            //println!("[DEBUG] File does not exist, creating new file: {}", path);
            let mut file = tokio::fs::OpenOptions::new()
                .create(true)
                .write(true)
                .truncate(true)
                .open(path)
                .await?;
            let encrypted_json = encript_json(json).await;
            //println!("[DEBUG] Encrypted JSON length: {} bytes", encrypted_json.len());
            file.write_all(&encrypted_json).await?;
            // Ensure data is flushed to disk before closing
            file.flush().await?;
            //println!("[INFO] Successfully wrote encrypted data to new file");
            Ok(true)
        },
        Ok(exists) if exists => {
            //println!("[DEBUG] File exists, opening for overwrite: {}", path);
            // Open the file with write permissions and truncate existing contents
            let mut file = tokio::fs::OpenOptions::new()
                .write(true)
                .truncate(true)
                .open(path)
                .await?;
            let encrypted_json = encript_json(json).await;
            //println!("[DEBUG] Encrypted JSON length: {} bytes", encrypted_json.len());
            file.write_all(&encrypted_json).await?;
            // Ensure data is flushed to disk before closing
            file.flush().await?;
            //println!("[INFO] Successfully overwrote encrypted data to existing file");
            Ok(true)
        },
        Ok(_)=>{Ok(true)},
        Err(e) => return Err(e.into()),
    }
}

pub async fn read_data(set_name: String) -> Result<Set, Box<dyn std::error::Error>> {
    let path = env::var("PATH_DIR").unwrap_or_else(|_| "storage".to_string());
    let path = format!("{}/{}.{}", path, set_name, DATA_TYPE);
    let mut file = tokio::fs::File::open(path).await?;
    let mut buffer: Vec<u8> = Vec::new();
    file.read_to_end(&mut buffer).await?;
    let encrypted_json = buffer;
    let decrypted_json = decrypt_json(encrypted_json).await;
    let set: Set = serde_json::from_str(&decrypted_json)?;
    Ok(set)
}

// Crea un Item desde un JSON de entrada y retorna el Item serializado como JSON
// Formato de entrada esperado:
// {
//   "set_name": "set1",
//   "item_name": "itemX",
//   "content": { ... cualquier JSON ... }
// }
pub async fn create_item_from_json(input_json: String) -> Result<Item, Box<dyn std::error::Error>> {
    let input: ItemInput = serde_json::from_str(&input_json)?;
    let content_str = serde_json::to_string(&input.content)?;
    let item = Item::new(input.set_name.clone(), input.item_name.clone(), content_str).await;
    Ok(item)
}

pub async fn create_item(set_name: String, item_name: String, content: String) -> Result<Item, Box<dyn std::error::Error>> {
    let item = Item::new(set_name, item_name, content).await;
    Ok(item)
}

// Añade un Item al Set correspondiente a partir del JSON del Item y retorna el Set serializado
pub async fn add_item_from_json(item_json: String) -> Result<bool, Box<dyn std::error::Error>> {
    let item: Item = serde_json::from_str(&item_json)?;
    let mut set = match read_data(item.set_name.clone()).await {
        Ok(s) => s,
        Err(_) => Set::new(item.set_name.clone()).await,
    };
    match set.insert_item(item).await {
        Ok(_) => {
            let set_serialized = serde_json::to_string(&set)?;
            save_data(set_serialized.clone(), set.name.clone()).await?;
            Ok(true)
        },
        Err(e) => {
            let set_serialized = serde_json::to_string(&set)?;
            save_data(set_serialized.clone(), set.name.clone()).await?;
            Err(e.into())
        },
    }
    
}

pub async fn add_item(item: &Item) -> Result<bool, Box<dyn std::error::Error>> {
    let mut set = match read_data(item.set_name.clone()).await {
        Ok(s) => s,
        Err(_) => Set::new(item.set_name.clone()).await,
    };
    //println!("{:?}", set);
    match set.insert_item(item.clone()).await {
        Ok(result) => {
            println!("{:?}", result);
            let set_serialized = serde_json::to_string(&set)?;
            save_data(set_serialized.clone(), set.name.clone()).await?;
            Ok(true)
        },
        Err(e) => {
            eprintln!("{:?}", e);
            let set_serialized = serde_json::to_string(&set)?;
            save_data(set_serialized.clone(), set.name.clone()).await?;
            Err(e.into())
        },
    }
}

// Busca un Item por UUID y/o nombre dentro de un Set y retorna el Item serializado
pub async fn find_item_in_set(
    set_name: String,
    uuid_id: Option<String>,
    item_name: Option<String>,
) -> Result<Item, Box<dyn std::error::Error>> {
    let set = read_data(set_name).await?;
    let found = set.content.iter().find(|i| {
        let mut ok = true;
        if let Some(ref uid) = uuid_id { ok &= &i.uuid_id == uid; }
        if let Some(ref name) = item_name { ok &= &i.item_name == name; }
        ok
    });
    match found {
        Some(item) => Ok(item.clone()),
        None => Err("Item not found".into()),
    }
}

// Actualiza el contenido de un Item por uuid dentro de un Set y retorna el Set serializado
pub async fn update_item_content_by_id(
    set_name: String,
    uuid_id: String,
    item_json: String,
) -> Result<bool, Box<dyn std::error::Error>> {
    let mut set = read_data(set_name).await?;
    let item: Item = serde_json::from_str(&item_json)?;
    let new_content_str = serde_json::to_string(&item.content)?;
    set.update_item_by_id(&uuid_id, item).await?;
    let set_serialized = serde_json::to_string(&set)?;
    save_data(set_serialized.clone(), set.name.clone()).await?;
    Ok(true)
}

// Actualiza el contenido de un Item por nombre dentro de un Set y retorna el Set serializado
pub async fn update_item_content_by_name(
    set_name: String,
    item_name: String,
    item_json: String,
) -> Result<bool, Box<dyn std::error::Error>> {
    let mut set = read_data(set_name).await?;
    let item: Item = serde_json::from_str(&item_json)?;
    let new_content_str = serde_json::to_string(&item.content)?;
    set.update_item_by_name(&item_name, item).await?;
    let set_serialized = serde_json::to_string(&set)?;
    save_data(set_serialized.clone(), set.name.clone()).await?;
    Ok(true)
}

#[pyfunction]
fn py_save_data(set_name: &str, data: &str) -> PyResult<bool> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    rt.block_on(save_data(data.to_string(), set_name.to_string()))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn py_create_set(set_name: &str) -> PyResult<Set> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    rt.block_on(create_set(set_name.to_string()))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

// Wrappers PyO3 para exponer las funciones a Python
#[pyfunction]
fn py_create_item_from_json(input_json: &str) -> PyResult<Item> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    rt.block_on(create_item_from_json(input_json.to_string()))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn py_create_item(set_name: &str, item_name: &str, content: &str) -> PyResult<Item> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    rt.block_on(create_item(set_name.to_string(), item_name.to_string(), content.to_string()))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn py_add_item_from_json(item_json: &str) -> PyResult<bool> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    rt.block_on(add_item_from_json(item_json.to_string()))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn py_add_item(item: &Item) -> PyResult<bool> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    rt.block_on(add_item(item))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

// Wrappers PyO3 para actualización de contenido
#[pyfunction]
fn py_update_item_content_by_id(set_name: &str, uuid_id: &str, content_json: &str) -> PyResult<bool> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    rt.block_on(update_item_content_by_id(
        set_name.to_string(),
        uuid_id.to_string(),
        content_json.to_string(),
    ))
    .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction]
fn py_update_item_content_by_name(set_name: &str, item_name: &str, content_json: &str) -> PyResult<bool> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    rt.block_on(update_item_content_by_name(
        set_name.to_string(),
        item_name.to_string(),
        content_json.to_string(),
    ))
    .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pyfunction(signature = (set_name, uuid_id=None, item_name=None))]
fn py_find_item_in_set(set_name: &str, uuid_id: Option<&str>, item_name: Option<&str>) -> PyResult<Item> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    let uid = uuid_id.map(|s| s.to_string());
    let name = item_name.map(|s| s.to_string());
    rt.block_on(find_item_in_set(set_name.to_string(), uid, name))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

// Leer un Set completo y retornarlo como objeto Python (Set)
#[pyfunction]
fn py_read_set(set_name: &str) -> PyResult<Set> {
    let rt = tokio::runtime::Runtime::new().map_err(|e| PyRuntimeError::new_err(e.to_string()))?;
    rt.block_on(read_data(set_name.to_string()))
        .map_err(|e| PyRuntimeError::new_err(e.to_string()))
}

#[pymethods]
impl Item {
    fn __repr__(&self) -> String {
        format!(
            "Item(uuid_id='{}', set_name='{}', item_name='{}')",
            self.uuid_id, self.set_name, self.item_name
        )
    }

    fn __str__(&self) -> String {
        format!(
            "Item(uuid_id='{}', set_name='{}', item_name='{}')",
            self.uuid_id, self.set_name, self.item_name
        )
    }

    fn update_content(&mut self, new_content: &str) {
        self.content = new_content.to_string();
        self.updated_at = Utc::now().timestamp();
    }

    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(self).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

#[pymethods]
impl Set {
    fn __repr__(&self) -> String {
        format!("Set(name='{}', items={})", self.name, self.content.len())
    }

    fn __str__(&self) -> String {
        format!("Set(name='{}', items={})", self.name, self.content.len())
    }

    fn items(&self, py: Python<'_>) -> PyResult<Vec<Py<Item>>> {
        self.content
            .iter()
            .cloned()
            .map(|it| Py::new(py, it))
            .collect()
    }

    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(self).map_err(|e| PyRuntimeError::new_err(e.to_string()))
    }
}

#[pymodule]
fn encript_storage(_py: Python, m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(py_create_item_from_json, m)?)?;
    m.add_function(wrap_pyfunction!(py_create_item, m)?)?;
    m.add_function(wrap_pyfunction!(py_add_item_from_json, m)?)?;
    m.add_function(wrap_pyfunction!(py_add_item, m)?)?;
    m.add_function(wrap_pyfunction!(py_update_item_content_by_id, m)?)?;
    m.add_function(wrap_pyfunction!(py_update_item_content_by_name, m)?)?;
    m.add_function(wrap_pyfunction!(py_find_item_in_set, m)?)?;
    m.add_function(wrap_pyfunction!(py_read_set, m)?)?;
    m.add_function(wrap_pyfunction!(py_create_set, m)?)?;
    m.add_function(wrap_pyfunction!(py_save_data, m)?)?;
    m.add_class::<Item>()?;
    m.add_class::<Set>()?;
    Ok(())
}