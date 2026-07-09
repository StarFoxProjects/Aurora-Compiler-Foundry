from __future__ import annotations
import re
from aurora_compiler.models.aurora import AuroraElement, clean_duplicate_name, slugify
from aurora_compiler.foundry.templates import base_item
from aurora_compiler.foundry import advancement as adv


ABILITY_MAP = {
    "strength": "str", "str": "str",
    "dexterity": "dex", "dex": "dex",
    "constitution": "con", "con": "con",
    "intelligence": "int", "int": "int",
    "wisdom": "wis", "wis": "wis",
    "charisma": "cha", "cha": "cha",
}

LANGUAGE_MAP = {
    "common": "languages:standard:common",
    "dwarvish": "languages:standard:dwarvish",
    "elvish": "languages:standard:elvish",
    "giant": "languages:standard:giant",
    "gnomish": "languages:standard:gnomish",
    "goblin": "languages:standard:goblin",
    "halfling": "languages:standard:halfling",
    "orc": "languages:standard:orc",
    "abyssal": "languages:exotic:abyssal",
    "celestial": "languages:exotic:celestial",
    "draconic": "languages:exotic:draconic",
    "deep speech": "languages:exotic:deep",
    "deepspeech": "languages:exotic:deep",
    "infernal": "languages:exotic:infernal",
    "primordial": "languages:exotic:primordial",
    "sylvan": "languages:exotic:sylvan",
    "undercommon": "languages:exotic:undercommon",
    "quori": "languages:exotic:quori",
    # Non-core languages that appear in Aurora source files. Foundry can still store them as custom trait keys
    # when they exist in the world/system config; otherwise they remain reported as missing.
    "auran": "languages:exotic:auran",
    "aarakocra": "languages:exotic:aarakocra",
}

LANGUAGE_ID_HINTS = {
    "ID_LANGUAGE_COMMON": "languages:standard:common",
    "ID_LANGUAGE_DWARVISH": "languages:standard:dwarvish",
    "ID_LANGUAGE_ELVISH": "languages:standard:elvish",
    "ID_LANGUAGE_GIANT": "languages:standard:giant",
    "ID_LANGUAGE_GNOMISH": "languages:standard:gnomish",
    "ID_LANGUAGE_GOBLIN": "languages:standard:goblin",
    "ID_LANGUAGE_HALFLING": "languages:standard:halfling",
    "ID_LANGUAGE_ORC": "languages:standard:orc",
    "ID_LANGUAGE_ABYSSAL": "languages:exotic:abyssal",
    "ID_LANGUAGE_CELESTIAL": "languages:exotic:celestial",
    "ID_LANGUAGE_DRACONIC": "languages:exotic:draconic",
    "ID_LANGUAGE_DEEP_SPEECH": "languages:exotic:deep",
    "ID_LANGUAGE_INFERNAL": "languages:exotic:infernal",
    "ID_LANGUAGE_PRIMORDIAL": "languages:exotic:primordial",
    "ID_LANGUAGE_SYLVAN": "languages:exotic:sylvan",
    "ID_LANGUAGE_UNDERCOMMON": "languages:exotic:undercommon",
    "ID_WOTC_ERLW_LANGUAGE_QUORI": "languages:exotic:quori",
    "ID_MM_LANGUAGE_AURAN": "languages:exotic:auran",
    "ID_LANGUAGE_AARAKOCRA": "languages:exotic:aarakocra",
}

SIZE_ID_MAP = {
    "ID_SIZE_TINY": "tiny",
    "ID_SIZE_SMALL": "sm",
    "ID_SIZE_MEDIUM": "med",
    "ID_SIZE_LARGE": "lg",
    "ID_SIZE_HUGE": "huge",
    "ID_SIZE_GARGANTUAN": "grg",
}

DAMAGE_TYPES = {
    "acid", "bludgeoning", "cold", "fire", "force", "lightning",
    "necrotic", "piercing", "poison", "psychic", "radiant", "slashing", "thunder",
}
CONDITION_TYPES = {
    "blinded", "charmed", "deafened", "diseased", "exhaustion", "frightened",
    "grappled", "incapacitated", "invisible", "paralyzed", "petrified",
    "poisoned", "prone", "restrained", "stunned", "unconscious",
}
CONDITION_WORDS = {
    "disease": "diseased", "diseases": "diseased", "diseased": "diseased",
    "poisoned": "poisoned", "charmed": "charmed", "frightened": "frightened",
    "sleep": "unconscious", "magical sleep": "unconscious",
}
MOVEMENT_KEYS = {"fly", "swim", "climb", "burrow"}
SENSE_KEYS = {"darkvision", "blindsight", "tremorsense", "truesight"}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def _parse_level(value: str | int | None) -> int:
    try:
        return max(1, min(20, int(str(value or "1"))))
    except ValueError:
        return 1


def _effective_rules(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None, _seen: set[str] | None = None) -> list[dict]:
    """Expand Aurora <grant type='Grants'> blocks into their underlying rules.

    Modern races such as MPMM Aarakocra use meta-grants like
    ID_WOTC_GRANTS_DEFAULT_RACIAL_ASI and ID_WOTC_GRANTS_DEFAULT_RACIAL_LANGUAGE.
    Without expanding them, Foundry sees the race but never gets the ASI/language advancements.
    """
    rules = list(e.rules or [])
    grant_elements_by_aurora_id = grant_elements_by_aurora_id or {}
    _seen = _seen or set()
    for rule in e.rules or []:
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "grant":
            continue
        if (attrs.get("type") or "").lower() != "grants":
            continue
        gid = attrs.get("id", "")
        if not gid or gid in _seen:
            continue
        ge = grant_elements_by_aurora_id.get(gid)
        if not ge:
            continue
        _seen.add(gid)
        rules.extend(_effective_rules(ge, grant_elements_by_aurora_id, _seen))
    return rules


def _feature_rules_for_granted_traits(
    e: AuroraElement,
    feature_docs_by_aurora_id: dict[str, dict] | None = None,
    grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None,
) -> list[dict]:
    feature_docs_by_aurora_id = feature_docs_by_aurora_id or {}
    rules: list[dict] = []
    for aurora_id, _level in _extract_trait_grants(e, grant_elements_by_aurora_id):
        doc = feature_docs_by_aurora_id.get(aurora_id)
        if not doc:
            continue
        rules.extend(doc.get("flags", {}).get("aurora", {}).get("rules", []) or [])
    return rules


def _extract_trait_grants(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None) -> list[tuple[str, int]]:
    grants: list[tuple[str, int]] = []
    for rule in _effective_rules(e, grant_elements_by_aurora_id):
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "grant":
            continue
        if (attrs.get("type") or "").lower() not in {"racial trait", "race feature", "feature"}:
            continue
        aurora_id = attrs.get("id", "")
        if not aurora_id:
            continue
        grants.append((aurora_id, _parse_level(attrs.get("level"))))
    return grants


def _size_from_text(e: AuroraElement) -> list[str]:
    text = _strip_html(e.description_html).lower()
    if "small or medium" in text or "medium or small" in text:
        return ["sm", "med"]
    if "your size is small" in text or "size is small" in text:
        return ["sm"]
    if "your size is medium" in text or "size is medium" in text:
        return ["med"]
    if "your size is tiny" in text or "size is tiny" in text:
        return ["tiny"]
    if "your size is large" in text or "size is large" in text:
        return ["lg"]
    return []


def _infer_sizes(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None) -> list[str]:
    sizes: list[str] = []
    for rule in _effective_rules(e, grant_elements_by_aurora_id):
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "grant":
            continue
        if (attrs.get("type") or "").lower() != "size":
            continue
        size = SIZE_ID_MAP.get(attrs.get("id", ""))
        if size and size not in sizes:
            sizes.append(size)
    if sizes:
        return sizes
    text_sizes = _size_from_text(e)
    if text_sizes:
        return text_sizes
    return ["med"]


def _infer_size(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None) -> str:
    return _infer_sizes(e, grant_elements_by_aurora_id)[0]


def _parse_movement_value(value: str | int | None, walk: int) -> int:
    raw = str(value or "").strip().lower()
    if raw in {"speed", "walk", "walking speed", "innate speed"}:
        return walk
    try:
        return int(raw)
    except ValueError:
        return 0


def _infer_speed(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None) -> int:
    for rule in _effective_rules(e, grant_elements_by_aurora_id):
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "stat":
            continue
        name = (attrs.get("name") or "").lower()
        if name in {"innate speed", "speed", "walking speed"}:
            try:
                return int(str(attrs.get("value") or "30"))
            except ValueError:
                pass

    text = _strip_html(e.description_html).lower()
    for pat in [
        r"walking speed is (\d+)\s*(?:feet|foot|ft)",
        r"base walking speed is (\d+)\s*(?:feet|foot|ft)",
        r"speed is (\d+)\s*(?:feet|foot|ft)",
        r"your speed is (\d+)\s*(?:feet|foot|ft)",
    ]:
        m = re.search(pat, text)
        if m:
            return int(m.group(1))
    return 30


def _infer_movement(
    e: AuroraElement,
    feature_docs_by_aurora_id: dict[str, dict] | None = None,
    grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None,
) -> dict:
    walk = _infer_speed(e, grant_elements_by_aurora_id)
    movement = {"walk": walk, "burrow": 0, "climb": 0, "fly": 0, "swim": 0, "units": "ft", "hover": False}
    all_rules = _effective_rules(e, grant_elements_by_aurora_id) + _feature_rules_for_granted_traits(e, feature_docs_by_aurora_id, grant_elements_by_aurora_id)
    for rule in all_rules:
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "stat":
            continue
        name = (attrs.get("name") or "").lower()
        value = attrs.get("value")
        if name in {"innate speed", "walking speed"}:
            movement["walk"] = _parse_movement_value(value, walk) or movement["walk"]
            walk = movement["walk"]
            continue
        if name == "speed":
            parsed = _parse_movement_value(value, walk)
            if parsed:
                movement["walk"] = parsed
                walk = parsed
            continue
        m = re.match(r"speed:(fly|swim|climb|burrow)$", name)
        if m:
            key = m.group(1)
            parsed = _parse_movement_value(value, walk)
            if parsed:
                movement[key] = max(movement[key], parsed)
    # Text fallback for features where the XML stat is missing.
    text = " ".join([_strip_html(e.description_html).lower()] + [
        _strip_html((feature_docs_by_aurora_id or {}).get(fid, {}).get("system", {}).get("description", {}).get("value", "")).lower()
        for fid, _level in _extract_trait_grants(e, grant_elements_by_aurora_id)
    ])
    if "flying speed equal to your walking speed" in text or "fly speed equal to your walking speed" in text:
        movement["fly"] = max(movement["fly"], walk)
    if "swimming speed equal to your walking speed" in text or "swim speed equal to your walking speed" in text:
        movement["swim"] = max(movement["swim"], walk)
    if "climbing speed equal to your walking speed" in text or "climb speed equal to your walking speed" in text:
        movement["climb"] = max(movement["climb"], walk)
    return movement


def _language_from_rule(rule: dict) -> str | None:
    attrs = rule.get("attrs", {}) or {}
    ident = attrs.get("id", "")
    if ident in LANGUAGE_ID_HINTS:
        return LANGUAGE_ID_HINTS[ident]
    lower = ident.lower().replace("_", " ")
    for name, grant in LANGUAGE_MAP.items():
        if name in lower:
            return grant
    return None


def _language_grants(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None) -> tuple[list[str], list[str]]:
    grants: list[str] = []
    missing: list[str] = []
    for rule in _effective_rules(e, grant_elements_by_aurora_id):
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "grant":
            continue
        if (attrs.get("type") or "").lower() != "language":
            continue
        grant = _language_from_rule(rule)
        if grant:
            if grant not in grants:
                grants.append(grant)
        else:
            missing.append(attrs.get("id", ""))
    return grants, missing


def _language_choices(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None) -> list[dict]:
    choices: list[dict] = []
    for rule in _effective_rules(e, grant_elements_by_aurora_id):
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "select":
            continue
        if (attrs.get("type") or "").lower() != "language":
            continue
        count_raw = attrs.get("number") or attrs.get("count") or "1"
        try:
            count = int(count_raw)
        except ValueError:
            count = 1
        supports = (attrs.get("supports") or "").lower()
        if "standard" in supports and "exotic" in supports:
            pool = list(dict.fromkeys(LANGUAGE_MAP.values()))
        elif "exotic" in supports:
            pool = [v for v in LANGUAGE_MAP.values() if v.startswith("languages:exotic:")]
        else:
            pool = [v for v in LANGUAGE_MAP.values() if v.startswith("languages:standard:")]
        choices.append({"count": count, "pool": pool})
    return choices


def _fixed_ability_scores(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None) -> dict[str, int]:
    fixed: dict[str, int] = {}
    for rule in _effective_rules(e, grant_elements_by_aurora_id):
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "stat":
            continue
        ability = ABILITY_MAP.get((attrs.get("name") or "").lower())
        if not ability:
            continue
        try:
            value = int(str(attrs.get("value") or "0"))
        except ValueError:
            continue
        if value:
            fixed[ability] = fixed.get(ability, 0) + value
    return fixed


def _selectable_ability_points(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None) -> int:
    """Count Aurora race/species selectable ASI rules.

    Default modern racial ASI is encoded as three select rules via a Grants block.
    Treat each select as one point with cap 2 in Foundry, which supports +2/+1 or +1/+1/+1.
    """
    total = 0
    for rule in _effective_rules(e, grant_elements_by_aurora_id):
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "select":
            continue
        if (attrs.get("type") or "").lower() != "ability score improvement":
            continue
        supports = (attrs.get("supports") or "").lower()
        if "class" in supports and "race" not in supports and "lineage" not in supports and "default_race_asi" not in supports:
            continue
        raw = attrs.get("number") or attrs.get("count") or "1"
        try:
            count = int(str(raw))
        except ValueError:
            count = 1
        total += max(1, count)
    return total


def _condition_grants_from_rules(rules: list[dict]) -> list[str]:
    grants: list[str] = []
    for rule in rules:
        attrs = rule.get("attrs", {}) or {}
        if (rule.get("tag") or "").lower() != "grant":
            continue
        typ = (attrs.get("type") or "").lower()
        if typ != "condition":
            continue
        ident = (attrs.get("id") or attrs.get("name") or "").upper()
        m = re.search(r"DAMAGE_(RESISTANCE|IMMUNITY|VULNERABILITY)_([A-Z]+)", ident)
        if m:
            mode, dtype = m.group(1), m.group(2).lower()
            if dtype not in DAMAGE_TYPES:
                continue
            prefix = {"RESISTANCE": "dr", "IMMUNITY": "di", "VULNERABILITY": "dv"}[mode]
            grant = f"{prefix}:{dtype}"
            if grant not in grants:
                grants.append(grant)
            continue
        # Condition immunity IDs often do not contain DAMAGE_.
        for word, cond in CONDITION_WORDS.items():
            if word.upper().replace(" ", "_") in ident and cond in CONDITION_TYPES:
                grant = f"ci:{cond}"
                if grant not in grants:
                    grants.append(grant)
    return grants


def _split_damage_type_phrase(phrase: str) -> list[str]:
    phrase = re.sub(r"[^a-z, /-]", " ", phrase.lower())
    phrase = phrase.replace(" and ", ",").replace(" or ", ",").replace("/", ",")
    out: list[str] = []
    for part in phrase.split(","):
        part = part.strip().replace("non magical", "").replace("nonmagical", "")
        for dtype in DAMAGE_TYPES:
            if re.search(rf"\b{re.escape(dtype)}\b", part) and dtype not in out:
                out.append(dtype)
    return out


def _trait_grants_from_text(text: str) -> list[str]:
    plain = _strip_html(text).lower()
    grants: list[str] = []

    patterns = [
        ("dr", r"(?:resistance to|resistant to)\s+([a-z, /-]+?)\s+damage"),
        ("di", r"(?:immunity to|immune to)\s+([a-z, /-]+?)\s+damage"),
        ("dv", r"(?:vulnerability to|vulnerable to)\s+([a-z, /-]+?)\s+damage"),
    ]
    for prefix, pattern in patterns:
        for m in re.finditer(pattern, plain):
            for dtype in _split_damage_type_phrase(m.group(1)):
                grant = f"{prefix}:{dtype}"
                if grant not in grants:
                    grants.append(grant)

    for phrase, cond in CONDITION_WORDS.items():
        if cond not in CONDITION_TYPES:
            continue
        checks = [
            f"immune to {phrase}",
            f"immunity to {phrase}",
            f"immune to being {phrase}",
            f"immune to the {phrase} condition",
        ]
        if any(c in plain for c in checks):
            grant = f"ci:{cond}"
            if grant not in grants:
                grants.append(grant)
    return grants


def _native_trait_grants(
    e: AuroraElement,
    feature_docs_by_aurora_id: dict[str, dict] | None = None,
    grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None,
) -> list[str]:
    grants: list[str] = []

    def add_many(items: list[str]):
        for item in items:
            if item and item not in grants:
                grants.append(item)

    add_many(_condition_grants_from_rules(_effective_rules(e, grant_elements_by_aurora_id)))
    add_many(_trait_grants_from_text(e.description_html))

    feature_docs_by_aurora_id = feature_docs_by_aurora_id or {}
    for aurora_id, _level in _extract_trait_grants(e, grant_elements_by_aurora_id):
        doc = feature_docs_by_aurora_id.get(aurora_id)
        if not doc:
            continue
        flags = doc.get("flags", {}).get("aurora", {})
        add_many(_condition_grants_from_rules(flags.get("rules", []) or []))
        desc = doc.get("system", {}).get("description", {}).get("value", "")
        add_many(_trait_grants_from_text(desc))
    return grants


def _infer_senses(
    e: AuroraElement,
    feature_docs_by_aurora_id: dict[str, dict] | None = None,
    grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None,
) -> dict:
    ranges = {"darkvision": None, "blindsight": None, "tremorsense": None, "truesight": None}
    all_rules = _effective_rules(e, grant_elements_by_aurora_id) + _feature_rules_for_granted_traits(e, feature_docs_by_aurora_id, grant_elements_by_aurora_id)
    for rule in all_rules:
        attrs = rule.get("attrs", {}) or {}
        tag = (rule.get("tag") or "").lower()
        if tag == "grant" and (attrs.get("type") or "").lower() == "vision":
            ident = (attrs.get("id") or "").upper()
            if "SUPERIORDARKVISION" in ident:
                ranges["darkvision"] = max(ranges["darkvision"] or 0, 120)
            elif "DARKVISION" in ident:
                ranges["darkvision"] = max(ranges["darkvision"] or 0, 60)
            elif "BLINDSIGHT" in ident:
                ranges["blindsight"] = max(ranges["blindsight"] or 0, 10)
            elif "TRUESIGHT" in ident:
                ranges["truesight"] = max(ranges["truesight"] or 0, 60)
            continue
        if tag != "stat":
            continue
        name = (attrs.get("name") or "").lower()
        for sense in SENSE_KEYS:
            if name in {f"{sense}:range", sense}:
                try:
                    ranges[sense] = max(ranges[sense] or 0, int(str(attrs.get("value") or 0)))
                except ValueError:
                    pass
            elif name == f"{sense}:increase":
                try:
                    ranges[sense] = (ranges[sense] or 0) + int(str(attrs.get("value") or 0))
                except ValueError:
                    pass
    text = " ".join([_strip_html(e.description_html).lower()] + [
        _strip_html((feature_docs_by_aurora_id or {}).get(fid, {}).get("system", {}).get("description", {}).get("value", "")).lower()
        for fid, _level in _extract_trait_grants(e, grant_elements_by_aurora_id)
    ])
    for sense in SENSE_KEYS:
        # darkvision out to 60 feet / truesight out to a range of 120 feet / blindsight 10 feet
        patterns = [
            rf"{sense}\s+(?:out to|to|within)\s+(?:a range of\s+)?(\d+)\s*(?:feet|foot|ft)",
            rf"(\d+)\s*(?:feet|foot|ft)\s+of\s+{sense}",
        ]
        if sense == "darkvision":
            patterns.append(r"dim light within\s+(\d+)\s*(?:feet|foot|ft)")
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                ranges[sense] = max(ranges[sense] or 0, int(m.group(1)))
    return {"ranges": ranges, "units": "ft", "special": ""}


def _ability_notes(e: AuroraElement, grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None) -> list[str]:
    notes: list[str] = []
    for rule in _effective_rules(e, grant_elements_by_aurora_id):
        attrs = rule.get("attrs", {}) or {}
        tag = (rule.get("tag") or "").lower()
        if tag == "stat":
            name = attrs.get("name", "")
            value = attrs.get("value", "")
            if name and value:
                notes.append(f"stat {name} += {value}")
        elif tag == "select":
            typ = attrs.get("type", "?")
            count = attrs.get("number") or attrs.get("count") or ""
            notes.append(f"select {typ} count={count}")
        elif tag == "grant":
            typ = attrs.get("type", "?")
            ident = attrs.get("id", "")
            if typ.lower() != "racial trait":
                notes.append(f"grant {typ} {ident}")
    return notes


def _advancements(
    e: AuroraElement,
    feature_uuid_by_aurora_id: dict[str, str] | None = None,
    feature_docs_by_aurora_id: dict[str, dict] | None = None,
    grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None,
) -> tuple[dict, list[str], list[str]]:
    seed = f"species:{e.id or e.name}:{e.source_code}"
    out: dict[str, dict] = {}

    def add(doc: dict):
        out[doc["_id"]] = doc

    sizes = _infer_sizes(e, grant_elements_by_aurora_id)
    add(adv.size_advancement(seed, sizes=sizes, title="Size"))

    fixed_asi = _fixed_ability_scores(e, grant_elements_by_aurora_id)
    selectable_points = _selectable_ability_points(e, grant_elements_by_aurora_id)
    if fixed_asi or selectable_points:
        add(adv.species_ability_score_improvement(seed, fixed=fixed_asi, points=selectable_points, title="Ability Score Increase"))

    language_grants, missing_languages = _language_grants(e, grant_elements_by_aurora_id)
    language_choices = _language_choices(e, grant_elements_by_aurora_id)
    if language_grants or language_choices:
        add(adv.trait(seed, grants=language_grants, choices=language_choices, level=1, title="Languages"))

    native_grants = _native_trait_grants(e, feature_docs_by_aurora_id, grant_elements_by_aurora_id)
    if native_grants:
        add(adv.trait(seed, grants=native_grants, level=1, title="Resistances, Immunities, and Vulnerabilities"))

    missing_traits: list[str] = []
    if feature_uuid_by_aurora_id is not None:
        grouped: dict[int, list[str]] = {}
        for aurora_id, level in _extract_trait_grants(e, grant_elements_by_aurora_id):
            uuid = feature_uuid_by_aurora_id.get(aurora_id)
            if not uuid:
                if "CORE_LINEAGE_CREATURE_TYPE" not in aurora_id:
                    missing_traits.append(aurora_id)
                continue
            grouped.setdefault(level, []).append(uuid)
        for level, uuids in sorted(grouped.items()):
            add(adv.item_grant(seed, uuids, level=level, title="Racial Traits"))

    return out, missing_traits, missing_languages


def compile_species(
    e: AuroraElement,
    include_source_name: bool = True,
    long_source: bool = False,
    feature_uuid_by_aurora_id: dict[str, str] | None = None,
    feature_docs_by_aurora_id: dict[str, dict] | None = None,
    grant_elements_by_aurora_id: dict[str, AuroraElement] | None = None,
) -> dict:
    name = e.display_name(include_source_name, long_source=long_source)
    base_name = clean_duplicate_name(e.name)
    item = base_item(name, "race", "icons/svg/mystery-man.svg")
    advancement, missing_traits, missing_languages = _advancements(e, feature_uuid_by_aurora_id, feature_docs_by_aurora_id, grant_elements_by_aurora_id)
    size = _infer_size(e, grant_elements_by_aurora_id)
    movement = _infer_movement(e, feature_docs_by_aurora_id, grant_elements_by_aurora_id)
    senses = _infer_senses(e, feature_docs_by_aurora_id, grant_elements_by_aurora_id)
    native_grants = _native_trait_grants(e, feature_docs_by_aurora_id, grant_elements_by_aurora_id)

    item["system"] = {
        "description": {"value": e.description_html, "chat": ""},
        "source": {"custom": e.source, "book": e.source_code, "page": "", "license": "", "rules": "2014", "revision": 1},
        "identifier": slugify(base_name),
        "advancement": advancement,
        "movement": movement,
        "senses": senses,
        "size": size,
        "type": {"value": "humanoid", "subtype": "subrace" if e.type == "Sub Race" else ""},
        "properties": [],
    }
    item["flags"] = {
        "aurora": {
            "id": e.id,
            "source": e.source,
            "sourceCode": e.source_code,
            "file": e.file,
            "type": e.type,
            "rules": e.rules,
            "effectiveRules": _effective_rules(e, grant_elements_by_aurora_id),
            "setters": e.setters,
            "supports": e.supports,
            "compiler": "species-v1.3",
            "inferredSize": size,
            "inferredSizes": _infer_sizes(e, grant_elements_by_aurora_id),
            "inferredMovement": movement,
            "inferredSenses": senses,
            "selectableAbilityScorePoints": _selectable_ability_points(e, grant_elements_by_aurora_id),
            "nativeTraitGrants": native_grants,
            "missingRacialTraitGrants": missing_traits,
            "missingLanguageGrants": missing_languages,
            "nativeRuleNotes": _ability_notes(e, grant_elements_by_aurora_id),
            "expandedGrants": [
                (rule.get("attrs", {}) or {}).get("id", "")
                for rule in e.rules or []
                if (rule.get("tag") or "").lower() == "grant" and ((rule.get("attrs", {}) or {}).get("type") or "").lower() == "grants"
            ],
        }
    }
    return item
