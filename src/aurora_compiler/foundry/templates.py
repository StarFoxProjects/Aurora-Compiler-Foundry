from __future__ import annotations
import time, hashlib

def stable_id(seed: str, n: int = 16) -> str:
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:n]


def base_item(name: str, item_type: str, img: str = "icons/svg/book.svg") -> dict:
    return {
        "_id": stable_id(f"{item_type}:{name}"),
        "name": name,
        "type": item_type,
        "img": img,
        "system": {},
        "effects": [],
        "folder": None,
        "flags": {},
        "_stats": {
            "coreVersion": "14.364",
            "systemId": "dnd5e",
            "systemVersion": "5.3.3",
            "createdTime": int(time.time() * 1000),
            "modifiedTime": int(time.time() * 1000),
        },
        "ownership": {"default": 0},
    }
