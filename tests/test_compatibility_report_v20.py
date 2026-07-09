from pathlib import Path
import csv

from aurora_compiler.reporting.compatibility import _write_csv, _write_tsv


def test_v20_csv_quotes_comma_fields(tmp_path: Path):
    rows = [{"backend": "Compile actor/token, do not keep plain text", "name": "Oath Spells", "problem": "Feature has rules"}]
    fields = ["backend", "name", "problem"]
    out = tmp_path / "issues.csv"
    _write_csv(out, rows, fields)
    raw = out.read_text(encoding="utf-8")
    assert '"Compile actor/token, do not keep plain text"' in raw
    parsed = list(csv.DictReader(out.open(encoding="utf-8")))
    assert parsed[0]["backend"] == "Compile actor/token, do not keep plain text"


def test_v20_tsv_keeps_columns(tmp_path: Path):
    rows = [{"backend": "Compile actor/token, do not keep plain text", "name": "Oath Spells", "problem": "Feature has rules"}]
    fields = ["backend", "name", "problem"]
    out = tmp_path / "issues.tsv"
    _write_tsv(out, rows, fields)
    parsed = list(csv.DictReader(out.open(encoding="utf-8"), delimiter="\t"))
    assert parsed[0]["backend"] == "Compile actor/token, do not keep plain text"
    assert parsed[0]["name"] == "Oath Spells"
