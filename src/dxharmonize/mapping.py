"""Conversion logic between ICD-9-CM and ICD-10-CM.

A GEM entry is not always a simple "A becomes B". The flags describe four
situations, and :func:`convert` reports which one applies:

* ``exact``        – one target, identical meaning.
* ``approximate``  – one or more targets that are close but not identical.
* ``combination``  – the source code needs *several* target codes together
  (e.g. one ICD-9 code that ICD-10 splits into a condition plus a
  manifestation). Grouped by *scenario*; within a scenario, one code is
  chosen from each *choice list*.
* ``no_map``       – the GEM explicitly states there is no equivalent.
* ``not_found``    – the code is not in the GEM at all (for example, an
  ICD-10-CM code created after the final 2018 GEMs).
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field

from .codes import System, compact, format_code


@dataclass
class Target:
    code: str
    description: str | None


@dataclass
class ConversionResult:
    source: str
    source_system: System
    source_description: str | None
    kind: str
    # Non-combination results: a flat list of alternatives.
    targets: list[Target] = field(default_factory=list)
    # Combination results: scenario -> list of choice lists -> alternatives.
    scenarios: dict[int, list[list[Target]]] = field(default_factory=dict)

    @property
    def target_codes(self) -> list[str]:
        if self.kind == "combination":
            return [t.code for lists in self.scenarios.values() for cl in lists for t in cl]
        return [t.code for t in self.targets]

    def structure(self) -> list[list[list[str]]]:
        """The conversion as nested lists: scenarios → parts → alternatives.

        Always three levels, whatever the mapping type, so programs reading
        the output only have to handle one shape:

        * ``[[["I10"]]]``                 one code
        * ``[[["I10", "I16.9"]]]``        alternatives — choose one
        * ``[[["E11.29"], ["N18.9"]]]``   combination — one code from each part
        * ``[]``                          no conversion available
        """
        target_system = self.source_system.other()

        def fmt(t: Target) -> str:
            return format_code(t.code, target_system)

        if self.kind == "combination":
            return [
                [[fmt(t) for t in part] for part in parts]
                for _, parts in sorted(self.scenarios.items())
            ]
        if self.targets:
            return [[[fmt(t) for t in self.targets]]]
        return []

    def to_text(self) -> str:
        """Human-readable form: ``|`` means "or", ``+`` means "and".

        Examples: ``I10 | I16.9``, ``E11.29 + N18.9``, ``(A | B) + C``.
        Separate scenarios (rare) are joined with ``||``.
        """
        scenario_texts = []
        for parts in self.structure():
            if len(parts) == 1:
                scenario_texts.append(" | ".join(parts[0]))
            else:
                scenario_texts.append(" + ".join(
                    p[0] if len(p) == 1 else "(" + " | ".join(p) + ")" for p in parts
                ))
        return " || ".join(scenario_texts)

    def to_json(self) -> str:
        """Machine-readable form, e.g. ``{"kind": "exact", "scenarios": [[["I10"]]]}``."""
        return json.dumps({"kind": self.kind, "scenarios": self.structure()})


def describe(conn: sqlite3.Connection, code: str, system: System) -> str | None:
    row = conn.execute(
        "SELECT description FROM descriptions WHERE system = ? AND code = ?",
        (system.value, compact(code)),
    ).fetchone()
    return row["description"] if row else None


def convert(conn: sqlite3.Connection, code: str, source_system: System) -> ConversionResult:
    src = compact(code)
    target_system = source_system.other()
    rows = conn.execute(
        "SELECT * FROM gems WHERE source_system = ? AND source = ? "
        "ORDER BY scenario, choice_list, target",
        (source_system.value, src),
    ).fetchall()

    result = ConversionResult(
        source=src,
        source_system=source_system,
        source_description=describe(conn, src, source_system),
        kind="not_found",
    )
    if not rows:
        return result
    if all(r["no_map"] for r in rows):
        result.kind = "no_map"
        return result

    def target(r: sqlite3.Row) -> Target:
        return Target(r["target"], describe(conn, r["target"], target_system))

    if any(r["combination"] for r in rows):
        result.kind = "combination"
        for r in rows:
            lists = result.scenarios.setdefault(r["scenario"], [])
            idx = r["choice_list"] - 1
            while len(lists) <= idx:
                lists.append([])
            lists[idx].append(target(r))
        return result

    result.targets = [target(r) for r in rows]
    result.kind = "approximate" if any(r["approximate"] for r in rows) else "exact"
    return result


def search(
    conn: sqlite3.Connection, text: str, system: System | None = None, limit: int | None = 20
) -> list[sqlite3.Row]:
    """Find codes whose description contains every word in ``text``.

    ``limit=None`` returns every match.
    """
    words = [w for w in text.lower().split() if w]
    if not words:
        return []
    clauses = ["LOWER(description) LIKE ?" for _ in words]
    params: list[object] = [f"%{w}%" for w in words]
    if system is not None:
        clauses.append("system = ?")
        params.append(system.value)
    sql = (
        "SELECT system, code, description FROM descriptions WHERE "
        + " AND ".join(clauses)
        + " ORDER BY system, code"
    )
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    return conn.execute(sql, params).fetchall()


def is_negated(description: str, text: str) -> bool:
    """True if the description says the searched condition is *absent*.

    ICD-10-CM writes absence as "without <condition>", e.g. "Hypertensive
    heart disease without heart failure". "with or without <condition>"
    means the condition may be present, so it does not count as negated.
    """
    phrase = " ".join(text.lower().split())
    if not phrase:
        return False
    pattern = re.compile(r"(with or )?without " + re.escape(phrase))
    return any(m.group(1) is None for m in pattern.finditer(description.lower()))


def split_negated(
    rows: list[sqlite3.Row], text: str
) -> tuple[list[sqlite3.Row], list[sqlite3.Row]]:
    """Separate search results into (kept, hidden-because-negated)."""
    kept = [r for r in rows if not is_negated(r["description"], text)]
    hidden = [r for r in rows if is_negated(r["description"], text)]
    return kept, hidden
