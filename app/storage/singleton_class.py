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
    ignore_methods = {"__init__", "__new__", "create_table", "purge_expired", "_load", "_auto_flush", "_mark_dirty", "__init_storage", "_get_internal_all"}

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
            # Solo purgar si la tabla existe
            if table_name and table_name in self.data.tables:
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
    _cache = TTLCache(maxsize=100, ttl=timedelta(minutes=1).total_seconds())
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init_storage()
        return cls._instance

    def purge_expired(self, table_name: str) -> None:
        """Elimina items expirados de una tabla"""
        # Validar que la tabla existe
        if table_name not in self.data.tables:
            console.print(f"[yellow]Table '{table_name}' does not exist, skipping purge[/yellow]")
            return
            
        items = self._get_internal_all(table_name=table_name)
        if items is None:
            return
            
        now = datetime.now()
        self.data.tables[table_name].items = {
            item.key: item.value for item in items
            if item.value.expired and item.value.expired > now
        }

    def __init_storage(self):
        self._lock = threading.Lock()
        self._flush_event = threading.Event()
        self.data = None
        self._dirty = False
        
        # Asegurar que el directorio existe
        STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        if not STORAGE_PATH.exists():
            # Crear archivo con estructura inicial válida
            initial_data = {"tables": {}}
            STORAGE_PATH.write_bytes(orjson.dumps(initial_data, default=str))
        
        self._load()

        # Iniciar thread de auto-flush
        t = threading.Thread(target=self._auto_flush, daemon=True)
        t.start()

    def _load(self):
        """Carga los datos desde el archivo JSON"""
        try:
            raw = STORAGE_PATH.read_bytes()
            
            # Si el archivo está vacío o solo tiene espacios en blanco
            if not raw or not raw.strip():
                console.print("[yellow]Storage file is empty, initializing with default structure[/yellow]")
                self.data = Storage(tables={})
                self._mark_dirty()  # Guardar la estructura inicial
                return
            
            # Intentar parsear el JSON
            try:
                self.data = Storage.model_validate_json(raw)
            except Exception as json_error:
                console.print(f"[red]Error parsing JSON: {json_error}[/red]")
                console.print("[yellow]Resetting storage to default structure[/yellow]")
                # Si falla el parseo, crear estructura limpia
                self.data = Storage(tables={})
                self._mark_dirty()
                
        except FileNotFoundError:
            console.print("[yellow]Storage file not found, creating new one[/yellow]")
            self.data = Storage(tables={})
            self._mark_dirty()
        except Exception as e:
            console.print(f"[red]Unexpected error loading storage: {e}[/red]")
            self.data = Storage(tables={})
            self._mark_dirty()

    def _auto_flush(self):
        """Thread que guarda automáticamente los cambios cada segundo si hay cambios pendientes"""
        while True:
            self._flush_event.wait(timeout=1)
            with self._lock:
                if self._dirty:
                    try:
                        data_bytes = orjson.dumps(self.data.model_dump(), default=date_encoder)
                        STORAGE_PATH.write_bytes(data_bytes)
                        self._dirty = False
                        console.print("[green]Storage flushed successfully[/green]")
                    except Exception as e:
                        console.print(f"[red]Error flushing storage: {e}[/red]")
                self._flush_event.clear()

    def _mark_dirty(self):
        """Marca que hay cambios pendientes de guardar"""
        with self._lock:
            self._dirty = True
            self._flush_event.set()

    def create_table(self, table_name: str):
        """Crea una nueva tabla si no existe"""
        # No necesitamos recargar en cada operación si usamos el singleton correctamente
        if table_name in self.data.tables:
            console.print(f"[yellow]Table '{table_name}' already exists[/yellow]")
            return None
        
        table = Table(name=table_name, items={})
        self.data.tables[table_name] = table
        self._mark_dirty()
        console.print(f"[green]Table '{table_name}' created successfully[/green]")
        return table

    def _get_internal_all(self, table_name: str):
        """Método interno para obtener todos los items sin cache"""
        if table_name not in self.data.tables:
            return None
            
        items = self.data.tables[table_name].items
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

    def get_all(self, table_name: str = None) -> List[GetItem] | None:
        """Obtiene todos los items de una tabla (con cache)"""
        if table_name not in self.data.tables:
            return None
            
        items = self.data.tables[table_name].items
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

    def get(self, key: str, table_name: str) -> GetItem | None:
        """Obtiene un item específico por key"""
        # Validar que la tabla existe
        if table_name not in self.data.tables:
            console.print(f"[yellow]Table '{table_name}' does not exist, returning None[/yellow]")
            return None
            
        items = self.data.tables[table_name].items
        if not items or key not in items:
            return None
        
        item = items[key]
        
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
        """Busca un item por un parámetro específico"""
        if table_name not in self.data.tables:
            raise NoneResultException(f"Table '{table_name}' does not exist")
            
        for item in self.data.tables[table_name].items.values():
            data = item.value.get(parameter, None)
            if data is not None:
                if type(data) == type(equals) and data == equals:
                    return GetItem(key=item.key, value=item)
                    
        raise NoneResultException(f"No item found with {parameter} = {equals}")

    def set(self, key=None, value=None, table_name: str = "", long_live: bool = False, short_live: bool = False, auto_create_table: bool = True) -> SetItem:
        """Crea o actualiza un item"""
        # Auto-crear tabla si no existe y auto_create_table es True
        if table_name not in self.data.tables:
            if auto_create_table:
                console.print(f"[yellow]Table '{table_name}' does not exist, creating it automatically[/yellow]")
                self.create_table(table_name)
            else:
                raise ValueError(f"Table '{table_name}' does not exist. Create it first with create_table()")
            
        if long_live and short_live:
            raise ValueError("Only one of long_live or short_live can be True")
        
        # Determinar tiempo de expiración
        if long_live:
            expired = datetime.now() + timedelta(days=30)
        elif short_live:
            expired = datetime.now() + timedelta(minutes=1)
        else:
            expired = datetime.now() + timedelta(minutes=15)
        
        item = SetItem(
            key=key,
            value=value,
            created=datetime.now(),
            updated=datetime.now(),
            id=uuid4(),
            expired=expired
        )
            
        self.data.tables[table_name].items[key] = item
        self._mark_dirty()
        return item

    def delete(self, key, table_name: str) -> None:
        """Elimina un item por key"""
        if table_name not in self.data.tables:
            raise ValueError(f"Table '{table_name}' does not exist")
            
        if key in self.data.tables[table_name].items:
            del self.data.tables[table_name].items[key]
            self._mark_dirty()

    def clear(self, table_name: str = None) -> None:
        """Limpia todos los items de una tabla"""
        if table_name not in self.data.tables:
            raise ValueError(f"Table '{table_name}' does not exist")
            
        self.data.tables[table_name].items.clear()
        self._mark_dirty()

    def update(self, key, value, table_name, long_live: bool = False) -> None:
        """Actualiza un item existente o lo crea si no existe"""
        if table_name not in self.data.tables:
            raise ValueError(f"Table '{table_name}' does not exist")
            
        item: GetItem = self.get(key, table_name)
        
        if item is None:
            # Si no existe, crear uno nuevo
            self.set(key, value, table_name, long_live=long_live)
            return
        
        # Actualizar el existente
        expired = datetime.now() + timedelta(days=30) if long_live else datetime.now() + timedelta(minutes=15)
        
        updated_item = SetItem(
            key=item.key,
            value=value,  # Usar el nuevo valor, no el viejo
            created=item.value.created,
            updated=datetime.now(),
            id=uuid4(),
            expired=expired
        )
        
        self.data.tables[table_name].items[key] = updated_item
        self._mark_dirty()