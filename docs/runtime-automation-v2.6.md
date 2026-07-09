# v2.7 Runtime Automation Pass

The compatibility map is not only about whether an item exists in Foundry.  Some
content needs runtime behaviour: target selection, applying damage or temporary
hit points to tokens, using the parent actor's ability modifier, and creating or
controlling summoned tokens.

## Eldritch Cannon

The Artillerist `Eldritch Cannon` feature remains a single feature on the
character sheet.  It now contains these activities:

- `Create Eldritch Cannon` – places the selected visual cannon token.
- `Flamethrower` – save/damage activity using the artificer's save DC.
- `Force Ballista` – spell attack/damage activity using the artificer's attack
  data.
- `Protector` – healing activity that rolls temporary HP using the artificer's
  Intelligence modifier.

The summoned cannon actor is still useful as a map token/visual origin.  The
actual rolls are kept on the artificer's sheet because a vanilla Foundry summon
actor does not reliably know its owner's Intelligence modifier or apply results
to chosen allies without a runtime automation layer.

## Protector workflow

1. Put the Protector cannon token on the map.
2. Manually target the cannon and the chosen creatures within 10 feet.
3. Use the `Protector` activity from the artificer's `Eldritch Cannon` feature.
4. Apply the temporary HP from the chat card to the targeted actors.

This avoids the stale green measured-template circle and avoids treating
Protector as a d20 roll.

## Compiler implication

Future work should track runtime capability separately from static document
conversion:

- Static conversion: item exists, description exists, advancement exists.
- Native activity: damage/save/heal/attack/template exists.
- Token workflow: summon/token exists.
- Runtime automation: results apply correctly to selected tokens.
- Needs JS/Midi-QOL/DAE: conditional triggers, persistent auras, automatic
  target filtering, owner-to-summon ability sharing.
