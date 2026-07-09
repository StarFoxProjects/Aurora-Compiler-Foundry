from aurora_compiler.models.aurora import AuroraElement
from aurora_compiler.compiler.feature_compiler import compile_feature


def _activity(doc):
    return next(iter(doc["system"]["activities"].values()))


def test_v23_natural_weapon_bite_gets_attack_activity_and_damage():
    e = AuroraElement(
        id="ID_TEST_BITE",
        name="Bite",
        type="Racial Trait",
        source="Test",
        description_html="<p>Your fanged maw is a natural weapon, which you can use to make unarmed strikes. If you hit with it, you deal piercing damage equal to 1d6 + your Strength modifier.</p>",
    )
    doc = compile_feature(e)
    act = _activity(doc)
    assert act["type"] == "attack"
    assert act["attack"]["type"] == {"value": "melee", "classification": "weapon"}
    assert act["damage"]["parts"][0]["types"] == ["piercing"]
    assert act["damage"]["parts"][0]["custom"]["formula"] == "1d6 + @abilities.str.mod"


def test_v23_temp_hp_feature_gets_heal_activity():
    e = AuroraElement(
        id="ID_TEST_BEASTHIDE",
        name="Beasthide",
        type="Racial Trait",
        source="Test",
        description_html="<p>As a bonus action, you can shift and gain 1d6 temporary hit points.</p>",
    )
    doc = compile_feature(e)
    act = _activity(doc)
    assert act["type"] == "heal"
    assert act["activation"]["type"] == "bonus"
    assert act["healing"]["types"] == ["temphp"]
    assert act["healing"]["number"] == 1
    assert act["healing"]["denomination"] == 6


def test_v23_save_damage_feature_uses_save_activity():
    e = AuroraElement(
        id="ID_TEST_FIRE_BURST",
        name="Fire Burst",
        type="Archetype Feature",
        source="Test",
        description_html="<p>As an action, each creature in a 10-foot-radius sphere must make a Dexterity saving throw, taking 2d8 fire damage on a failed save.</p>",
    )
    doc = compile_feature(e)
    act = _activity(doc)
    assert act["type"] == "save"
    assert act["save"]["ability"] == "dex"
    assert act["damage"]["parts"][0]["types"] == ["fire"]
