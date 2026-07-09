# v1.8 Compatibility Map

v1.8 changes the project priority from isolated hotfixes to a full compiler map.

The build now emits human-readable compatibility reports alongside the Foundry module:

- `compatibility-summary-v1.8.md` — readable summary and first high-priority issues.
- `compatibility-summary-v1.8.html` — browser-readable summary.
- `compatibility-map-v1.8.json` — full machine-readable compatibility map.
- `compatibility-issues-v1.8.csv` — all detected issues in spreadsheet-friendly form.
- `compatibility-classes-v1.8.csv` — class advancement/subclass/item-choice coverage.
- `compatibility-species-v1.8.csv` — species advancement, movement, senses, resistances/immunities/vulnerabilities.
- `compatibility-spells-v1.8.csv` — spell activities, damage, saves, healing, templates.
- `compatibility-features-v1.8.csv` — class/subclass/species/feat feature automation coverage.
- `compatibility-equipment-v1.8.csv` — equipment/magic item uses, attunement and activities.

The map is heuristic. It does not claim rules correctness. It highlights where Aurora XML concepts are not yet converted into native Foundry dnd5e structures such as advancements, activities, active effects, item choices, uses, templates, summon actors, or native trait fields.

## Priority model

- `critical`: document is probably not usable as native Foundry content.
- `high`: a visible rules action or grant is likely missing.
- `medium`: automation is partial or may require manual setup.
- `low`: cosmetic/effect automation may be incomplete.

## Intended workflow

1. Generate the module.
2. Open `compatibility-summary-v1.8.md` first.
3. Use `compatibility-issues-v1.8.csv` for filtering by severity/area.
4. Pick a category, fix the compiler backend, regenerate, then compare the report again.

This keeps the project from becoming a long chain of one-off fixes.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
