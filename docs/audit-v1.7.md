# v1.7 Compiler Audit and Artificer Infusions

v1.7 adds a quality/audit report to stop treating the compiler as a collection of isolated hotfixes.

Generated modules now include:

- `compilation-report.json`: parser and missing-reference diagnostics.
- `compiler-audit-v1.7.json`: native coverage diagnostics.

The audit report lists:

- class advancement status;
- Artificer infusion pool size;
- species with no advancement;
- features that still have Aurora rules but no native Foundry activities/advancements;
- activity and advancement type counts.

## Artificer Infusions

Aurora databases are inconsistent: infusion choices can appear as Class Feature, Feat, Item, or Magic Item elements depending on the source pack. v1.7 detects infusion choices using supports, ids, file names, and rule metadata, then compiles them into a dedicated pack:

- `Aurora Content - Artificer Infusions`

The Artificer class receives one `ItemChoice` advancement titled `Artificer Infusions`, with the explicit infusion pool. This is intentionally separate from normal class features, because an infusion choice is not the same thing as gaining a fixed feature.

## Important limitation

The audit does not mean every rule is automated. It is a map of what still needs a native compiler backend.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
