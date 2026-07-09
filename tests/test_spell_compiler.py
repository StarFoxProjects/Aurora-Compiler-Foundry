from aurora_compiler.parser.xml_parser import parse_xml_bytes
from aurora_compiler.compiler.spell_compiler import compile_spell


def test_spell_level_and_concentration():
    xml = b'''<elements><element name="Acid Gate" type="Spell" source="Deep Magic: Alkemancy" id="ID_TEST"><description><p>A 20-foot-radius sphere. A creature makes a Dexterity saving throw and takes 8d6 fire damage.</p></description><setters><set name="abbreviation">DMA</set><set name="level">7</set><set name="school">Conjuration</set><set name="time">1 action</set><set name="range">60 feet</set><set name="duration">Concentration, up to 1 minute</set><set name="hasVerbalComponent">true</set><set name="hasSomaticComponent">true</set><set name="hasMaterialComponent">true</set><set name="materialComponent">a vial</set><set name="isConcentration">true</set></setters></element></elements>'''
    e = parse_xml_bytes(xml)[0]
    doc = compile_spell(e, include_source_name=True)
    assert doc["name"] == "Acid Gate (DMA)"
    assert doc["system"]["level"] == 7
    assert "concentration" in doc["system"]["properties"]
    act = next(iter(doc["system"]["activities"].values()))
    assert act["range"]["value"] == 60
