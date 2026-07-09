# Artificer compiler v1.1

This pass adds native-ish Foundry support for the Artificer features that are most visible during character creation and play.

## Artificer Infusions

The class compiler now creates an `ItemChoice` advancement called **Artificer Infusions** for Artificer classes.

The picker uses compiler-generated infusion features from the features compendium.

Modern Artificer classes use the `Artificer Infusion` support pool. UA Artificer classes use the `UA Artificer Infusion` support pool so the two versions are not mixed together.

Choice levels:

- Level 2: choose 4
- Level 6: choose 2 more
- Level 10: choose 2 more
- Level 14: choose 2 more
- Level 18: choose 2 more

This represents **Infusions Known**. The separate **Infused Items** scale remains a resource/scale value and represents how many items can be active.

## Nested feature grants

Some Aurora features grant other features. Example: **Eldritch Cannon** grants **Flamethrower**, **Force Ballista**, and **Protector**.

v1.1 builds a one-level nested grant index and expands class/subclass grants so those child features can appear on the actor directly when the parent feature is granted through advancement.

The parent feature also receives an internal `ItemGrant` advancement for traceability.

## Artillerist cannon activities

The three cannon options receive more specific activities:

- **Flamethrower**: bonus-action save activity, Dexterity save, 15 ft cone, 2d8 fire damage, half on save.
- **Force Ballista**: bonus-action ranged spell attack, 120 ft, 2d8 force damage.
- **Protector**: bonus-action healing activity using temporary HP, 10 ft radius, `1d8 + @abilities.int.mod`.

These are still best-effort conversions. They create usable rolls/buttons in Foundry, but advanced automation such as summoning an actual cannon actor/token is outside this pass.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
