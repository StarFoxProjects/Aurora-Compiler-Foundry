# v2.1 Compatibility Classifier Cleanup

v2.1 tightens the compatibility report classifier before backend work starts.

The important change is that spell-grant features are no longer treated as summons just because a spell name contains words such as `spirit`.

## New classifications

- `spell-grant-backend`: Oath Spells, Domain Spells, Circle Spells, Patron/Expanded spell lists, Innate Spellcasting and similar features.
- `needs-summon-backend`: only true token/actor features such as Eldritch Cannon, Steel Defender, Homunculus Servant, familiars, companions, mascots, turrets and similar controllable entities.
- `choice-or-crafting-backend`: crafting/replication/option features such as Cunning Artisan and Replicate Magic Item.
- `absorbed-helper:*`: Aurora helper atoms that should be absorbed into a parent class/species/subclass.

## Generated files

- `compatibility-summary-v2.1.html`
- `compatibility-summary-v2.1.md`
- `compatibility-next-actions-v2.1.md`
- `compatibility-real-issues-P0-P1-v2.1.tsv`
- `compatibility-real-issues-v2.1.tsv`
- `compatibility-absorbed-helpers-v2.1.tsv`
- `compatibility-map-v2.1.json`

## What to inspect first

Open `compatibility-next-actions-v2.1.md` first, then inspect `compatibility-real-issues-P0-P1-v2.1.tsv`.
