from aurora_compiler.compiler.class_compiler import compile_class
from aurora_compiler.compiler.feature_linker import extract_class_feature_grants, is_asi_feature_id
from aurora_compiler.models.aurora import AuroraElement


def test_extract_class_feature_grants_skips_asi():
    e = AuroraElement(
        id="ID_TEST_CLASS",
        name="Test Class",
        type="Class",
        source="Test",
        rules=[
            {"tag": "grant", "attrs": {"type": "Class Feature", "id": "ID_FEATURE_ONE", "level": "1"}},
            {"tag": "grant", "attrs": {"type": "Class Feature", "id": "ID_FEATURE_ABILITY_SCORE_IMPROVEMENT", "level": "4"}},
        ],
    )
    grants = extract_class_feature_grants(e)
    assert [g.aurora_id for g in grants] == ["ID_FEATURE_ONE"]
    assert is_asi_feature_id("ID_FEATURE_ABILITYSCOREIMPROVEMENT")


def test_compile_class_adds_item_grant_advancement_for_linked_feature():
    e = AuroraElement(
        id="ID_TEST_CLASS",
        name="Artificer",
        type="Class",
        source="Eberron: Rising from the Last War",
        description_html="<p><strong>Hit Dice:</strong> 1d8 per artificer level</p>",
        rules=[{"tag": "grant", "attrs": {"type": "Class Feature", "id": "ID_FEATURE_ONE", "level": "2"}}],
    )
    doc = compile_class(e, feature_uuid_by_aurora_id={"ID_FEATURE_ONE": "Compendium.test.features.abc123"})
    grants = [a for a in doc["system"]["advancement"].values() if a["type"] == "ItemGrant"]
    assert grants
    assert grants[0]["level"] == 2
    assert grants[0]["configuration"]["items"][0]["uuid"] == "Compendium.test.features.abc123"
    assert doc["flags"]["aurora"]["missingFeatureGrants"] == []


def test_compile_class_records_missing_feature_grants():
    e = AuroraElement(
        id="ID_TEST_CLASS",
        name="Artificer",
        type="Class",
        source="Eberron: Rising from the Last War",
        rules=[{"tag": "grant", "attrs": {"type": "Class Feature", "id": "ID_MISSING", "level": "1"}}],
    )
    doc = compile_class(e, feature_uuid_by_aurora_id={})
    assert doc["flags"]["aurora"]["missingFeatureGrants"] == ["ID_MISSING"]
