from pydantic import BaseModel
from typing import Optional, Any, Dict, List

from uuid import UUID, uuid4

from functools import wraps

from datetime import datetime, timedelta

from time import time

from pathlib import Path

import json

import os

from app.config import STORAGE_DIR_NAME, GET_CURRENT_TIME, console

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


class Singleton:
    _instance = None
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.__init_storage()
        return cls._instance

    @timeit
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
            original_len = 0
            filtered_items = []
            for it in items:
                original_len += 1
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
                    filtered_items.append(json.loads(it.to_json()))
            if len(filtered_items) != original_len:
                new_set = {"name": set_obj.name, "content": filtered_items}
                es.py_save_data(table_name, json.dumps(new_set, default=date_encoder))
        except Exception:
            set_dict = json.loads(set_obj.to_json())
            content = set_dict.get("content", [])
            original_len = len(content) if isinstance(content, list) else 0
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
            if len(filtered) != original_len:
                set_dict["content"] = filtered
                es.py_save_data(table_name, orjson.dumps(set_dict, default=date_encoder).decode())

    def __init_storage(self):
        self.data = Storage(tables={})

    def _load(self):
        return None


    def _auto_flush(self):
        return None

    

    def create_table(self, table_name: str):
        try:
            es.py_read_set(table_name)
            return None
        except Exception:
            s = es.py_create_set(table_name)
            es.py_save_data(table_name, s.to_json())
            return None

    def _get_internal_all(self, table_name: str) -> List[GetItem] | None:
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
                expired = it.expired_at
                created = it.created_at
                updated = it.updated_at
                items_response.append(
                    GetItem(
                        key=key,
                        value=Response(
                            key=key,
                            value=payload.get("value"),
                            expired=datetime.fromisoformat(expired) if expired else None,
                            created=datetime.fromisoformat(created) if created else None,
                            updated=datetime.fromisoformat(updated) if updated else None,
                            id=UUID(it.uuid_id),
                        )
                    )
                )
        except Exception:
            set_dict = json.loads(set_obj.to_json())
            content = set_dict.get("content", None)
            if not content:
                return None
            for it in content:
                key = it.item_name
                payload = it.content
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = {}
                created = it.created_at
                updated = it.updated_at
                expired = it.expired_at
                items_response.append(
                    GetItem(
                        key=key,
                        value=Response(
                            key=key,
                            value=payload.get("value"),
                            expired=datetime.fromisoformat(expired) if expired else None,
                            created=datetime.fromisoformat(created) if created else None,
                            updated=datetime.fromisoformat(updated) if updated else None,
                            id=UUID(it.uuid_id),
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
            raise NoneResultException(f"No exist set whit name = {table_name}")
        try:
            for it in set_obj.items():
                key = it.item_name
                payload = it.content
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        continue
                data = payload.get(parameter, None) if isinstance(payload, dict) else payload
                if data is not None and type(data) == type(equals) and data == equals:
                    created = it.created_at
                    updated = it.updated_at
                    expired = it.expired_at
                    return GetItem(
                        key=key,
                        value=Response(
                            key=key,
                            value=val,
                            expired=datetime.fromtimestamp(expired) if expired else None,
                            created=datetime.fromtimestamp(created) if created else None,
                            updated=datetime.fromtimestamp(updated) if updated else None,
                            id=UUID(payload.get("id")) if isinstance(payload.get("id"), str) else None,
                        )
                    )
        except Exception:
            set_dict = json.loads(set_obj.to_json())
            for it in set_dict.get("content", []):
                key = it.get("item_name")
                payload = it.get("content")
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        continue
                val = payload.get("value")
                data = val.get(parameter, None) if isinstance(val, dict) else val
                if data is not None and type(data) == type(equals) and data == equals:
                    created = it.created_at
                    updated = it.updated_at
                    expired = it.expired_at
                    return GetItem(
                        key=key,
                        value=Response(
                            key=key,
                            value=val,
                            expired=datetime.fromtimestamp(expired) if expired else None,
                            created=datetime.fromtimestamp(created) if created else None,
                            updated=datetime.fromtimestamp(updated) if updated else None,
                            id=UUID(payload.get("id")) if isinstance(payload.get("id"), str) else None,
                        )
                    )
        raise NoneResultException(f"No exist item whit {parameter} = {equals}")

    def set(self, key = None, value = None, table_name: str = "") -> GetItem:

        match type(value):
            case dict:
                value = json.dumps(value)

        item = es.py_create_item(
            set_name=table_name,
            item_name=key,
            content=value,
        )
        try:
            es.py_add_item(item)
        except Exception:
            console.print(f"Error to set item {key} in set {table_name} item already exist or another thing")
            pass
        item_model = GetItem(
            key=key,
            value=Response(
                key=key,
                value=value,
                expired=datetime.fromtimestamp(item.expired_at) if item.expired_at else None,
                created=datetime.fromtimestamp(item.created_at) if item.created_at else None,
                updated=datetime.fromtimestamp(item.updated_at) if item.updated_at else None,
                id=UUID(item.uuid_id),
            )
        )

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

    def clear(self, table_name: str = None) -> None:
        try:
            set_obj = es.py_read_set(table_name)
        except Exception:
            s = es.py_create_set(table_name)
            es.py_save_data(table_name, s.to_json())
            return
        set_dict = json.loads(set_obj.to_json())
        set_dict["content"] = []
        es.py_save_data(table_name, json.dumps(set_dict, default=date_encoder))

    def update(self, key, value, table_name) -> None:
        try:
            item: es.Item = es.py_find_item_in_set(table_name, item_name=key)
        except Exception:
            self.set(key=key, value=value, table_name=table_name)
            return
        
        match type(value):
            case dict:
                value = json.dumps(value)

        es.py_update_item_content_by_name(
            table_name=table_name,
            item_name=key,
            content=value,
        )