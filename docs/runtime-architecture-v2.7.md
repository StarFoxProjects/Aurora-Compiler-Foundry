# Aurora Runtime Architecture v2.7

v2.7 changes the project direction from a pure XML → compendium converter to an
Aurora → Foundry compiler plus runtime automation layer.

The generated module now contains:

- `scripts/runtime.js`
- `module.json` with `esmodules: ["scripts/runtime.js"]`
- activity-level `flags.aurora.runtime` metadata for effects that cannot be
  fully represented by static Foundry data alone.

## Runtime action shape

Activities can now carry metadata like:

```json
{
  "flags": {
    "aurora": {
      "runtime": {
        "action": "targeted-temphp",
        "label": "Eldritch Cannon: Protector",
        "formula": "1d8 + @abilities.int.mod",
        "origin": "eldritch-cannon-token",
        "target": "chosen-creatures-within-radius",
        "radius": 10,
        "units": "ft",
        "backend": "aurora-runtime-js-v2.7"
      }
    }
  }
}
```

## Implemented runtime actions

### `targeted-temphp`

Rolls a formula using the source actor roll data, then applies the result as
non-stacking temporary HP to targeted/selected tokens.

This is the first step toward automating effects like Artillerist Protector:

- source actor: the Artificer, so `@abilities.int.mod` is correct
- affected actors: tokens the user targets/selects
- result: `system.attributes.hp.temp` is set to the higher of current temp HP or
  rolled temp HP

### `targeted-healing`

Rolls a formula and restores HP to targeted/selected tokens, capped at max HP.

## Current limitations

This runtime is intentionally conservative. It does not yet fully automate:

- checking radius from a turret token
- opening a token-choice dialog filtered by distance
- persistent aura effects
- triggered reactions
- attack/damage application without Midi-QOL or a custom damage workflow
- active effects from passive bonuses
- summon ownership/linking back to the summoner actor

Those are future runtime backends, not static compiler fixes.

## Manual v2.7 workflow for Protector

1. Use `Create Eldritch Cannon` to place the visual Protector token.
2. Target/select the creatures that should receive temp HP.
3. Use the Protector activity on the Artificer's `Eldritch Cannon` feature.
4. The runtime rolls `1d8 + @abilities.int.mod` and applies temporary HP to the
   targeted/selected tokens.

## Design goal

Every Aurora rule should eventually fall into one of these runtime categories:

- static Foundry data only
- Foundry activity only
- Active Effect
- Aurora Runtime JS action
- optional Midi-QOL/DAE integration
- manual-only note when automation would be unsafe
