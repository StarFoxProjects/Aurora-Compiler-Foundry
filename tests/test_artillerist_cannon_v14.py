from aurora_compiler.models.aurora import AuroraElement
from aurora_compiler.compiler.feature_compiler import compile_feature, add_nested_grant_advancements, eldricht_cannon_actor_docs


def test_eldritch_cannon_has_summon_and_mode_activities_on_artificer_sheet():
    e = AuroraElement(
        id="ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_ELDRITCH_CANNON",
        name="Eldritch Cannon",
        type="Archetype Feature",
        source="Eberron: Rising from the Last War",
        description_html="<p>You create a magical cannon.</p>",
    )
    doc = compile_feature(e, module_id="aurora-extra-pack")
    names = sorted(a["name"] for a in doc["system"]["activities"].values())
    assert names == ["Create Eldritch Cannon", "Flamethrower", "Force Ballista", "Protector"]
    protector = next(a for a in doc["system"]["activities"].values() if a["name"] == "Protector")
    assert protector["type"] == "heal"
    assert protector["healing"]["bonus"] == "@abilities.int.mod"
    assert protector["target"]["affects"]["choice"] is False
    summon = next(a for a in doc["system"]["activities"].values() if a["type"] == "summon")
    assert len(summon["profiles"]) == 3
    assert {p["name"] for p in summon["profiles"]} == {
        "Eldritch Cannon - Flamethrower",
        "Eldritch Cannon - Force Ballista",
        "Eldritch Cannon - Protector",
    }
    assert summon["profiles"][0]["uuid"].startswith("Compendium.aurora-extra-pack.summons.")


def test_eldritch_cannon_skips_nested_option_grants():
    doc = compile_feature(AuroraElement(
        id="ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_ELDRITCH_CANNON",
        name="Eldritch Cannon",
        type="Archetype Feature",
        source="Eberron: Rising from the Last War",
    ))
    count = add_nested_grant_advancements([doc], {doc["flags"]["aurora"]["id"]: ["Compendium.x.features.a", "Compendium.x.features.b"]})
    assert count == 0
    assert doc["system"]["advancement"] == {}
    assert "nestedFeatureGrantSkipped" in doc["flags"]["aurora"]


def test_eldritch_cannon_actor_docs_are_actors_with_mode_items():
    actors = eldricht_cannon_actor_docs()
    assert len(actors) == 3
    assert {a["name"] for a in actors} == {
        "Eldritch Cannon - Flamethrower",
        "Eldritch Cannon - Force Ballista",
        "Eldritch Cannon - Protector",
    }
    for actor in actors:
        assert actor["type"] == "npc"
        assert actor["system"]["attributes"]["ac"]["flat"] == 18
        assert "poison" in actor["system"]["traits"]["di"]["value"]
        assert len(actor["items"]) == 1
