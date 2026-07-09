from aurora_compiler.models.aurora import AuroraElement
from aurora_compiler.compiler.feature_compiler import compile_feature


def test_feature_compiler_creates_activity_for_action_save_area():
    e = AuroraElement(
        id="ID_TEST_FEATURE",
        name="Searing Sunburst",
        type="Archetype Feature",
        source="Unearthed Arcana: Test",
        description_html="<p>As an action, each creature in a 20-foot-radius sphere must make a Constitution saving throw or take 2d6 radiant damage.</p>",
    )
    doc = compile_feature(e)
    assert doc["type"] == "feat"
    acts = doc["system"]["activities"]
    assert len(acts) == 1
    activity = next(iter(acts.values()))
    assert activity["activation"]["type"] == "action"
    assert activity["target"]["template"]["type"] == "circle"
    assert activity["target"]["template"]["size"] == 20
    assert activity["save"]["ability"] == "con"
    assert activity["damage"]["parts"][0]["types"] == ["radiant"]


def test_feature_compiler_parses_limited_uses():
    e = AuroraElement(
        id="ID_TEST_LIMITED",
        name="Shadow Jaunt",
        type="Class Feature",
        source="Homebrew",
        description_html="<p>You can use this feature once per short or long rest.</p>",
    )
    doc = compile_feature(e)
    assert doc["system"]["uses"]["max"] == "1"
    assert doc["system"]["uses"]["recovery"][0]["period"] == "sr"


def test_artillerist_protector_gets_temp_hp_heal_activity():
    e = AuroraElement(
        id="ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_ELDRITCH_CANNON_PROTECTOR",
        name="Protector",
        type="Archetype Feature",
        source="Eberron: Rising from the Last War",
        description_html="<p>The cannon emits a burst of positive energy that grants temporary hit points equal to 1d8 + your Intelligence modifier.</p>",
    )
    doc = compile_feature(e)
    activity = next(iter(doc["system"]["activities"].values()))
    assert activity["type"] == "heal"
    assert activity["activation"]["type"] == "bonus"
    assert activity["healing"]["types"] == ["temphp"]
    assert activity["healing"]["bonus"] == "@abilities.int.mod"


def test_artillerist_force_ballista_gets_spell_attack_activity():
    e = AuroraElement(
        id="ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_ELDRITCH_CANNON_FORCE_BALLISTA",
        name="Force Ballista",
        type="Archetype Feature",
        source="Eberron: Rising from the Last War",
        description_html="<p>Make a ranged spell attack at one creature within 120 feet. On a hit, the target takes 2d8 force damage.</p>",
    )
    doc = compile_feature(e)
    activity = next(iter(doc["system"]["activities"].values()))
    assert activity["type"] == "attack"
    assert activity["activation"]["type"] == "bonus"
    assert activity["attack"]["type"] == {"value": "ranged", "classification": "spell"}
    assert activity["damage"]["parts"][0]["types"] == ["force"]
