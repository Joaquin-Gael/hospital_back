import click

from rich.console import Console
from rich.traceback import install

from app.storage.main import storage

console = Console()

@click.group()
def cli():
    install(show_locals=True)

@cli.command()
@click.argument("name")
def create_table(name: str):
    console.rule("values")
    console.print(storage.create_table(table_name=name))

@cli.command()
@click.argument("table")
def list_values(table: str):
    console.rule("values")
    console.print(storage.get_all(table_name=table))

@cli.command()
@click.argument("key")
@click.argument("table")
def get(key, table):
    result = storage.get(key=key, table_name=table)
    console.rule("values")
    console.print(result)

@cli.command()
@click.argument("key")
@click.argument("value")
@click.argument("table")
def set(key, value, table):
    result = storage.set(key=key, value=value, table_name=table)
    console.rule("values")
    console.print(result)

@cli.command()
@click.argument("key")
@click.argument("table")
def delete(key, table):
    storage.delete(key=key, table_name=table)
    console.rule("values")
    console.print("Deleted")


if __name__ == "__main__":
    cli()