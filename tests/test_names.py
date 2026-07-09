from aurora_compiler.models.aurora import clean_duplicate_name, slugify


def test_clean_duplicate_name():
    assert clean_duplicate_name("Acid Gate Acid Gate") == "Acid Gate"
    assert clean_duplicate_name("Fireball - Fireball") == "Fireball"
    assert clean_duplicate_name("Fireball") == "Fireball"


def test_slugify():
    assert slugify("Acid Gate") == "acid-gate"
