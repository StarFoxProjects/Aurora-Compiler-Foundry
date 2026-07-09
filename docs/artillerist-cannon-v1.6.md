# v1.6 Eldritch Cannon model fix

This version models Artillerist Eldritch Cannon closer to the rules:

- The artificer character receives only one feature: **Eldritch Cannon**.
- That feature has one activity: **Create Eldritch Cannon**.
- The summon activity offers three summon profiles:
  - Eldritch Cannon - Flamethrower
  - Eldritch Cannon - Force Ballista
  - Eldritch Cannon - Protector
- Flamethrower / Force Ballista / Protector are no longer compiled as standalone character features.
- Each summoned cannon actor carries its own mode action.
- Protector no longer creates a persistent green measured-template circle. It is a temporary-HP healing roll: `1d8 + @abilities.int.mod` with type `temphp`.

Rules note: Protector is not a continuous aura. It is activated as a bonus action and grants temporary HP to the cannon and creatures of your choice within 10 feet at that moment.

## v2.0 Report cleanup

Adds spreadsheet-safe quoted CSV files, TSV files for easier LibreOffice import, and a small P0/P1 next-actions report.
