from aurora_compiler.models.aurora import AuroraElement
from aurora_compiler.compiler.species_compiler import compile_species


def test_species_compiler_infers_speed_size_and_trait_grants():
    e = AuroraElement(
        id="ID_WOTC_ERLW_RACE_WARFORGED",
        name="Warforged",
        type="Race",
        source="Eberron: Rising from the Last War",
        description_html="<p>Your size is Medium. Your base walking speed is 30 feet.</p>",
        rules=[{"tag":"grant", "attrs":{"type":"Racial Trait", "id":"ID_TRAIT_RESILIENCE", "level":"1"}, "text":"", "children":[]}],
    )
    doc = compile_species(e, feature_uuid_by_aurora_id={"ID_TRAIT_RESILIENCE": "Compendium.test.features.abc123"})
    assert doc["type"] == "race"
    assert doc["system"]["size"] == "med"
    assert doc["system"]["movement"]["walk"] == 30
    sizes = [a for a in doc["system"]["advancement"].values() if a["type"] == "Size"]
    assert sizes
    grants = [a for a in doc["system"]["advancement"].values() if a["type"] == "ItemGrant"]
    assert grants
    assert grants[0]["configuration"]["items"][0]["uuid"] == "Compendium.test.features.abc123"


def test_species_compiler_records_missing_traits():
    e = AuroraElement(
        id="ID_TEST_RACE",
        name="Test Race",
        type="Race",
        source="Test",
        rules=[{"tag":"grant", "attrs":{"type":"Racial Trait", "id":"ID_MISSING"}, "text":"", "children":[]}],
    )
    doc = compile_species(e, feature_uuid_by_aurora_id={})
    assert doc["flags"]["aurora"]["missingRacialTraitGrants"] == ["ID_MISSING"]


def test_species_compiler_always_adds_size_advancement_even_without_traits():
    e = AuroraElement(
        id="ID_TEST_EMPTY_RACE",
        name="Empty Race",
        type="Race",
        source="Test",
        description_html="<p>Your size is Small or Medium. Your walking speed is 30 feet.</p>",
        rules=[],
    )
    doc = compile_species(e, feature_uuid_by_aurora_id={})
    advancements = doc["system"]["advancement"].values()
    size_adv = [a for a in advancements if a["type"] == "Size"]
    assert size_adv
    assert size_adv[0]["configuration"]["sizes"] == ["sm", "med"]


def test_species_compiler_adds_language_trait_and_fixed_asi():
    e = AuroraElement(
        id="ID_WOTC_ERLW_RACE_KALASHTAR",
        name="Kalashtar",
        type="Race",
        source="Eberron: Rising from the Last War",
        rules=[
            {"tag":"stat", "attrs":{"name":"wisdom", "value":"2"}, "text":"", "children":[]},
            {"tag":"stat", "attrs":{"name":"charisma", "value":"1"}, "text":"", "children":[]},
            {"tag":"grant", "attrs":{"type":"Language", "id":"ID_LANGUAGE_COMMON"}, "text":"", "children":[]},
            {"tag":"grant", "attrs":{"type":"Language", "id":"ID_WOTC_ERLW_LANGUAGE_QUORI"}, "text":"", "children":[]},
        ],
    )
    doc = compile_species(e, feature_uuid_by_aurora_id={})
    advancements = list(doc["system"]["advancement"].values())
    asi = [a for a in advancements if a["type"] == "AbilityScoreImprovement"]
    assert asi
    assert asi[0]["configuration"]["fixed"]["wis"] == 2
    assert asi[0]["configuration"]["fixed"]["cha"] == 1
    trait = [a for a in advancements if a["type"] == "Trait"]
    assert trait
    assert "languages:standard:common" in trait[0]["configuration"]["grants"]


def test_fixed_asi_advancement_is_prepopulated():
    from aurora_compiler.foundry.advancement import fixed_ability_score_improvement
    doc = fixed_ability_score_improvement("test-species", {"wis": 2, "cha": 1})
    assert doc["type"] == "AbilityScoreImprovement"
    assert doc["configuration"]["points"] == 0
    assert doc["configuration"]["fixed"]["wis"] == 2
    assert doc["configuration"]["fixed"]["cha"] == 1
    assert set(doc["configuration"]["locked"]) == {"wis", "cha"}
    assert doc["value"] == {}
    assert doc["level"] == 1


def test_species_compiler_adds_selectable_asi_points_for_warforged():
    e = AuroraElement(
        id="ID_WOTC_ERLW_RACE_WARFORGED",
        name="Warforged",
        type="Race",
        source="Eberron: Rising from the Last War",
        rules=[
            {"tag":"stat", "attrs":{"name":"constitution", "value":"2"}, "text":"", "children":[]},
            {"tag":"select", "attrs":{"type":"Ability Score Improvement", "name":"Ability Score Increase, Warforged", "supports":"ID_INTERNAL_ASI_STRENGTH|ID_INTERNAL_ASI_DEXTERITY"}, "text":"", "children":[]},
        ],
    )
    doc = compile_species(e, feature_uuid_by_aurora_id={})
    asi = [a for a in doc["system"]["advancement"].values() if a["type"] == "AbilityScoreImprovement"][0]
    assert asi["configuration"]["fixed"]["con"] == 2
    assert asi["configuration"]["points"] == 1
    assert asi["value"] == {}
    assert asi["level"] == 1


def test_species_compiler_adds_damage_resistance_from_racial_trait_rules():
    e = AuroraElement(
        id="ID_WOTC_ERLW_RACE_KALASHTAR",
        name="Kalashtar",
        type="Race",
        source="Eberron: Rising from the Last War",
        rules=[{"tag":"grant", "attrs":{"type":"Racial Trait", "id":"ID_TRAIT_MENTAL_DISCIPLINE"}, "text":"", "children":[]}],
    )
    feature_doc = {
        "system": {"description": {"value": "<p>You have resistance to psychic damage.</p>"}},
        "flags": {"aurora": {"rules": [
            {"tag":"grant", "attrs":{"type":"Condition", "id":"ID_INTERNAL_CONDITION_DAMAGE_RESISTANCE_PSYCHIC"}, "text":"", "children":[]}
        ]}}
    }
    doc = compile_species(
        e,
        feature_uuid_by_aurora_id={"ID_TRAIT_MENTAL_DISCIPLINE": "Compendium.test.features.mental"},
        feature_docs_by_aurora_id={"ID_TRAIT_MENTAL_DISCIPLINE": feature_doc},
    )
    traits = [a for a in doc["system"]["advancement"].values() if a["type"] == "Trait"]
    grants = sum((t["configuration"]["grants"] for t in traits), [])
    assert "dr:psychic" in grants


def test_species_compiler_adds_poison_resistance_and_disease_immunity_from_text():
    e = AuroraElement(
        id="ID_WOTC_ERLW_RACE_WARFORGED",
        name="Warforged",
        type="Race",
        source="Eberron: Rising from the Last War",
        rules=[{"tag":"grant", "attrs":{"type":"Racial Trait", "id":"ID_TRAIT_CONSTRUCTED"}, "text":"", "children":[]}],
    )
    feature_doc = {
        "system": {"description": {"value": "<p>You have resistance to poison damage. You are immune to disease.</p>"}},
        "flags": {"aurora": {"rules": []}}
    }
    doc = compile_species(
        e,
        feature_uuid_by_aurora_id={"ID_TRAIT_CONSTRUCTED": "Compendium.test.features.constructed"},
        feature_docs_by_aurora_id={"ID_TRAIT_CONSTRUCTED": feature_doc},
    )
    traits = [a for a in doc["system"]["advancement"].values() if a["type"] == "Trait"]
    grants = sum((t["configuration"]["grants"] for t in traits), [])
    assert "dr:poison" in grants
    assert "ci:diseased" in grants


def test_species_compiler_expands_default_modern_race_grants():
    race = AuroraElement(
        id="ID_WOTC_MOTM_RACE_AARAKOCRA",
        name="Aarakocra",
        type="Race",
        source="MPMM",
        rules=[
            {"tag":"grant", "attrs":{"type":"Grants", "id":"ID_WOTC_GRANTS_DEFAULT_RACIAL_ASI"}, "text":"", "children":[]},
            {"tag":"grant", "attrs":{"type":"Grants", "id":"ID_WOTC_GRANTS_DEFAULT_RACIAL_LANGUAGE"}, "text":"", "children":[]},
            {"tag":"grant", "attrs":{"type":"Racial Trait", "id":"ID_FLIGHT"}, "text":"", "children":[]},
            {"tag":"stat", "attrs":{"name":"innate speed", "value":"30"}, "text":"", "children":[]},
        ],
    )
    asi_grant = AuroraElement(
        id="ID_WOTC_GRANTS_DEFAULT_RACIAL_ASI",
        name="Ability Score Increases",
        type="Grants",
        source="Test",
        rules=[
            {"tag":"select", "attrs":{"type":"Ability Score Improvement", "supports":"DEFAULT_RACE_ASI_1A"}, "text":"", "children":[]},
            {"tag":"select", "attrs":{"type":"Ability Score Improvement", "supports":"DEFAULT_RACE_ASI_1B"}, "text":"", "children":[]},
            {"tag":"select", "attrs":{"type":"Ability Score Improvement", "supports":"DEFAULT_RACE_ASI_1C"}, "text":"", "children":[]},
        ],
    )
    language_grant = AuroraElement(
        id="ID_WOTC_GRANTS_DEFAULT_RACIAL_LANGUAGE",
        name="Languages",
        type="Grants",
        source="Test",
        rules=[
            {"tag":"grant", "attrs":{"type":"Language", "id":"ID_LANGUAGE_COMMON"}, "text":"", "children":[]},
            {"tag":"select", "attrs":{"type":"Language", "supports":"Standard||Exotic"}, "text":"", "children":[]},
        ],
    )
    feature_doc = {
        "system": {"description": {"value": "<p>You have a flying speed equal to your walking speed.</p>"}},
        "flags": {"aurora": {"rules": [{"tag":"stat", "attrs":{"name":"speed:fly", "value":"speed"}, "text":"", "children":[]}]}}
    }
    doc = compile_species(
        race,
        feature_uuid_by_aurora_id={"ID_FLIGHT": "Compendium.test.features.flight"},
        feature_docs_by_aurora_id={"ID_FLIGHT": feature_doc},
        grant_elements_by_aurora_id={
            "ID_WOTC_GRANTS_DEFAULT_RACIAL_ASI": asi_grant,
            "ID_WOTC_GRANTS_DEFAULT_RACIAL_LANGUAGE": language_grant,
        },
    )
    asi = [a for a in doc["system"]["advancement"].values() if a["type"] == "AbilityScoreImprovement"][0]
    assert asi["configuration"]["points"] == 3
    assert doc["system"]["movement"]["fly"] == 30
    language = [a for a in doc["system"]["advancement"].values() if a["type"] == "Trait" and a["title"] == "Languages"][0]
    assert "languages:standard:common" in language["configuration"]["grants"]
    assert language["configuration"]["choices"][0]["count"] == 1


def test_species_compiler_infers_darkvision_from_racial_trait_text():
    race = AuroraElement(
        id="ID_RACE_DEEP_GNOME",
        name="Deep Gnome",
        type="Race",
        source="MPMM",
        rules=[{"tag":"grant", "attrs":{"type":"Racial Trait", "id":"ID_DARKVISION"}, "text":"", "children":[]}],
    )
    feature_doc = {
        "system": {"description": {"value": "<p>You can see in dim light within 120 feet of you.</p>"}},
        "flags": {"aurora": {"rules": [{"tag":"grant", "attrs":{"type":"Vision", "id":"ID_VISION_DARKVISION"}, "text":"", "children":[]}]}}
    }
    doc = compile_species(
        race,
        feature_uuid_by_aurora_id={"ID_DARKVISION": "Compendium.test.features.darkvision"},
        feature_docs_by_aurora_id={"ID_DARKVISION": feature_doc},
    )
    assert doc["system"]["senses"]["ranges"]["darkvision"] == 120
