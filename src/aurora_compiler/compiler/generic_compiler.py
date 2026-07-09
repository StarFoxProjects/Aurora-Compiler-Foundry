from __future__ import annotations
from aurora_compiler.models.aurora import AuroraElement, slugify
from aurora_compiler.foundry.templates import base_item


def compile_generic_item(e: AuroraElement, item_type: str = "feat", include_source_name: bool = True, long_source: bool = False) -> dict:
    item = base_item(e.display_name(include_source_name, long_source=long_source), item_type, "icons/svg/book.svg")
    item["system"] = {
        "description": {"value": e.description_html, "chat": ""},
        "source": {"custom": e.source, "book": e.source_code, "page": "", "license": "", "rules": "2014", "revision": 1},
        "identifier": slugify(e.name),
    }
    # Basic skeletons per type so Foundry can open these documents more consistently.
    if item_type == "class":
        item["system"].update({
            "levels": 1,
            "advancement": {},
            "spellcasting": {"progression": "", "ability": "", "preparation": {"formula": ""}},
            "hd": {"denomination": "d6", "spent": 0, "additional": ""},
            "startingEquipment": [],
            "wealth": "",
            "primaryAbility": {"value": [], "all": True},
            "properties": [],
        })
    item["flags"] = {"aurora": {"id": e.id, "source": e.source, "sourceCode": e.source_code, "file": e.file, "type": e.type, "rules": e.rules, "setters": e.setters, "supports": e.supports}}
    return item
