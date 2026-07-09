from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from aurora_compiler.models.aurora import AuroraElement

ARTILLERIST_CANNON_OPTION_ID_PARTS = {"FLAMETHROWER", "FORCE_BALLISTA", "FORCEBALLISTA", "PROTECTOR"}


def is_artillerist_cannon_option_id(aurora_id: str) -> bool:
    upper = (aurora_id or "").upper()
    return "ARTILLERIST" in upper and any(part in upper for part in ARTILLERIST_CANNON_OPTION_ID_PARTS)

FEATURE_TYPES = {"Class Feature", "Archetype Feature", "Racial Trait", "Feat"}

ASI_MARKERS = {
    "ABILITYSCOREIMPROVEMENT",
    "ABILITY_SCORE_IMPROVEMENT",
    "ABILITY_SCORE",
}

@dataclass(frozen=True)
class FeatureGrant:
    aurora_id: str
    level: int
    requirements: str = ""
    optional: bool = False


def is_asi_feature_id(aurora_id: str) -> bool:
    upper = (aurora_id or "").upper()
    return any(marker in upper for marker in ASI_MARKERS)


def is_class_feature_grant(rule: dict[str, Any]) -> bool:
    attrs = rule.get("attrs", {}) or {}
    return (rule.get("tag") or "").lower() == "grant" and (attrs.get("type") or "").lower() == "class feature"


def parse_level(value: str | int | None) -> int:
    try:
        level = int(str(value or "1"))
    except ValueError:
        level = 1
    return max(1, min(20, level))


def extract_class_feature_grants(class_element: AuroraElement) -> list[FeatureGrant]:
    grants: list[FeatureGrant] = []
    for rule in class_element.rules:
        if not is_class_feature_grant(rule):
            continue
        attrs = rule.get("attrs", {}) or {}
        aurora_id = attrs.get("id", "")
        if not aurora_id or is_asi_feature_id(aurora_id) or is_artillerist_cannon_option_id(aurora_id):
            continue
        grants.append(FeatureGrant(
            aurora_id=aurora_id,
            level=parse_level(attrs.get("level")),
            requirements=attrs.get("requirements", ""),
            optional=False,
        ))
    return grants


def group_feature_uuids_by_level(
    class_element: AuroraElement,
    feature_uuid_by_aurora_id: dict[str, str],
    child_feature_uuids_by_aurora_id: dict[str, list[str]] | None = None,
) -> tuple[dict[int, list[str]], list[str]]:
    grouped: dict[int, list[str]] = defaultdict(list)
    missing: list[str] = []
    for grant in extract_class_feature_grants(class_element):
        uuid = feature_uuid_by_aurora_id.get(grant.aurora_id)
        if not uuid:
            missing.append(grant.aurora_id)
            continue
        if uuid not in grouped[grant.level]:
            grouped[grant.level].append(uuid)
        if is_artillerist_cannon_option_id(grant.aurora_id):
            continue
        for child_uuid in (child_feature_uuids_by_aurora_id or {}).get(grant.aurora_id, []):
            if child_uuid not in grouped[grant.level]:
                grouped[grant.level].append(child_uuid)
    return dict(grouped), missing
