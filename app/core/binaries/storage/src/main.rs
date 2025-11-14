use std::fs;
use std::path::Path;

use clap::{Parser, Subcommand};
use encript_storage::{
    Item,
    create_set, read_data, save_data,
    add_item,
    find_item_in_set,
    update_item_content_by_id, update_item_content_by_name,
};

#[derive(Parser, Debug)]
#[command(name = "encript_storage_cli", version, about = "CLI para gestionar Sets e Items encriptados")]
struct Cli {
    /// Directorio donde se guardan los archivos (PATH_DIR)
    #[arg(long, global = true, default_value = "storage")]
    dir: String,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    /// Operaciones sobre Sets
    Set {
        #[command(subcommand)]
        command: SetCommands,
    },
    /// Operaciones sobre Items
    Item {
        #[command(subcommand)]
        command: ItemCommands,
    },
}

#[derive(Subcommand, Debug)]
enum SetCommands {
    /// Crear un Set vacío
    Create { name: String },
    /// Leer un Set desde disco y mostrarlo
    Read { name: String },
    /// Guardar JSON (del Set) directamente en disco
    Save { name: String, #[arg(long)] json: String },
}

#[derive(Subcommand, Debug)]
enum ItemCommands {
    /// Crear un Item a partir de contenido JSON; opcionalmente guardarlo
    Create {
        #[arg(long)] set: String,
        #[arg(long)] name: String,
        /// Contenido JSON (inline o ruta a archivo)
        #[arg(long)] content: String,
        /// Si se indica, se inserta el item en el Set
        #[arg(long, default_value_t = false)] save: bool,
    },
    /// Añadir un Item leyendo su JSON completo (inline o archivo)
    AddJson {
        /// JSON del Item (inline o ruta a archivo)
        #[arg(long)] json: String,
    },
    /// Buscar un Item por id y/o nombre dentro de un Set
    Find {
        set: String,
        #[arg(long)] id: Option<String>,
        #[arg(long)] name: Option<String>,
    },
    /// Actualizar solo el contenido de un Item (por id o nombre)
    UpdateContent {
        set: String,
        #[arg(long)] id: Option<String>,
        #[arg(long)] name: Option<String>,
        /// Contenido JSON (inline o ruta a archivo)
        #[arg(long)] content: String,
    },
    /// Reemplazar un Item usando su JSON completo (por id o nombre)
    UpdateJson {
        set: String,
        #[arg(long)] id: Option<String>,
        #[arg(long)] name: Option<String>,
        /// JSON completo del Item (inline o ruta a archivo)
        #[arg(long)] json: String,
    },
}

#[tokio::main]
async fn main() {
    if let Err(e) = run().await {
        eprintln!("Error: {e}");
        std::process::exit(1);
    }
}

async fn run() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    // Configurar PATH_DIR y asegurar el directorio
    unsafe {
        std::env::set_var("PATH_DIR", &cli.dir);
    }
    fs::create_dir_all(&cli.dir)?;

    match cli.command {
        Commands::Set { command: cmd } => match cmd {
            SetCommands::Create { name } => {
                let set = create_set(name).await?;
                println!("{}", serde_json::to_string_pretty(&set)?);
            }
            SetCommands::Read { name } => {
                let set = read_data(name).await?;
                println!("{}", serde_json::to_string_pretty(&set)?);
            }
            SetCommands::Save { name, json } => {
                let json_str = resolve_json_arg(&json)?;
                let ok = save_data(json_str, name).await?;
                println!("saved={}", ok);
            }
        },
        Commands::Item { command: cmd } => match cmd {
            ItemCommands::Create { set, name, content, save } => {
                let content_value: serde_json::Value = serde_json::from_str(&resolve_json_arg(&content)?)?;
                let item = Item::new(set.clone(), name, serde_json::to_string(&content_value)?).await;
                println!("{}", serde_json::to_string_pretty(&item)?);
                if save {
                    let ok = add_item(&item).await?;
                    eprintln!("inserted={}", ok);
                }
            }
            ItemCommands::AddJson { json } => {
                let json_str = resolve_json_arg(&json)?;
                let item: Item = serde_json::from_str(&json_str)?;
                let ok = add_item(&item).await?;
                println!("inserted={}", ok);
            }
            ItemCommands::Find { set, id, name } => {
                let item = find_item_in_set(set, id, name).await?;
                println!("{}", serde_json::to_string_pretty(&item)?);
            }
            ItemCommands::UpdateContent { set, id, name, content } => {
                let content_value: serde_json::Value = serde_json::from_str(&resolve_json_arg(&content)?)?;
                // Recuperar el item actual y actualizar su contenido usando la estructura
                let mut item = find_item_in_set(set.clone(), id.clone(), name.clone()).await?;
                item.content = serde_json::to_string(&content_value)?;
                // Garantizamos set_name consistente
                item.set_name = set.clone();
                let item_json = serde_json::to_string(&item)?;
                let ok = match (id, name) {
                    (Some(uid), _) => update_item_content_by_id(set, uid, item_json).await?,
                    (None, Some(nm)) => update_item_content_by_name(set, nm, item_json).await?,
                    _ => return Err("Debe indicar --id o --name".into()),
                };
                println!("updated={}", ok);
            }
            ItemCommands::UpdateJson { set, id, name, json } => {
                let json_str = resolve_json_arg(&json)?;
                let mut item: Item = serde_json::from_str(&json_str)?;
                // Alinear el set_name con el argumento del comando
                item.set_name = set.clone();
                let item_json = serde_json::to_string(&item)?;
                let ok = match (id, name) {
                    (Some(uid), _) => update_item_content_by_id(set, uid, item_json).await?,
                    (None, Some(nm)) => update_item_content_by_name(set, nm, item_json).await?,
                    _ => return Err("Debe indicar --id o --name".into()),
                };
                println!("updated={}", ok);
            }
        },
    }

    Ok(())
}

/// Si el argumento apunta a un archivo existente, lee su contenido.
/// De lo contrario, retorna la cadena tal cual (se asume JSON inline).
fn resolve_json_arg(arg: &str) -> Result<String, Box<dyn std::error::Error>> {
    let p = Path::new(arg);
    if p.exists() && p.is_file() {
        let s = fs::read_to_string(p)?;
        Ok(s)
    } else {
        Ok(arg.to_string())
    }
}