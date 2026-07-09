# Foundry D&D5e target format

The compiler targets Foundry VTT v14 and D&D5e system v5.x.

## Spell target

A compiled spell must contain at least:

- `type: "spell"`
- `system.level`
- `system.school`
- `system.properties`
- `system.materials`
- `system.activities`
- `system.source`
- `flags.aurora`

The activity object is where Foundry v14 stores cast data such as:

- activation
- duration
- range
- target/template
- spell slot consumption
- effects

## Class target

A native class needs:

- `system.hd.denomination`
- `system.advancement`
- `system.spellcasting`
- trait advancement for weapons/saves/skills
- item grants for class features
- subclass advancement
- starting equipment

This is the next major milestone.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
