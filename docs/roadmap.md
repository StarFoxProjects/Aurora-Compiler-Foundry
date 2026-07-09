# Roadmap

## Milestone 1: Parser and spell compiler

- [x] Parse Aurora ZIP
- [x] Preserve setters/rules/supports
- [x] Build Foundry module
- [x] Basic spell activities
- [ ] Use official spell exports as templates
- [ ] Damage/save/scaling parser
- [ ] Active effects for buff/debuff spells

## Milestone 2: Class compiler

- [ ] Parse class rules into grants/selects
- [ ] Generate hit dice advancement
- [ ] Generate trait advancement
- [ ] Generate item grants for features
- [ ] Generate spellcasting progression
- [ ] Generate subclass choice advancement

## Milestone 3: Species compiler

- [ ] Speed/size/languages
- [ ] Trait grants
- [ ] Ability score choices
- [ ] Active effects for special traits

## Milestone 4: Linker

- [ ] Aurora ID → Foundry UUID mapping
- [ ] Class → feature links
- [ ] Subclass → feature links
- [ ] Spell list links

## Milestone 5: Quality and diagnostics

- [ ] Compilation report
- [ ] Missing reference report
- [ ] Duplicate source report
- [ ] Unsupported Aurora rule report


## v1.2 note
- Species ASI now keeps `value` empty in compendium items so Foundry applies the actor update during the advancement flow.
- Flexible species ASI rules now set `configuration.points`, so the + / - controls appear for selectable ASI.
- Race/species advancements now add native Trait grants for common damage resistances, damage immunities, vulnerabilities, and condition immunities parsed from Aurora condition rules and racial trait descriptions.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
