from aurora_compiler.reporting.compatibility import _species_text_explicitly_grants_flight


def test_v24_species_flight_detector_ignores_generic_fly_words():
    text = "this species can cast spells and mentions flying creatures in examples, but grants no movement."
    assert not _species_text_explicitly_grants_flight(text)


def test_v24_species_flight_detector_accepts_real_fly_speed():
    assert _species_text_explicitly_grants_flight("you have a flying speed equal to your walking speed")
    assert _species_text_explicitly_grants_flight("you gain a fly speed of 30 feet")
