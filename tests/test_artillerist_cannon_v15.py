from aurora_compiler.models.aurora import AuroraElement
from aurora_compiler.compiler.class_compiler import compile_class
from aurora_compiler.compiler.feature_compiler import compile_feature, child_feature_uuid_index, eldricht_cannon_actor_docs
from aurora_compiler.compiler.subclass_compiler import compile_subclass


def test_class_compiler_does_not_create_duplicate_cantrip_item_choice():
    e = AuroraElement(source="Eberron: Rising from the Last War", id="ID_WOTC_ERLW_CLASS_ARTIFICER", name="Artificer", type="Class")
    doc = compile_class(e, class_cantrip_uuids=["Compendium.x.spells.a", "Compendium.x.spells.b"])
    advancements = list(doc["system"]["advancement"].values())
    assert any(a["type"] == "ScaleValue" and a["title"] == "Cantrips Known" for a in advancements)
    assert not any(a["type"] == "ItemChoice" and a["title"] == "Cantrips" for a in advancements)


def test_eldritch_cannon_child_options_are_not_indexed_as_actor_features():
    cannon = AuroraElement(
        source="Eberron: Rising from the Last War",
        id="ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_ELDRITCH_CANNON",
        name="Eldritch Cannon",
        type="Archetype Feature",
        rules=[{"tag": "grant", "attrs": {"type": "Archetype Feature", "id": "ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_FORCE_BALLISTA"}}],
    )
    option = AuroraElement(
        source="Eberron: Rising from the Last War",
        id="ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_FORCE_BALLISTA",
        name="Force Ballista",
        type="Archetype Feature",
    )
    idx = child_feature_uuid_index([cannon, option], {
        cannon.id: "Compendium.test.features.cannon",
        option.id: "Compendium.test.features.force",
    })
    assert cannon.id not in idx


def test_artillerist_subclass_does_not_grant_cannon_option_features_directly():
    artillerist = AuroraElement(
        source="Eberron: Rising from the Last War",
        id="ID_WOTC_ERLW_ARCHETYPE_ARTIFICER_ARTILLERIST",
        name="Artillerist",
        type="Archetype",
        supports=["Artificer Specialist"],
        rules=[
            {"tag": "grant", "attrs": {"type": "Archetype Feature", "id": "ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_ELDRITCH_CANNON", "level": "3"}},
            {"tag": "grant", "attrs": {"type": "Archetype Feature", "id": "ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_FLAMETHROWER", "level": "3"}},
        ],
    )
    doc = compile_subclass(artillerist, feature_uuid_by_aurora_id={
        "ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_ELDRITCH_CANNON": "Compendium.test.features.cannon",
        "ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_FLAMETHROWER": "Compendium.test.features.flame",
    })
    grants = []
    for adv in doc["system"]["advancement"].values():
        for item in adv.get("configuration", {}).get("items", []):
            grants.append(item["uuid"])
    assert "Compendium.test.features.cannon" in grants
    assert "Compendium.test.features.flame" not in grants


def test_cannon_mode_activities_are_available_on_visual_cannon_actors():
    actors = {a["name"]: a for a in eldricht_cannon_actor_docs()}

    flame = actors["Eldritch Cannon - Flamethrower"]["items"][0]
    flame_activity = next(iter(flame["system"]["activities"].values()))
    assert flame_activity["name"] == "Flamethrower"
    assert flame_activity["target"]["template"]["type"] == "cone"
    assert flame_activity["target"]["template"]["size"] == 15
    assert flame_activity["target"]["prompt"] is True

    protector = actors["Eldritch Cannon - Protector"]["items"][0]
    protector_activity = next(iter(protector["system"]["activities"].values()))
    assert protector_activity["name"] == "Protector"
    assert protector_activity["type"] == "heal"
    assert protector_activity["target"]["template"]["type"] == ""
    assert protector_activity["target"]["prompt"] is False
    assert protector_activity["target"]["affects"]["choice"] is False
    assert protector_activity["healing"]["number"] == 1
    assert protector_activity["healing"]["denomination"] == 8
    assert protector_activity["healing"]["bonus"] == "@abilities.int.mod"
    assert "temphp" in protector_activity["healing"]["types"]
