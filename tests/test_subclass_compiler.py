from aurora_compiler.models.aurora import AuroraElement
from aurora_compiler.compiler.subclass_compiler import compile_subclass, infer_class_identifier


def test_infer_class_identifier_from_supports():
    e = AuroraElement(
        id="ID_WOTC_SCAG_ARCHETYPE_BLADESINGING",
        name="Bladesinging",
        type="Archetype",
        source="Sword Coast Adventurer’s Guide",
        supports=["Arcane Tradition"],
    )
    assert infer_class_identifier(e) == "wizard"


def test_compile_subclass_sets_class_identifier_and_type():
    e = AuroraElement(
        id="ID_WOTC_SCAG_ARCHETYPE_OATH_OF_THE_CROWN",
        name="Oath of the Crown",
        type="Archetype",
        source="Sword Coast Adventurer’s Guide",
        supports=["Sacred Oath"],
    )
    doc = compile_subclass(e)
    assert doc["type"] == "subclass"
    assert doc["system"]["classIdentifier"] == "paladin"
    assert doc["system"]["identifier"] == "oath-of-the-crown"


def test_compile_subclass_links_feature_grants():
    e = AuroraElement(
        id="ID_TEST_ARCHETYPE",
        name="Test Path",
        type="Archetype",
        source="Test Source",
        supports=["Primal Path"],
        rules=[{"tag":"grant", "attrs":{"type":"Archetype Feature", "id":"ID_TEST_FEATURE", "level":"3"}, "text":"", "children":[]}],
    )
    doc = compile_subclass(e, feature_uuid_by_aurora_id={"ID_TEST_FEATURE": "Compendium.test.features.abc123"})
    grants = [a for a in doc["system"]["advancement"].values() if a["type"] == "ItemGrant"]
    assert grants
    assert grants[0]["level"] == 3
    assert grants[0]["configuration"]["items"][0]["uuid"] == "Compendium.test.features.abc123"
