from __future__ import annotations
import re
from aurora_compiler.models.aurora import AuroraElement, clean_duplicate_name, slugify
from aurora_compiler.foundry.templates import base_item, stable_id

SCHOOLS = {
    "abjuration": "abj", "conjuration": "con", "divination": "div", "enchantment": "enc",
    "evocation": "evo", "illusion": "ill", "necromancy": "nec", "transmutation": "trs"
}

DAMAGE_TYPES = [
    "acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
    "poison", "psychic", "radiant", "slashing", "thunder"
]

SAVE_ABILITIES = {
    "strength": "str", "dexterity": "dex", "constitution": "con", "intelligence": "int", "wisdom": "wis", "charisma": "cha"
}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")

HEAL_WORDS = ["regain hit points", "restore hit points", "heals", "healing", "temporary hit points", "temporary hp"]


def _ability_formula(raw: str) -> str:
    out = raw or ""
    for long, short in SAVE_ABILITIES.items():
        out = re.sub(rf"your\s+{long}\s+modifier", f"@abilities.{short}.mod", out, flags=re.I)
        out = re.sub(rf"{long}\s+modifier", f"@abilities.{short}.mod", out, flags=re.I)
    out = re.sub(r"your\s+spellcasting\s+ability\s+modifier", "@mod", out, flags=re.I)
    out = re.sub(r"your\s+proficiency\s+bonus", "@prof", out, flags=re.I)
    return re.sub(r"\s+", " ", out).strip()


def _runtime_flag(action: str, label: str, formula: str = "", *, damage_type: str = "", save_ability: str = "", target: str = "selected-or-targeted-tokens") -> dict:
    data = {
        "action": action,
        "label": label,
        "formula": formula,
        "target": target,
        "backend": "aurora-runtime-js-v2.8",
    }
    if damage_type:
        data["damageType"] = damage_type
    if save_ability:
        data["saveAbility"] = save_ability
    return {"aurora": {"runtime": data}}


def _damage_formula_from_part(part: dict | None) -> str:
    if not isinstance(part, dict):
        return ""
    custom = part.get("custom", {}) if isinstance(part.get("custom"), dict) else {}
    if custom.get("enabled") and custom.get("formula"):
        return str(custom.get("formula"))
    number = part.get("number")
    denom = part.get("denomination")
    bonus = part.get("bonus") or ""
    if number and denom:
        base = f"{number}d{denom}"
        return f"{base} + {bonus}" if bonus else base
    return str(part.get("formula") or "")


def _parse_healing(e: AuroraElement) -> dict | None:
    text = _strip_html(e.description_html).lower()
    if not any(w in text for w in HEAL_WORDS):
        return None
    heal_type = "temphp" if "temporary" in text else "healing"
    m = re.search(r"(\d+d\d+(?:\s*[+\-]\s*(?:\d+|your\s+\w+\s+modifier|your\s+spellcasting\s+ability\s+modifier|your\s+proficiency\s+bonus))?)", text, flags=re.I)
    formula = _ability_formula(m.group(1)) if m else ""
    if not formula:
        if "proficiency bonus" in text:
            formula = "@prof"
        else:
            for long, short in SAVE_ABILITIES.items():
                if f"{long} modifier" in text:
                    formula = f"@abilities.{short}.mod"
                    break
    if not formula:
        formula = "1"
    return {"number": None, "denomination": None, "bonus": "", "types": [heal_type], "custom": {"enabled": True, "formula": formula}}



def _parse_int(value: str, default: int = 0) -> int:
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _parse_time(raw: str) -> dict:
    raw_l = (raw or "").lower()
    m = re.search(r"(\d+)", raw_l)
    val = int(m.group(1)) if m else 1
    if "bonus" in raw_l:
        unit = "bonus"
    elif "reaction" in raw_l:
        unit = "reaction"
    elif "minute" in raw_l:
        unit = "minute"
    elif "hour" in raw_l:
        unit = "hour"
    else:
        unit = "action"
    return {"value": val, "units": unit, "condition": ""}


def _parse_range(raw: str) -> dict:
    raw_l = (raw or "").strip().lower()
    if not raw_l:
        return {"value": None, "units": "", "special": ""}
    if raw_l == "self" or raw_l.startswith("self "):
        return {"value": None, "units": "self", "special": ""}
    if "touch" in raw_l:
        return {"value": None, "units": "touch", "special": ""}
    m = re.search(r"(\d+)", raw_l)
    value = int(m.group(1)) if m else None
    units = "ft" if any(x in raw_l for x in ["feet", "foot", "ft"]) else "mi" if "mile" in raw_l else ""
    return {"value": value, "units": units, "special": "" if value else raw}


def _parse_duration(raw: str) -> tuple[dict, bool]:
    raw_l = (raw or "").strip().lower()
    concentration = "concentration" in raw_l
    if "instant" in raw_l:
        return {"value": None, "units": "inst", "special": ""}, concentration
    m = re.search(r"(\d+)\s*(round|minute|hour|day)", raw_l)
    if m:
        units = {"round": "round", "minute": "minute", "hour": "hour", "day": "day"}[m.group(2)]
        return {"value": int(m.group(1)), "units": units, "special": ""}, concentration
    return {"value": None, "units": "spec" if raw_l else "", "special": raw}, concentration


def _parse_properties(e: AuroraElement) -> tuple[set[str], dict]:
    properties: set[str] = set()
    materials = {"value": "", "consumed": False, "cost": 0, "supply": 0}

    if e.setter_bool("hasVerbalComponent"):
        properties.add("vocal")
    if e.setter_bool("hasSomaticComponent"):
        properties.add("somatic")
    if e.setter_bool("hasMaterialComponent"):
        properties.add("material")
        materials["value"] = e.setter("materialComponent")
    if e.setter_bool("isRitual"):
        properties.add("ritual")
    if e.setter_bool("isConcentration"):
        properties.add("concentration")
    return properties, materials


def _parse_target_template(e: AuroraElement) -> dict:
    text = f"{e.setter('range')} {_strip_html(e.description_html)}".lower()
    template = {"type": "", "size": "", "width": "", "units": "ft"}
    affects = {"type": "", "count": "", "choice": False, "special": ""}

    # Common 5e wording.
    patterns = [
        ("sphere", r"(\d+)\s*[- ]?foot[- ]radius sphere", "circle"),
        ("sphere", r"(\d+)\s*[- ]?foot sphere", "circle"),
        ("cone", r"(\d+)\s*[- ]?foot cone", "cone"),
        ("cube", r"(\d+)\s*[- ]?foot cube", "rect"),
        ("line", r"(\d+)\s*[- ]?foot[- ]long.*?(\d+)\s*[- ]?foot[- ]wide", "ray"),
        ("cylinder", r"(\d+)\s*[- ]?foot[- ]radius.*?cylinder", "circle"),
    ]
    for _label, pat, foundry_type in patterns:
        m = re.search(pat, text)
        if m:
            template["type"] = foundry_type
            template["size"] = int(m.group(1))
            if foundry_type == "ray" and len(m.groups()) >= 2:
                template["width"] = int(m.group(2))
            return {"template": template, "affects": affects}
    return {"template": template, "affects": affects}


def _parse_save(e: AuroraElement) -> dict:
    text = _strip_html(e.description_html).lower()
    for long, short in SAVE_ABILITIES.items():
        if f"{long} saving throw" in text:
            return {"ability": short, "dc": {"calculation": "spellcasting", "formula": ""}}
    return {"ability": "", "dc": {"calculation": "spellcasting", "formula": ""}}


def _parse_damage(e: AuroraElement) -> dict:
    text = _strip_html(e.description_html).lower()
    # Simple best-effort: first dice expression near a damage type.
    parts = []
    for dtype in DAMAGE_TYPES:
        m = re.search(rf"(\d+d\d+(?:\s*[+\-]\s*(?:\d+|your\s+\w+\s+modifier|your\s+spellcasting\s+ability\s+modifier|your\s+proficiency\s+bonus))?)\s+{dtype}\s+damage", text, flags=re.I)
        if m:
            parts.append({"number": None, "denomination": None, "bonus": "", "types": [dtype], "custom": {"enabled": True, "formula": _ability_formula(m.group(1))}})
            break
    return {"parts": parts}


def compile_spell(e: AuroraElement, include_source_name: bool = True, long_source: bool = False) -> dict:
    name = e.display_name(include_source_name, long_source=long_source)
    base_name = clean_duplicate_name(e.name)
    level = _parse_int(e.setter("level"), 0)
    school_raw = e.setter("school").lower()
    school = SCHOOLS.get(school_raw, school_raw[:3] if school_raw else "")

    properties, materials = _parse_properties(e)
    duration, concentration_from_duration = _parse_duration(e.setter("duration"))
    if concentration_from_duration:
        properties.add("concentration")

    activity_id = stable_id(f"activity:{e.id or name}", 16)
    target = _parse_target_template(e)
    save = _parse_save(e)
    damage = _parse_damage(e)
    healing = _parse_healing(e)

    item = base_item(name, "spell", "icons/svg/book.svg")
    item["system"] = {
        "description": {"value": e.description_html, "chat": ""},
        "source": {"custom": e.source, "book": e.source_code, "page": "", "license": "", "rules": "2014", "revision": 1},
        "level": level,
        "school": school,
        "properties": sorted(properties),
        "materials": materials,
        "preparation": {"mode": "prepared", "prepared": False},
        "activities": {
            activity_id: {
                "_id": activity_id,
                "type": "cast",
                "name": base_name,
                "activation": _parse_time(e.setter("time")),
                "consumption": {"targets": [{"type": "spellSlots", "value": str(level)}] if level else []},
                "duration": duration,
                "range": _parse_range(e.setter("range")),
                "target": target,
                "uses": {"spent": 0, "max": "", "recovery": []},
                "effects": [],
                "damage": damage,
                "save": save,
                "description": {"chatFlavor": ""},
            }
        },
        "uses": {"spent": 0, "max": "", "recovery": []},
        "identifier": slugify(base_name),
    }
    activity = item["system"]["activities"][activity_id]
    if healing:
        activity["type"] = "heal"
        activity["healing"] = healing
        formula = _damage_formula_from_part(healing)
        action = "targeted-temphp" if "temphp" in (healing.get("types") or []) else "targeted-healing"
        activity["flags"] = _runtime_flag(action, base_name, formula or "1")
    elif damage.get("parts"):
        first = damage.get("parts", [{}])[0]
        formula = _damage_formula_from_part(first)
        dtype = ""
        if isinstance(first, dict) and first.get("types"):
            dtype = first.get("types", [""])[0]
        action = "targeted-save-damage" if save.get("ability") else "targeted-damage"
        activity["flags"] = _runtime_flag(action, base_name, formula or "1", damage_type=dtype, save_ability=save.get("ability", ""))

    item["flags"] = {"aurora": {"id": e.id, "source": e.source, "sourceCode": e.source_code, "file": e.file, "type": e.type, "rules": e.rules, "setters": e.setters, "supports": e.supports, "compiler": "spell-v2.8", "runtimeMapped": bool(healing or damage.get("parts"))}}
    return item
