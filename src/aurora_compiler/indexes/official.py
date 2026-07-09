from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass, field
from aurora_compiler.models.aurora import slugify

@dataclass
class OfficialIndex:
    by_type_name: set[tuple[str, str]] = field(default_factory=set)

    def has(self, item_type: str, name: str) -> bool:
        return (item_type, slugify(name)) in self.by_type_name


def load_official_examples(path: str | Path | None) -> OfficialIndex:
    idx = OfficialIndex()
    if not path:
        return idx
    p = Path(path)
    if not p.exists():
        return idx
    files = list(p.rglob("*.json")) + list(p.rglob("*.db"))
    for file in files:
        try:
            if file.suffix == ".db":
                for line in file.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if not line.strip():
                        continue
                    doc = json.loads(line)
                    if doc.get("type") and doc.get("name"):
                        idx.by_type_name.add((doc["type"], slugify(doc["name"])))
            else:
                doc = json.loads(file.read_text(encoding="utf-8"))
                if doc.get("type") and doc.get("name"):
                    idx.by_type_name.add((doc["type"], slugify(doc["name"])))
        except Exception as exc:
            print(f"[WARN] Could not index official example {file}: {exc}")
    return idx
