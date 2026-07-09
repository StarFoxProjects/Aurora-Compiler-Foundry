from aurora_compiler.reporting.compatibility import _backend_classification, _is_spell_grant_feature, _is_true_summon_feature


def _feat(name, desc='', rules=None, aurora_id='ID_TEST'):
    return {
        'name': name,
        'type': 'feat',
        'system': {
            'description': {'value': desc},
            'activities': {},
            'advancement': {},
        },
        'flags': {'aurora': {'id': aurora_id, 'type': 'Archetype Feature', 'rules': rules or []}},
    }


def test_v21_oath_spells_are_spell_grants_not_summons():
    doc = _feat('Oath Spells (SCAG)', 'You gain oath spells including spirit guardians.', rules=[{'tag': 'grant', 'attrs': {'type': 'Spell', 'id': 'ID_WOTC_PHB_SPELL_SPIRIT_GUARDIANS'}}])
    text = 'oath spells spirit guardians spell list you can cast'
    assert _is_spell_grant_feature(doc, text)
    assert not _is_true_summon_feature(doc, text)
    kind, backend, priority = _backend_classification(doc, text, {'count': 0}, {'count': 0}, 'features')
    assert kind == 'spell-grant-backend'
    assert priority == 'P1'


def test_v21_eldritch_cannon_is_true_summon():
    doc = _feat('Eldritch Cannon (ERLW)', 'Create a magical cannon in an unoccupied space. It uses your spell attack modifier.')
    text = 'eldritch cannon create a magical cannon in an unoccupied space uses your spell attack modifier'
    assert _is_true_summon_feature(doc, text)
    kind, backend, priority = _backend_classification(doc, text, {'count': 0}, {'count': 0}, 'features')
    assert kind == 'needs-summon-backend'
    assert priority == 'P1'


def test_v21_spirit_word_alone_does_not_make_summon():
    doc = _feat('Unyielding Spirit (SCAG)', 'You have advantage on saving throws against becoming paralyzed or stunned.')
    text = 'unyielding spirit advantage saving throws paralyzed stunned'
    assert not _is_true_summon_feature(doc, text)
    kind, backend, priority = _backend_classification(doc, text, {'count': 0}, {'count': 0}, 'features')
    assert kind != 'needs-summon-backend'
