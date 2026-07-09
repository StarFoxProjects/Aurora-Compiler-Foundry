from __future__ import annotations
import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from aurora_compiler.models.aurora import slugify, clean_duplicate_name
from aurora_compiler.parser.xml_parser import parse_aurora_zip
from aurora_compiler.compiler.spell_compiler import compile_spell
from aurora_compiler.compiler.generic_compiler import compile_generic_item
from aurora_compiler.compiler.class_compiler import compile_class
from aurora_compiler.compiler.feature_compiler import compile_feature, child_feature_uuid_index, add_nested_grant_advancements, eldricht_cannon_actor_docs, is_artillerist_cannon_option_id, is_artillerist_cannon_option_name
from aurora_compiler.compiler.subclass_compiler import compile_subclass
from aurora_compiler.compiler.species_compiler import compile_species
from aurora_compiler.foundry.module_writer import write_module
from aurora_compiler.indexes.official import load_official_examples
from aurora_compiler.reporting.report import build_report, write_report
from aurora_compiler.reporting.audit import build_audit
from aurora_compiler.reporting.compatibility import build_compatibility_map, write_compatibility_reports

TYPE_TO_PACK = {
    "Spell": "spells",
    "Class": "classes",
    "Archetype": "subclasses",
    "Race": "species",
    "Sub Race": "species",
    "Background": "backgrounds",
    "Feat": "features",
    "Class Feature": "features",
    "Racial Trait": "features",
    "Archetype Feature": "features",
    "Item": "equipment",
    "Magic Item": "equipment",
    "Weapon": "equipment",
    "Armor": "equipment",
}

TYPE_TO_ITEM = {
    "Class": "class",
    "Archetype": "subclass",
    "Race": "race",
    "Sub Race": "race",
    "Background": "background",
    "Feat": "feat",
    "Class Feature": "feat",
    "Racial Trait": "feat",
    "Archetype Feature": "feat",
    "Item": "equipment",
    "Magic Item": "equipment",
    "Weapon": "weapon",
    "Armor": "equipment",
}

CORE_SOURCE_CODES = {"PHB", "DMG", "MM", "SRD"}


def _is_core_duplicate(e, foundry_item_type: str, official_index, extra_only: bool) -> bool:
    if not extra_only:
        return False
    # Prefer real official index when available.
    if official_index.has(foundry_item_type, e.name):
        return True
    # Fallback source filter: keep UA/third-party/expansion, skip core.
    return e.source_code in CORE_SOURCE_CODES


def _compile_non_class(e, foundry_type: str, args):
    if e.type == "Spell":
        return compile_spell(e, include_source_name=args.include_source, long_source=args.long_source)
    if _is_artificer_infusion(e):
        # Infusions are selectable class feature options. Compile them as feat
        # documents regardless of Aurora's original element type so the
        # Artificer ItemChoice advancement can point to a stable explicit pool.
        return compile_feature(e, include_source_name=args.include_source, long_source=args.long_source, module_id=args.module_id)
    if e.type in {"Class Feature", "Archetype Feature", "Racial Trait", "Feat"}:
        if e.type == "Archetype Feature" and (is_artillerist_cannon_option_id(e.id) or is_artillerist_cannon_option_name(e.name)):
            # These are compiled onto the summoned Eldritch Cannon actors, not as
            # standalone character features.
            return None
        return compile_feature(e, include_source_name=args.include_source, long_source=args.long_source, module_id=args.module_id)
    if e.type == "Archetype":
        # Subclasses need feature/spell indexes, so they are compiled in the dedicated subclass pass.
        return None
    if e.type in {"Race", "Sub Race"}:
        # Species need racial-trait indexes, so they are compiled after features exist.
        return None
    return compile_generic_item(e, foundry_type, include_source_name=args.include_source, long_source=args.long_source)


def _foundry_uuid(module_id: str, pack: str, doc_id: str) -> str:
    # Foundry D&D5e class advancement ItemGrant accepts compact compendium UUIDs.
    return f"Compendium.{module_id}.{pack}.{doc_id}"


def _spell_list_key(name: str) -> str:
    return slugify(str(name or "").split("(")[0].strip())


def _element_haystack(e) -> str:
    bits = [
        getattr(e, "id", ""), getattr(e, "name", ""), getattr(e, "type", ""),
        getattr(e, "source", ""), getattr(e, "file", ""), " ".join(getattr(e, "supports", []) or []),
    ]
    for rule in getattr(e, "rules", []) or []:
        attrs = rule.get("attrs", {}) or {}
        bits.extend([rule.get("tag", ""), attrs.get("type", ""), attrs.get("id", ""), attrs.get("name", ""), attrs.get("value", "")])
    return " ".join(str(b) for b in bits if b).lower()


def _is_artificer_infusion(e) -> bool:
    """Detect Artificer infusion *choices* from Aurora, even when Aurora
    stores them as items/feats rather than Class Feature documents.

    We intentionally exclude the base class feature "Infuse Item" and scale
    helper elements; those belong on the Artificer class, not inside the picker.
    """
    base_slug = slugify(clean_duplicate_name(getattr(e, "name", "") or "").split("(")[0])
    if base_slug in {"infuse-item", "infusions-known", "infused-items", "artificer-infusions"}:
        return False
    hay = _element_haystack(e)
    if "artificer infusion" in hay or "ua artificer infusion" in hay:
        return True
    if "artificer" in hay and ("_infusion" in hay or "infusion_" in hay or " infusion " in hay):
        return True
    if "id_wotc_erlw_artificer_infusion" in hay or "id_wotc_tce_artificer_infusion" in hay:
        return True
    return False


def _is_ua_artificer_class(e) -> bool:
    return e.type == "Class" and "artificer" in (e.name or "").lower() and e.source_code == "UA"


def _doc_haystack(doc: dict) -> str:
    flags = doc.get("flags", {}).get("aurora", {}) or {}
    bits = [
        doc.get("name", ""), flags.get("id", ""), flags.get("type", ""),
        flags.get("source", ""), flags.get("sourceCode", ""), flags.get("file", ""),
        " ".join(flags.get("supports", []) or []),
    ]
    for rule in flags.get("rules", []) or []:
        attrs = rule.get("attrs", {}) or {}
        bits.extend([rule.get("tag", ""), attrs.get("type", ""), attrs.get("id", ""), attrs.get("name", ""), attrs.get("value", "")])
    return " ".join(str(b) for b in bits if b).lower()


def _is_artificer_infusion_doc(doc: dict) -> bool:
    base_slug = slugify(clean_duplicate_name(doc.get("name", "") or "").split("(")[0])
    if base_slug in {"infuse-item", "infusions-known", "infused-items", "artificer-infusions"}:
        return False
    hay = _doc_haystack(doc)
    return (
        "artificer infusion" in hay
        or "ua artificer infusion" in hay
        or ("artificer" in hay and ("_infusion" in hay or "infusion_" in hay or " infusion " in hay))
    )


def _artificer_infusion_pool_for_class(e, feature_docs_by_aurora_id: dict[str, dict], feature_uuid_by_aurora_id: dict[str, str]) -> list[str]:
    """Build a compendium UUID pool for Artificer Infusions.

    v1.7 is deliberately more permissive than v1.6: Aurora databases are not
    consistent about whether infusion choices are Class Feature, Feat, Item, or
    Magic Item elements. We compile any detected infusion choice into the
    dedicated infusions pack and expose that pack through one ItemChoice
    advancement at Artificer level 2.
    """
    want_ua = _is_ua_artificer_class(e)
    out: list[str] = []
    for aurora_id, doc in feature_docs_by_aurora_id.items():
        if not _is_artificer_infusion_doc(doc):
            continue
        hay = _doc_haystack(doc)
        is_ua_pool = "ua artificer infusion" in hay or "unearthed arcana" in hay or "sourcecode ua" in hay
        if want_ua != bool(is_ua_pool):
            # Modern Artificer should not receive the obsolete UA infusion list,
            # and the UA Artificer should not receive ERLW/TCE infusions.
            continue
        uuid = feature_uuid_by_aurora_id.get(aurora_id)
        if uuid and uuid not in out:
            out.append(uuid)
    return out


def write_runtime_coverage_report(pack_docs: dict[str, list[dict]], out_dir: Path, version: str = "v2.8") -> None:
    rows: list[dict] = []
    action_counts: Counter[str] = Counter()
    pack_counts: Counter[str] = Counter()
    for pack, docs in sorted(pack_docs.items()):
        for doc in docs:
            system = doc.get("system", {}) or {}
            activities = system.get("activities", {}) or {}
            for activity in activities.values():
                runtime = (activity.get("flags", {}) or {}).get("aurora", {}).get("runtime", {}) or {}
                if not runtime.get("action"):
                    continue
                flags = doc.get("flags", {}).get("aurora", {}) or {}
                action = runtime.get("action", "")
                action_counts[action] += 1
                pack_counts[pack] += 1
                rows.append({
                    "pack": pack,
                    "documentName": doc.get("name", ""),
                    "foundryType": doc.get("type", ""),
                    "auroraType": flags.get("type", ""),
                    "source": flags.get("sourceCode", "") or flags.get("source", ""),
                    "auroraId": flags.get("id", ""),
                    "activityName": activity.get("name", ""),
                    "activityType": activity.get("type", ""),
                    "runtimeAction": action,
                    "formula": runtime.get("formula", ""),
                    "target": runtime.get("target", ""),
                    "damageType": runtime.get("damageType", ""),
                    "saveAbility": runtime.get("saveAbility", ""),
                    "backend": runtime.get("backend", ""),
                })
    fields = ["pack", "documentName", "foundryType", "auroraType", "source", "auroraId", "activityName", "activityType", "runtimeAction", "formula", "target", "damageType", "saveAbility", "backend"]
    tsv = out_dir / f"runtime-coverage-{version}.tsv"
    with tsv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t")
        w.writeheader(); w.writerows(rows)
    md_lines = [
        f"# Aurora Runtime Coverage {version}",
        "",
        "This report lists every generated Foundry activity that received an Aurora Runtime action flag.",
        "It does not mean every D&D rule is fully automated; it shows what the runtime can currently intercept.",
        "",
        f"- Runtime-mapped activities: {len(rows)}",
        "",
        "## By action",
        "",
    ]
    for k, v in action_counts.most_common():
        md_lines.append(f"- {k}: {v}")
    md_lines += ["", "## By pack", ""]
    for k, v in pack_counts.most_common():
        md_lines.append(f"- {k}: {v}")
    md_lines += ["", f"Full table: `runtime-coverage-{version}.tsv`", ""]
    (out_dir / f"runtime-summary-{version}.md").write_text("\n".join(md_lines), encoding="utf-8")

def build(args):
    elems = parse_aurora_zip(args.aurora_zip)
    official = load_official_examples(args.official_examples)
    packs = defaultdict(list)
    skipped: list[dict] = []
    seen = set()
    queued: list[tuple[object, str, str]] = []

    # First pass: filter and queue elements. We need this because classes may link to
    # feature documents that are compiled later into the features pack.
    for e in elems:
        if not e.name or not e.type:
            continue
        foundry_type = "spell" if e.type == "Spell" else TYPE_TO_ITEM.get(e.type, "feat")
        pack = TYPE_TO_PACK.get(e.type, "other")
        if _is_core_duplicate(e, foundry_type, official, args.extra_only):
            skipped.append({"reason": "official-or-core-duplicate", "name": e.name, "type": e.type, "source": e.source, "id": e.id})
            continue
        if _is_artificer_infusion(e):
            foundry_type = "feat"
            pack = "infusions"
        key = (e.type, e.name, e.source_code, e.id)
        if key in seen:
            skipped.append({"reason": "exact-duplicate", "name": e.name, "type": e.type, "source": e.source, "id": e.id})
            continue
        seen.add(key)
        queued.append((e, foundry_type, pack))

    # Second pass: compile non-class documents first and build an Aurora ID -> UUID index
    # for feature documents. Classes use this to create ItemGrant advancements.
    feature_uuid_by_aurora_id: dict[str, str] = {}
    feature_docs_by_aurora_id: dict[str, dict] = {}
    class_queue: list[tuple[object, str, str]] = []
    subclass_queue: list[tuple[object, str, str]] = []
    species_queue: list[tuple[object, str, str]] = []
    spell_uuid_by_aurora_id: dict[str, str] = {}
    spell_uuids_by_class_level: dict[tuple[str, int], list[str]] = defaultdict(list)
    grant_elements_by_aurora_id = {e.id: e for e, _, _ in queued if getattr(e, "type", "") == "Grants" and getattr(e, "id", "")}
    for e, foundry_type, pack in queued:
        if e.type == "Class":
            class_queue.append((e, foundry_type, pack))
            continue
        if e.type == "Archetype":
            subclass_queue.append((e, foundry_type, pack))
            continue
        if e.type in {"Race", "Sub Race"}:
            species_queue.append((e, foundry_type, pack))
            continue
        doc = _compile_non_class(e, foundry_type, args)
        if doc is None:
            continue
        packs[pack].append(doc)
        if e.type == "Spell" and e.id:
            uuid = _foundry_uuid(args.module_id, pack, doc["_id"])
            spell_uuid_by_aurora_id[e.id] = uuid
            level = int(doc.get("system", {}).get("level", 0) or 0)
            for support in getattr(e, "supports", []) or []:
                key = _spell_list_key(support)
                if key:
                    spell_uuids_by_class_level[(key, level)].append(uuid)
        if pack in {"features", "infusions"} and e.id:
            feature_uuid_by_aurora_id[e.id] = _foundry_uuid(args.module_id, pack, doc["_id"])
            feature_docs_by_aurora_id[e.id] = doc

    child_feature_uuids_by_aurora_id = child_feature_uuid_index([e for e, _, _ in queued], feature_uuid_by_aurora_id)
    nested_feature_docs = add_nested_grant_advancements(packs.get("features", []), child_feature_uuids_by_aurora_id)
    packs["summons"].extend(eldricht_cannon_actor_docs())

    # Third pass: compile subclasses after features/spells exist so subclass advancements can grant them.
    for e, foundry_type, pack in subclass_queue:
        doc = compile_subclass(
            e,
            include_source_name=args.include_source,
            long_source=args.long_source,
            feature_uuid_by_aurora_id=feature_uuid_by_aurora_id,
            spell_uuid_by_aurora_id=spell_uuid_by_aurora_id,
            child_feature_uuids_by_aurora_id=child_feature_uuids_by_aurora_id,
        )
        missing_features = doc.get("flags", {}).get("aurora", {}).get("missingSubclassFeatureGrants", []) or []
        missing_spells = doc.get("flags", {}).get("aurora", {}).get("missingSubclassSpellGrants", []) or []
        missing_class = not doc.get("system", {}).get("classIdentifier")
        for fid in missing_features:
            skipped.append({"reason": "missing-subclass-feature-reference", "name": e.name, "type": e.type, "source": e.source, "id": e.id, "missing": fid})
        for sid in missing_spells:
            skipped.append({"reason": "missing-subclass-spell-reference", "name": e.name, "type": e.type, "source": e.source, "id": e.id, "missing": sid})
        if missing_class:
            skipped.append({"reason": "missing-subclass-class-identifier", "name": e.name, "type": e.type, "source": e.source, "id": e.id, "supports": e.supports})
        packs[pack].append(doc)

    # Fourth pass: compile races/species after racial trait features exist.
    for e, foundry_type, pack in species_queue:
        doc = compile_species(
            e,
            include_source_name=args.include_source,
            long_source=args.long_source,
            feature_uuid_by_aurora_id=feature_uuid_by_aurora_id,
            feature_docs_by_aurora_id=feature_docs_by_aurora_id,
            grant_elements_by_aurora_id=grant_elements_by_aurora_id,
        )
        missing = doc.get("flags", {}).get("aurora", {}).get("missingRacialTraitGrants", []) or []
        for fid in missing:
            skipped.append({"reason": "missing-racial-trait-reference", "name": e.name, "type": e.type, "source": e.source, "id": e.id, "missing": fid})
        packs[pack].append(doc)

    # Fifth pass: compile classes with feature link information.
    for e, foundry_type, pack in class_queue:
        doc = compile_class(
            e,
            include_source_name=args.include_source,
            long_source=args.long_source,
            feature_uuid_by_aurora_id=feature_uuid_by_aurora_id,
            artificer_infusion_uuids=_artificer_infusion_pool_for_class(e, feature_docs_by_aurora_id, feature_uuid_by_aurora_id),
            child_feature_uuids_by_aurora_id=child_feature_uuids_by_aurora_id,
            class_cantrip_uuids=spell_uuids_by_class_level.get((_spell_list_key(e.name), 0), []),
        )
        missing = doc.get("flags", {}).get("aurora", {}).get("missingFeatureGrants", []) or []
        for fid in missing:
            skipped.append({"reason": "missing-class-feature-reference", "name": e.name, "type": e.type, "source": e.source, "id": e.id, "missing": fid})
        packs[pack].append(doc)

    out = write_module(args.out, dict(packs), module_id=args.module_id, title=args.title, version="2.8.0-alpha")
    report = build_report(elems, {k: len(v) for k, v in packs.items()}, skipped)
    write_report(report, Path(out) / "compilation-report.json")
    audit = build_audit(dict(packs), skipped)
    write_report(audit, Path(out) / "compiler-audit-v1.7.json")
    compatibility = build_compatibility_map(elems, dict(packs), skipped)
    write_compatibility_reports(compatibility, Path(out))
    write_runtime_coverage_report(dict(packs), Path(out), version="v2.8")
    print(f"Wrote {out}")
    for k, v in sorted(packs.items()):
        print(f"  {k}: {len(v)}")
    print(f"Feature links indexed: {len(feature_uuid_by_aurora_id)}")
    print(f"Spell links indexed: {len(spell_uuid_by_aurora_id)}")
    print(f"Nested feature grant docs: {nested_feature_docs}")
    print(f"Artificer infusions compiled: {len(packs.get('infusions', []))}")
    print(f"Skipped/warnings: {len(skipped)}")
    print("Audit: compiler-audit-v1.7.json")
    print("Compatibility map: compatibility-summary-v2.8.md / compatibility-real-issues-v2.8.tsv")
    print("Runtime coverage: runtime-summary-v2.8.md / runtime-coverage-v2.8.tsv")

def inspect(args):
    elems = parse_aurora_zip(args.aurora_zip)
    report = build_report(elems)
    write_report(report, args.out)
    print(f"Wrote {args.out}")
    print(f"Elements: {len(elems)}")


def main():
    p = argparse.ArgumentParser("aurora-compiler")
    sub = p.add_subparsers(required=True)

    i = sub.add_parser("inspect")
    i.add_argument("--aurora-zip", required=True)
    i.add_argument("--out", default="aurora-report.json")
    i.set_defaults(func=inspect)

    b = sub.add_parser("build")
    b.add_argument("--aurora-zip", required=True)
    b.add_argument("--out", default="Aurora_Content_Pack")
    b.add_argument("--module-id", default="aurora-content-pack")
    b.add_argument("--title", default="Aurora Content Pack")
    b.add_argument("--include-source", action="store_true", help="Append source code to item names")
    b.add_argument("--long-source", action="store_true", help="Use full source names instead of short codes in item names")
    b.add_argument("--extra-only", action="store_true", help="Skip official/core duplicates when possible")
    b.add_argument("--official-examples", default=None, help="Folder containing exported official Foundry JSON/.db examples")
    b.set_defaults(func=build)

    args = p.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
