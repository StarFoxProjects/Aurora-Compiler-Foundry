import json
from aurora_compiler.foundry.module_writer import write_module
from aurora_compiler.compiler.feature_compiler import compile_feature
from aurora_compiler.models.aurora import AuroraElement


def test_module_writer_includes_runtime_esmodule(tmp_path):
    out = write_module(tmp_path / "module", {"features": []}, module_id="aurora-extra-pack", title="Aurora Extra Pack", version="2.8.0-alpha")
    module = json.loads((out / "module.json").read_text())
    assert module["esmodules"] == ["scripts/runtime.js"]
    runtime = (out / "scripts" / "runtime.js").read_text()
    assert 'const MODULE_ID = "aurora-extra-pack"' in runtime
    assert "targetedTempHp" in runtime


def test_protector_activity_has_runtime_temphp_flag():
    e = AuroraElement(
        id="ID_WOTC_ERLW_ARCHETYPE_FEATURE_ARTILLERIST_ELDRITCH_CANNON_PROTECTOR",
        name="Protector",
        type="Archetype Feature",
        source="Eberron: Rising from the Last War",
        description_html="<p>As a bonus action, the cannon emits temporary hit points equal to 1d8 + your Intelligence modifier to creatures of your choice within 10 feet.</p>",
    )
    item = compile_feature(e, module_id="aurora-extra-pack")
    acts = item["system"]["activities"]
    protector = next(a for a in acts.values() if a["name"] == "Protector")
    runtime = protector["flags"]["aurora"]["runtime"]
    assert runtime["action"] == "targeted-temphp"
    assert runtime["formula"] == "1d8 + @abilities.int.mod"
    assert runtime["radius"] == 10
    assert runtime["backend"] == "aurora-runtime-js-v2.8"


def test_generic_temphp_activity_gets_runtime_flag():
    e = AuroraElement(
        id="ID_TEST_TEMP_HP",
        name="Protective Pulse",
        type="Racial Trait",
        source="Test",
        description_html="<p>As a bonus action, one creature gains temporary hit points equal to your proficiency bonus.</p>",
    )
    item = compile_feature(e, module_id="aurora-extra-pack")
    activity = next(iter(item["system"]["activities"].values()))
    assert activity["type"] == "heal"
    runtime = activity["flags"]["aurora"]["runtime"]
    assert runtime["action"] == "targeted-temphp"
    assert runtime["formula"] == "@prof"
