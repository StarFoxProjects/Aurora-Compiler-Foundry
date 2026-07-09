# v2.4 Compatibility Report Cleanup

v2.4 is a reporting/triage cleanup release after reading the v2.3 report.

## What changed

- Fixed the species flight false-positive flood from v2.3.
- The report no longer flags every species as P1 just because the combined text contains the substring `fly`.
- Species missing fly speed are now flagged only when the text/rules explicitly grant a flying/fly speed.
- Compatibility report outputs now use v2.4 filenames.

## Why

The v2.3 report showed 251 P1 species issues like “Warforged has flying text but no fly speed”. These were report noise, not real compiler failures. Removing this false-positive group makes the next real backend target clearer: feature activities, spell grants, spell activities, and true summons.
