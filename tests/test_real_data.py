"""Integration tests against the REAL CMS files.

Two layers:

1. ``tests/fixtures/real/``: a stratified sample of the official files, made by
   ``scripts/make_real_sample.py`` (lines copied byte for byte). Always runs,
   including on GitHub.
2. ``data/raw/``: the complete official files. Only runs where they have been
   downloaded (see README → Getting the data); skipped elsewhere.

Both layers check that, for every source code, dxharmonize returns exactly the
targets written in the official GEM file, with the matching mapping type.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import pytest

from dxharmonize import db
from dxharmonize.cli import _find, main
from dxharmonize.codes import System, compact
from dxharmonize.mapping import convert

ROOT = Path(__file__).resolve().parents[1]
REAL_SAMPLE = Path(__file__).parent / "fixtures" / "real"
FULL_DATA = ROOT / "data" / "raw"


def official_mappings(gem_file: Path) -> dict[str, tuple[set[str], str]]:
    """Read a GEM file directly (without dxharmonize) -> {source: (targets, kind)}."""
    lines_by_code = defaultdict(list)
    for line in gem_file.read_text(encoding="latin-1").splitlines():
        if line.strip():
            source, target, flags = line.split()
            lines_by_code[compact(source)].append((compact(target), flags))

    result = {}
    for source, rows in lines_by_code.items():
        targets = {t for t, f in rows if f[1] != "1"}
        if all(f[1] == "1" for _, f in rows):
            kind = "no_map"
        elif any(f[2] == "1" for _, f in rows):
            kind = "combination"
        elif any(f[0] == "1" for _, f in rows):
            kind = "approximate"
        else:
            kind = "exact"
        result[source] = (targets, kind)
    return result


def build(raw_dir: Path, db_path: Path):
    assert main(["--db", str(db_path), "build", "--from-dir", str(raw_dir)]) == 0
    return db.connect(db_path)


def check_every_code(conn, raw_dir: Path) -> int:
    """Compare dxharmonize with the official file for every source code."""
    checked = 0
    for key, system in [("icd9_gem", System.ICD9), ("icd10_gem", System.ICD10)]:
        for source, (targets, kind) in official_mappings(_find(raw_dir, key)).items():
            res = convert(conn, source, system)
            assert (set(res.target_codes), res.kind) == (targets, kind), source
            checked += 1
    return checked


# --- layer 1: stratified sample of the real files (always runs) -----------


@pytest.fixture(scope="module")
def real_conn(tmp_path_factory):
    conn = build(REAL_SAMPLE, tmp_path_factory.mktemp("real") / "real.db")
    yield conn
    conn.close()


def test_sample_matches_official_files(real_conn):
    assert check_every_code(real_conn, REAL_SAMPLE) >= 40


def test_sample_covers_every_mapping_type():
    for key in ("icd9_gem", "icd10_gem"):
        kinds = {kind for _, kind in official_mappings(_find(REAL_SAMPLE, key)).values()}
        assert {"exact", "approximate", "combination", "no_map"} <= kinds, key


# Anchors: conversions checked by hand against the official files.


def test_anchor_hypertension_has_two_alternatives(real_conn):
    res = convert(real_conn, "401.9", System.ICD9)
    assert res.source_description == "Unspecified essential hypertension"
    assert res.kind == "approximate"
    assert res.to_text() == "I10 | I16.9"


def test_anchor_heart_failure(real_conn):
    res = convert(real_conn, "428.0", System.ICD9)
    assert res.source_description == "Congestive heart failure, unspecified"
    assert res.to_text() == "I50.814 | I50.9"


def test_anchor_type_2_diabetes(real_conn):
    res = convert(real_conn, "250.00", System.ICD9)
    assert res.kind == "approximate"
    assert res.to_text() == "E11.9"


# --- layer 2: the complete official files (only where downloaded) --------

full_data_available = FULL_DATA.exists() and _find(FULL_DATA, "icd9_gem") is not None


@pytest.mark.skipif(not full_data_available, reason="full CMS files not in data/raw")
def test_full_files_every_code(tmp_path):
    conn = build(FULL_DATA, tmp_path / "full.db")
    assert check_every_code(conn, FULL_DATA) > 80_000
