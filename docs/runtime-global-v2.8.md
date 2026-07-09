# v2.8 Global Runtime Mapper

v2.8 changes the runtime goal from single-feature fixes to a global mapping pass.

The compiler now marks every generated activity it can safely recognize with `flags.aurora.runtime`, not only Eldritch Cannon. The generated module includes `scripts/runtime.js`, which exposes runtime actions for:

- `targeted-damage`
- `targeted-save-damage`
- `targeted-healing`
- `targeted-temphp`

The build also writes:

- `runtime-summary-v2.8.md`
- `runtime-coverage-v2.8.tsv`

These files show which generated activities are currently mapped to runtime automation.

## Important limitation

This is not a claim that every Aurora rule is fully automated. v2.8 creates the global runtime layer and maps all parseable damage/healing/temp-HP activity shapes. Rules that depend on timing triggers, auras, transformations, conditional modifiers, save-half/save-none handling, automatic radius target selection, equipment bonuses, or complex summon behavior still need dedicated runtime backends.

## Test result with Aurora Paid.zip

The test build produced 1,346 runtime-mapped activities:

- `targeted-damage`: 742
- `targeted-save-damage`: 318
- `targeted-temphp`: 168
- `targeted-healing`: 118

By pack:

- features: 847
- spells: 497
- infusions: 2
