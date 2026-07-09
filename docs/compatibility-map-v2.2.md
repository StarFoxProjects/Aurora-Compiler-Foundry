# Compatibility Map v2.2

v2.2 is a classifier cleanup and subclass-parent inference release.

## Changes

- Added source/name fallback mapping for extra Aurora classes such as Pugilist, Cook, Magus, Swordmage, Factotum, Spiritualist, Grave Warden and Weaveshaper.
- Removed remaining P0 subclass rows caused by missing `system.classIdentifier` in the tested Aurora Paid build.
- Split spell activity issues into specific backend families:
  - `spell-damage-backend`
  - `spell-save-backend`
  - `spell-healing-backend`
  - `spell-template-backend`
- Made spell-grant detection stricter so passive features like Potent Spellcasting and Spell Breaker are no longer incorrectly treated as spell grant backends.
- Added transformation/form classification for Shapechanger, Starry Form, Astral Self and similar features.
- Reduced duplicated P1 rows for spell-grant features by suppressing damage/heal/save rows that only come from spell list text.
- Kept true summon backend focused on real companion/cannon/familiar/servant/token features.

## Tested result with the provided Aurora Paid zip

- Real issues: 5302
- P0/P1 real issues: 1450
- P0 rows: 0
- P1 features: 865
- P1 spells: 327
- P1 species: 251
- P1 subclasses: 7

The next compiler backend should target feature activities first, then spell grants/spell activities.
