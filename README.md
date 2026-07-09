# Aurora Compiler for Foundry D&D5e

Aurora Compiler converts Aurora Builder XML databases into Foundry VTT add-on modules for the official D&D5e system.

The project goal is **not** to create a new game system. The generated module extends the existing Foundry D&D5e system and D&D Legacy/Modern Content with extra, UA, third-party, and homebrew content.

## Current status

Alpha compiler. Current focus:

1. Stable Aurora XML parser.
2. Better spell compiler using Aurora setters.
3. Clean module writer.
4. Diagnostics/reporting so we can see what compiled and what still needs native Foundry support.

## Install for development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Inspect an Aurora ZIP

```bash
aurora-compiler inspect --aurora-zip "Aurora Paid.zip" --out report.json
```

## Build a Foundry module

Full content pack:

```bash
aurora-compiler build \
  --aurora-zip "Aurora Paid.zip" \
  --out Aurora_Content_Pack \
  --module-id aurora-content-pack \
  --title "Aurora Content Pack" \
  --include-source
```

Extra-only pack, using exported official Foundry JSON examples to filter duplicates:

```bash
aurora-compiler build \
  --aurora-zip "Aurora Paid.zip" \
  --official-examples data/official_examples \
  --extra-only \
  --out Aurora_Extra_Pack \
  --module-id aurora-extra-pack \
  --title "Aurora Extra Pack" \
  --include-source
```

Copy the output folder into Foundry:

```bash
cd /home/ubuntu/.local/share/FoundryVTT/Data/modules/
rm -rf aurora-content-pack aurora-extra-pack
cp -r /path/to/Aurora_Content_Pack aurora-content-pack
sudo systemctl restart foundry
```

## Important legal note

This repository should contain only compiler code and test fixtures that you are allowed to share. Do **not** commit copyrighted Aurora databases, full D&D books, or generated packs containing protected text.

The intended workflow is local: users provide their own Aurora XML files and generate their own private Foundry module.

## Architecture

See:

- `docs/architecture.md`
- `docs/foundry-target-format.md`
- `docs/roadmap.md`
- `docs/export-foundry-examples.md`

## v0.3 alpha status

This version introduces the first native class compiler foundation. Classes now generate Foundry D&D5e `advancement`, `spellcasting`, hit dice, saving throw traits, skill-choice traits, subclass placeholders and ASI advancements where possible.

The compiler is still alpha. Feature grants are intentionally not complete yet; the next milestone is the Feature Linker that resolves Aurora class-feature IDs into generated Foundry UUIDs.


## v0.4 Feature Linker

Adds the first Aurora rule linker: class `<grant type="Class Feature">` rules are converted into Foundry `ItemGrant` advancement entries when the target feature exists in the generated features compendium.


## v0.5 alpha

Adds the first native Feature Compiler pass for class features, racial traits, archetype features, and feats.

## v0.9 Resource Compiler

Adds the first resource compiler pass:

- class scale values for Rages, Rage Damage, Channel Divinity, Ki, Sorcery Points, Superiority Dice, Blood Maledict, Hemocraft Die, Infusions Known and Infused Items;
- feature `system.uses` generation for common resources such as Rage, Bardic Inspiration, Channel Divinity, Wild Shape, Ki, Sorcery Points, Superiority Dice, Blood Maledict and Infuse Item;
- `flags.aurora.resources` and `flags.aurora.resource` metadata for future Actor-resource and DAE/Midi-QOL integration.

See `docs/resource-compiler.md`.


## v0.9

Adds the first species/race compiler with racial trait ItemGrant advancements, speed/size inference, and missing trait diagnostics.


## Species Compiler v0.9

Every race/species now gets a native Size advancement. The compiler also emits fixed ASI and language Trait advancements when Aurora rules provide enough information.

- `docs/artificer-compiler.md`


## v1.2 note
- Species ASI now keeps `value` empty in compendium items so Foundry applies the actor update during the advancement flow.
- Flexible species ASI rules now set `configuration.points`, so the + / - controls appear for selectable ASI.
- Race/species advancements now add native Trait grants for common damage resistances, damage immunities, vulnerabilities, and condition immunities parsed from Aurora condition rules and racial trait descriptions.

## v1.7 Compiler Audit

Adds `compiler-audit-v1.7.json` to generated modules and moves detected Artificer infusion choices into a dedicated `infusions` compendium used by the Artificer `ItemChoice` advancement.

This version is the start of quality control: instead of fixing only one class at a time, the compiler now reports likely text-only features and missing native rule backends.


## v1.8 Compatibility Map

Builds now generate compatibility reports: `compatibility-summary-v1.8.md`, `compatibility-map-v1.8.json`, and spreadsheet-friendly CSV files for issues, classes, species, spells, features, and equipment.


## v2.0 Compatibility Classifier

Builds now generate a cleaner compatibility map that separates real compiler gaps from Aurora helper entries.

Main files:

- `compatibility-summary-v2.0.html`
- `compatibility-summary-v2.0.md`
- `compatibility-real-issues-v2.0.csv`
- `compatibility-absorbed-helpers-v2.0.csv`
- `compatibility-issues-v2.0.csv`
- `compatibility-map-v2.0.json`

Use `compatibility-real-issues-v2.0.csv` for backend work and `compatibility-absorbed-helpers-v2.0.csv` for movement/senses/ASI/language/proficiency/trait absorption work.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.

## v2.1 Compatibility Classifier Cleanup

v2.1 cleans the compatibility classifier before backend fixes:

- Oath/Domain/Circle/Patron/Innate spell grants are classified as `spell-grant-backend`, not summon problems.
- True summon/token problems are limited to companion, familiar, cannon, turret, servant, mascot and similar controllable entities.
- Crafting/replication/option features are separated as `choice-or-crafting-backend`.
- Reports are written as `.csv` and `.tsv`; use `compatibility-real-issues-P0-P1-v2.1.tsv` for the first review.


## v2.4

Compatibility report cleanup: stricter species flight detection to remove false P1 movement issues.

### v2.7 Runtime Automation Pass

- Eldritch Cannon remains one feature with multiple activities.
- Protector is now a temporary-HP heal activity on the artificer sheet so it can use the artificer INT modifier.
- The cannon token is treated as the visual map origin; the roll/apply workflow is handled from the character sheet until a real JS automation layer exists.
- Feature activities no longer mark `spellSlot` consumption by default.

