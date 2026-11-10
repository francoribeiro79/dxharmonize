"""Convert a whole CSV column of codes and report problem cases."""

from __future__ import annotations

import csv
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .codes import System, compact
from .mapping import convert


@dataclass
class BatchReport:
    total: int = 0
    kinds: Counter = field(default_factory=Counter)
    unmapped: Counter = field(default_factory=Counter)  # code -> occurrences


def convert_csv(
    conn: sqlite3.Connection,
    input_path: Path,
    output_path: Path,
    column: str,
    source_system: System,
) -> BatchReport:
    """Add ``<column>_converted`` and ``<column>_mapping`` columns to a CSV.

    Each distinct code is converted once and cached, so large files with
    repeated codes stay fast.
    """
    report = BatchReport()
    cache: dict[str, tuple[str, str]] = {}

    with input_path.open(newline="", encoding="utf-8-sig") as fin:
        reader = csv.DictReader(fin)
        if reader.fieldnames is None or column not in reader.fieldnames:
            raise KeyError(f"column {column!r} not found in {input_path.name}")
        out_fields = [*reader.fieldnames, f"{column}_converted", f"{column}_mapping"]

        with output_path.open("w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=out_fields)
            writer.writeheader()
            for row in reader:
                raw = (row.get(column) or "").strip()
                report.total += 1
                if not raw:
                    converted, kind = "", "empty"
                else:
                    key = compact(raw)
                    if key not in cache:
                        res = convert(conn, key, source_system)
                        cache[key] = (";".join(dict.fromkeys(res.target_codes)), res.kind)
                    converted, kind = cache[key]
                    if kind in ("no_map", "not_found"):
                        report.unmapped[key] += 1
                report.kinds[kind] += 1
                row[f"{column}_converted"] = converted
                row[f"{column}_mapping"] = kind
                writer.writerow(row)
    return report
