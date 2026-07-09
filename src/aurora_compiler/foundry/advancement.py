from __future__ import annotations
from aurora_compiler.foundry.templates import stable_id


def _id(seed: str) -> str:
    return stable_id(seed, 16)


def hit_points(seed: str) -> dict:
    return {
        "_id": _id(f"{seed}:hp"),
        "type": "HitPoints",
        "configuration": {},
        "value": {},
        "title": "Hit Points",
        "icon": "systems/dnd5e/icons/svg/hit-points.svg",
        "flags": {},
        "hint": "",
    }


def trait(seed: str, grants: list[str] | None = None, choices: list[dict] | None = None, level: int = 1, title: str = "", class_restriction: str | None = None) -> dict:
    doc = {
        "_id": _id(f"{seed}:trait:{title}:{level}:{','.join(grants or [])}"),
        "type": "Trait",
        "configuration": {
            "mode": "default",
            "allowReplacements": False,
            "grants": grants or [],
            "choices": choices or [],
        },
        "level": level,
        "title": title,
        "value": {"chosen": []},
        "flags": {},
        "hint": "",
    }
    if class_restriction:
        doc["classRestriction"] = class_restriction
    return doc


def item_grant(seed: str, uuids: list[str], level: int, title: str = "Features", optional: bool = False) -> dict:
    return {
        "_id": _id(f"{seed}:grant:{level}:{title}:{','.join(uuids)}"),
        "type": "ItemGrant",
        "configuration": {
            "items": [{"uuid": u, "optional": optional} for u in uuids],
            "optional": optional,
            "spell": {
                "ability": [],
                "uses": {"max": "", "per": "", "requireSlot": False},
                "prepared": 0,
            },
        },
        "value": {},
        "level": level,
        "title": title,
        "flags": {},
        "hint": "",
    }


def ability_score_improvement(seed: str, level: int, title: str = "Ability Score Improvement") -> dict:
    return {
        "_id": _id(f"{seed}:asi:{level}"),
        "type": "AbilityScoreImprovement",
        "configuration": {
            "points": 2,
            "fixed": {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0},
            "cap": 2,
            "locked": [],
            "recommendation": None,
        },
        "value": {},
        "level": level,
        "title": title,
        "flags": {},
        "hint": "",
    }


def subclass(seed: str, level: int, title: str) -> dict:
    return {
        "_id": _id(f"{seed}:subclass:{level}:{title}"),
        "type": "Subclass",
        "configuration": {},
        "value": {"document": None, "uuid": None},
        "level": level,
        "title": title,
        "flags": {},
        "hint": "",
    }


def scale_value(seed: str, identifier: str, title: str, scale: dict[int, int | str]) -> dict:
    return {
        "_id": _id(f"{seed}:scale:{identifier}"),
        "type": "ScaleValue",
        "configuration": {
            "identifier": identifier,
            "type": "number" if all(isinstance(v, int) for v in scale.values()) else "string",
            "distance": {"units": ""},
            "scale": {str(k): {"value": v} for k, v in sorted(scale.items())},
        },
        "value": {},
        "title": title,
        "flags": {},
        "hint": "",
    }


def size_advancement(seed: str, sizes: list[str] | None = None, title: str = "Size") -> dict:
    sizes = sizes or ["med"]
    return {
        "_id": _id(f"{seed}:size:{','.join(sizes)}"),
        "type": "Size",
        "configuration": {"sizes": sizes},
        "value": {"size": sizes[0] if len(sizes) == 1 else None},
        "title": title,
        "icon": "systems/dnd5e/icons/svg/size.svg",
        "flags": {},
        "hint": "",
    }


def species_ability_score_improvement(seed: str, fixed: dict[str, int] | None = None, points: int = 0, title: str = "Ability Score Increase") -> dict:
    """Create a species/race ASI advancement.

    For Foundry's advancement manager the item document should describe the
    fixed bonuses and unassigned points in `configuration`, while `value` stays
    empty until the item is dropped on an actor. If `value.assignments` is
    pre-filled on the compendium item, Foundry can treat the advancement as
    already completed without applying the actor update. This mirrors the
    official class ASI pattern: config first, actor value after apply.
    """
    normalized = {"str": 0, "dex": 0, "con": 0, "int": 0, "wis": 0, "cha": 0}
    normalized.update({k: int(v) for k, v in (fixed or {}).items() if k in normalized})
    locked = [k for k, v in normalized.items() if v]
    return {
        "_id": _id(f"{seed}:species-asi:{points}:{','.join(f'{k}{v}' for k, v in sorted(normalized.items()) if v)}"),
        "type": "AbilityScoreImprovement",
        "configuration": {
            "points": max(0, int(points or 0)),
            "fixed": normalized,
            "cap": 2,
            "locked": locked,
            "recommendation": None,
        },
        "value": {},
        "level": 1,
        "title": title,
        "flags": {"auroraCompiler": {"kind": "species-asi", "fixed": normalized, "points": points}},
        "hint": "Ability score increase compiled from Aurora race/species rules.",
    }


def fixed_ability_score_improvement(seed: str, fixed: dict[str, int], title: str = "Ability Score Increase") -> dict:
    return species_ability_score_improvement(seed, fixed=fixed, points=0, title=title)


def item_choice(seed: str, uuids: list[str], choices: dict[int, int], title: str = "Item Choices", item_type: str = "feat", restriction_type: str = "", restriction_subtype: str = "") -> dict:
    """Create an ItemChoice advancement.

    Used for Artificer Infusions and similar class feature picks.
    `choices` maps character level -> number of new items to choose at that level.
    """
    clean_uuids = []
    for u in uuids or []:
        if u and u not in clean_uuids:
            clean_uuids.append(u)
    normalized_choices = {str(int(level)): {"count": int(count), "replacement": False}
                          for level, count in sorted((choices or {}).items()) if int(count) > 0}
    return {
        "_id": _id(f"{seed}:item-choice:{title}:{','.join(clean_uuids[:20])}:{len(clean_uuids)}"),
        "type": "ItemChoice",
        "configuration": {
            "allowDrops": True,
            "choices": normalized_choices,
            "pool": [{"uuid": u} for u in clean_uuids],
            "restriction": {
                "level": "",
                "list": [],
                "subtype": restriction_subtype,
                "type": restriction_type,
            },
            "spell": None,
            "type": item_type,
        },
        "value": {"added": {}, "replaced": {}},
        "title": title,
        "flags": {"auroraCompiler": {"kind": "item-choice", "poolSize": len(clean_uuids)}},
        "hint": "Choose from compiler-generated Aurora items in this compendium.",
    }
