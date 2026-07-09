from aurora_compiler.models.aurora import AuroraElement
from aurora_compiler.compiler.resource_compiler import detect_feature_resource, class_resource_advancements, class_resource_flags
from aurora_compiler.compiler.feature_compiler import compile_feature
from aurora_compiler.compiler.class_compiler import compile_class


def elem(name, type_="Class Feature", source="Player's Handbook"):
    return AuroraElement(id=f"ID_TEST_{name.upper().replace(' ', '_')}", name=name, type=type_, source=source, description_html=f"<p>{name}</p>")


def test_detect_rage_resource():
    spec = detect_feature_resource(elem("Rage"))
    assert spec is not None
    assert spec.identifier == "rage"
    assert spec.max == "@scale.barbarian.rages"


def test_compile_feature_resource_uses():
    doc = compile_feature(elem("Channel Divinity"))
    assert doc["system"]["uses"]["max"] == "@scale.cleric.channel-divinity-uses"
    assert doc["system"]["uses"]["recovery"][0]["period"] == "sr"
    assert doc["flags"]["aurora"]["resource"]["identifier"] == "channel-divinity"


def test_class_resource_advancements_barbarian():
    docs = class_resource_advancements("class:test", "barbarian")
    identifiers = {d["configuration"]["identifier"] for d in docs}
    assert "rages" in identifiers
    assert "rage-damage" in identifiers


def test_compile_class_has_resource_flags():
    doc = compile_class(elem("Artificer", type_="Class", source="Eberron: Rising from the Last War"))
    resources = doc["flags"]["aurora"]["resources"]
    assert any(r["identifier"] == "infusions-known" for r in resources)
    advancement_identifiers = [a.get("configuration", {}).get("identifier") for a in doc["system"]["advancement"].values()]
    assert "infusions-known" in advancement_identifiers
