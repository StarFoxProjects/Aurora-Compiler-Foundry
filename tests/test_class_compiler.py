from aurora_compiler.compiler.class_compiler import compile_class
from aurora_compiler.models.aurora import AuroraElement


def test_wizard_like_class_has_full_casting_and_hit_die():
    e = AuroraElement(
        id="ID_WOTC_PHB_CLASS_WIZARD",
        name="Wizard",
        type="Class",
        source="Player's Handbook",
        description_html="<p><strong>Hit Dice:</strong> 1d6 per wizard level</p><p><strong>Saving Throws:</strong> Intelligence, Wisdom</p><p><strong>Skills:</strong> Choose two from Arcana, History, Insight, Investigation, Medicine, and Religion.</p>",
    )
    doc = compile_class(e)
    assert doc["type"] == "class"
    assert doc["system"]["hd"]["denomination"] == "d6"
    assert doc["system"]["spellcasting"]["progression"] == "full"
    assert doc["system"]["spellcasting"]["ability"] == "int"
    assert doc["system"]["advancement"]


def test_artificer_is_half_caster_int():
    e = AuroraElement(
        id="ID_WOTC_ERLW_CLASS_ARTIFICER",
        name="Artificer",
        type="Class",
        source="Eberron: Rising from the Last War",
        description_html="<p><strong>Hit Dice:</strong> 1d8 per artificer level</p><p><strong>Saving Throws:</strong> Constitution, Intelligence</p>",
    )
    doc = compile_class(e)
    assert doc["system"]["hd"]["denomination"] == "d8"
    assert doc["system"]["spellcasting"]["progression"] == "half"
    assert doc["system"]["spellcasting"]["ability"] == "int"


def test_artificer_has_infusion_item_choice_when_pool_is_provided():
    e = AuroraElement(
        id="ID_WOTC_ERLW_CLASS_ARTIFICER",
        name="Artificer",
        type="Class",
        source="Eberron: Rising from the Last War",
        description_html="<p><strong>Hit Dice:</strong> 1d8 per artificer level</p>",
    )
    doc = compile_class(e, artificer_infusion_uuids=["Compendium.test.features.infusion1", "Compendium.test.features.infusion2"])
    choices = [a for a in doc["system"]["advancement"].values() if a["type"] == "ItemChoice"]
    assert choices
    choice = choices[0]
    assert choice["title"] == "Artificer Infusions"
    assert choice["configuration"]["choices"]["2"]["count"] == 4
    assert choice["configuration"]["choices"]["6"]["count"] == 2
    assert len(choice["configuration"]["pool"]) == 2
