from aurora_compiler.reporting.compatibility import (
    _backend_classification,
    _is_spell_grant_feature,
    _is_true_summon_feature,
    _is_transformation_feature,
)
from aurora_compiler.compiler.subclass_compiler import infer_class_identifier
from aurora_compiler.models.aurora import AuroraElement


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


def test_v22_potent_spellcasting_is_not_spell_grant():
    doc = _feat('Potent Spellcasting (SCAG)', 'You add your Wisdom modifier to damage with cleric cantrips.')
    text = 'potent spellcasting add your wisdom modifier to damage with cleric cantrips'
    assert not _is_spell_grant_feature(doc, text)
    kind, backend, priority = _backend_classification(doc, text, {'count': 0}, {'count': 0}, 'features')
    assert kind == 'needs-active-effect-or-js'
    assert priority == 'P2'


def test_v22_shapechanger_is_transformation_not_summon():
    doc = _feat('Shapechanger (MPMM)', 'You can transform. Your game statistics remain the same.')
    text = 'shapechanger transform your game statistics remain the same'
    assert _is_transformation_feature(doc, text)
    assert not _is_true_summon_feature(doc, text)
    kind, backend, priority = _backend_classification(doc, text, {'count': 0}, {'count': 0}, 'features')
    assert kind == 'needs-transformation-backend'


def test_v22_starry_form_is_transformation_not_summon():
    doc = _feat('Starry Form (TCE)', 'As a bonus action, you can expend a use of Wild Shape to take on a starry form.')
    text = 'starry form bonus action expend wild shape starry form damage healing'
    assert not _is_true_summon_feature(doc, text)
    kind, backend, priority = _backend_classification(doc, text, {'count': 0}, {'count': 0}, 'features')
    assert kind == 'needs-transformation-backend'


def test_v22_extra_subclass_parent_inference():
    assert infer_class_identifier(AuroraElement(id='ID_X', name='The Sweet Science', type='Archetype', source='PUGL')) == 'pugilist'
    assert infer_class_identifier(AuroraElement(id='ID_X', name='Spellsword', type='Archetype', source='AASM')) == 'swordmage'
    assert infer_class_identifier(AuroraElement(id='ID_X', name='Alchemist', type='Archetype', source='Unearthed Arcana')) == 'artificer'
