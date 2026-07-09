# v1.5 Artillerist Cannon cleanup

This release fixes three issues found during Foundry testing:

- The compiler no longer adds a custom `Cantrips` ItemChoice advancement for classes. Foundry dnd5e already handles cantrip selection through the official `Cantrips Known` spellcasting advancement, so the extra picker was redundant.
- Artillerist cannon options (`Flamethrower`, `Force Ballista`, `Protector`) are no longer granted as separate actor features when `Eldritch Cannon` is granted. They are kept as activities on the single `Eldritch Cannon` feature.
- Cannon activities now use normalized target template fields so Foundry has enough data to prompt measured template placement for `Flamethrower` and `Protector`.

The `Create Eldritch Cannon` activity still depends on Foundry dnd5e's Summon activity permissions. GM users should be able to create the token. Player users need the D&D5e summon setting/permission enabled.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
