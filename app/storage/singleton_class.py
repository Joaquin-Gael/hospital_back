from pydantic import BaseModel
from typing import Optional, Any, Dict

from uuid import UUID, uuid4

from cachetools import cached, TTLCache
from functools import wraps, singledispatch

from datetime import datetime, timedelta

from time import time

from pathlib import Path

import json

import os

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
        for attr, val in namespace.items():
            if callable(val) and not attr.startswith('_'):
                namespace[attr] = mcs.wrap_with_purge(val)
        return super().__new__(mcs, name, bases, namespace)

    @staticmethod
    def wrap_with_purge(method):
        @wraps(method)
        @timeit
        def wrapper(self, *args, **kwargs):
            keys_to_delete = []
            for key in self.data.items.keys():
                if self.data.items.get(key).expired <= datetime.now():
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self.data.items[key]

            return method(self, *args, **kwargs)
        return wrapper

class FechaEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, UUID):
            return str(o)
        return super().default(o)

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

class Storage(BaseModel):
    items: Dict[str, Item | SetItem]


class Singleton(metaclass=PurgeMeta):
    _instance = None
    _cache = TTLCache(maxsize=100, ttl=timedelta(minutes=15).total_seconds())
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            if not os.path.exists(STORAGE_PATH):
                STORAGE_PATH.touch()
                with open(STORAGE_PATH, "w", encoding="utf-8") as f:
                    json.dump({"items": {}}, f, indent=4)
            cls._instance.data = Storage.parse_file(STORAGE_PATH, content_type="text/json", encoding="utf-8")
        else:
            pass

        return cls._instance

    @cached(_cache)
    def get(self, key) -> GetItem:
        with open(STORAGE_PATH, "r", encoding="utf-8") as f:
            self.data.items = Storage.model_validate_json(f.read()).items
        response = GetItem(
            key=key,
            value=self.data.items.get(key, None)
        )
        return response


    def set(self, key = None, value = None) -> SetItem:
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

        self.data.items[key] = data

        with open(STORAGE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data.model_dump(), f, cls=FechaEncoder, indent=4)

        return data

    def delete(self, key):
        del self.data.items[key]

    def clear(self):
        self.data.items.clear()

    def update(self, key, value):
        self.data.items[key].value = value
        self.data.items[key].updated = datetime.now()