# Resource Compiler v0.6

The Resource Compiler is the first pass that turns common Aurora class resources into native Foundry-friendly data.

It currently handles two layers:

1. **Class scale values** inside `system.advancement`.
2. **Feature use counters** inside `system.uses`.

The compiler still does not fully create Actor resource bars because those live on the actor, not on the class item. Instead it exposes scale values and feature uses that Foundry D&D5e can evaluate when the feature/class is added to a character.

## Supported class scale values

| Class | Generated scales |
|---|---|
| Barbarian | Rages, Rage Damage |
| Bard | Bardic Inspiration Die |
| Cleric | Channel Divinity Uses |
| Fighter | Superiority Dice, Superiority Die |
| Monk | Ki Points |
| Sorcerer | Sorcery Points |
| Blood Hunter | Blood Maledict Uses, Hemocraft Die |
| Artificer | Infusions Known, Infused Items |

## Supported feature resources

| Feature | Uses |
|---|---|
| Rage | `@scale.barbarian.rages`, long rest |
| Bardic Inspiration | `@abilities.cha.mod`, long rest |
| Channel Divinity | `@scale.cleric.channel-divinity-uses`, short rest |
| Wild Shape | `2`, short rest |
| Ki | `@classes.monk.levels`, short rest |
| Sorcery Points | `@classes.sorcerer.levels`, long rest |
| Superiority Dice | `@scale.fighter.superiority-dice`, short rest |
| Blood Maledict | `@scale.blood-hunter.blood-maledict-uses`, short rest |
| Infuse Item | `@scale.artificer.infused-items`, long rest |

## Flags

Compiled classes include:

```json
flags.aurora.resources
```

Compiled features include:

```json
flags.aurora.resource
```

These flags are intentionally redundant. They help future passes create Actor resources, Midi-QOL/DAE effects, and validation reports without reparsing Aurora XML.

## Limitations

- Some resources depend on subclass features or later class features. Example: Bardic Inspiration should recover on a short rest only after Font of Inspiration.
- Dice resources like Superiority Dice still need activity/effect integration.
- Actor resource bars are not generated yet.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
