# Feature Compiler v0.5

The feature compiler converts Aurora `Class Feature`, `Archetype Feature`, `Racial Trait`, and `Feat` elements into Foundry D&D5e `feat` Items.

This is the first native feature pass. It does not yet fully implement every Aurora rule, but it now extracts common gameplay structure from text and rules:

- feature type: class / race / feat
- limited uses where obvious (`once per short or long rest`, `PB per long rest`, etc.)
- activation type (`action`, `bonus action`, `reaction`)
- simple range patterns
- simple area templates
- saving throw ability
- first damage formula and damage type
- raw Aurora rules preserved in `flags.aurora`
- human-readable `flags.aurora.nativeRuleNotes` for unsupported grants/stats/selects

## Why this matters

Before v0.5, most features were only text. Starting in v0.5, features can expose enough native data for Foundry/Midi/DAE integration work.

## Current limitations

- Activities are best-effort and text-derived.
- Complex resources such as Ki, Channel Divinity, Superiority Dice, Blood Maledict, etc. are not fully compiled yet.
- Active Effects are not generated yet.
- Feature-to-feature grants are handled by the Feature Linker, not by this compiler.

## Next milestone

v0.6 should add a resource compiler and improve feature activities for common class resources:

- Channel Divinity
- Ki
- Rage
- Bardic Inspiration
- Superiority Dice
- Blood Maledict
- Infusions

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
