from aurora_compiler.parser.xml_parser import parse_xml_bytes


def test_setter_text_value():
    xml = b'''<elements><element name="Acid Gate" type="Spell" source="Deep Magic: Alkemancy" id="ID_TEST"><description><p>x</p></description><setters><set name="level">7</set><set name="isConcentration">true</set></setters></element></elements>'''
    e = parse_xml_bytes(xml)[0]
    assert e.setter("level") == "7"
    assert e.setter_bool("isConcentration") is True
