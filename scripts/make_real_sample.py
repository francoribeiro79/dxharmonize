"""Build a small, stratified sample of the REAL CMS files for the test suite.

The full CMS files are too large to keep in the repository, so the tests use
a sample of their lines, copied byte for byte (nothing is edited or invented).

How the sample is chosen, for each GEM file (ICD-9 -> ICD-10 and back):

* every source code is put in one of five categories: exact, approximate,
  alternatives (|), combination (+), no equivalent;
* PER_CATEGORY codes are drawn at random from each category, so rare but
  difficult cases are as well represented as common ones (not proportional);
* the draw uses a fixed SEED, so anyone running this script on the same files
  gets the same sample;
* a few hand-checked "anchor" codes are always included.

All GEM lines of each chosen code are kept, plus the descriptions of every
code involved (sources and targets).

Usage:
    python scripts/make_real_sample.py data/raw tests/fixtures/real
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path

from dxharmonize.cli import _find
from dxharmonize.codes import compact

SEED = 2026
PER_CATEGORY = 5
# Codes checked by hand against the official files (see tests/test_real_data.py)
ANCHORS = {"icd9_gem": ["4019", "4280", "25000"], "icd10_gem": []}


def read_lines(path: Path) -> list[bytes]:
    """Lines as raw bytes, so they are copied exactly (some files are Latin-1)."""
    return [line for line in path.read_bytes().splitlines(keepends=True) if line.strip()]


def first_token(line: bytes) -> str:
    return compact(line.split()[0].decode("latin-1"))


def category(lines: list[bytes]) -> str:
    """Same categories as the mapping types reported by dxharmonize."""
    flags = [line.split()[2].decode() for line in lines]
    if all(f[1] == "1" for f in flags):
        return "no_map"
    if any(f[2] == "1" for f in flags):
        return "combination"
    if len(lines) > 1:
        return "alternatives"
    return "approximate" if flags[0][0] == "1" else "exact"


def sample_gem(path: Path, anchors: list[str], rng: random.Random) -> dict[str, list[bytes]]:
    by_code: dict[str, list[bytes]] = defaultdict(list)
    for line in read_lines(path):
        by_code[first_token(line)].append(line)

    by_category: dict[str, list[str]] = defaultdict(list)
    for code in sorted(by_code):  # sorted: the draw must not depend on file order
        by_category[category(by_code[code])].append(code)

    chosen = [code for code in anchors if code in by_code]
    for cat in sorted(by_category):
        pool = [c for c in by_category[cat] if c not in chosen]
        picked = rng.sample(pool, min(PER_CATEGORY, len(pool)))
        chosen += picked
        print(f"  {path.name}: {cat:<13} {len(by_category[cat]):>6,} codes -> {len(picked)} sampled")
    return {code: by_code[code] for code in chosen}


def main(raw_dir: Path, out_dir: Path) -> None:
    rng = random.Random(SEED)
    out_dir.mkdir(parents=True, exist_ok=True)

    files = {key: _find(raw_dir, key) for key in ("icd9_gem", "icd10_gem", "icd9_desc", "icd10_desc")}
    missing = [key for key, path in files.items() if path is None]
    if missing:
        sys.exit(f"error: could not find {', '.join(missing)} in {raw_dir}")

    needed = {"icd9": set(), "icd10": set()}  # codes whose description we keep
    for key, source, target in [("icd9_gem", "icd9", "icd10"), ("icd10_gem", "icd10", "icd9")]:
        sample = sample_gem(files[key], ANCHORS[key], rng)
        lines = [line for code in sample for line in sample[code]]
        (out_dir / files[key].name).write_bytes(b"".join(lines))
        for line in lines:
            needed[source].add(first_token(line))
            target_code = compact(line.split()[1].decode())
            if target_code not in ("NODX", "NOPCS"):
                needed[target].add(target_code)

    for key, system in [("icd9_desc", "icd9"), ("icd10_desc", "icd10")]:
        kept = [line for line in read_lines(files[key]) if first_token(line) in needed[system]]
        (out_dir / files[key].name).write_bytes(b"".join(kept))
        print(f"  {files[key].name}: kept {len(kept)} descriptions")

    print(f"Sample written to {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
