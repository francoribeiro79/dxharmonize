"""Normalisation and formatting of ICD-9-CM and ICD-10-CM diagnosis codes.

The official CMS files store codes without the decimal point (``42800``,
``I509``). Users usually type them with a point (``428.0``, ``I50.9``).
Internally icdmap always works with the *compact* form and only adds the
point when showing codes to a person.
"""

from __future__ import annotations

import re
from enum import Enum


class System(str, Enum):
    """Supported coding systems."""

    ICD9 = "icd9"
    ICD10 = "icd10"

    def other(self) -> System:
        return System.ICD10 if self is System.ICD9 else System.ICD9


_ICD9_RE = re.compile(r"^(\d{3,5}|V\d{2,4}|E\d{3,4})$")
_ICD10_RE = re.compile(r"^[A-Z]\d[0-9A-Z]{1,5}$")


def compact(code: str) -> str:
    """Return ``code`` in upper case with dots and whitespace removed."""
    return code.strip().upper().replace(".", "")


def candidate_systems(code: str) -> list[System]:
    """Return every system ``code`` could belong to, most likely first.

    ICD-9 V and E codes start with a letter, just like ICD-10 codes, so some
    codes are genuinely ambiguous (``V12.51`` exists in both). When the user
    typed a decimal point its position settles E-codes: ICD-9 E-codes have
    four characters before the point (``E888.9``), ICD-10 codes have three.
    """
    raw = code.strip().upper()
    c = compact(raw)
    systems = []
    if _ICD10_RE.match(c):
        systems.append(System.ICD10)
    if _ICD9_RE.match(c):
        systems.append(System.ICD9)
    if len(systems) == 2 and "." in raw and raw.index(".") == 4:
        systems.reverse()  # "E888.9": only an ICD-9 E-code puts the point there
        systems = systems[:1]
    return systems


def detect_system(code: str) -> System | None:
    """Most likely system for ``code``, or ``None`` if it looks invalid.

    For ambiguous codes ICD-10 is preferred; :func:`candidate_systems` gives
    all options so callers can check which one actually exists.
    """
    systems = candidate_systems(code)
    return systems[0] if systems else None


def format_code(code: str, system: System) -> str:
    """Insert the decimal point the way clinicians write the code."""
    c = compact(code)
    if system is System.ICD9:
        split = 4 if c.startswith("E") else 3
    else:
        split = 3
    if len(c) <= split:
        return c
    return f"{c[:split]}.{c[split:]}"
