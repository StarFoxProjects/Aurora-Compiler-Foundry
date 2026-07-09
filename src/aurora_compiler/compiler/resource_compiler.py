from __future__ import annotations
from dataclasses import dataclass
from aurora_compiler.models.aurora import AuroraElement, clean_duplicate_name, slugify
from aurora_compiler.foundry import advancement as adv


@dataclass(frozen=True)
class ResourceSpec:
    identifier: str
    label: str
    max: str = ""
    recovery_period: str = ""
    recovery_type: str = "recoverAll"
    scale: dict[int, int | str] | None = None
    dice_scale: dict[int, str] | None = None
    notes: str = ""

    def uses(self) -> dict:
        if not self.max and not self.recovery_period:
            return {"spent": 0, "max": "", "recovery": []}
        recovery = []
        if self.recovery_period:
            recovery.append({"period": self.recovery_period, "type": self.recovery_type})
        return {"spent": 0, "max": self.max, "recovery": recovery}

    def flag(self) -> dict:
        return {
            "identifier": self.identifier,
            "label": self.label,
            "max": self.max,
            "recoveryPeriod": self.recovery_period,
            "recoveryType": self.recovery_type,
            "scale": self.scale or {},
            "diceScale": self.dice_scale or {},
            "notes": self.notes,
        }


FEATURE_RESOURCES: dict[str, ResourceSpec] = {
    "rage": ResourceSpec(
        identifier="rage",
        label="Rage",
        max="@scale.barbarian.rages",
        recovery_period="lr",
        notes="Uses the Barbarian rages scale value generated on the class.",
    ),
    "bardic-inspiration": ResourceSpec(
        identifier="bardic-inspiration",
        label="Bardic Inspiration",
        max="@abilities.cha.mod",
        recovery_period="lr",
        notes="Later compiler passes should switch recovery to sr when Font of Inspiration is granted.",
    ),
    "channel-divinity": ResourceSpec(
        identifier="channel-divinity",
        label="Channel Divinity",
        max="@scale.cleric.channel-divinity-uses",
        recovery_period="sr",
    ),
    "wild-shape": ResourceSpec(
        identifier="wild-shape",
        label="Wild Shape",
        max="2",
        recovery_period="sr",
    ),
    "ki": ResourceSpec(
        identifier="ki",
        label="Ki Points",
        max="@classes.monk.levels",
        recovery_period="sr",
    ),
    "sorcery-points": ResourceSpec(
        identifier="sorcery-points",
        label="Sorcery Points",
        max="@classes.sorcerer.levels",
        recovery_period="lr",
    ),
    "superiority-dice": ResourceSpec(
        identifier="superiority-dice",
        label="Superiority Dice",
        max="@scale.fighter.superiority-dice",
        recovery_period="sr",
    ),
    "blood-maledict": ResourceSpec(
        identifier="blood-maledict",
        label="Blood Maledict",
        max="@scale.blood-hunter.blood-maledict-uses",
        recovery_period="sr",
    ),
    "crimson-rite": ResourceSpec(
        identifier="crimson-rite",
        label="Crimson Rite",
        max="",
        recovery_period="",
        notes="Crimson Rite mainly needs damage/effect compilation, not a use counter.",
    ),
    "infuse-item": ResourceSpec(
        identifier="infuse-item",
        label="Infuse Item",
        max="@scale.artificer.infused-items",
        recovery_period="lr",
    ),
    "psionic-talent": ResourceSpec(
        identifier="psionic-talent",
        label="Psionic Talent",
        max="@prof",
        recovery_period="lr",
    ),
}


CLASS_RESOURCE_SCALES: dict[str, list[ResourceSpec]] = {
    "barbarian": [
        ResourceSpec("rages", "Rages", scale={1: 2, 3: 3, 6: 4, 12: 5, 17: 6, 20: "unlimited"}),
        ResourceSpec("rage-damage", "Rage Damage", scale={1: 2, 9: 3, 16: 4}),
    ],
    "bard": [
        ResourceSpec("bardic-inspiration-die", "Bardic Inspiration Die", dice_scale={1: "d6", 5: "d8", 10: "d10", 15: "d12"}),
    ],
    "cleric": [
        ResourceSpec("channel-divinity-uses", "Channel Divinity Uses", scale={2: 1, 6: 2, 18: 3}),
    ],
    "fighter": [
        ResourceSpec("superiority-dice", "Superiority Dice", scale={3: 4, 7: 5, 15: 6}),
        ResourceSpec("superiority-die", "Superiority Die", dice_scale={3: "d8", 10: "d10", 18: "d12"}),
    ],
    "monk": [
        ResourceSpec("ki-points", "Ki Points", scale={2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13, 14: 14, 15: 15, 16: 16, 17: 17, 18: 18, 19: 19, 20: 20}),
    ],
    "sorcerer": [
        ResourceSpec("sorcery-points", "Sorcery Points", scale={2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8, 9: 9, 10: 10, 11: 11, 12: 12, 13: 13, 14: 14, 15: 15, 16: 16, 17: 17, 18: 18, 19: 19, 20: 20}),
    ],
    "blood-hunter": [
        ResourceSpec("blood-maledict-uses", "Blood Maledict Uses", scale={1: 1, 6: 2, 13: 3, 17: 4}),
        ResourceSpec("hemocraft-die", "Hemocraft Die", dice_scale={1: "d4", 5: "d6", 11: "d8", 17: "d10"}),
    ],
    "artificer": [
        ResourceSpec("infusions-known", "Infusions Known", scale={2: 4, 6: 6, 10: 8, 14: 10, 18: 12}),
        ResourceSpec("infused-items", "Infused Items", scale={2: 2, 6: 3, 10: 4, 14: 5, 18: 6}),
    ],
}


def element_slug(e: AuroraElement) -> str:
    return slugify(clean_duplicate_name(e.name))


def detect_feature_resource(e: AuroraElement) -> ResourceSpec | None:
    slug = element_slug(e)
    if slug in FEATURE_RESOURCES:
        return FEATURE_RESOURCES[slug]
    # Common Aurora variants include source/version suffixes in the raw name. Match by prefix.
    for key, spec in FEATURE_RESOURCES.items():
        if slug.startswith(key):
            return spec
    return None


def class_resource_advancements(seed: str, class_name: str) -> list[dict]:
    docs: list[dict] = []
    for spec in CLASS_RESOURCE_SCALES.get(class_name, []):
        if spec.scale:
            docs.append(adv.scale_value(seed, spec.identifier, spec.label, spec.scale))
        if spec.dice_scale:
            docs.append(adv.scale_value(seed, spec.identifier, spec.label, spec.dice_scale))
    return docs


def class_resource_flags(class_name: str) -> list[dict]:
    return [spec.flag() for spec in CLASS_RESOURCE_SCALES.get(class_name, [])]
