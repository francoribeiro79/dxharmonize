"""Parsers for the official CMS text files.

Two kinds of file are supported:

* **GEMs** (General Equivalence Mappings), e.g. ``2018_I9gem.txt`` and
  ``2018_I10gem.txt``. One mapping per line::

      42800   I509    10000

  source code, target code, and five flag digits.

* **Code descriptions**, e.g. ``icd10cm_codes_2026.txt`` or
  ``CMS32_DESC_LONG_DX.txt``. One code per line, followed by its title::

      I509    Heart failure, unspecified
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from .codes import compact

NO_MAP_TARGETS = {"NODX", "NOPCS"}


@dataclass(frozen=True)
class GemFlags:
    """The five GEM flags, in the order CMS publishes them."""

    approximate: bool
    no_map: bool
    combination: bool
    scenario: int
    choice_list: int

    @classmethod
    def parse(cls, raw: str) -> GemFlags:
        if len(raw) != 5 or not raw.isdigit():
            raise ValueError(f"GEM flags must be 5 digits, got {raw!r}")
        return cls(
            approximate=raw[0] == "1",
            no_map=raw[1] == "1",
            combination=raw[2] == "1",
            scenario=int(raw[3]),
            choice_list=int(raw[4]),
        )


@dataclass(frozen=True)
class GemRow:
    source: str
    target: str | None  # None when the GEM says there is no equivalent
    flags: GemFlags


def _read_lines(path: Path) -> Iterator[str]:
    """Yield non-empty lines; CMS files are mostly ASCII but some are Latin-1."""
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    for line in text.splitlines():
        if line.strip():
            yield line


def parse_gems(path: Path) -> Iterator[GemRow]:
    """Parse a GEM file into :class:`GemRow` objects."""
    for lineno, line in enumerate(_read_lines(path), start=1):
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"{path.name}:{lineno}: expected 3 columns, got {len(parts)}")
        source, target, flags = parts
        target_c = compact(target)
        yield GemRow(
            source=compact(source),
            target=None if target_c in NO_MAP_TARGETS else target_c,
            flags=GemFlags.parse(flags),
        )


def parse_descriptions(path: Path) -> Iterator[tuple[str, str]]:
    """Parse a code-description file into ``(code, description)`` pairs."""
    for lineno, line in enumerate(_read_lines(path), start=1):
        parts = line.strip().split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"{path.name}:{lineno}: expected a code and a description")
        code, desc = parts
        yield compact(code), desc.strip()
