from pydantic import BaseModel
from typing import Optional, Any, Dict, List

from uuid import UUID, uuid4

from functools import wraps

from datetime import datetime, timedelta

from time import time

from pathlib import Path

import orjson

import os

from app.config import STORAGE_DIR_NAME, GET_CURRENT_TIME

os.environ["PATH_DIR"] = str(Path(__file__).parent / STORAGE_DIR_NAME)
Path(os.environ["PATH_DIR"]).mkdir(parents=True, exist_ok=True)

import encript_storage as es

 

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
            if not table_name:
                try:
                    import inspect
                    sig = inspect.signature(method)
                    bound = sig.bind_partial(self, *args, **kwargs)
                    table_name = bound.arguments.get("table_name")
                except Exception:
                    table_name = None
            if table_name:
                self.purge_expired(table_name)
                self._mark_dirty()
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

class GetItem(BaseModel):
    key: str
    value: Optional[Response] = None

class SetItem(Response):
    key: Optional[str] = None

class Storage(BaseModel):
    tables: Dict[str, Dict[str, Any]] = {}


class Singleton(metaclass=PurgeMeta):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init_storage()
        else:
            pass

        return cls._instance

    def purge_expired(self, table_name: str) -> None:
        try:
            set_obj: es.Set = es.py_read_set(table_name)
        except Exception:
            return
        now = GET_CURRENT_TIME()
        ttl = timedelta(days=30)
        tz = now.tzinfo
        try:
            items = set_obj.items()
            filtered_items = []
            for it in items:
                ca = getattr(it, "created_at", None)
                created = None
                if isinstance(ca, (int, float)):
                    try:
                        created = datetime.fromtimestamp(float(ca), tz=tz)
                    except Exception:
                        created = None
                elif isinstance(ca, str):
                    try:
                        created = datetime.fromtimestamp(float(ca), tz=tz)
                    except Exception:
                        created = None
                if created and (created + ttl) > now:
                    filtered_items.append(orjson.loads(it.to_json()))
            new_set = {"name": set_obj.name, "content": filtered_items}
            es.py_save_data(table_name, orjson.dumps(new_set, default=date_encoder).decode())
        except Exception:
            set_dict = orjson.loads(set_obj.to_json())
            filtered = []
            for it in set_dict.get("content", []):
                ca = it.get("created_at")
                created = None
                if isinstance(ca, (int, float)):
                    try:
                        created = datetime.fromtimestamp(float(ca), tz=tz)
                    except Exception:
                        created = None
                elif isinstance(ca, str):
                    try:
                        created = datetime.fromtimestamp(float(ca), tz=tz)
                    except Exception:
                        created = None
                if created and (created + ttl) > now:
                    filtered.append(it)
            set_dict["content"] = filtered
            es.py_save_data(table_name, orjson.dumps(set_dict, default=date_encoder).decode())

    def __init_storage(self):
        self.data = Storage(tables={})
        self._dirty = False


    def _load(self):
        return None


    def _auto_flush(self):
        return None

    def _mark_dirty(self):
        self._dirty = True

    def create_table(self, table_name: str):
        try:
            es.py_read_set(table_name)
            return None
        except Exception:
            s = es.py_create_set(table_name)
            es.py_save_data(table_name, s.to_json())
            self._mark_dirty()
            return None

    def _get_internal_all(self, table_name: str):
        try:
            set_obj: es.Set = es.py_read_set(table_name)
        except Exception:
            return None
        items_response: List[GetItem] = []
        try:
            for it in set_obj.items():
                key = it.item_name
                payload = it.content
                if isinstance(payload, str):
                    try:
                        payload = orjson.loads(payload)
                    except Exception:
                        payload = {}
                created = payload.get("created")
                updated = payload.get("updated")
                expired = payload.get("expired")
                items_response.append(
                    GetItem(
                        key=key,
                        value=Response(
                            key=key,
                            value=payload.get("value"),
                            expired=datetime.fromisoformat(expired) if isinstance(expired, str) else None,
                            created=datetime.fromisoformat(created) if isinstance(created, str) else None,
                            updated=datetime.fromisoformat(updated) if isinstance(updated, str) else None,
                            id=UUID(payload.get("id")) if isinstance(payload.get("id"), str) else None,
                        )
                    )
                )
        except Exception:
            set_dict = orjson.loads(set_obj.to_json())
            content = set_dict.get("content", [])
            if not content:
                return None
            for it in content:
                key = it.get("item_name")
                payload = it.get("content")
                if isinstance(payload, str):
                    try:
                        payload = orjson.loads(payload)
                    except Exception:
                        payload = {}
                created = payload.get("created")
                updated = payload.get("updated")
                expired = payload.get("expired")
                items_response.append(
                    GetItem(
                        key=key,
                        value=Response(
                            key=key,
                            value=payload.get("value"),
                            expired=datetime.fromisoformat(expired) if isinstance(expired, str) else None,
                            created=datetime.fromisoformat(created) if isinstance(created, str) else None,
                            updated=datetime.fromisoformat(updated) if isinstance(updated, str) else None,
                            id=UUID(payload.get("id")) if isinstance(payload.get("id"), str) else None,
                        )
                    )
                )
        return items_response or None

    def get_all(self, table_name: str = None) -> List[GetItem] | None:
        return self._get_internal_all(table_name=table_name)

    def get(self, key: str, table_name: str) -> GetItem | None:
        try:
            item: es.Item = es.py_find_item_in_set(table_name, item_name=key)
        except Exception:
            return None
        payload = item.content
        if isinstance(payload, str):
            try:
                payload = orjson.loads(payload)
            except Exception:
                payload = {}
        created = payload.get("created")
        updated = payload.get("updated")
        expired = payload.get("expired")
        return GetItem(
            key=item.item_name,
            value=Response(
                key=item.item_name,
                value=payload.get("value"),
                expired=datetime.fromisoformat(expired) if isinstance(expired, str) else None,
                created=datetime.fromisoformat(created) if isinstance(created, str) else None,
                updated=datetime.fromisoformat(updated) if isinstance(updated, str) else None,
                id=UUID(payload.get("id")) if isinstance(payload.get("id"), str) else None,
            )
        )
    
    def get_by_parameter(self, parameter: str, equals: Any, table_name: str) -> GetItem:
        try:
            set_obj: es.Set = es.py_read_set(table_name)
        except Exception:
            raise NoneResultException(f"No exist item whit {parameter} = {equals}")
        try:
            for it in set_obj.items():
                key = it.item_name
                payload = it.content
                if isinstance(payload, str):
                    try:
                        payload = orjson.loads(payload)
                    except Exception:
                        continue
                val = payload.get("value")
                data = val.get(parameter, None) if isinstance(val, dict) else val
                if data is not None and type(data) == type(equals) and data == equals:
                    created = payload.get("created")
                    updated = payload.get("updated")
                    expired = payload.get("expired")
                    return GetItem(
                        key=key,
                        value=Response(
                            key=key,
                            value=val,
                            expired=datetime.fromisoformat(expired) if isinstance(expired, str) else None,
                            created=datetime.fromisoformat(created) if isinstance(created, str) else None,
                            updated=datetime.fromisoformat(updated) if isinstance(updated, str) else None,
                            id=UUID(payload.get("id")) if isinstance(payload.get("id"), str) else None,
                        )
                    )
        except Exception:
            set_dict = orjson.loads(set_obj.to_json())
            for it in set_dict.get("content", []):
                key = it.get("item_name")
                payload = it.get("content")
                if isinstance(payload, str):
                    try:
                        payload = orjson.loads(payload)
                    except Exception:
                        continue
                val = payload.get("value")
                data = val.get(parameter, None) if isinstance(val, dict) else val
                if data is not None and type(data) == type(equals) and data == equals:
                    created = payload.get("created")
                    updated = payload.get("updated")
                    expired = payload.get("expired")
                    return GetItem(
                        key=key,
                        value=Response(
                            key=key,
                            value=val,
                            expired=datetime.fromisoformat(expired) if isinstance(expired, str) else None,
                            created=datetime.fromisoformat(created) if isinstance(created, str) else None,
                            updated=datetime.fromisoformat(updated) if isinstance(updated, str) else None,
                            id=UUID(payload.get("id")) if isinstance(payload.get("id"), str) else None,
                        )
                    )
        raise NoneResultException(f"No exist item whit {parameter} = {equals}")

    def set(self, key = None, value = None, table_name: str = "", long_live: bool = False, short_live: bool = False) -> SetItem:
        if long_live and short_live:
            raise ValueError("Only one of long_live or short_live can be True")
        now = GET_CURRENT_TIME()
        if long_live:
            exp = now + timedelta(days=30)
        elif short_live:
            exp = now + timedelta(minutes=1)
        else:
            exp = now + timedelta(minutes=15)
        item_model = SetItem(
            key=key,
            value=value,
            created=now,
            updated=now,
            id=uuid4(),
            expired=exp
        )
        content_payload = {
            "value": item_model.value,
            "created": item_model.created.isoformat() if item_model.created else None,
            "updated": item_model.updated.isoformat() if item_model.updated else None,
            "expired": item_model.expired.isoformat() if item_model.expired else None,
            "id": str(item_model.id) if item_model.id else None,
        }
        input_json = {
            "set_name": table_name,
            "item_name": key,
            "content": content_payload,
        }
        item = es.py_create_item_from_json(orjson.dumps(input_json, default=date_encoder).decode())
        es.py_add_item(item)
        self._mark_dirty()
        return item_model

    def delete(self, key, table_name: str) -> None:
        try:
            set_obj: es.Set = es.py_read_set(table_name)
        except Exception:
            return
        try:
            items = set_obj.items()
            filtered_items = []
            for it in items:
                if getattr(it, "item_name", None) != key:
                    filtered_items.append(orjson.loads(it.to_json()))
            new_set = {"name": set_obj.name, "content": filtered_items}
            es.py_save_data(table_name, orjson.dumps(new_set, default=date_encoder).decode())
        except Exception:
            set_dict = orjson.loads(set_obj.to_json())
            content = set_dict.get("content", [])
            set_dict["content"] = [it for it in content if it.get("item_name") != key]
            es.py_save_data(table_name, orjson.dumps(set_dict, default=date_encoder).decode())
        self._mark_dirty()

    def clear(self, table_name: str = None) -> None:
        try:
            set_obj = es.py_read_set(table_name)
        except Exception:
            s = es.py_create_set(table_name)
            es.py_save_data(table_name, s.to_json())
            self._mark_dirty()
            return
        set_dict = orjson.loads(set_obj.to_json())
        set_dict["content"] = []
        es.py_save_data(table_name, orjson.dumps(set_dict, default=date_encoder).decode())
        self._mark_dirty()

    def update(self, key, value, table_name, long_live: bool = False) -> None:
        try:
            item: es.Item = es.py_find_item_in_set(table_name, item_name=key)
        except Exception:
            self.set(key=key, value=value, table_name=table_name, long_live=long_live)
            return
        item_dict = orjson.loads(item.to_json())
        payload = item_dict.get("content")
        if isinstance(payload, str):
            try:
                payload = orjson.loads(payload)
            except Exception:
                payload = {}
        now = GET_CURRENT_TIME()
        if long_live:
            exp = now + timedelta(days=30)
        else:
            exp = now + timedelta(minutes=15)
        new_payload = {
            "value": value,
            "created": payload.get("created") if payload.get("created") else now.isoformat(),
            "updated": now.isoformat(),
            "expired": exp.isoformat(),
            "id": str(uuid4()),
        }
        new_item_json = {
            "uuid_id": item_dict.get("uuid_id"),
            "set_name": table_name,
            "item_name": key,
            "content": orjson.dumps(new_payload, default=date_encoder).decode(),
            "created_at": item_dict.get("created_at"),
            "data_type": item_dict.get("data_type") or "st",
        }
        es.py_update_item_content_by_name(table_name, key, orjson.dumps(new_item_json, default=date_encoder).decode())
        self._mark_dirty()