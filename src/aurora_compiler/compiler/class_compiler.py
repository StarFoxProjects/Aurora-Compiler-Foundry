from __future__ import annotations
import re
from aurora_compiler.models.aurora import AuroraElement, clean_duplicate_name, slugify
from aurora_compiler.foundry.templates import base_item
from aurora_compiler.foundry import advancement as adv
from aurora_compiler.compiler.feature_linker import group_feature_uuids_by_level
from aurora_compiler.compiler.resource_compiler import class_resource_advancements, class_resource_flags

ABILITY_MAP = {
    "strength": "str", "dexterity": "dex", "constitution": "con",
    "intelligence": "int", "wisdom": "wis", "charisma": "cha",
}

SKILL_MAP = {
    "acrobatics": "acr", "animal handling": "ani", "arcana": "arc", "athletics": "ath",
    "deception": "dec", "history": "his", "insight": "ins", "intimidation": "itm",
    "investigation": "inv", "medicine": "med", "nature": "nat", "perception": "prc",
    "performance": "prf", "persuasion": "per", "religion": "rel", "sleight of hand": "slt",
    "stealth": "ste", "survival": "sur",
}

ARMOR_GRANTS = {
    "light armor": "armor:lgt",
    "medium armor": "armor:med",
    "heavy armor": "armor:hvy",
    "shields": "armor:shl",
}

WEAPON_GRANTS = {
    "simple weapons": "weapon:sim",
    "martial weapons": "weapon:mar",
    "daggers": "weapon:sim:dagger",
    "darts": "weapon:sim:dart",
    "slings": "weapon:sim:sling",
    "quarterstaffs": "weapon:sim:quarterstaff",
    "light crossbows": "weapon:sim:lightcrossbow",
    "shortswords": "weapon:mar:shortsword",
    "longswords": "weapon:mar:longsword",
    "rapiers": "weapon:mar:rapier",
    "hand crossbows": "weapon:mar:handcrossbow",
}

FULL_CASTERS = {"bard", "cleric", "druid", "sorcerer", "wizard"}
HALF_CASTERS = {"artificer", "paladin", "ranger"}
PACT_CASTERS = {"warlock"}
CASTING_ABILITY = {
    "artificer": "int", "wizard": "int",
    "cleric": "wis", "druid": "wis", "ranger": "wis",
    "bard": "cha", "paladin": "cha", "sorcerer": "cha", "warlock": "cha",
}
SUBCLASS_LEVELS = {
    "artificer": (3, "Artificer Specialist"),
    "barbarian": (3, "Primal Path"),
    "bard": (3, "Bard College"),
    "cleric": (1, "Divine Domain"),
    "druid": (2, "Druid Circle"),
    "fighter": (3, "Martial Archetype"),
    "monk": (3, "Monastic Tradition"),
    "paladin": (3, "Sacred Oath"),
    "ranger": (3, "Ranger Archetype"),
    "rogue": (3, "Roguish Archetype"),
    "sorcerer": (1, "Sorcerous Origin"),
    "warlock": (1, "Otherworldly Patron"),
    "wizard": (2, "Arcane Tradition"),
    "blood hunter": (3, "Blood Hunter Order"),
    "mystic": (1, "Mystic Order"),
}


def _text(e: AuroraElement) -> str:
    return re.sub(r"<[^>]+>", " ", e.description_html or "")


def _class_slug(e: AuroraElement) -> str:
    return slugify(clean_duplicate_name(e.name).split("(")[0])


def _hit_die(e: AuroraElement) -> str:
    text = _text(e).lower()
    m = re.search(r"hit dice?\s*:?\s*1?d(\d+)", text)
    if not m:
        m = re.search(r"hit die\s*:?\s*d(\d+)", text)
    if m:
        return f"d{m.group(1)}"
    name = _class_slug(e)
    if name in {"wizard", "sorcerer"}:
        return "d6"
    if name in {"barbarian"}:
        return "d12"
    if name in {"fighter", "paladin", "ranger"}:
        return "d10"
    return "d8"


def _saving_throw_grants(e: AuroraElement) -> list[str]:
    text = _text(e).lower()
    m = re.search(r"saving throws?\s*:?\s*([a-z, and]+)", text)
    grants: list[str] = []
    if m:
        for label, short in ABILITY_MAP.items():
            if label in m.group(1):
                grants.append(f"saves:{short}")
    return sorted(set(grants))


def _skill_choice(e: AuroraElement) -> list[dict]:
    text = _text(e).lower()
    m = re.search(r"skills?\s*:?\s*choose\s+(\w+|\d+)\s+from\s+(.+?)(?:\.|equipment|hit points|proficiencies|$)", text, re.S)
    if not m:
        return []
    raw_count = m.group(1)
    count_words = {"one": 1, "two": 2, "three": 3, "four": 4}
    count = int(raw_count) if raw_count.isdigit() else count_words.get(raw_count, 1)
    pool: list[str] = []
    for label, short in SKILL_MAP.items():
        if label in m.group(2):
            pool.append(f"skills:{short}")
    return [{"count": count, "pool": sorted(set(pool))}] if pool else []


def _proficiency_grants(e: AuroraElement) -> list[str]:
    text = _text(e).lower()
    grants: list[str] = []
    for label, grant in ARMOR_GRANTS.items():
        if label in text:
            grants.append(grant)
    for label, grant in WEAPON_GRANTS.items():
        if label in text:
            grants.append(grant)
    # Tool proficiencies are currently too varied; preserve raw Aurora rules in flags until a tool mapper exists.
    return sorted(set(grants))


def _spellcasting(name: str) -> dict:
    if name in FULL_CASTERS:
        progression = "full"
    elif name in HALF_CASTERS:
        progression = "half"
    elif name in PACT_CASTERS:
        progression = "pact"
    else:
        progression = ""
    ability = CASTING_ABILITY.get(name, "")
    formula = ""
    if progression and ability:
        if name in {"artificer", "paladin", "ranger"}:
            formula = f"@abilities.{ability}.mod + ceil(@classes.{name}.levels / 2)"
        elif name in {"cleric", "druid", "wizard"}:
            formula = f"@abilities.{ability}.mod + @classes.{name}.levels"
    return {"progression": progression, "ability": ability, "preparation": {"formula": formula}}


def _cantrip_scale(name: str) -> dict | None:
    known = {
        "artificer": {1: 2, 10: 3, 14: 4},
        "bard": {1: 2, 4: 3, 10: 4},
        "cleric": {1: 3, 4: 4, 10: 5},
        "druid": {1: 2, 4: 3, 10: 4},
        "sorcerer": {1: 4, 4: 5, 10: 6},
        "warlock": {1: 2, 4: 3, 10: 4},
        "wizard": {1: 3, 4: 4, 10: 5},
    }.get(name)
    if known:
        return adv.scale_value(name, "cantrips-known", "Cantrips Known", known)
    return None


def _cantrip_choice_counts(name: str) -> dict[int, int]:
    known = {
        "artificer": {1: 2, 10: 3, 14: 4},
        "bard": {1: 2, 4: 3, 10: 4},
        "cleric": {1: 3, 4: 4, 10: 5},
        "druid": {1: 2, 4: 3, 10: 4},
        "sorcerer": {1: 4, 4: 5, 10: 6},
        "warlock": {1: 2, 4: 3, 10: 4},
        "wizard": {1: 3, 4: 4, 10: 5},
    }.get(name)
    if not known:
        return {}
    previous = 0
    choices: dict[int, int] = {}
    for level, total in sorted(known.items()):
        delta = int(total) - previous
        if delta > 0:
            choices[level] = delta
        previous = int(total)
    return choices


def _advancements(
    e: AuroraElement,
    class_name: str,
    feature_uuid_by_aurora_id: dict[str, str] | None = None,
    artificer_infusion_uuids: list[str] | None = None,
    child_feature_uuids_by_aurora_id: dict[str, list[str]] | None = None,
    class_cantrip_uuids: list[str] | None = None,
) -> tuple[dict, list[str]]:
    seed = f"class:{e.id or e.name}:{e.source_code}"
    out: dict[str, dict] = {}

    def add(doc: dict):
        out[doc["_id"]] = doc

    add(adv.hit_points(seed))

    prof = _proficiency_grants(e)
    if prof:
        add(adv.trait(seed, grants=prof, level=1, title="Proficiencies", class_restriction="primary"))

    saves = _saving_throw_grants(e)
    if saves:
        add(adv.trait(seed, grants=saves, level=1, title="Saving Throws", class_restriction="primary"))

    skill_choices = _skill_choice(e)
    if skill_choices:
        add(adv.trait(seed, choices=skill_choices, level=1, title="Skill Proficiencies", class_restriction="primary"))

    sub = SUBCLASS_LEVELS.get(class_name)
    if sub:
        add(adv.subclass(seed, level=sub[0], title=sub[1]))

    asi_levels = [4, 8, 12, 16, 19]
    if class_name == "fighter":
        asi_levels = [4, 6, 8, 12, 14, 16, 19]
    elif class_name == "rogue":
        asi_levels = [4, 8, 10, 12, 16, 19]
    for lvl in asi_levels:
        add(adv.ability_score_improvement(seed, lvl))

    cantrips = _cantrip_scale(class_name)
    if cantrips:
        add(cantrips)

    # Do not create a custom cantrip ItemChoice advancement. Foundry dnd5e already
    # derives the official cantrip selection UI from spellcasting + Cantrips Known.
    # Adding a second ItemChoice here creates a duplicate empty/partial page before
    # the real official "Cantrips Known" step.

    for resource_adv in class_resource_advancements(seed, class_name):
        add(resource_adv)

    if class_name == "artificer" and artificer_infusion_uuids:
        add(adv.item_choice(
            seed,
            artificer_infusion_uuids,
            choices={2: 4, 6: 2, 10: 2, 14: 2, 18: 2},
            title="Artificer Infusions",
            item_type="feat",
            restriction_type="class",
        ))

    missing_features: list[str] = []
    if feature_uuid_by_aurora_id is not None:
        grouped, missing_features = group_feature_uuids_by_level(e, feature_uuid_by_aurora_id, child_feature_uuids_by_aurora_id)
        for level, uuids in sorted(grouped.items()):
            add(adv.item_grant(seed, uuids, level=level, title="Aurora Feature Grants"))
    return out, missing_features


def compile_class(
    e: AuroraElement,
    include_source_name: bool = True,
    long_source: bool = False,
    feature_uuid_by_aurora_id: dict[str, str] | None = None,
    artificer_infusion_uuids: list[str] | None = None,
    child_feature_uuids_by_aurora_id: dict[str, list[str]] | None = None,
    class_cantrip_uuids: list[str] | None = None,
) -> dict:
    display = e.display_name(include_source_name, long_source=long_source)
    class_name = _class_slug(e)
    item = base_item(display, "class", "icons/svg/book.svg")
    item["system"] = {
        "description": {"value": e.description_html, "chat": ""},
        "source": {"custom": e.source, "book": e.source_code, "page": "", "license": "", "rules": "2014", "revision": 1},
        "identifier": class_name,
        "levels": 1,
        "advancement": {},
        "spellcasting": _spellcasting(class_name),
        "startingEquipment": [],
        "wealth": "",
        "primaryAbility": {"value": [], "all": True},
        "hd": {"denomination": _hit_die(e), "spent": 0, "additional": ""},
        "properties": [],
    }
    advancement, missing_features = _advancements(e, class_name, feature_uuid_by_aurora_id, artificer_infusion_uuids, child_feature_uuids_by_aurora_id, class_cantrip_uuids)
    item["system"]["advancement"] = advancement
    item["flags"] = {"aurora": {"id": e.id, "source": e.source, "sourceCode": e.source_code, "file": e.file, "type": e.type, "rules": e.rules, "setters": e.setters, "supports": e.supports, "compiler": "class-v1.7", "resources": class_resource_flags(class_name), "artificerInfusionChoices": len(artificer_infusion_uuids or []), "cantripChoices": len(class_cantrip_uuids or []), "missingFeatureGrants": missing_features}}
    return item
