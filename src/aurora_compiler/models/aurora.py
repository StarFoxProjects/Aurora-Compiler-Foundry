from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import re

@dataclass
class AuroraElement:
    id: str
    name: str
    type: str
    source: str
    description_html: str = ""
    rules: list[dict[str, Any]] = field(default_factory=list)
    setters: list[dict[str, Any]] = field(default_factory=list)
    supports: list[str] = field(default_factory=list)
    file: str = ""
    attrs: dict[str, str] = field(default_factory=dict)

    def setter(self, name: str, default: str = "") -> str:
        needle = name.lower()
        for s in self.setters:
            attrs = s.get("attrs", {}) or {}
            if attrs.get("name", "").lower() == needle:
                return str(s.get("value") or attrs.get("value") or s.get("text") or default).strip()
        return default

    def setter_bool(self, name: str, default: bool = False) -> bool:
        v = self.setter(name, "")
        if not v:
            return default
        return v.strip().lower() in {"true", "yes", "1"}

    @property
    def source_code(self) -> str:
        abbreviation = self.setter("abbreviation")
        if abbreviation:
            return abbreviation.strip()

        s = normalize_apostrophe(self.source or "").lower()
        mapping = [
            ("player's handbook", "PHB"),
            ("players handbook", "PHB"),
            ("dungeon master's guide", "DMG"),
            ("monster manual", "MM"),
            ("xanathar", "XGTE"),
            ("tasha", "TCE"),
            ("eberron: rising from the last war", "ERLW"),
            ("wayfinder", "WGE"),
            ("strixhaven", "SCOC"),
            ("fizban", "FTD"),
            ("mordenkainen", "MPMM"),
            ("volo", "VGTM"),
            ("sword coast", "SCAG"),
            ("critical role", "CR"),
            ("blood hunter", "BH"),
            ("unearthed arcana", "UA"),
        ]
        for key, code in mapping:
            if key in s:
                return code

        # Aurora IDs frequently include compact source segments.
        # ID_WOTC_ERLW_CLASS_ARTIFICER -> ERLW
        m = re.match(r"ID_[A-Z0-9]+_([A-Z0-9]+)_", self.id or "")
        if m:
            code = m.group(1)
            if code not in {"CLASS", "SPELL", "RACE", "FEAT", "ITEM"}:
                return code
        return clean_source_fallback(self.source)

    def display_name(self, include_source: bool = True, long_source: bool = False) -> str:
        base = clean_duplicate_name(self.name)
        if not include_source:
            return base
        src = self.source if long_source else self.source_code
        src = clean_source_fallback(src)
        return f"{base} ({src})" if src else base

    @property
    def identifier(self) -> str:
        return slugify(clean_duplicate_name(self.name))


def normalize_apostrophe(s: str) -> str:
    return s.replace("’", "'").replace("‘", "'")


def clean_source_fallback(source: str) -> str:
    source = " ".join((source or "").split())
    if not source:
        return ""
    return source[:32]


def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower())
    return s.strip("-") or "item"


def clean_duplicate_name(name: str) -> str:
    """Fix simple Aurora/display names like 'Acid Gate Acid Gate'."""
    n = " ".join((name or "").replace("\n", " ").split())
    if not n:
        return n

    # exact half repeat: Acid Gate Acid Gate -> Acid Gate
    parts = n.split()
    if len(parts) % 2 == 0:
        half = len(parts) // 2
        if [p.lower() for p in parts[:half]] == [p.lower() for p in parts[half:]]:
            return " ".join(parts[:half])

    # repeated title separated by punctuation: Fireball - Fireball
    m = re.match(r"^(.+?)\s*[-:|/]\s*\1$", n, re.I)
    if m:
        return m.group(1).strip()
    return n
