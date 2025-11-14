import click
import os
from pathlib import Path
import orjson
from pydantic_core.core_schema import custom_error_schema
from rich.console import Console
from rich.traceback import install
from rich.table import Table
from app.config import STORAGE_DIR_NAME

os.environ["PATH_DIR"] = str(Path(__file__).parent.parent / STORAGE_DIR_NAME)
Path(os.environ["PATH_DIR"]).mkdir(parents=True, exist_ok=True)

import encript_storage as es
from app.storage.main import storage

console = Console()

@click.group()
def cli():
    install(show_locals=True)

@cli.command()
@click.argument("name")
def create_table(name: str):
    console.rule("create-table")
    console.print(storage.create_table(table_name=name))

@cli.command()
def list_sets():
    console.rule("sets")
    path_dir = Path(os.environ.get("PATH_DIR", Path(__file__).parent.parent / "sets"))
    if not path_dir.exists():
        console.print([])
        return
    files = [p.stem for p in path_dir.iterdir() if p.is_file()]
    console.print(files)

@cli.command()
@click.argument("table")
@click.option("json_out", "--json", is_flag=True, default=False)
def view(table: str, json_out: bool):
    console.rule("view")
    items = storage.get_all(table_name=table) or []
    if json_out:
        console.print(orjson.loads(orjson.dumps([i.model_dump() for i in items])))
        return
    t = Table(show_header=True, header_style="bold")
    t.add_column("key")
    t.add_column("created")
    t.add_column("updated")
    t.add_column("expired")
    t.add_column("id")
    t.add_column("value")
    for i in items:
        v = i.value
        val = v.value if v else None
        val_str = str(val)
        if len(val_str) > 120:
            val_str = val_str[:117] + "..."
        t.add_row(
            i.key,
            str(v.created) if v and v.created else "",
            str(v.updated) if v and v.updated else "",
            str(v.expired) if v and v.expired else "",
            str(v.id) if v and v.id else "",
            val_str,
        )
    console.print(t)

@cli.command()
@click.argument("key")
@click.argument("table")
def get(key, table):
    result = storage.get(key=key, table_name=table)
    console.rule("get")
    console.print(result.model_dump() if result else None)

@cli.command()
@click.argument("parameter")
@click.argument("equals")
@click.argument("table")
def find(parameter, equals, table):
    try:
        try:
            equals_parsed = orjson.loads(equals)
        except Exception:
            equals_parsed = equals
        result = storage.get_by_parameter(parameter=parameter, equals=equals_parsed, table_name=table)
        console.rule("find")
        console.print(result.model_dump() if result else None)
    except Exception as e:
        console.print(None)

@cli.command()
@click.argument("key")
@click.argument("value")
@click.argument("table")
@click.option("long_live", "--long-live", is_flag=True, default=False)
@click.option("short_live", "--short-live", is_flag=True, default=False)
def set(key, value, table, long_live, short_live):
    try:
        value_parsed = orjson.loads(value)
    except Exception:
        value_parsed = value
    result = storage.set(key=key, value=value_parsed, table_name=table, long_live=long_live, short_live=short_live)
    console.rule("set")
    console.print(result.model_dump())

@cli.command()
@click.argument("key")
@click.argument("table")
def delete(key, table):
    storage.delete(key=key, table_name=table)
    console.rule("delete")
    console.print("ok")

@cli.command()
@click.argument("table")
def clear(table):
    storage.clear(table_name=table)
    console.rule("clear")
    console.print("ok")

@cli.command()
@click.argument("table")
def purge(table):
    storage.purge_expired(table_name=table)
    console.rule("purge")
    console.print("ok")

@cli.command()
@click.argument("table")
def dump_raw(table):
    console.rule("raw")
    current_set: es.Set = es.py_read_set(set_name=table)
    for item in current_set.items():
        console.print(item.content)

if __name__ == "__main__":
    cli()