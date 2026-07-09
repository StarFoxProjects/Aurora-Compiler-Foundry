# Species/Race Compiler v0.9

The species compiler emits Foundry `race` items for Aurora `Race` and `Sub Race` elements.

v0.9 focuses on making every species visible in the Foundry Advancement workflow. The compiler now always emits a native `Size` advancement even when the source has no racial trait grants.

## Compiled data

- `system.movement.walk` from Aurora `stat name="innate speed"` or text fallback.
- `system.size` from Aurora size grants or text fallback.
- `Size` advancement for every race/species.
- Fixed racial ability score increases as `AbilityScoreImprovement` advancement when Aurora has ability `stat` rules.
- Language grants and language selections as `Trait` advancement.
- Racial trait grants as `ItemGrant` advancement when the referenced trait exists in the generated features compendium.

## Important Foundry behavior

Species do not have a level progression table like classes. A class can show a level-by-level advancement table because classes advance from level 1 to 20. A species normally has one-time advancements such as Size, Languages, Ability Score Increase, and Racial Traits.

So the expected result is not a class-style table, but an Advancement tab containing species-specific advancement entries.

## Remaining work

- Better language mapping for setting-specific languages.
- Better ability score choice handling for Tasha-style custom lineage.
- Subrace/parent race linking.
- Creature type and senses parsing.


## v1.0 fixed racial ASI behavior

Fixed racial/species ability scores are compiled as `AbilityScoreImprovement` advancements with:

- `configuration.fixed` populated, e.g. `{ "wis": 2, "cha": 1 }`;
- `configuration.points = 0`;
- `configuration.locked` set to the fixed abilities;
- `value.type = "asi"`;
- `value.assignments` pre-populated with the fixed values.

This avoids the empty ASI-flow issue observed with species such as Kalashtar (ERLW).


## v1.2 note
- Species ASI now keeps `value` empty in compendium items so Foundry applies the actor update during the advancement flow.
- Flexible species ASI rules now set `configuration.points`, so the + / - controls appear for selectable ASI.
- Race/species advancements now add native Trait grants for common damage resistances, damage immunities, vulnerabilities, and condition immunities parsed from Aurora condition rules and racial trait descriptions.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
