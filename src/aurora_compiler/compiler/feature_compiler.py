from __future__ import annotations
import re
from aurora_compiler.models.aurora import AuroraElement, clean_duplicate_name, slugify
from aurora_compiler.foundry.templates import base_item, stable_id
from aurora_compiler.foundry import advancement as adv
from aurora_compiler.compiler.resource_compiler import detect_feature_resource

SAVE_ABILITIES = {
    "strength": "str", "dexterity": "dex", "constitution": "con",
    "intelligence": "int", "wisdom": "wis", "charisma": "cha",
}

DAMAGE_TYPES = [
    "acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
    "poison", "psychic", "radiant", "slashing", "thunder"
]

ACTIVITY_WORDS = [
    ("bonus action", "bonus"),
    ("reaction", "reaction"),
    ("action", "action"),
]

LIMITED_USE_PATTERNS = [
    (r"once per short or long rest", "1", "sr"),
    (r"once per long rest", "1", "lr"),
    (r"once per short rest", "1", "sr"),
    (r"once,?\s+and\s+you\s+regain\s+the\s+ability\s+to\s+do\s+so\s+when\s+you\s+finish\s+a\s+long\s+rest", "1", "lr"),
    (r"once,?\s+and\s+regain\s+the\s+ability\s+to\s+do\s+so\s+when\s+you\s+finish\s+a\s+long\s+rest", "1", "lr"),
    (r"once,?\s+and\s+you\s+regain\s+the\s+ability\s+to\s+do\s+so\s+when\s+you\s+finish\s+a\s+short\s+or\s+long\s+rest", "1", "sr"),
    (r"once,?\s+and\s+regain\s+the\s+ability\s+to\s+do\s+so\s+when\s+you\s+finish\s+a\s+short\s+or\s+long\s+rest", "1", "sr"),
    (r"a number of times equal to your proficiency bonus", "@prof", "lr"),
    (r"you can use this (?:trait|feature) a number of times equal to your proficiency bonus", "@prof", "lr"),
    (r"a number of times equal to your (\w+) modifier", "@abilities.{ability}.mod", "lr"),
]

ABILITY_WORD_TO_SHORT = {
    "strength": "str", "dexterity": "dex", "constitution": "con",
    "intelligence": "int", "wisdom": "wis", "charisma": "cha",
}

ELDRITCH_CANNON_ACTOR_ID = stable_id("actor:artificer:eldritch-cannon", 16)
ELDRITCH_CANNON_ACTOR_NAME = "Eldritch Cannon"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def _activity_type(text: str) -> str | None:
    low = text.lower()
    for phrase, unit in ACTIVITY_WORDS:
        if phrase in low:
            return unit
    return None


def _parse_activation(text: str) -> dict:
    unit = _activity_type(text) or ""
    return {"type": unit, "cost": 1 if unit else None, "condition": ""}


def _parse_range(text: str) -> dict:
    low = text.lower()
    if "touch" in low:
        return {"value": None, "units": "touch", "special": ""}
    if "self" in low or "yourself" in low:
        return {"value": None, "units": "self", "special": ""}
    # Prefer wording like within 30 feet / range of 30 feet.
    m = re.search(r"(?:within|range of|up to)\s+(\d+)\s*(?:feet|foot|ft)", low)
    if not m:
        m = re.search(r"(\d+)\s*(?:feet|foot|ft)", low)
    if m:
        return {"value": int(m.group(1)), "units": "ft", "special": ""}
    return {"value": None, "units": "", "special": ""}


def _parse_target_template(text: str) -> dict:
    low = text.lower()
    template = {"type": "", "size": "", "width": "", "units": "ft"}
    affects = {"type": "", "count": "", "choice": False, "special": ""}

    for pat, kind in [
        (r"(\d+)\s*[- ]?foot[- ]radius sphere", "circle"),
        (r"(\d+)\s*[- ]?foot sphere", "circle"),
        (r"(\d+)\s*[- ]?foot cone", "cone"),
        (r"(\d+)\s*[- ]?foot cube", "rect"),
    ]:
        m = re.search(pat, low)
        if m:
            template["type"] = kind
            template["size"] = int(m.group(1))
            return {"template": template, "affects": affects}

    m = re.search(r"each creature(?: of your choice)? within (\d+)\s*(?:feet|foot|ft)", low)
    if m:
        template["type"] = "circle"
        template["size"] = int(m.group(1))
        affects["type"] = "creature"
        affects["choice"] = "of your choice" in low
        return {"template": template, "affects": affects}

    if "one creature" in low:
        affects["type"] = "creature"
        affects["count"] = 1
    return {"template": template, "affects": affects}


def _parse_save(text: str) -> dict:
    low = text.lower()
    for label, short in SAVE_ABILITIES.items():
        if f"{label} saving throw" in low:
            return {"ability": short, "dc": {"calculation": "", "formula": ""}}
    return {"ability": "", "dc": {"calculation": "", "formula": ""}}


def _ability_formula(raw: str) -> str:
    """Normalize phrases like ``your Strength modifier`` into Foundry data paths."""
    out = raw or ""
    for long, short in ABILITY_WORD_TO_SHORT.items():
        out = re.sub(rf"your\s+{long}\s+modifier", f"@abilities.{short}.mod", out, flags=re.I)
        out = re.sub(rf"{long}\s+modifier", f"@abilities.{short}.mod", out, flags=re.I)
    return re.sub(r"\s+", " ", out).strip()


def _first_dice_formula(text: str) -> str:
    m = re.search(r"\d+d\d+(?:\s*[+\-]\s*(?:\d+|your\s+\w+\s+modifier|\w+\s+modifier|@abilities\.[a-z]{3}\.mod))?", text, flags=re.I)
    return _ability_formula(m.group(0)) if m else ""


def _formula_from_common_phrase(text: str) -> str:
    """Best-effort formula parser for non-dice feature damage/healing.

    v2.6 handles many features that do not use a literal dice formula but still
    have a roll/application in Foundry terms, for example ``equal to your
    proficiency bonus`` or ``equal to your Charisma modifier``. These are safe as
    custom formulas and reduce the large "mentions damage but no native damage"
    report bucket.
    """
    low = text.lower()
    formula = _first_dice_formula(low)
    if formula:
        return formula
    if re.search(r"twice\s+(?:your\s+)?proficiency bonus", low):
        return "2 * @prof"
    if re.search(r"(?:your\s+)?proficiency bonus", low):
        return "@prof"
    for long, short in ABILITY_WORD_TO_SHORT.items():
        if re.search(rf"(?:your\s+)?{long}\s+modifier", low):
            return f"@abilities.{short}.mod"
    m = re.search(r"equal to\s+(\d+)", low)
    if m:
        return m.group(1)
    return ""


def _infer_damage_type(text: str, feature_name: str = "") -> str:
    low = f"{feature_name} {text}".lower()
    for dtype in DAMAGE_TYPES:
        if f"{dtype} damage" in low or re.search(rf"\b{dtype}\b", low):
            return dtype
    natural = {
        "bite": "piercing",
        "fang": "piercing",
        "claw": "slashing",
        "talon": "slashing",
        "horn": "piercing",
        "ram": "bludgeoning",
        "hoof": "bludgeoning",
        "hooves": "bludgeoning",
    }
    for key, dtype in natural.items():
        if key in low:
            return dtype
    return ""


def _parse_damage(text: str, feature_name: str = "") -> dict:
    low = text.lower()
    parts = []

    # Prefer an explicit dice formula next to a damage type.
    for dtype in DAMAGE_TYPES:
        patterns = [
            rf"(\d+d\d+(?:\s*[+\-]\s*(?:\d+|your\s+\w+\s+modifier|\w+\s+modifier|@abilities\.[a-z]{{3}}\.mod))?)\s+{dtype}\s+damage",
            rf"{dtype}\s+damage\s+equal\s+to\s+(\d+d\d+(?:\s*[+\-]\s*(?:\d+|your\s+\w+\s+modifier|\w+\s+modifier|@abilities\.[a-z]{{3}}\.mod))?)",
        ]
        for pat in patterns:
            m = re.search(pat, low, flags=re.I)
            if m:
                formula = _ability_formula(m.group(1))
                parts.append({
                    "number": None,
                    "denomination": None,
                    "bonus": "",
                    "types": [dtype],
                    "custom": {"enabled": True, "formula": formula},
                })
                return {"parts": parts}

    # Natural weapons often say "damage equal to 1d6 + your Strength modifier".
    if "damage" in low:
        formula = _first_dice_formula(low)
        if formula:
            dtype = _infer_damage_type(low, feature_name)
            parts.append({
                "number": None,
                "denomination": None,
                "bonus": "",
                "types": [dtype] if dtype else [],
                "custom": {"enabled": True, "formula": formula},
            })
            return {"parts": parts}

    # Many class/subclass features say things like "the target takes radiant
    # damage equal to your proficiency bonus" or "extra damage equal to your
    # Charisma modifier". There is no dice expression, but Foundry can still
    # roll/apply a custom formula.
    if "damage" in low and any(x in low for x in ["equal to", "proficiency bonus", "modifier"]):
        formula = _formula_from_common_phrase(low)
        if formula:
            dtype = _infer_damage_type(low, feature_name)
            parts.append(_damage_part(formula, dtype))
    return {"parts": parts}


def _parse_healing(text: str) -> dict | None:
    low = text.lower()
    if not any(x in low for x in ["temporary hit points", "temporary hp", "regain hit points", "regain a number of hit points", "restore hit points"]):
        return None

    heal_type = "temphp" if "temporary" in low else "healing"
    formula = _formula_from_common_phrase(low)
    if not formula:
        # Handle ability-modifier-only temporary HP, common in racial/class features.
        for long, short in ABILITY_WORD_TO_SHORT.items():
            if f"{long} modifier" in low:
                formula = f"@abilities.{short}.mod"
                break
    if not formula:
        m = re.search(r"equal to (?:your )?proficiency bonus", low)
        if m:
            formula = "@prof"
    if not formula:
        formula = "1"
    return _damage_part(formula, heal_type)


def _parse_attack(text: str, feature_name: str = "") -> dict | None:
    low = f"{feature_name} {text}".lower()
    if "spell attack" in low:
        classification = "spell"
    elif any(x in low for x in ["weapon attack", "natural weapon", "unarmed strike", "bite", "claw", "talon", "horn", "ram", "hoof", "hooves"]):
        classification = "weapon"
    else:
        return None

    value = "ranged" if "ranged" in low else "melee"
    ability = "spellcasting" if classification == "spell" else ""
    return {"ability": ability, "bonus": "", "critical": {"threshold": None}, "flat": False, "type": {"value": value, "classification": classification}}


def _parse_uses(text: str) -> dict:
    low = text.lower()
    for pat, max_value, period in LIMITED_USE_PATTERNS:
        m = re.search(pat, low)
        if not m:
            continue
        if "{ability}" in max_value:
            ability = ABILITY_WORD_TO_SHORT.get(m.group(1).lower(), m.group(1).lower()[:3])
            max_value = max_value.format(ability=ability)
        return {"spent": 0, "max": max_value, "recovery": [{"period": period, "type": "recoverAll"}]}
    return {"spent": 0, "max": "", "recovery": []}


PASSIVE_OR_TRIGGERED_WORDS = [
    "when you hit", "whenever you hit", "once per turn", "damage roll", "damage rolls",
    "you add", "you can add", "add your", "extra damage", "bonus to the damage",
    "reduce the damage", "subtract", "reroll", "advantage", "disadvantage",
    "when a creature", "when you take", "when you fail", "when you succeed",
]


def _looks_passive_or_triggered_modifier(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in PASSIVE_OR_TRIGGERED_WORDS)


def _effect_summary(e: AuroraElement) -> list[str]:
    """Human-readable compiler notes until every Aurora rule has a native backend."""
    notes: list[str] = []
    for rule in e.rules:
        tag = (rule.get("tag") or "").lower()
        attrs = rule.get("attrs", {}) or {}
        if tag == "grant":
            notes.append(f"grant {attrs.get('type','?')} {attrs.get('id','')}")
        elif tag == "stat":
            notes.append(f"stat {attrs.get('name','?')} += {attrs.get('value','')}")
        elif tag == "select":
            notes.append(f"select {attrs.get('type','?')} count={attrs.get('number') or attrs.get('count') or ''}")
    return notes



def _damage_part(formula: str, damage_type: str) -> dict:
    m = re.match(r"^\s*(\d+)d(\d+)(?:\s*\+\s*(.+))?\s*$", formula)
    if m:
        return {
            "number": int(m.group(1)),
            "denomination": int(m.group(2)),
            "bonus": m.group(3) or "",
            "types": [damage_type] if damage_type else [],
            "custom": {"enabled": False, "formula": ""},
            "scaling": {"mode": "", "number": None, "formula": ""},
        }
    return {
        "number": None,
        "denomination": None,
        "bonus": "",
        "types": [damage_type] if damage_type else [],
        "custom": {"enabled": True, "formula": formula},
        "scaling": {"mode": "", "number": None, "formula": ""},
    }




def _part_to_formula(part: dict | None) -> str:
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


def _runtime_flag(action: str, label: str, formula: str = "", *, radius: int | None = None, origin: str = "source-token", target: str = "selected-or-targeted-tokens") -> dict:
    data = {
        "action": action,
        "label": label,
        "formula": formula,
        "origin": origin,
        "target": target,
        "backend": "aurora-runtime-js-v2.8",
    }
    if radius is not None:
        data["radius"] = radius
        data["units"] = "ft"
    return {"aurora": {"runtime": data}}

def _normalize_target(target: dict | None = None) -> dict:
    data = target or {"template": {"type": "", "size": "", "width": "", "units": "ft"}, "affects": {"type": "", "count": "", "choice": False, "special": ""}, "override": False, "prompt": True}
    template = data.setdefault("template", {})
    template.setdefault("count", "1" if template.get("type") else "")
    template.setdefault("contiguous", False)
    template.setdefault("stationary", False)
    template.setdefault("height", "")
    template.setdefault("width", "")
    template.setdefault("units", "ft")
    data.setdefault("affects", {"type": "", "count": "", "choice": False, "special": ""})
    data.setdefault("override", False)
    data.setdefault("prompt", True)
    return data


def _base_activity(activity_id: str, activity_type: str, name: str, activation_type: str = "", target: dict | None = None, range_data: dict | None = None) -> dict:
    return {
        "_id": activity_id,
        "type": activity_type,
        "name": name,
        "activation": {"type": activation_type, "cost": 1 if activation_type else None, "condition": ""},
        "consumption": {"scaling": {"allowed": False, "max": ""}, "spellSlot": False, "targets": []},
        "duration": {"value": None, "units": "", "special": "", "concentration": False, "override": False},
        "range": range_data or {"value": None, "units": "", "special": "", "override": False},
        "target": _normalize_target(target),
        "uses": {"spent": 0, "max": "", "recovery": []},
        "effects": [],
        "description": {"chatFlavor": ""},
        "visibility": {"identifier": "", "level": {"min": None, "max": None}, "requireAttunement": False, "requireIdentification": False, "requireMagic": False},
    }



def _artillerist_activity_override(e: AuroraElement, base_name: str) -> dict[str, dict] | None:
    """Native-ish activities for one Eldritch Cannon mode.

    Runtime activities for one Eldritch Cannon mode.

    v2.6 deliberately keeps these activities usable from the artificer's
    Eldritch Cannon feature as well as the optional visual cannon actor.  This
    is important for Protector: the formula uses the artificer's Intelligence,
    while a summoned cannon actor does not reliably know its owner's ability
    modifier in vanilla Foundry.
    """
    slug = slugify(base_name)
    activity_id = stable_id(f"artillerist-activity:{e.id or base_name}:{slug}", 16)

    if slug == "flamethrower":
        activity = _base_activity(
            activity_id, "save", base_name, "bonus",
            target={"template": {"type": "cone", "size": 15, "width": "", "units": "ft"}, "affects": {"type": "creature", "count": "", "choice": False, "special": ""}, "override": False, "prompt": True},
            range_data={"value": None, "units": "self", "special": "Adjacent 15-foot cone from the cannon", "override": False},
        )
        activity["damage"] = {"onSave": "half", "parts": [_damage_part("2d8", "fire")]}
        activity["save"] = {"ability": ["dex"], "dc": {"calculation": "spellcasting", "formula": ""}}
        return {activity_id: activity}

    if slug == "force-ballista":
        activity = _base_activity(
            activity_id, "attack", base_name, "bonus",
            target={"template": {"type": "", "size": "", "width": "", "units": "ft"}, "affects": {"type": "creature", "count": 1, "choice": False, "special": "One creature or object"}, "override": False, "prompt": True},
            range_data={"value": 120, "units": "ft", "special": "Originates from the cannon", "override": False},
        )
        activity["attack"] = {"ability": "spellcasting", "bonus": "", "critical": {"threshold": None}, "flat": False, "type": {"value": "ranged", "classification": "spell"}}
        activity["damage"] = {"critical": {"bonus": ""}, "includeBase": True, "parts": [_damage_part("2d8", "force")]}
        return {activity_id: activity}

    if slug == "protector":
        # Protector is not a persistent measured-template aura. Rules-wise it is a
        # bonus-action burst that grants temporary HP to the cannon and creatures
        # of your choice within 10 ft. We deliberately avoid a template here,
        # because Foundry leaves those green circles on the scene.
        activity = _base_activity(
            activity_id, "heal", base_name, "bonus",
            target={"template": {"type": "", "size": "", "width": "", "units": "ft"}, "affects": {"type": "creature", "count": "", "choice": False, "special": "Manually target the cannon and any chosen creatures within 10 feet of it"}, "override": False, "prompt": False},
            range_data={"value": 10, "units": "ft", "special": "Originates from the cannon", "override": False},
        )
        activity["healing"] = _damage_part("1d8 + @abilities.int.mod", "temphp")
        activity["flags"] = _runtime_flag(
            "targeted-temphp",
            "Eldritch Cannon: Protector",
            "1d8 + @abilities.int.mod",
            radius=10,
            origin="eldritch-cannon-token",
            target="chosen-creatures-within-radius",
        )
        return {activity_id: activity}

    return None


ARTILLERIST_CANNON_OPTION_SLUGS = {"flamethrower", "force-ballista", "protector"}
ARTILLERIST_CANNON_OPTION_ID_PARTS = {"FLAMETHROWER", "FORCE_BALLISTA", "FORCEBALLISTA", "PROTECTOR"}
ELDRITCH_CANNON_MODES = [
    ("flamethrower", "Eldritch Cannon - Flamethrower", "Flamethrower"),
    ("force-ballista", "Eldritch Cannon - Force Ballista", "Force Ballista"),
    ("protector", "Eldritch Cannon - Protector", "Protector"),
]
ELDRITCH_CANNON_ACTOR_IDS = {
    slug: stable_id(f"actor:artificer:eldritch-cannon:{slug}", 16)
    for slug, _, _ in ELDRITCH_CANNON_MODES
}


def is_eldritch_cannon_feature_name(name: str) -> bool:
    return slugify(clean_duplicate_name(name).split("(")[0]) == "eldritch-cannon"


def is_artillerist_cannon_option_name(name: str) -> bool:
    return slugify(clean_duplicate_name(name).split("(")[0]) in ARTILLERIST_CANNON_OPTION_SLUGS


def is_artillerist_cannon_option_id(aurora_id: str) -> bool:
    upper = (aurora_id or "").upper()
    return "ELDRITCH_CANNON" in upper and any(part in upper for part in ARTILLERIST_CANNON_OPTION_ID_PARTS)


def _summon_activity(activity_id: str, module_id: str) -> dict:
    activity = _base_activity(
        activity_id,
        "summon",
        "Create Eldritch Cannon",
        "action",
        target={"template": {"type": "", "size": "", "width": "", "units": "ft"}, "affects": {"type": "object", "count": 1, "choice": False, "special": "Choose Flamethrower, Force Ballista, or Protector"}, "override": False, "prompt": True},
        range_data={"value": 5, "units": "ft", "special": "Unoccupied space within 5 feet", "override": False},
    )
    activity["duration"] = {"value": 1, "units": "hour", "special": "The cannon disappears early if reduced to 0 hit points or dismissed.", "concentration": False, "override": False}
    activity["bonuses"] = {"ac": "", "hd": "", "hp": "5 * @classes.artificer.levels", "attackDamage": "", "saveDamage": "", "healing": ""}
    activity["creatureSizes"] = ["tiny", "sm"]
    activity["creatureTypes"] = ["construct"]
    activity["match"] = {"ability": "", "attacks": False, "disposition": True, "proficiency": False, "saves": False}
    activity["profiles"] = [{
        "_id": stable_id(f"summon-profile:artificer:eldritch-cannon:{slug}", 16),
        "count": "1",
        "cr": "",
        "level": {"min": 3},
        "name": label,
        "types": ["construct"],
        "uuid": f"Compendium.{module_id}.summons.{ELDRITCH_CANNON_ACTOR_IDS[slug]}",
    } for slug, label, _ in ELDRITCH_CANNON_MODES]
    activity["summon"] = {"mode": "", "prompt": True}
    activity["tempHP"] = ""
    return activity


def _eldritch_cannon_main_activities(e: AuroraElement, module_id: str = "aurora-extra-pack") -> dict[str, dict]:
    # The character sheet gets one feature, Eldritch Cannon, with multiple
    # activities. Create Eldritch Cannon places the visual token. The three mode
    # activities are also present here so their rolls use the artificer's data
    # (@abilities.int.mod, spell attack modifier, save DC) instead of the dummy
    # summoned actor's data.
    summon_id = stable_id(f"artillerist-activity:{e.id or 'eldritch-cannon'}:summon", 16)
    activities = {summon_id: _summon_activity(summon_id, module_id)}
    for slug, _actor_name, mode_name in ELDRITCH_CANNON_MODES:
        mode_element = AuroraElement(
            id=f"ID_INTERNAL_ELDRITCH_CANNON_MAIN_{slug.upper()}",
            name=mode_name,
            type="Archetype Feature",
            source="Eberron: Rising from the Last War",
        )
        activities.update(_artillerist_activity_override(mode_element, mode_name) or {})
    return activities


def _cannon_mode_item(mode_name: str) -> dict:
    item = base_item(mode_name, "feat", "icons/svg/cog.svg")
    item["system"] = {
        "description": {"value": f"<p>{mode_name} mode for the Artillerist Eldritch Cannon.</p>", "chat": ""},
        "source": {"custom": "Eberron: Rising from the Last War", "book": "ERLW", "page": "", "license": "", "rules": "2014", "revision": 1},
        "identifier": slugify(mode_name),
        "type": {"value": "class", "subtype": ""},
        "advancement": {},
        "prerequisites": {"level": None, "repeatable": False},
        "properties": [],
        "requirements": "Artillerist 3",
        "activities": _artillerist_activity_override(AuroraElement(id=f"ID_INTERNAL_ELDRITCH_CANNON_{slugify(mode_name).upper()}", name=mode_name, type="Archetype Feature", source="Eberron: Rising from the Last War"), mode_name) or {},
        "uses": {"spent": 0, "max": "", "recovery": []},
    }
    item["flags"] = {"aurora": {"compiler": "artificer-cannon-mode-v2.8", "mode": slugify(mode_name)}}
    return item


def _eldritch_cannon_actor_doc(slug: str, actor_name: str, mode_name: str) -> dict:
    now = 0
    img = "systems/dnd5e/tokens/construct/Homonculus.webp"
    return {
        "_id": ELDRITCH_CANNON_ACTOR_IDS[slug],
        "name": actor_name,
        "type": "npc",
        "img": img,
        "items": [_cannon_mode_item(mode_name)],
        "effects": [],
        "folder": None,
        "system": {
            "abilities": {k: {"value": 10, "proficient": 0} for k in ["str", "dex", "con", "int", "wis", "cha"]},
            "attributes": {
                "ac": {"calc": "flat", "flat": 18},
                "hp": {"value": 15, "max": 15, "temp": 0, "tempmax": 0, "formula": "5 * @classes.artificer.levels"},
                "movement": {"walk": 15, "climb": 15, "fly": 0, "swim": 0, "burrow": 0, "units": "ft", "hover": False},
                "prof": 2,
            },
            "details": {"type": {"value": "construct", "subtype": ""}, "cr": 0, "source": {"custom": "Eberron: Rising from the Last War", "book": "ERLW", "page": "", "license": "", "rules": "2014", "revision": 1}},
            "traits": {
                "size": "tiny",
                "di": {"value": ["poison", "psychic"], "bypasses": [], "custom": ""},
                "dr": {"value": [], "bypasses": [], "custom": ""},
                "dv": {"value": [], "bypasses": [], "custom": ""},
                "ci": {"value": [], "custom": ""},
                "languages": {"value": [], "custom": ""},
            },
        },
        "prototypeToken": {
            "name": actor_name,
            "actorLink": False,
            "displayName": 20,
            "displayBars": 40,
            "disposition": 1,
            "width": 1,
            "height": 1,
            "texture": {"src": img, "scaleX": 1, "scaleY": 1, "rotation": 0, "tint": "#ffffff"},
            "bar1": {"attribute": "attributes.hp"},
            "bar2": {"attribute": ""},
            "sight": {"enabled": False, "range": 0, "angle": 360, "visionMode": "basic", "color": None, "attenuation": 0.5, "brightness": 0, "saturation": 0, "contrast": 0},
        },
        "ownership": {"default": 3},
        "flags": {"aurora": {"compiler": "artificer-summon-v2.8", "kind": "eldritch-cannon", "mode": slug}},
        "_stats": {"coreVersion": "14.364", "systemId": "dnd5e", "systemVersion": "5.3.3", "createdTime": now, "modifiedTime": now},
    }


def eldricht_cannon_actor_docs() -> list[dict]:
    """Actors available in the summon picker for the Eldritch Cannon feature."""
    return [_eldritch_cannon_actor_doc(slug, actor_name, mode_name) for slug, actor_name, mode_name in ELDRITCH_CANNON_MODES]


def eldricht_cannon_actor_doc() -> dict:
    """Backward-compatible helper for older tests: return the first cannon actor."""
    return eldricht_cannon_actor_docs()[0]

def child_feature_grant_ids(e: AuroraElement) -> list[str]:
    out: list[str] = []
    for rule in e.rules:
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "grant":
            continue
        if (attrs.get("type") or "").lower() not in {"class feature", "archetype feature", "racial trait", "feat"}:
            continue
        aurora_id = attrs.get("id", "")
        if aurora_id and aurora_id not in out:
            out.append(aurora_id)
    return out


def child_feature_uuid_index(elements: list[AuroraElement], feature_uuid_by_aurora_id: dict[str, str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for e in elements:
        if e.type not in {"Class Feature", "Archetype Feature", "Racial Trait", "Feat"} or not e.id:
            continue
        # Eldritch Cannon options are activities inside the single Eldritch Cannon
        # feature. Do not expose them as nested ItemGrant actor features.
        if is_eldritch_cannon_feature_name(e.name) or is_artillerist_cannon_option_name(e.name):
            continue
        uuids: list[str] = []
        for aurora_id in child_feature_grant_ids(e):
            if is_artillerist_cannon_option_id(aurora_id):
                continue
            uuid = feature_uuid_by_aurora_id.get(aurora_id)
            if uuid and uuid not in uuids:
                uuids.append(uuid)
        if uuids:
            out[e.id] = uuids
    return out


def add_nested_grant_advancements(feature_docs: list[dict], child_feature_uuids_by_aurora_id: dict[str, list[str]]) -> int:
    added = 0
    for item in feature_docs:
        aurora_id = item.get("flags", {}).get("aurora", {}).get("id", "")
        # The Artillerist Eldritch Cannon options are represented as activities on
        # the single Eldritch Cannon feature. Do not auto-grant Flamethrower,
        # Force Ballista and Protector as three separate actor features.
        if is_eldritch_cannon_feature_name(item.get("name", "")) or is_artillerist_cannon_option_name(item.get("name", "")):
            item.setdefault("flags", {}).setdefault("aurora", {})["nestedFeatureGrantSkipped"] = "artillerist cannon options merged into activities"
            continue
        child_uuids = child_feature_uuids_by_aurora_id.get(aurora_id, [])
        if not child_uuids:
            continue
        item.setdefault("system", {}).setdefault("advancement", {})
        seed = f"feature:{aurora_id}:{item.get('name', '')}"
        doc = adv.item_grant(seed, child_uuids, level=0, title="Granted Feature Options")
        item["system"]["advancement"][doc["_id"]] = doc
        item.setdefault("flags", {}).setdefault("aurora", {})["nestedFeatureGrantCount"] = len(child_uuids)
        added += 1
    return added


def compile_feature(e: AuroraElement, include_source_name: bool = True, long_source: bool = False, module_id: str = "aurora-extra-pack") -> dict:
    name = e.display_name(include_source_name, long_source=long_source)
    base_name = clean_duplicate_name(e.name)
    text = _strip_html(e.description_html)
    activity_kind = _activity_type(text)

    item = base_item(name, "feat", "icons/svg/book.svg")
    resource = detect_feature_resource(e)

    item["system"] = {
        "description": {"value": e.description_html, "chat": ""},
        "source": {"custom": e.source, "book": e.source_code, "page": "", "license": "", "rules": "2014", "revision": 1},
        "identifier": slugify(base_name),
        "type": {"value": "class" if e.type in {"Class Feature", "Archetype Feature"} else "race" if e.type == "Racial Trait" else "feat", "subtype": ""},
        "advancement": {},
        "prerequisites": {"level": None, "repeatable": False},
        "properties": [],
        "requirements": "",
        "activities": {},
        "uses": resource.uses() if resource else _parse_uses(text),
    }

    # Add a best-effort activity only when the text clearly exposes a use action/save/damage/template.
    if is_eldritch_cannon_feature_name(base_name):
        artillerist_override = _eldritch_cannon_main_activities(e, module_id=module_id)
    else:
        artillerist_override = _artillerist_activity_override(e, base_name)
    if artillerist_override is not None:
        item["system"]["activities"] = artillerist_override

    save = _parse_save(text)
    damage = _parse_damage(text, base_name)
    healing = _parse_healing(text)
    attack = _parse_attack(text, base_name)
    target = _parse_target_template(text)
    # Do not create fake click-buttons for passive/triggered modifiers such as
    # "when you hit, add X damage" or "reduce damage by ...". Those belong in a
    # future Active Effect / manual-trigger backend, not in an ordinary activity.
    passive_or_triggered = _looks_passive_or_triggered_modifier(text) and not attack and not healing and not target["template"]["type"] and not is_eldritch_cannon_feature_name(base_name)
    has_activity_payload = bool(activity_kind or save["ability"] or damage["parts"] or healing or attack or target["template"]["type"])
    if has_activity_payload and artillerist_override is None:
        activity_id = stable_id(f"feature-activity:{e.id or name}", 16)
        if healing and not (attack or damage["parts"] or save["ability"]):
            foundry_activity_type = "heal"
        elif attack:
            foundry_activity_type = "attack"
        elif save["ability"]:
            foundry_activity_type = "save"
        elif passive_or_triggered:
            foundry_activity_type = "utility"
        else:
            foundry_activity_type = "utility"
        activity = {
            "_id": activity_id,
            "type": foundry_activity_type,
            "name": base_name,
            "activation": _parse_activation(text),
            "consumption": {"targets": []},
            "duration": {"value": None, "units": "", "special": ""},
            "range": _parse_range(text),
            "target": target,
            "uses": {"spent": 0, "max": "", "recovery": []},
            "effects": [],
            "damage": damage,
            "save": save,
            "description": {"chatFlavor": ""},
        }
        if attack:
            activity["attack"] = attack
        if healing:
            activity["healing"] = healing
            formula = _part_to_formula(healing)
            damage_types = healing.get("types", []) if isinstance(healing, dict) else []
            action = "targeted-temphp" if "temphp" in damage_types else "targeted-healing"
            activity["flags"] = _runtime_flag(action, base_name, formula or "1")
        elif damage.get("parts"):
            first = damage.get("parts", [{}])[0]
            activity["flags"] = _runtime_flag("targeted-damage", base_name, _part_to_formula(first), target="selected-targets")
        item["system"]["activities"][activity_id] = activity

    notes = _effect_summary(e)
    item["flags"] = {
        "aurora": {
            "id": e.id,
            "source": e.source,
            "sourceCode": e.source_code,
            "file": e.file,
            "type": e.type,
            "rules": e.rules,
            "setters": e.setters,
            "supports": e.supports,
            "compiler": "feature-v2.8",
            "resource": resource.flag() if resource else None,
            "nativeRuleNotes": notes,
        }
    }
    return item
