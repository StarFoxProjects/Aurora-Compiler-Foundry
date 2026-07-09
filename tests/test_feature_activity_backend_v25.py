from aurora_compiler.models.aurora import AuroraElement
from aurora_compiler.compiler.feature_compiler import compile_feature
from aurora_compiler.reporting.compatibility import _backend_classification, _activity_summary, _advancement_summary


def _activity(doc):
    return next(iter(doc["system"]["activities"].values()))


def test_v25_damage_equal_to_proficiency_bonus_gets_custom_damage_formula():
    e = AuroraElement(
        id="ID_TEST_PROF_DAMAGE",
        name="Radiant Burst",
        type="Archetype Feature",
        source="Test",
        description_html="<p>As a bonus action, one creature within 30 feet takes radiant damage equal to your proficiency bonus.</p>",
    )
    doc = compile_feature(e)
    act = _activity(doc)
    assert act["type"] == "utility"
    assert act["activation"]["type"] == "bonus"
    assert act["damage"]["parts"][0]["types"] == ["radiant"]
    assert act["damage"]["parts"][0]["custom"]["formula"] == "@prof"


def test_v25_temp_hp_equal_to_ability_modifier_gets_formula():
    e = AuroraElement(
        id="ID_TEST_MOD_THP",
        name="Protective Magic",
        type="Archetype Feature",
        source="Test",
        description_html="<p>As an action, you grant temporary hit points equal to your Charisma modifier.</p>",
    )
    doc = compile_feature(e)
    act = _activity(doc)
    assert act["type"] == "heal"
    assert act["healing"]["types"] == ["temphp"]
    assert act["healing"]["custom"]["formula"] == "@abilities.cha.mod"


def test_v25_passive_extra_damage_classified_as_active_effect_or_js():
    doc = {
        "name": "Magical Inspiration",
        "type": "feat",
        "system": {"description": {"value": "<p>When a creature adds your Bardic Inspiration die to a damage roll, it can roll the die and add the number rolled to the damage.</p>"}, "activities": {}, "advancement": {}},
        "flags": {"aurora": {"rules": [{"tag": "stat", "attrs": {"name": "damage", "value": "1"}}]}},
    }
    kind, backend, priority = _backend_classification(doc, "magical inspiration when a creature adds your bardic inspiration die to a damage roll", _activity_summary(doc), _advancement_summary(doc), "features")
    assert kind == "needs-active-effect-or-js"
    assert priority == "P2"
