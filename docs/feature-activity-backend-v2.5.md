# Feature Activity Backend v2.7

v2.7 is a second pass for feature activities and the compatibility report.

## Compiler improvements

- Parses non-dice formulas such as `your proficiency bonus`, `twice your proficiency bonus`, and ability modifiers.
- Converts formulas such as `your Charisma modifier` into Foundry roll data like `@abilities.cha.mod`.
- Better temporary HP formulas when no dice are present.
- More long-rest and short-rest phrasing for limited uses.

## Report improvements

- Passive/triggered modifiers are no longer treated as normal P1 rollable activities.
- Text such as `when you hit`, `damage roll`, `extra damage`, `reduce the damage`, `reroll`, advantage/disadvantage now goes to `needs-active-effect-or-js` with P2 priority.

This keeps the P1 bucket focused on features that should become real attack/save/heal/damage activities.
