"""Convert a whole CSV column of codes and report problem cases."""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .codes import System, compact, is_valid
from .mapping import convert


@dataclass
class BatchReport:
    total: int = 0
    kinds: Counter = field(default_factory=Counter)
    unmapped: Counter = field(default_factory=Counter)  # code -> occurrences
    invalid: Counter = field(default_factory=Counter)  # malformed value -> occurrences
    encoding: str = "utf-8"


# Encodings tried in order. UTF-8 first (what most tools write today), then
# Windows-1252 (Excel on Windows), then Latin-1, which can decode any bytes.
ENCODINGS = ("utf-8-sig", "cp1252", "latin-1")


def read_text(path: Path) -> tuple[str, str]:
    """Return the file's text and the encoding that worked."""
    data = path.read_bytes()
    for enc in ENCODINGS:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    raise AssertionError("unreachable: latin-1 decodes any bytes")


def convert_csv(
    conn: sqlite3.Connection,
    input_path: Path,
    output_path: Path,
    column: str,
    source_system: System,
) -> BatchReport:
    """Add ``<column>_converted``, ``<column>_mapping`` and ``<column>_mapping_detail``.

    ``_converted`` is for people (``|`` = or, ``+`` = and), ``_mapping_detail``
    is JSON for programs.

    Each distinct code is converted once and cached, so large files with
    repeated codes stay fast. The input may be UTF-8 or Windows-1252 (Excel);
    the output is always UTF-8. Raises ``ValueError`` for an empty file and
    ``KeyError`` for a missing column.
    """
    report = BatchReport()
    cache: dict[str, tuple[str, str, str]] = {}

    text, report.encoding = read_text(input_path)
    if not text.strip():
        raise ValueError(f"{input_path.name} is empty")

    with io.StringIO(text, newline="") as fin:
        reader = csv.DictReader(fin)
        if reader.fieldnames is None or column not in reader.fieldnames:
            raise KeyError(f"column {column!r} not found in {input_path.name}")
        out_fields = [
            *reader.fieldnames,
            f"{column}_converted",
            f"{column}_mapping",
            f"{column}_mapping_detail",
        ]

        with output_path.open("w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=out_fields)
            writer.writeheader()
            for row in reader:
                raw = (row.get(column) or "").strip()
                report.total += 1
                if not raw:
                    converted, kind, detail = "", "empty", ""
                elif not is_valid(raw, source_system):
                    # malformed value (typo, truncated code...): not a code at all
                    converted, kind = "", "invalid"
                    detail = json.dumps({"kind": "invalid", "scenarios": []})
                    report.invalid[raw] += 1
                else:
                    key = compact(raw)
                    if key not in cache:
                        res = convert(conn, key, source_system)
                        cache[key] = (res.to_text(), res.kind, res.to_json())
                    converted, kind, detail = cache[key]
                    if kind in ("no_map", "not_found"):
                        report.unmapped[key] += 1
                report.kinds[kind] += 1
                row[f"{column}_converted"] = converted
                row[f"{column}_mapping"] = kind
                row[f"{column}_mapping_detail"] = detail
                writer.writerow(row)
    return report
