# Feature Linker v0.4

The Feature Linker is the first step that turns Aurora class rules into native Foundry class advancement.

Aurora class XML often contains rules like:

```xml
<grant type="Class Feature" id="ID_WOTC_ERLW_CLASS_FEATURE_ARTIFICER_MAGICAL_TINKERING" level="1" />
```

v0.4 indexes all compiled feature documents by their Aurora ID and then emits Foundry `ItemGrant` advancement entries on the class.

Example output shape:

```json
{
  "type": "ItemGrant",
  "level": 1,
  "title": "Aurora Feature Grants",
  "configuration": {
    "items": [
      { "uuid": "Compendium.aurora-content-pack.features.<feature-id>", "optional": false }
    ]
  }
}
```

Limitations in v0.4:

- Only `Class Feature` grants are linked.
- ASI feature grants are skipped because Foundry has native `AbilityScoreImprovement` advancement.
- Missing feature references are written to `flags.aurora.missingFeatureGrants` and to `compilation-report.json`.
- Subclass features, racial traits, spell-list linking, and starting equipment are not compiled yet.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
