# Species compiler v1.3

Adds expansion of Aurora meta-grants used by modern species, such as default racial ASI and default languages.

Also compiles species movement and senses into native race fields:

- walk/fly/swim/climb/burrow movement from race and granted racial trait rules
- darkvision/blindsight/tremorsense/truesight from race and granted racial trait rules/text
- damage resistances, immunities, vulnerabilities, and condition immunities via Trait advancement where safe

Damage modification is intentionally not auto-applied yet because Foundry needs a numeric amount/formula and Aurora often stores this as feature-specific attack/damage logic. These notes remain available in flags/reporting until a dedicated active-effect/damage compiler is added.

Subrace selection is not native in Foundry D&D5e the way class subclass selection is. The current safe approach keeps subraces/species variants as separate race documents; a later pass can add a custom UI or merge base race + subrace into ready-to-drop combined race documents.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
