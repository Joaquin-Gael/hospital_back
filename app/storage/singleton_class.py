from pydantic import BaseModel
from typing import Optional, Any, Dict

from uuid import UUID, uuid4

from cachetools import cached, TTLCache
from functools import wraps, singledispatch

from datetime import datetime, timedelta

from time import time

from pathlib import Path

from rich.console import Console

import json

import os

console = Console()

STORAGE_PATH: Path = (Path(__file__).parent / "storage.json").resolve()

def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time()
        result = func(*args, **kwargs)
        end = time()
        print(f"Function {func.__name__!r} executed in {(end-start):.4f}s")
        return result
    return wrapper

class PurgeMeta(type):
    def __new__(mcs, name, bases, namespace):
        ignore_methods = ["__init__", "__new__", "create_table"]
        for attr, val in namespace.items():
            if callable(val) and not attr.startswith('_') and attr not in ignore_methods:
                namespace[attr] = mcs.wrap_with_purge(val)
        return super().__new__(mcs, name, bases, namespace)

    @staticmethod
    def wrap_with_purge(method):
        @wraps(method)
        @timeit
        def wrapper(self, *args, **kwargs):
            table_name = kwargs.get("table_name")
            keys_to_delete = []
            for key in self.data.tables[table_name].items.keys():
                if self.data.tables[table_name].items.get(key).expired <= datetime.now():
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.data.tables[table_name].items[key]

            return method(self, *args, **kwargs)
        return wrapper

class FechaEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, UUID):
            return str(o)
        return super().default(o)

# NOTE: Posible deprecacion
@singledispatch
def parse_value(value):
    """Por defecto, no hacemos nada."""
    return value

@parse_value.register
def _(value: str):
    """Intentamos convertir cadenas a datetime o UUID."""
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        pass
    return value

def response_hook(dct: Dict[str, Any]) -> Any:
    converted = {
        key: parse_value(val)
        for key, val in dct.items()
    }

    expected = {"key", "value", "expired", "created", "updated"}
    if expected.issubset(converted):
        return Response(**converted)

    return converted

class Response(BaseModel):
    key: str
    value: Any
    expired: Optional[datetime] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None
    id: Optional[UUID] = None

class Item(Response):
    pass

class GetItem(BaseModel):
    key: str
    value: Optional[Response] = None

class SetItem(Response):
    key: Optional[str] = None

class Table(BaseModel):
    name: str
    items: Optional[Dict[str, Item | SetItem]]

class Storage(BaseModel):
    tables: Dict[str, Table]


class Singleton(metaclass=PurgeMeta):
    _instance = None
    _cache = TTLCache(maxsize=100, ttl=timedelta(minutes=15).total_seconds())
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if not os.path.exists(STORAGE_PATH):
                STORAGE_PATH.touch()
                with open(STORAGE_PATH, "w", encoding="utf-8") as f:
                    json.dump({"tables": {}}, f, indent=4)
            cls._instance.data = Storage.parse_file(STORAGE_PATH, content_type="text/json", encoding="utf-8")
        else:
            pass

        return cls._instance

    def create_table(self, table_name: str):
        with open(STORAGE_PATH, "w", encoding="utf-8") as f:
            new_table = Table(name=table_name, items={})
            self.data.tables[table_name] = new_table
            json.dump(self.data.model_dump(), f, cls=FechaEncoder, indent=4)

        return self.data.tables[table_name]

    @cached(_cache)
    def get_all(self, table_name: str = None) -> Dict[Any, Any]:
        with open(STORAGE_PATH, "r", encoding="utf-8") as f:
            self.data.tables = Storage.model_validate_json(f.read()).tables
        return self.data.tables.get(table_name, {}).items

    @cached(_cache)
    def get(self, key: str, table_name: str) -> GetItem | None:
        try:
            with open(STORAGE_PATH, "r", encoding="utf-8") as f:
                self.data.tables = Storage.model_validate_json(f.read()).tables
            response = GetItem(
                key=key,
                value=self.data.tables.get(table_name, {}).items.get(key, None)
            )
            return response
        except Exception:
            console.print_exception(show_locals=True)
            return None


    def set(self, key = None, value = None, table_name: str = "") -> SetItem:
        if value is None:
            raise Exception("value cannot be None.")

        data = SetItem(
            id=uuid4(),
            key=key,
            value=value,
            expired=datetime.now() + timedelta(seconds=300),
                created=datetime.now(),
            updated=datetime.now()
        )

        self.data.tables[table_name].items[key] = data

        with open(STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data.model_dump(), f, cls=FechaEncoder, indent=4)

        return data

    def delete(self, key, table_name: str):
        del self.data.tables[table_name].items[key]
        with open(STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data.model_dump(), f, cls=FechaEncoder, indent=4)

    def clear(self, table_name: str = None):
        self.data.tables[table_name].clear()
        with open(STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data.model_dump(), f, cls=FechaEncoder, indent=4)

    def update(self, key, value, table_name):
        self.data.tables[table_name].items[key].value = value
        self.data.tables[table_name].items[key].updated = datetime.now()
        with open(STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data.model_dump(), f, cls=FechaEncoder, indent=4)