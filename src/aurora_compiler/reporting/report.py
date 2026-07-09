from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
import json
from aurora_compiler.models.aurora import AuroraElement, slugify


def build_report(elements: list[AuroraElement], compiled_counts: dict[str, int] | None = None, skipped: list[dict] | None = None) -> dict:
    by_type = Counter(e.type or "Unknown" for e in elements)
    by_source = Counter(e.source_code or "Unknown" for e in elements)
    duplicate_names = defaultdict(list)
    for e in elements:
        duplicate_names[(e.type, slugify(e.name))].append({"name": e.name, "source": e.source, "id": e.id, "file": e.file})
    dupes = {f"{t}:{n}": vals for (t, n), vals in duplicate_names.items() if len(vals) > 1}
    return {
        "totalElements": len(elements),
        "byType": dict(by_type.most_common()),
        "bySource": dict(by_source.most_common()),
        "duplicateTypeNames": dupes,
        "compiledCounts": compiled_counts or {},
        "skipped": skipped or [],
    }


def write_report(report: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
