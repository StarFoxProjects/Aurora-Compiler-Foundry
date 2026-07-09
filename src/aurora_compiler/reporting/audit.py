from __future__ import annotations
from collections import Counter
from typing import Any


def _advancements(doc: dict) -> list[dict]:
    adv = doc.get("system", {}).get("advancement", {}) or {}
    if isinstance(adv, dict):
        return [v for v in adv.values() if isinstance(v, dict)]
    if isinstance(adv, list):
        return [v for v in adv if isinstance(v, dict)]
    return []


def _activities(doc: dict) -> dict:
    return doc.get("system", {}).get("activities", {}) or {}


def _flags(doc: dict) -> dict:
    return doc.get("flags", {}).get("aurora", {}) or {}


def _doc_ref(doc: dict) -> dict[str, Any]:
    f = _flags(doc)
    return {
        "name": doc.get("name", ""),
        "type": doc.get("type", ""),
        "auroraType": f.get("type", ""),
        "source": f.get("sourceCode") or f.get("source") or "",
        "auroraId": f.get("id", ""),
        "compiler": f.get("compiler", ""),
    }


def _item_choice_count(doc: dict, title_contains: str = "") -> int:
    count = 0
    needle = title_contains.lower()
    for a in _advancements(doc):
        if a.get("type") != "ItemChoice":
            continue
        if needle and needle not in str(a.get("title", "")).lower():
            continue
        pool = a.get("configuration", {}).get("pool", []) or []
        count += len(pool)
    return count


def build_audit(packs: dict[str, list[dict]], skipped: list[dict] | None = None) -> dict:
    """Create a quality report for the generated Foundry module.

    This does not guarantee every rule is automated. It tells us where the module
    is likely native, where it is only text, and which areas need hand-written
    compiler backends next.
    """
    docs = [(pack, doc) for pack, docs in (packs or {}).items() for doc in (docs or [])]
    item_counts = Counter(pack for pack, _ in docs)
    by_type = Counter(doc.get("type", "unknown") for _, doc in docs)
    activity_counts = Counter()
    advancement_counts = Counter()
    likely_text_only: list[dict] = []
    risky_rules: list[dict] = []
    class_status: list[dict] = []
    species_without_advancement: list[dict] = []
    artificer_status: list[dict] = []

    for pack, doc in docs:
        acts = _activities(doc)
        for a in acts.values():
            activity_counts[a.get("type", "unknown")] += 1
        advs = _advancements(doc)
        for a in advs:
            advancement_counts[a.get("type", "unknown")] += 1

        flags = _flags(doc)
        native_notes = flags.get("nativeRuleNotes", []) or []
        has_rules = bool(flags.get("rules"))
        has_native_surface = bool(acts or advs or doc.get("type") in {"spell", "class", "subclass", "race"})
        if doc.get("type") == "feat" and has_rules and not acts and not advs:
            entry = _doc_ref(doc)
            entry["pack"] = pack
            entry["reason"] = "Has Aurora rules but no activities/advancement yet"
            likely_text_only.append(entry)
        if native_notes and not acts and not advs:
            entry = _doc_ref(doc)
            entry["pack"] = pack
            entry["notes"] = native_notes[:8]
            risky_rules.append(entry)

        if doc.get("type") == "class":
            adv_types = Counter(a.get("type", "unknown") for a in advs)
            entry = _doc_ref(doc)
            entry.update({
                "pack": pack,
                "advancementTypes": dict(adv_types),
                "featureGrantCount": adv_types.get("ItemGrant", 0),
                "hasSubclassChoice": adv_types.get("Subclass", 0) > 0,
                "infusionPoolSize": _item_choice_count(doc, "Infusions"),
            })
            class_status.append(entry)
            if "artificer" in str(doc.get("system", {}).get("identifier", doc.get("name", ""))).lower():
                artificer_status.append(entry)

        if doc.get("type") == "race" and not advs:
            entry = _doc_ref(doc)
            entry["pack"] = pack
            species_without_advancement.append(entry)

    return {
        "summary": {
            "packs": dict(item_counts),
            "documentTypes": dict(by_type),
            "activityTypes": dict(activity_counts),
            "advancementTypes": dict(advancement_counts),
            "warnings": len(skipped or []),
            "likelyTextOnlyFeatures": len(likely_text_only),
            "riskyRuleFeatures": len(risky_rules),
            "speciesWithoutAdvancement": len(species_without_advancement),
        },
        "artificer": artificer_status,
        "classes": class_status,
        "speciesWithoutAdvancement": species_without_advancement[:200],
        "likelyTextOnlyFeatures": likely_text_only[:500],
        "riskyRuleFeatures": risky_rules[:500],
        "warnings": skipped or [],
    }
