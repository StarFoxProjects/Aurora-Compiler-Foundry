# Class Compiler v0.3

The class compiler is the first native-D&D5e compiler pass. It does not simply copy Aurora class descriptions into Foundry. It tries to map Aurora class information into the same major structures used by Foundry D&D5e class documents.

## Current output

For `element type="Class"`, v0.3 generates:

- `type: "class"`
- `system.hd.denomination`
- `system.spellcasting.progression`
- `system.spellcasting.ability`
- `system.spellcasting.preparation.formula`
- `system.advancement` entries for:
  - hit points
  - saving throws
  - armor and weapon proficiencies when detectable
  - skill choice pools when detectable
  - subclass selection level
  - ability score improvements
  - cantrips-known scale for common spellcasters
- `flags.aurora` preserving raw Aurora rules, setters, supports, file, source and id.

## Known limitations

This is not yet a complete class compiler. It still needs the linker stage before classes can grant every feature automatically.

Missing or incomplete in v0.3:

- item grants for class features from Aurora IDs
- true starting equipment choices
- tool proficiency choices
- class-specific scales such as Rage, Sneak Attack, Ki, Bardic Inspiration, Infusions
- subclass linking to the generated subclass compendium
- optional or alternate class features

## Next planned step

The next milestone is the Feature Linker:

1. Parse Aurora `grant type="Class Feature"` and similar rules.
2. Resolve the referenced Aurora feature ID to a generated Foundry Item UUID.
3. Emit Foundry `ItemGrant` advancement entries for the correct class levels.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
