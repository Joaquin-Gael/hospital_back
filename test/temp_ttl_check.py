import orjson
from datetime import timedelta

from app.storage.main import storage
from app.config import GET_CURRENT_TIME
import encript_storage as es


def main():
    tbl = "ttl-test"
    storage.create_table(tbl)
    storage.set(key="old", value={"foo": "bar"}, table_name=tbl)

    it = es.py_find_item_in_set(tbl, item_name="old")
    it_dict = orjson.loads(it.to_json())
    new_item_json = {
        "uuid_id": it_dict["uuid_id"],
        "set_name": tbl,
        "item_name": "old",
        "content": it_dict["content"],
        "created_at": int((GET_CURRENT_TIME() - timedelta(days=40)).timestamp()),
        "data_type": it_dict.get("data_type") or "st",
    }
    es.py_update_item_content_by_name(tbl, "old", orjson.dumps(new_item_json).decode())

    storage.set(key="new", value={"foo": "baz"}, table_name=tbl)

    items = storage.get_all(table_name=tbl) or []
    keys = [gi.key for gi in items]
    print("ITEMS", keys)
    assert "old" not in keys and "new" in keys
    print("TTL_PURGE_PASS")


if __name__ == "__main__":
    main()