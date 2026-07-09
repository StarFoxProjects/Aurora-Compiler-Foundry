# v2.0 Compatibility Classifier

v2.0 keeps the v1.8 compatibility map, but makes it less noisy.

The main change is issue classification:

- `compatibility-real-issues-v2.0.csv` contains real compiler gaps that should be fixed by a backend.
- `compatibility-absorbed-helpers-v2.0.csv` contains Aurora helper entries such as movement, senses, ASI, languages, proficiencies, resistances and immunities. These should usually be absorbed into a parent race/class/subclass instead of being treated as standalone Foundry features.
- `compatibility-issues-v2.0.csv` contains both lists together.

New issue fields:

- `priority`: `P0`, `P1`, `P2`, `P3`
- `issueKind`: examples include `real-missing-activity`, `needs-active-effect-or-js`, `needs-summon-backend`, `absorbed-helper:movement`, `absorbed-helper:senses`, `absorbed-helper:traits`, `absorbed-helper:ability-score`
- `backend`: the compiler backend that probably needs to solve the item

The recommended reading order is:

1. Open `compatibility-summary-v2.0.html`.
2. Open `compatibility-real-issues-v2.0.csv` in a spreadsheet.
3. Filter by `priority = P0` or `P1`.
4. Then filter by `issueKind` or `area`.

This version is not meant to make all content rules-perfect. It produces a cleaner map for the next backend fixes.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
