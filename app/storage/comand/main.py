import click

from rich.console import Console
from rich.traceback import install

from app.storage.main import storage

console = Console()

@click.group()
def cli():
    install(show_locals=True)

@cli.command()
@click.argument("key")
def get(key):
    result = storage.get(key)
    console.rule("values")
    console.print(result)

@cli.command()
@click.argument("key")
@click.argument("value")
def set(key, value):
    result = storage.set(key, value)
    console.rule("values")
    console.print(result)

@cli.command()
@click.argument("key")
def delete(key):
    storage.delete(key)
    console.rule("values")
    console.print("Deleted")


if __name__ == "__main__":
    cli()