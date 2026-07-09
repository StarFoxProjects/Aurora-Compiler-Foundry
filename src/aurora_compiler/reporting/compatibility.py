from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
import csv
import html
import json
import re

from aurora_compiler.models.aurora import AuroraElement


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "")


def _compact(text: str, limit: int = 240) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _flags(doc: dict) -> dict:
    return doc.get("flags", {}).get("aurora", {}) or {}


def _rules(doc: dict) -> list[dict]:
    return _flags(doc).get("rules", []) or []


def _description(doc: dict) -> str:
    return _strip_html(doc.get("system", {}).get("description", {}).get("value", ""))


def _activities(doc: dict) -> dict:
    return doc.get("system", {}).get("activities", {}) or {}


def _advancements(doc: dict) -> list[dict]:
    adv = doc.get("system", {}).get("advancement", {}) or {}
    if isinstance(adv, dict):
        return [v for v in adv.values() if isinstance(v, dict)]
    if isinstance(adv, list):
        return [v for v in adv if isinstance(v, dict)]
    return []


def _activity_summary(doc: dict) -> dict[str, Any]:
    acts = _activities(doc)
    out = {
        "count": len(acts),
        "types": Counter(),
        "hasDamage": False,
        "hasSave": False,
        "hasHeal": False,
        "hasSummon": False,
        "hasTemplate": False,
        "hasAttack": False,
    }
    for act in acts.values():
        typ = act.get("type", "unknown")
        out["types"][typ] += 1
        damage_parts = act.get("damage", {}).get("parts", []) if isinstance(act.get("damage"), dict) else []
        if damage_parts:
            out["hasDamage"] = True
        save = act.get("save", {}) if isinstance(act.get("save"), dict) else {}
        if save.get("ability"):
            out["hasSave"] = True
        healing = act.get("healing", {}) if isinstance(act.get("healing"), dict) else {}
        if healing.get("number") or healing.get("formula") or typ in {"heal"}:
            out["hasHeal"] = True
        if typ == "summon":
            out["hasSummon"] = True
        target = act.get("target", {}) if isinstance(act.get("target"), dict) else {}
        template = target.get("template", {}) if isinstance(target, dict) else {}
        if isinstance(template, dict) and template.get("type"):
            out["hasTemplate"] = True
        attack = act.get("attack", {}) if isinstance(act.get("attack"), dict) else {}
        if attack or typ in {"attack"}:
            out["hasAttack"] = True
    out["types"] = dict(out["types"])
    return out


def _advancement_summary(doc: dict) -> dict[str, Any]:
    advs = _advancements(doc)
    types = Counter(a.get("type", "unknown") for a in advs)
    item_choices = []
    item_grants = 0
    empty_item_choices = []
    for a in advs:
        if a.get("type") == "ItemChoice":
            pool = a.get("configuration", {}).get("pool", []) or []
            row = {"title": a.get("title", ""), "level": a.get("level", ""), "poolSize": len(pool)}
            item_choices.append(row)
            if not pool:
                empty_item_choices.append(row)
        if a.get("type") == "ItemGrant":
            item_grants += 1
    return {
        "count": len(advs),
        "types": dict(types),
        "itemChoiceCount": len(item_choices),
        "itemChoices": item_choices,
        "emptyItemChoices": empty_item_choices,
        "itemGrantCount": item_grants,
    }


def _doc_row(pack: str, doc: dict) -> dict[str, str]:
    f = _flags(doc)
    return {
        "pack": pack,
        "name": doc.get("name", ""),
        "foundryType": doc.get("type", ""),
        "auroraType": f.get("type", ""),
        "source": f.get("sourceCode") or f.get("source") or "",
        "auroraId": f.get("id", ""),
        "compiler": f.get("compiler", ""),
    }


def _issue(issues: list[dict[str, str]], severity: str, area: str, pack: str, doc: dict, problem: str, recommendation: str, issue_kind: str = "backend-gap", backend: str = "", priority: str | None = None) -> None:
    row = _doc_row(pack, doc)
    priority = priority or _priority_for(severity, issue_kind)
    row.update({
        "severity": severity,
        "priority": priority,
        "area": area,
        "issueKind": issue_kind,
        "backend": backend or recommendation,
        "problem": problem,
        "recommendation": recommendation,
    })
    issues.append(row)


def _lower_text(doc: dict) -> str:
    f = _flags(doc)
    rules_text = " ".join(
        " ".join(str(v) for v in (r.get("attrs", {}) or {}).values()) + " " + str(r.get("tag", ""))
        for r in _rules(doc)
    )
    return f"{doc.get('name','')} {_description(doc)} {rules_text} {json.dumps(f, ensure_ascii=False)}".lower()


def _has_words(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


ABILITY_WORDS = {"strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"}
MOVEMENT_WORDS = {"flying speed", "fly speed", "climbing speed", "climb speed", "swimming speed", "swim speed", "burrowing speed", "burrow speed", "walking speed", "walk speed", "speed, 5 feet", "speed, 10 feet", "speed, 15 feet", "speed, 20 feet", "speed, 25 feet", "speed, 30 feet", "speed, 35 feet", "speed, 40 feet", "speed, 45 feet", "speed, 50 feet"}
SENSE_WORDS = {"darkvision", "superior darkvision", "blindsight", "truesight", "tremorsense"}
TRAIT_WORDS = {"resistance", "immunity", "vulnerability", "damage resistance", "damage immunity", "condition immunity"}
LANGUAGE_WORDS = {"language", "languages", "speak", "read", "write"}
PROFICIENCY_WORDS = {"proficiency", "proficiencies", "training", "weapon training", "armor training", "tool proficiency", "skill proficiency"}

SPELL_GRANT_NAME_PATTERNS = (
    "oath spells", "domain spells", "circle spells", "patron spells",
    "expanded spell list", "expanded spells", "psionic spells", "origin spells",
    "bloodline spells", "always prepared", "additional spells",
    "innate spellcasting", "racial spellcasting", "magic of", "fairy magic",
    "duergar magic", "drow magic", "hex magic", "dragonmark spells",
    "spells of the mark", "mark spells", "artillerist spells",
    "alchemist spells", "battle smith spells", "armorer spells",
)

SPELL_GRANT_TEXT_PATTERNS = (
    "you learn the", "you learn one", "you know the", "you can cast",
    "spell list", "without expending a spell slot", "always prepared",
    "added to the", "doesn't count against the number of spells",
    "do not count against the number of spells", "counts as an artificer spell",
)

SPELL_MODIFIER_NAME_PATTERNS = (
    "potent spellcasting", "empowered evocation", "arcane firearm",
    "alchemical savant", "spell breaker", "blessed healer",
)

TRUE_SUMMON_NAME_PATTERNS = (
    "eldritch cannon", "steel defender", "homunculus servant",
    "wildfire spirit", "drake companion", "primal companion",
    "ranger's companion", "beast companion", "find familiar",
    "strixhaven mascot", "dancing item",
)

TRUE_SUMMON_TEXT_PATTERNS = (
    "summon a", "summon the", "summon an", "conjure a", "conjure the",
    "create a cannon", "create the cannon", "create an eldritch cannon",
    "appears in an unoccupied space", "obeys your commands",
    "shares your initiative", "takes its turn immediately after yours",
    "acts on your initiative",
)

TRANSFORMATION_NAME_PATTERNS = (
    "shapechanger", "wild shape", "starry form", "form of dread",
    "guardian model", "infiltrator model", "arcane armor",
    "rage", "shifting feature", "astral self", "arms of the astral self", "visage of the astral self", "awakened astral self",
)

TRANSFORMATION_TEXT_PATTERNS = (
    "transform", "assume the form", "change your form", "while transformed",
    "your game statistics", "retain your game statistics", "while your starry form is active",
)

AURA_NAME_PATTERNS = (
    "aura", "boon aura", "twilight sanctuary", "spirit shield",
)

CRAFTING_NAME_PATTERNS = (
    "cunning artisan", "magical tinkering", "right tool for the job", "tools required",
    "infuse item", "replicate magic item",
)

PASSIVE_OR_TRIGGERED_PATTERNS = (
    "when you hit", "whenever you hit", "when a creature", "when you take",
    "when you fail", "when you succeed", "once per turn", "damage roll",
    "damage rolls", "you add", "you can add", "add your", "extra damage",
    "bonus to the damage", "reduce the damage", "subtract", "reroll",
    "advantage", "disadvantage", "resistance", "immunity",
)


def _name_lower(doc: dict) -> str:
    return str(doc.get("name", "") or "").lower()


def _has_spell_rule(doc: dict) -> bool:
    for r in _rules(doc):
        attrs = r.get("attrs", {}) or {}
        joined = " ".join(str(v) for v in attrs.values()).lower()
        tag = str(r.get("tag", "")).lower()
        typ = str(attrs.get("type", "")).lower()
        if "spell" in tag or "spell" in typ or "_spell_" in joined or " id_spell" in joined or "id_wotc" in joined and "spell" in joined:
            return True
    return False


def _is_spell_grant_feature(doc: dict, text: str) -> bool:
    """Detect features that grant, prepare, or expand spells.

    v2.8 deliberately avoids broad words such as plain "spellcasting".
    Features like Potent Spellcasting and Spell Breaker modify rolls/effects;
    they do not grant spell choices and should not go to spell-grant-backend.
    """
    name = _name_lower(doc)
    aurora_id = str(_flags(doc).get("id", "")).lower()
    if any(p in name for p in SPELL_MODIFIER_NAME_PATTERNS):
        return False
    if any(p in name for p in SPELL_GRANT_NAME_PATTERNS):
        return True
    if "spells" in name and any(w in name for w in ["additional", "warlock", "wizard", "cleric", "paladin", "ranger", "druid", "bard", "sorcerer", "artificer", "oath", "domain", "circle", "patron", "swarmkeeper"]):
        return True
    if any(p.replace(" ", "_") in aurora_id for p in ("oath spells", "domain spells", "circle spells", "patron spells", "expanded spells", "artillerist spells", "alchemist spells", "battle smith spells")):
        return True
    if _has_spell_rule(doc) and any(p in text for p in SPELL_GRANT_TEXT_PATTERNS):
        return True
    return False


def _is_spell_modifier_feature(doc: dict, text: str) -> bool:
    name = _name_lower(doc)
    if any(p in name for p in SPELL_MODIFIER_NAME_PATTERNS):
        return True
    if "add your" in text and any(w in text for w in ["spell", "cantrip", "damage roll", "healing"]):
        return True
    return False


def _is_transformation_feature(doc: dict, text: str) -> bool:
    name = _name_lower(doc)
    return any(p in name for p in TRANSFORMATION_NAME_PATTERNS) or any(p in text for p in TRANSFORMATION_TEXT_PATTERNS)


def _is_aura_feature(doc: dict, text: str) -> bool:
    name = _name_lower(doc)
    return any(p in name for p in AURA_NAME_PATTERNS) or _has_words(text, ["aura", "emanation", "within 10 feet", "within 30 feet", "while within", "creatures of your choice"] )


def _is_true_summon_feature(doc: dict, text: str) -> bool:
    """Detect true companion/token/summon features.

    v2.8 is intentionally stricter: names like Shapechanger, Starry Form,
    Improved Defender or Boon Aura may need automation, but they are not the
    same as creating a separate controllable actor/token.
    """
    name = _name_lower(doc)
    aurora_id = str(_flags(doc).get("id", "")).lower()
    if _is_spell_grant_feature(doc, text) or _is_transformation_feature(doc, text):
        return False
    if any(p in name for p in TRUE_SUMMON_NAME_PATTERNS):
        return True
    if any(p.replace(" ", "_") in aurora_id for p in TRUE_SUMMON_NAME_PATTERNS):
        return True
    if any(p in text for p in TRUE_SUMMON_TEXT_PATTERNS):
        # Require an actual token-like clue, not only generic stat-block language.
        return True
    return False


def _is_crafting_or_option_feature(doc: dict, text: str) -> bool:
    name = _name_lower(doc)
    return any(p in name for p in CRAFTING_NAME_PATTERNS) or any(p in text for p in CRAFTING_NAME_PATTERNS)


def _is_passive_or_triggered_modifier_feature(doc: dict, text: str) -> bool:
    """Features that should not become ordinary click activities.

    v2.8 separates passive/conditional text from clear rollable features. A lot
    of the v2.4 P1 feature bucket was technically real work, but not the Feature
    Activity backend: text like "when you hit, add extra damage" needs Active
    Effects, manual prompts, or JS hooks rather than a standalone button.
    """
    name = _name_lower(doc)
    if any(p in name for p in ("potent spellcasting", "divine strike", "brutal critical", "sneak attack", "improved divine smite")):
        return True
    return any(p in text for p in PASSIVE_OR_TRIGGERED_PATTERNS)


def _helper_classification(doc: dict, text: str) -> tuple[str, str] | None:
    """Classify Aurora helper features that should normally be absorbed into a parent document.

    Aurora often models atomic choices as features: "Flying Speed, 30 feet",
    "Wisdom", "Darkvision", language helpers, etc. Those are not normally
    user-facing Foundry features. They should become movement, senses, ASI,
    languages, proficiencies, or traits on the species/class/subclass item.
    """
    name = _name_lower(doc).strip()
    compact_name = re.sub(r"\s+", " ", name)
    compact_name_core = re.sub(r"\s*\([a-z0-9'’ :.-]+\)\s*$", "", compact_name).strip()
    exact_ability = compact_name_core in ABILITY_WORDS
    if exact_ability or any(f"{a} +" in text or f"increase your {a}" in text for a in ABILITY_WORDS):
        return ("absorbed-helper:ability-score", "Absorb into AbilityScoreImprovement advancement or fixed ability grant")
    if any(w in compact_name_core for w in MOVEMENT_WORDS) or re.search(r"\b(fly|flying|climb|climbing|swim|swimming|burrow|burrowing) speed\b", text):
        return ("absorbed-helper:movement", "Absorb into system.movement on the parent species/feature")
    if any(w in compact_name_core for w in SENSE_WORDS) or any(w in text for w in SENSE_WORDS):
        return ("absorbed-helper:senses", "Absorb into system.senses on the parent species/feature")
    if any(w in compact_name_core for w in TRAIT_WORDS) or any(w in text for w in TRAIT_WORDS):
        return ("absorbed-helper:traits", "Absorb into system.traits dr/di/dv/ci on the parent document")
    if any(w in compact_name_core for w in LANGUAGE_WORDS) or ("common" in text and any(w in text for w in LANGUAGE_WORDS)):
        return ("absorbed-helper:languages", "Absorb into language Trait advancement")
    if any(w in compact_name_core for w in PROFICIENCY_WORDS) or any(w in text for w in PROFICIENCY_WORDS):
        return ("absorbed-helper:proficiency", "Absorb into Trait advancement for skills/tools/weapons/armor")
    if "subrace" in compact_name_core or "ancestral legacy" in compact_name_core:
        return ("absorbed-helper:choice", "Absorb into parent species variant/choice handling")
    return None


def _backend_classification(doc: dict, text: str, act: dict, adv: dict, pack: str) -> tuple[str, str, str]:
    """Return issueKind, recommended backend, priority.

    v2.8 separates real backend families more cleanly so the report becomes a
    work map rather than one huge "missing activity" pile.
    """
    helper = _helper_classification(doc, text)
    if helper:
        return helper[0], helper[1], "P3"
    if _is_spell_grant_feature(doc, text):
        return "spell-grant-backend", "Compile granted/prepared/expanded spell lists as ItemGrant/ItemChoice or spell-list metadata", "P1"
    if _is_true_summon_feature(doc, text):
        return "needs-summon-backend", "Compile an actor/token plus summon activity for true companion/cannon/familiar/servant features", "P1"
    if _is_transformation_feature(doc, text):
        return "needs-transformation-backend", "Represent form/shape/model states with Active Effects, item choices, or manual state notes", "P2"
    if _is_aura_feature(doc, text):
        return "needs-aura-backend", "Use Active Effects where possible; custom JS may be needed for live aura/conditional automation", "P2"
    if _is_spell_modifier_feature(doc, text):
        return "needs-active-effect-or-js", "Compile passive spell/damage/healing modifiers as Active Effects where possible; flag complex triggers for JS/manual handling", "P2"
    if _is_crafting_or_option_feature(doc, text):
        return "choice-or-crafting-backend", "Compile crafting/options/replication choices as ItemChoice or manual utility notes, not summon", "P2"
    if _is_passive_or_triggered_modifier_feature(doc, text):
        return "needs-active-effect-or-js", "Compile passive/triggered modifiers as Active Effects where possible; flag complex triggers for JS/manual handling", "P2"
    if _has_words(text, ["reaction", "when you", "whenever", "once per turn", "reroll", "reduce the damage", "add your", "subtract", "advantage", "disadvantage"]):
        return "needs-active-effect-or-js", "Compile passive/conditional Active Effects; flag complex triggers for JS/manual handling", "P2"
    if _has_words(text, ["saving throw", "damage", "regain hit points", "temporary hit points", "temporary hp", "spell attack", "melee weapon attack", "ranged weapon attack"]):
        return "real-missing-activity", "Generate native Foundry activity: attack/save/damage/heal/template/uses", "P1"
    if pack == "equipment" or doc.get("type") in {"equipment", "weapon", "consumable", "tool", "loot"}:
        return "magic-item-backend", "Parse attunement, charges, activities and effects", "P2"
    return "backend-gap", "Needs a dedicated compiler backend or a safe manual/no-op classification", "P2"


def _priority_for(severity: str, issue_kind: str) -> str:
    if issue_kind.startswith("absorbed-helper"):
        return "P3"
    if severity == "critical":
        return "P0"
    if severity == "high":
        return "P1"
    if severity == "medium":
        return "P2"
    return "P3"




def _species_text_explicitly_grants_flight(text: str) -> bool:
    """Return True only when a species text/rule appears to grant a fly speed.

    v2.8 fixes the v2.3 broad ``"fly" in text`` check, which flooded the report with
    false positives (for example species whose descriptions merely mention
    flying creatures, or whose granted spells include fly-related words). The
    compatibility report should only flag missing fly speed when the species
    itself looks like it grants movement.flight.
    """
    if not text:
        return False
    patterns = [
        r"\bflying speed\b",
        r"\bfly speed\b",
        r"\bspeed of \d+ feet.*\bfly",
        r"\byou have a flying speed\b",
        r"\byou gain a flying speed\b",
        r"\byou have a fly speed\b",
        r"\byou gain a fly speed\b",
        r"\bwalking speed.*flying speed\b",
        r"\bflying speed equal to your walking speed\b",
        r"\bfly speed equal to your walking speed\b",
    ]
    return any(re.search(p, text) for p in patterns)


def _system_traits(doc: dict) -> dict:
    return doc.get("system", {}).get("traits", {}) or {}


def _movement(doc: dict) -> dict:
    return doc.get("system", {}).get("movement", {}) or {}


def _senses(doc: dict) -> dict:
    return doc.get("system", {}).get("senses", {}) or {}


def build_compatibility_map(elements: list[AuroraElement], packs: dict[str, list[dict]], skipped: list[dict] | None = None) -> dict[str, Any]:
    """Build a human-oriented compatibility map between Aurora XML and Foundry dnd5e output.

    This report is intentionally heuristic. It identifies areas that are likely
    text-only or incomplete so they can be prioritized by compiler backends.
    """
    skipped = skipped or []
    docs = [(pack, doc) for pack, ds in (packs or {}).items() for doc in (ds or [])]

    input_by_type = Counter(e.type or "Unknown" for e in elements)
    input_by_source = Counter(e.source_code or "Unknown" for e in elements)
    output_by_pack = Counter(pack for pack, _ in docs)
    output_by_type = Counter(doc.get("type", "unknown") for _, doc in docs)
    activity_types = Counter()
    advancement_types = Counter()
    issues: list[dict[str, str]] = []

    class_map: list[dict[str, Any]] = []
    subclass_map: list[dict[str, Any]] = []
    species_map: list[dict[str, Any]] = []
    spell_map: list[dict[str, Any]] = []
    feature_map: list[dict[str, Any]] = []
    equipment_map: list[dict[str, Any]] = []
    summon_map: list[dict[str, Any]] = []

    for pack, doc in docs:
        act = _activity_summary(doc)
        adv = _advancement_summary(doc)
        activity_types.update(act["types"])
        advancement_types.update(adv["types"])
        text = _lower_text(doc)
        rules = _rules(doc)
        foundry_type = doc.get("type", "")
        base = _doc_row(pack, doc)

        if foundry_type == "class":
            row = dict(base)
            row.update({
                "advancementCount": adv["count"],
                "advancementTypes": adv["types"],
                "hasSubclassChoice": adv["types"].get("Subclass", 0) > 0,
                "itemChoices": adv["itemChoices"],
                "emptyItemChoices": adv["emptyItemChoices"],
                "itemGrantCount": adv["itemGrantCount"],
                "spellcastingProgression": doc.get("system", {}).get("spellcasting", {}).get("progression", ""),
            })
            class_map.append(row)
            if adv["count"] == 0:
                _issue(issues, "critical", "classes", pack, doc, "Class has no advancement data", "Generate HitPoints/Trait/ItemGrant/Subclass/ASI advancement")
            if adv["emptyItemChoices"]:
                _issue(issues, "high", "classes", pack, doc, "Class has ItemChoice advancement with empty pool", "Build the UUID pool or remove the picker")
            if not row["hasSubclassChoice"] and "class" in (base["auroraType"] or "").lower():
                _issue(issues, "medium", "classes", pack, doc, "Class has no subclass picker", "Add Subclass advancement when the class has archetypes")

        elif foundry_type == "subclass":
            row = dict(base)
            row.update({
                "classIdentifier": doc.get("system", {}).get("classIdentifier", ""),
                "advancementCount": adv["count"],
                "advancementTypes": adv["types"],
                "itemGrantCount": adv["itemGrantCount"],
            })
            subclass_map.append(row)
            if not row["classIdentifier"]:
                _issue(issues, "critical", "subclasses", pack, doc, "Subclass has no classIdentifier", "Map Aurora archetype/support to Foundry parent class identifier")
            if adv["count"] == 0 and rules:
                _issue(issues, "high", "subclasses", pack, doc, "Subclass has Aurora rules but no advancement", "Generate ItemGrant/ItemChoice advancement for subclass features and spells")

        elif foundry_type == "race":
            traits = _system_traits(doc)
            row = dict(base)
            row.update({
                "advancementCount": adv["count"],
                "advancementTypes": adv["types"],
                "movement": _movement(doc),
                "senses": _senses(doc),
                "damageResistances": traits.get("dr", {}).get("value", []),
                "damageImmunities": traits.get("di", {}).get("value", []),
                "conditionImmunities": traits.get("ci", {}).get("value", []),
                "damageVulnerabilities": traits.get("dv", {}).get("value", []),
            })
            species_map.append(row)
            if adv["count"] == 0:
                _issue(issues, "high", "species", pack, doc, "Species/race has no advancement", "Generate Size/ASI/Languages/Traits advancement")
            if _species_text_explicitly_grants_flight(text) and not (_movement(doc).get("fly") or 0):
                _issue(issues, "high", "species", pack, doc, "Species text/rules grant flying speed but native fly speed is empty", "Parse movement.fly from Aurora rules/text")
            if "darkvision" in text and not (_senses(doc).get("darkvision") or 0):
                _issue(issues, "medium", "species", pack, doc, "Text/rules mention darkvision but native sense is empty", "Parse senses.darkvision")
            if "resistance" in text and not row["damageResistances"]:
                _issue(issues, "medium", "species", pack, doc, "Text/rules mention resistance but native resistance list is empty", "Parse traits.dr")
            if "immunity" in text and not (row["damageImmunities"] or row["conditionImmunities"]):
                _issue(issues, "medium", "species", pack, doc, "Text/rules mention immunity but native immunity lists are empty", "Parse traits.di/traits.ci")

        elif foundry_type == "spell":
            row = dict(base)
            row.update({
                "level": doc.get("system", {}).get("level", ""),
                "school": doc.get("system", {}).get("school", ""),
                "activityCount": act["count"],
                "activityTypes": act["types"],
                "hasDamage": act["hasDamage"],
                "hasSave": act["hasSave"],
                "hasHeal": act["hasHeal"],
                "hasTemplate": act["hasTemplate"],
                "properties": doc.get("system", {}).get("properties", []),
            })
            spell_map.append(row)
            if act["count"] == 0:
                _issue(issues, "critical", "spells", pack, doc, "Spell has no activity", "Generate cast/attack/save/heal/summon activity", "spell-activity-backend", "Generate native spell activity")
            if "saving throw" in text and not act["hasSave"]:
                _issue(issues, "high", "spells", pack, doc, "Spell text mentions saving throw but activity has no native save", "Parse save ability and DC calculation", "spell-save-backend", "Parse save ability and DC calculation", "P1")
            if "damage" in text and not act["hasDamage"]:
                _issue(issues, "high", "spells", pack, doc, "Spell text mentions damage but activity has no native damage", "Parse damage parts and scaling", "spell-damage-backend", "Parse damage parts and scaling", "P1")
            if _has_words(text, ["regain hit points", "healing", "temporary hit points", "temporary hp"]) and not act["hasHeal"]:
                _issue(issues, "high", "spells", pack, doc, "Spell text mentions healing/temp HP but has no heal activity", "Generate healing/temphp activity", "spell-healing-backend", "Generate healing/temphp activity", "P1")
            if _has_words(text, ["cone", "sphere", "cube", "line", "cylinder", "radius"]) and not act["hasTemplate"]:
                _issue(issues, "medium", "spells", pack, doc, "Spell text mentions area/template but activity has no measured template", "Parse target.template", "spell-template-backend", "Parse target.template", "P2")

        elif foundry_type == "feat":
            row = dict(base)
            row.update({
                "activityCount": act["count"],
                "activityTypes": act["types"],
                "advancementCount": adv["count"],
                "advancementTypes": adv["types"],
                "hasRules": bool(rules),
                "nativeRuleNotes": _flags(doc).get("nativeRuleNotes", []) or [],
            })
            # Classify Aurora helper features separately from real automation gaps.
            # This is the core v2.0 noise reduction: many high-count Aurora
            # entries such as "Flying Speed, 30 feet" should be absorbed into
            # movement/senses/traits instead of becoming user-facing Foundry features.
            helper = _helper_classification(doc, text)
            is_spell_grant = _is_spell_grant_feature(doc, text)
            if helper:
                row.update({"issueKind": helper[0], "recommendedBackend": helper[1], "priority": "P3"})
            else:
                kind, backend, priority = _backend_classification(doc, text, act, adv, pack)
                row.update({"issueKind": kind, "recommendedBackend": backend, "priority": priority})
            feature_map.append(row)
            if rules and act["count"] == 0 and adv["count"] == 0:
                kind, backend, priority = _backend_classification(doc, text, act, adv, pack)
                sev = "low" if kind.startswith("absorbed-helper") else "high"
                _issue(issues, sev, "features", pack, doc, "Feature has Aurora rules but no native Foundry activity/advancement", backend, kind, backend, priority)
            if _has_words(text, ["bonus action", "reaction", "action", "once per", "short rest", "long rest"]) and act["count"] == 0 and not helper and not is_spell_grant:
                kind, backend, priority = _backend_classification(doc, text, act, adv, pack)
                _issue(issues, "medium", "features", pack, doc, "Feature appears usable but has no activity", backend, kind, backend, priority)
            if _has_words(text, ["saving throw"]) and not act["hasSave"] and not helper and not is_spell_grant:
                kind, backend, priority = _backend_classification(doc, text, act, adv, pack)
                _issue(issues, "medium", "features", pack, doc, "Feature mentions saving throw but no native save", backend, kind, backend, priority)
            if _has_words(text, ["damage"]) and not act["hasDamage"] and not helper and not is_spell_grant:
                kind, backend, priority = _backend_classification(doc, text, act, adv, pack)
                _issue(issues, "medium", "features", pack, doc, "Feature mentions damage but no native damage", backend, kind, backend, priority)
            if _has_words(text, ["temporary hit points", "temporary hp", "regain hit points", "healing"]) and not act["hasHeal"] and not helper and not is_spell_grant:
                kind, backend, priority = _backend_classification(doc, text, act, adv, pack)
                _issue(issues, "medium", "features", pack, doc, "Feature mentions healing/temp HP but no native heal activity", backend, kind, backend, priority)
            if _is_true_summon_feature(doc, text) and not act["hasSummon"] and pack != "summons" and not helper:
                kind, backend, priority = _backend_classification(doc, text, act, adv, pack)
                _issue(issues, "medium", "features", pack, doc, "Feature may create or control another token but has no summon backend", backend, kind, backend, priority)

        elif pack == "equipment" or foundry_type in {"equipment", "weapon", "consumable", "tool", "loot"}:
            uses = doc.get("system", {}).get("uses", {}) or {}
            row = dict(base)
            row.update({
                "activityCount": act["count"],
                "activityTypes": act["types"],
                "attunement": doc.get("system", {}).get("attunement", ""),
                "usesMax": uses.get("max", ""),
                "equipped": doc.get("system", {}).get("equipped", ""),
                "rarity": doc.get("system", {}).get("rarity", ""),
            })
            equipment_map.append(row)
            if "requires attunement" in text and not row["attunement"]:
                _issue(issues, "medium", "equipment", pack, doc, "Item text says requires attunement but native attunement is empty", "Parse attunement")
            if _has_words(text, ["charges", "charge", "once per", "regains", "dawn"]) and not row["usesMax"]:
                _issue(issues, "medium", "equipment", pack, doc, "Item appears to have charges/uses but native uses are empty", "Parse uses/recovery")
            if _has_words(text, ["spell attack", "saving throw", "damage", "heal", "temporary hit points"]) and act["count"] == 0:
                _issue(issues, "medium", "equipment", pack, doc, "Item appears usable but has no activity", "Generate attack/save/damage/heal activity")
            if re.search(r"\+\s*[123]\b", doc.get("name", "") + " " + text) and not doc.get("effects"):
                _issue(issues, "low", "equipment", pack, doc, "Item may grant a numeric bonus but has no active effect", "Parse bonuses/effects where safe")

        if pack == "summons":
            items = doc.get("items", []) or []
            summon_map.append({
                **base,
                "actorType": doc.get("type", ""),
                "itemCount": len(items),
                "itemNames": [i.get("name", "") for i in items[:20]],
            })
            if not items:
                _issue(issues, "medium", "summons", pack, doc, "Summon actor has no abilities/items", "Compile actor features/activities")

    issue_counts = Counter((i["severity"], i["area"]) for i in issues)
    severity_counts = Counter(i["severity"] for i in issues)
    issue_kind_counts = Counter(i.get("issueKind", "unknown") for i in issues)
    priority_counts = Counter(i.get("priority", "unknown") for i in issues)
    backend_counts = Counter(i.get("backend", "unknown") for i in issues)
    absorbed_helpers = [i for i in issues if str(i.get("issueKind", "")).startswith("absorbed-helper")]
    real_issues = [i for i in issues if not str(i.get("issueKind", "")).startswith("absorbed-helper")]

    return {
        "schemaVersion": "2.6",
        "summary": {
            "inputElements": len(elements),
            "outputDocuments": len(docs),
            "inputByType": dict(input_by_type.most_common()),
            "inputBySource": dict(input_by_source.most_common()),
            "outputByPack": dict(output_by_pack.most_common()),
            "outputByFoundryType": dict(output_by_type.most_common()),
            "activityTypes": dict(activity_types.most_common()),
            "advancementTypes": dict(advancement_types.most_common()),
            "warnings": len(skipped),
            "issues": len(issues),
            "issuesBySeverity": dict(severity_counts),
            "issuesByPriority": dict(priority_counts),
            "issuesByKind": dict(issue_kind_counts),
            "issuesByBackend": dict(backend_counts.most_common()),
            "realIssues": len(real_issues),
            "absorbedHelpers": len(absorbed_helpers),
            "issuesBySeverityArea": {f"{sev}:{area}": count for (sev, area), count in issue_counts.items()},
        },
        "coverageByAuroraType": _coverage_by_aurora_type(elements, docs, skipped),
        "issues": issues,
        "realIssues": real_issues,
        "absorbedHelpers": absorbed_helpers,
        "classes": class_map,
        "subclasses": subclass_map,
        "species": species_map,
        "spells": spell_map,
        "features": feature_map,
        "equipment": equipment_map,
        "summons": summon_map,
        "warnings": skipped,
    }


def _coverage_by_aurora_type(elements: list[AuroraElement], docs: list[tuple[str, dict]], skipped: list[dict]) -> list[dict[str, Any]]:
    input_counts = Counter(e.type or "Unknown" for e in elements)
    output_counts = Counter((_flags(doc).get("type") or "Unknown") for _, doc in docs)
    skipped_counts = Counter(s.get("type") or "Unknown" for s in skipped or [])
    rows = []
    for typ in sorted(set(input_counts) | set(output_counts) | set(skipped_counts)):
        rows.append({
            "auroraType": typ,
            "input": input_counts.get(typ, 0),
            "compiled": output_counts.get(typ, 0),
            "skippedOrWarnings": skipped_counts.get(typ, 0),
        })
    return rows


def _clean_cell_value(v: Any) -> str:
    if isinstance(v, (dict, list)):
        v = json.dumps(v, ensure_ascii=False)
    v = "" if v is None else str(v)
    return v.replace("\r", " ").replace("\n", " ").replace("\t", " ").strip()


def _write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    """Write a spreadsheet-safe CSV.

    v1.9 reports could be painful to inspect when commas appeared in backend or
    recommendation text. v2.0 quotes every field explicitly so LibreOffice/Calc
    and simple parsers keep columns aligned.
    """
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
            quoting=csv.QUOTE_ALL,
        )
        w.writeheader()
        for row in rows:
            w.writerow({k: _clean_cell_value(row.get(k, "")) for k in fields})


def _write_tsv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    """Write a tab-separated version for easier terminal/LibreOffice import."""
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
            delimiter="\t",
            quoting=csv.QUOTE_MINIMAL,
        )
        w.writeheader()
        for row in rows:
            w.writerow({k: _clean_cell_value(row.get(k, "")) for k in fields})


def _write_table_pair(out: Path, stem: str, rows: list[dict[str, Any]], fields: list[str]) -> None:
    _write_csv(out / f"{stem}.csv", rows, fields)
    _write_tsv(out / f"{stem}.tsv", rows, fields)

def write_compatibility_reports(report: dict[str, Any], out_dir: str | Path) -> None:
    out = Path(out_dir)
    (out / "compatibility-map-v2.8.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    issue_fields = ["priority", "severity", "area", "issueKind", "backend", "pack", "name", "foundryType", "auroraType", "source", "auroraId", "problem", "recommendation"]
    _write_table_pair(out, "compatibility-issues-v2.8", report.get("issues", []), issue_fields)
    _write_table_pair(out, "compatibility-real-issues-v2.8", report.get("realIssues", []), issue_fields)
    _write_table_pair(out, "compatibility-absorbed-helpers-v2.8", report.get("absorbedHelpers", []), issue_fields)
    high_priority = [r for r in report.get("realIssues", []) if r.get("priority") in {"P0", "P1"}]
    _write_table_pair(out, "compatibility-real-issues-P0-P1-v2.8", high_priority, issue_fields)

    _write_table_pair(out, "compatibility-classes-v2.8", report.get("classes", []), [
        "pack", "name", "source", "auroraId", "advancementCount", "advancementTypes", "hasSubclassChoice", "itemChoices", "emptyItemChoices", "itemGrantCount", "spellcastingProgression",
    ])
    _write_table_pair(out, "compatibility-species-v2.8", report.get("species", []), [
        "pack", "name", "source", "auroraId", "advancementCount", "advancementTypes", "movement", "senses", "damageResistances", "damageImmunities", "conditionImmunities", "damageVulnerabilities",
    ])
    _write_table_pair(out, "compatibility-spells-v2.8", report.get("spells", []), [
        "pack", "name", "source", "auroraId", "level", "school", "activityCount", "activityTypes", "hasDamage", "hasSave", "hasHeal", "hasTemplate", "properties",
    ])
    _write_table_pair(out, "compatibility-features-v2.8", report.get("features", []), [
        "pack", "name", "source", "auroraId", "auroraType", "activityCount", "activityTypes", "advancementCount", "advancementTypes", "hasRules", "issueKind", "priority", "recommendedBackend", "nativeRuleNotes",
    ])
    _write_table_pair(out, "compatibility-equipment-v2.8", report.get("equipment", []), [
        "pack", "name", "source", "auroraId", "foundryType", "activityCount", "activityTypes", "attunement", "usesMax", "equipped", "rarity",
    ])

    (out / "compatibility-summary-v2.8.md").write_text(_markdown_summary(report), encoding="utf-8")
    (out / "compatibility-summary-v2.8.html").write_text(_html_summary(report), encoding="utf-8")
    (out / "compatibility-next-actions-v2.8.md").write_text(_next_actions_summary(report), encoding="utf-8")


def _markdown_summary(report: dict[str, Any]) -> str:
    s = report.get("summary", {})
    lines = [
        "# Aurora → Foundry Compatibility Map v2.8",
        "",
        "This is a compiler quality map, not a rules sourcebook. v2.8 introduces the Aurora Runtime architecture: compendium data can now mark activities that require Foundry-side JS automation such as targeted temporary HP, targeted healing, token-driven effects, and future active-effect workflows.",
        "",
        "## Summary",
        "",
        f"- Input Aurora elements: {s.get('inputElements', 0)}",
        f"- Output Foundry documents: {s.get('outputDocuments', 0)}",
        f"- Warnings/skipped references: {s.get('warnings', 0)}",
        f"- Compatibility entries found: {s.get('issues', 0)}",
        f"- Real compiler issues: {s.get('realIssues', 0)}",
        f"- Aurora helpers to absorb: {s.get('absorbedHelpers', 0)}",
        "",
        "## Issues by priority",
        "",
    ]
    for key in ["P0", "P1", "P2", "P3"]:
        lines.append(f"- {key}: {(s.get('issuesByPriority', {}) or {}).get(key, 0)}")
    lines += ["", "## Issues by severity",
        "",
    ]
    sev = s.get("issuesBySeverity", {}) or {}
    for key in ["critical", "high", "medium", "low"]:
        lines.append(f"- {key}: {sev.get(key, 0)}")
    lines += ["", "## Issues by kind", ""]
    for k, v in (s.get("issuesByKind", {}) or {}).items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Top backend targets", ""]
    for k, v in list((s.get("issuesByBackend", {}) or {}).items())[:12]:
        lines.append(f"- {k}: {v}")
    lines += ["", "## Output packs", ""]
    for k, v in (s.get("outputByPack", {}) or {}).items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Activity types", ""]
    for k, v in (s.get("activityTypes", {}) or {}).items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## Advancement types", ""]
    for k, v in (s.get("advancementTypes", {}) or {}).items():
        lines.append(f"- {k}: {v}")
    lines += ["", "## First real high-priority issues", ""]
    real_first = [x for x in report.get("realIssues", []) if x.get("priority") in {"P0", "P1"}][:80]
    for i in real_first:
        lines.append(f"- **{i.get('priority')} / {i.get('issueKind')} / {i.get('area')}** — {i.get('name')} ({i.get('source')}): {i.get('problem')}")
    lines += ["", "## First Aurora helpers to absorb", ""]
    for i in report.get("absorbedHelpers", [])[:40]:
        lines.append(f"- **{i.get('issueKind')} / {i.get('area')}** — {i.get('name')} ({i.get('source')}): {i.get('backend')}")
    lines += [
        "",
        "## Files generated",
        "",
        "- `compatibility-map-v2.8.json`: full machine-readable map",
        "- `compatibility-issues-v2.8.csv` and `.tsv`: full issue/helper list for spreadsheet filtering",
        "- `compatibility-real-issues-v2.8.csv` and `.tsv`: noise-reduced list of real compiler gaps",
        "- `compatibility-absorbed-helpers-v2.8.csv` and `.tsv`: Aurora helper entries that should be absorbed into parent docs",
        "- `compatibility-classes-v2.8.csv`",
        "- `compatibility-species-v2.8.csv`",
        "- `compatibility-spells-v2.8.csv`",
        "- `compatibility-features-v2.8.csv`",
        "- `compatibility-equipment-v2.8.csv`",
        "- `compatibility-real-issues-P0-P1-v2.8.tsv`: small high-priority work file",
        "- `compatibility-next-actions-v2.8.md`: suggested compiler roadmap",
    ]
    return "\n".join(lines) + "\n"



def _next_actions_summary(report: dict[str, Any]) -> str:
    s = report.get("summary", {})
    real = report.get("realIssues", []) or []
    p0p1 = [r for r in real if r.get("priority") in {"P0", "P1"}]
    by_backend = Counter(r.get("backend", "") for r in p0p1)
    by_area = Counter(r.get("area", "") for r in p0p1)
    by_kind = Counter(r.get("issueKind", "") for r in p0p1)
    lines = [
        "# v2.8 Compatibility Next Actions",
        "",
        "This file is meant to decide compiler work order. It ignores P2/P3 noise and focuses on P0/P1 real issues. v2.8 adds the first runtime layer, so the next work is deciding which Aurora rule shapes become plain Foundry data, which become Active Effects, and which require Aurora Runtime JS actions.",
        "",
        "## Counts",
        "",
        f"- Real issues: {s.get('realIssues', 0)}",
        f"- P0/P1 real issues: {len(p0p1)}",
        "",
        "## P0/P1 by area",
        "",
    ]
    for k, v in by_area.most_common():
        lines.append(f"- {k}: {v}")
    lines += ["", "## P0/P1 by issue kind", ""]
    for k, v in by_kind.most_common():
        lines.append(f"- {k}: {v}")
    lines += ["", "## P0/P1 backend targets", ""]
    for k, v in by_backend.most_common(20):
        lines.append(f"- {k}: {v}")
    p0_count = sum(1 for r in p0p1 if r.get("priority") == "P0")
    first_step = "1. **Subclass parent linker**: finish any remaining missing classIdentifier P0 rows." if p0_count else "1. **Subclass advancement cleanup**: only remaining subclass rows are missing advancement/grants, not missing parent classIdentifier."
    lines += [
        "",
        "## Recommended compiler roadmap",
        "",
        first_step,
        "2. **Feature activity backend**: parse action/bonus action/reaction, uses, damage, save and healing from class/subclass/species features.",
        "3. **Spell grant backend**: compile Oath/Domain/Circle/Patron/Innate spell grants into ItemGrant/ItemChoice or spell-list metadata.",
        "4. **Spell activity backend**: parse damage, save, healing and templates into native Foundry activities.",
        "5. **Summon backend**: build actors/tokens and summon activities only for true companion/cannon/familiar/servant-like features.",
        "6. **Active Effect/JS classifier**: separate safe passive effects, transformations, auras and effects that require a JS module.",
        "",
        "## First P0/P1 rows",
        "",
    ]
    for r in p0p1[:120]:
        lines.append(f"- {r.get('priority')} | {r.get('area')} | {r.get('issueKind')} | {r.get('name')} ({r.get('source')}): {r.get('problem')}")
    return "\n".join(lines) + "\n"

def _html_summary(report: dict[str, Any]) -> str:
    md = _markdown_summary(report)
    # Simple safe HTML without third-party markdown dependency.
    body = []
    for line in md.splitlines():
        if line.startswith("# "):
            body.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            body.append(f"<li>{html.escape(line[2:])}</li>")
        elif not line.strip():
            body.append("<br>")
        else:
            body.append(f"<p>{html.escape(line)}</p>")
    return "<!doctype html><meta charset='utf-8'><title>Aurora Compatibility Map</title><body>" + "\n".join(body) + "</body>\n"
