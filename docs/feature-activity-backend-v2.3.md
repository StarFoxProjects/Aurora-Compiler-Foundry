# v2.3 Feature Activity Backend

v2.3 starts converting common class/species/subclass features into more native Foundry activities instead of leaving them as plain utility text.

Implemented patterns:

- natural weapon / unarmed strike features such as Bite, Claws, Horns, Hooves and Ram become attack activities when the text supports it;
- damage formulas like `1d6 + your Strength modifier` are normalized to Foundry formulas such as `1d6 + @abilities.str.mod`;
- temporary hit point features become heal activities with `temphp`;
- save + damage features become save activities instead of generic utility activities.

This is still heuristic. Complex reactions, conditional bonuses, auras and form-state toggles remain compatibility-report items for later Active Effect/JS backends.
