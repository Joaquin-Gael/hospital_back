from pydantic import BaseModel
from typing import Optional, Any, Dict, List

from uuid import UUID, uuid4

from cachetools import cached, TTLCache
from functools import wraps

from datetime import datetime, timedelta

from time import time

from pathlib import Path

from rich.console import Console

import orjson

#import mmap TODO implementar

import threading

console = Console()

STORAGE_PATH: Path = (Path(__file__).parent / "storage.json").resolve()

class NoneResultException(Exception):
    def __init__(self, message: str = "Result is None"):
        self.message = message
        super().__init__(self.message)

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
    ignore_methods = {"__init__", "__new__", "create_table", "purge_expired"}

    def __new__(mcs, name, bases, namespace):
        for attr, val in namespace.items():
            if callable(val) and not attr.startswith('_') and attr not in mcs.ignore_methods:
                namespace[attr] = mcs.wrap_with_purge(val)
        return super().__new__(mcs, name, bases, namespace)

    @staticmethod
    def wrap_with_purge(method):
        from functools import wraps
        @wraps(method)
        @timeit
        def wrapper(self, *args, **kwargs):
            table_name = kwargs.get("table_name")
            if table_name:
                self.purge_expired(table_name)
            return method(self, *args, **kwargs)
        return wrapper

def date_encoder(o):
    if isinstance(o, datetime):
        return o.isoformat()
    if isinstance(o, UUID):
        return str(o)
    return o

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
            cls._instance.__init_storage()
        else:
            pass

        return cls._instance

    def purge_expired(self, table_name: str) -> None:
        items = self._get_internal_all(table_name=table_name)
        if items is None:
            return
        now = datetime.now()
        self.data.tables[table_name].items = {
            item.key: item.value for item in items
            if item.value.expired > now
        }

    def __init_storage(self):
        self._lock = threading.Lock()
        self._flush_event = threading.Event()
        self.data = None
        self._dirty = False
        if not STORAGE_PATH.exists():
            STORAGE_PATH.touch()
            STORAGE_PATH.write_bytes(orjson.dumps({"tables": {}}, default=str))
        self._load()

        t = threading.Thread(target=self._auto_flush, daemon=True)
        t.start()


    def _load(self):
        raw = STORAGE_PATH.read_bytes()
        self.data = Storage.model_validate_json(raw)


    def _auto_flush(self):
        while True:
            self._flush_event.wait(timeout=1)
            with self._lock:
                if self._dirty:
                    data_bytes = orjson.dumps(self.data.model_dump(), default=date_encoder)
                    STORAGE_PATH.write_bytes(data_bytes)
                    self._dirty = False
                # Resetea el evento
                self._flush_event.clear()

    def _mark_dirty(self):
        with self._lock:
            self._dirty = True
            self._flush_event.set()

    def create_table(self, table_name: str):
        self._load()
        if table_name in self.data.tables:
            return None
        table = Table(
            name=table_name,
            items={}
        )
        self.data.tables[table_name] = table
        console.print(self.data)
        self._mark_dirty()
        return table

    def _get_internal_all(self, table_name: str):
        self._load()
        items = self.data.tables.get(table_name, {}).items
        if not items:
            return None

        items_response = []
        for item in items.values():
            console.print(item)
            items_response.append(
                GetItem(
                    key=item.key,
                    value=Response(
                        key=item.key,
                        value=item.value,
                        expired=item.expired,
                        created=item.created,
                        updated=item.updated,
                        id=item.id
                    )
                )
            )

        return items_response

    @cached(_cache)
    def get_all(self, table_name: str = None) -> List[GetItem] | None:
        self._load()
        items = self.data.tables.get(table_name, {}).items
        if not items:
            return None

        items_response = []
        for item in items.values():
            items_response.append(
                GetItem(
                    key=item.key,
                    value=Response(
                        key=item.key,
                        value=item.value,
                        expired=item.expired,
                        created=item.created,
                        updated=item.updated,
                        id=item.id
                    )
                )
            )

        return items_response

    @cached(_cache)
    def get(self, key: str, table_name: str) -> GetItem | None:
        self._load()
        item = self.data.tables[table_name].items.get(key, None)
        if not item:
            return None
        return GetItem(
            key=item.key,
            value=Response(
                key=item.key,
                value=item.value,
                expired=item.expired,
                created=item.created,
                updated=item.updated,
                id=item.id
            )
        )
    
    def get_by_parameter(self, parameter: str, equals: Any, table_name: str) -> GetItem:
        self._load()
        for item in self.data.tables[table_name].items.values():
            console.print(item)
            data = item.value.get(parameter, None)
            if data:
                if type(data) == type(equals) and data == equals:
                    return GetItem(key=item.key, value=item)
                else:
                    continue
        raise NoneResultException(f"No exist item whit {parameter} = {equals}")

    def set(self, key = None, value = None, table_name: str = "", long_live: bool = False) -> SetItem:
        item = SetItem(
            key=key,
            value=value,
            created=datetime.now(),
            updated=datetime.now(),
            id=uuid4(),
            expired=datetime.now() + timedelta(minutes=15) if not long_live else datetime.now() + timedelta(days=30)
        )
        self.data.tables[table_name].items[key] = item
        self._mark_dirty()
        return item

    def delete(self, key, table_name: str) -> None:
        del self.data.tables[table_name].items[key]
        self._mark_dirty()

    def clear(self, table_name: str = None) -> None:
        self.data.tables[table_name].clear()
        self._mark_dirty()

    def update(self, key, value, table_name, long_live: bool = False) -> None:
        item = self.get(key, table_name)
        if item is None:
            self.set(key, value, table_name)
            return
        item = SetItem(
            key=item.key,
            value=item.value,
            created=item.value.created,
            updated=datetime.now(),
            id=uuid4(),
            expired=datetime.now() + timedelta(minutes=15) if not long_live else datetime.now() + timedelta(days=30)
        )
        self.data.tables[table_name].items[key] = item
        self._mark_dirty()