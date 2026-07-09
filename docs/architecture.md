# Architecture

Aurora XML is treated as source code. Foundry D&D5e Item documents are the compiled target.

```text
Aurora XML ZIP
    ↓
Parser
    ↓
Intermediate AuroraElement objects
    ↓
Linker / duplicate resolver / source normalizer
    ↓
Foundry compiler modules
    ↓
Foundry add-on module with compendium packs
```

## Stages

### 1. Parser

Reads Aurora XML without knowing Foundry. It preserves:

- element id
- name
- type
- source
- description
- setters
- rules
- supports
- original file path

### 2. Semantic compiler

Turns Aurora elements into Foundry documents.

Current compiler supports basic native spell fields. Class/species/feature compilers are still incomplete and currently fall back to generic items.

### 3. Module writer

Writes:

```text
module.json
packs/*.db
compilation-report.json
```

The `.db` pack format is line-delimited JSON, which Foundry can migrate to its current internal storage format on load.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
