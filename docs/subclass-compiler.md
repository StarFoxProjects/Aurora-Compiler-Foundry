# Subclass Compiler v0.7

The subclass compiler converts Aurora `Archetype` elements into native Foundry D&D5e `subclass` items.

## Goals

- Generate `type: "subclass"` documents instead of generic description-only items.
- Infer `system.classIdentifier` from Aurora `<supports>` labels such as:
  - `Arcane Tradition` -> `wizard`
  - `Artificer Specialist` -> `artificer`
  - `Divine Domain` -> `cleric`
  - `Sacred Oath` -> `paladin`
  - `Roguish Archetype` -> `rogue`
- Compile subclass feature grants into `ItemGrant` advancements where possible.
- Compile subclass spell grants into `ItemGrant` advancements where the spell exists in the generated module.
- Preserve raw Aurora rules in `flags.aurora` for future refinement.

## Limitations

- If a subclass grants a spell that is skipped because it already exists in D&D Legacy/Modern content, v0.7 records it as a missing spell grant. A future version should resolve those references to official compendium UUIDs.
- Some custom/homebrew subclasses may use non-standard `<supports>` labels. These are recorded as `missing-subclass-class-identifier` in `compilation-report.json`.
- Subclass feature grants require the referenced Aurora feature to be compiled into the module.

## Foundry integration

Foundry's class subclass picker depends on two pieces:

1. The class item has a `Subclass` advancement at the correct level.
2. Subclass items have `system.classIdentifier` matching the class `system.identifier`.

v0.7 implements the second piece for Aurora archetypes. The class compiler already creates the first piece for common D&D5e classes.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
