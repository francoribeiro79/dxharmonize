"""Command-line interface: ``dxharmonize build | convert | search | convert-file``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__, db
from .batch import convert_csv
from .codes import System, candidate_systems, format_code
from .mapping import ConversionResult, convert, search, split_negated

KIND_LABELS = {
    "exact": "exact match",
    "approximate": "approximate match",
    "combination": "combination — several codes needed together",
    "no_map": "no equivalent code exists (official GEM)",
    "not_found": "code not in the GEMs (unknown, or created after 2018)",
}

# Filename patterns used by `build --from-dir`. CMS names change slightly
# between releases, so each entry lists the patterns we accept.
FILE_PATTERNS = {
    "icd9_gem": ["*I9gem*.txt"],
    "icd10_gem": ["*I10gem*.txt"],
    "icd9_desc": ["CMS32_DESC_LONG_DX*.txt", "*icd9*desc*.txt"],
    "icd10_desc": ["icd10cm_codes_*.txt", "icd10cm-codes-*.txt"],
}


# CMS ships "addenda" files (only this year's changes, different format) next
# to the full code lists, with similar names. They must never be picked.
EXCLUDED_WORDS = ("addenda", "addendum")


def _find(directory: Path, key: str) -> Path | None:
    for pattern in FILE_PATTERNS[key]:
        matches = sorted(
            p for p in directory.rglob(pattern)
            if not any(word in p.name.lower() for word in EXCLUDED_WORDS)
        )
        if matches:
            return matches[-1]  # latest year sorts last
    return None


def _system_arg(value: str | None) -> System | None:
    return System(value) if value else None


def cmd_build(args: argparse.Namespace) -> int:
    paths = {
        "icd9_gem": args.icd9_gem,
        "icd10_gem": args.icd10_gem,
        "icd9_desc": args.icd9_desc,
        "icd10_desc": args.icd10_desc,
    }
    if args.from_dir:
        for key, given in paths.items():
            paths[key] = given or _find(args.from_dir, key)

    if not (paths["icd9_gem"] or paths["icd10_gem"]):
        print("error: no GEM file given or found. See README → 'Getting the data'.", file=sys.stderr)
        return 2

    conn = db.connect(args.db)
    with conn:
        for key, system, loader in [
            ("icd9_desc", System.ICD9, db.load_descriptions),
            ("icd10_desc", System.ICD10, db.load_descriptions),
            ("icd9_gem", System.ICD9, db.load_gems),
            ("icd10_gem", System.ICD10, db.load_gems),
        ]:
            path = paths[key]
            if path is None:
                print(f"  skipped {key} (file not found)")
                continue
            try:
                n = loader(conn, system, Path(path))
            except ValueError as exc:
                print(f"error: could not read {Path(path).name}: {exc}", file=sys.stderr)
                return 2
            db.set_metadata(conn, key, Path(path).name)
            print(f"  loaded {n:>7,} rows from {Path(path).name}")
    print(f"Database ready: {args.db or db.default_db_path()}")
    return 0


def _print_result(res: ConversionResult) -> None:
    src_fmt = format_code(res.source, res.source_system)
    tgt_sys = res.source_system.other()
    desc = f"  {res.source_description}" if res.source_description else ""
    print(f"{src_fmt} [{res.source_system.value.upper()}]{desc}")
    print(f"  mapping: {KIND_LABELS[res.kind]}")
    if res.kind == "combination":
        for scenario, lists in res.scenarios.items():
            print(f"  scenario {scenario}: use one code from each list")
            for i, choices in enumerate(lists, start=1):
                options = " | ".join(format_code(t.code, tgt_sys) for t in choices)
                print(f"    list {i}: {options}")
    else:
        for t in res.targets:
            d = f"  {t.description}" if t.description else ""
            print(f"  → {format_code(t.code, tgt_sys)}{d}")


def cmd_convert(args: argparse.Namespace) -> int:
    conn = db.connect(args.db)
    if not db.is_built(conn):
        print("error: database is empty — run `dxharmonize build` first.", file=sys.stderr)
        return 2
    status = 0
    for code in args.codes:
        systems = [System(args.source)] if args.source else candidate_systems(code)
        if not systems:
            print(f"{code}: not a valid ICD-9-CM or ICD-10-CM code", file=sys.stderr)
            status = 1
            continue
        # For ambiguous codes (e.g. V12.51) use the first system that knows it.
        results = [convert(conn, code, s) for s in systems]
        found = [r for r in results if r.kind != "not_found"]
        if len(found) > 1:
            print(f"note: {code} exists in both systems; showing {found[0].source_system.value}. "
                  "Use --from to choose.", file=sys.stderr)
        _print_result(found[0] if found else results[0])
    return status


def _print_row(r) -> None:
    system = System(r["system"])
    print(f"{format_code(r['code'], system):<9} [{system.value.upper()}]  {r['description']}")


def cmd_search(args: argparse.Namespace) -> int:
    conn = db.connect(args.db)
    # Fetch every match first, so hidden results do not use up the --limit.
    rows = search(conn, args.text, _system_arg(args.system), limit=None)
    if args.keep_negated:
        kept, hidden = rows, []
    else:
        kept, hidden = split_negated(rows, args.text)
    if not kept and not hidden:
        print("no results")
        return 1
    for r in kept[: args.limit]:
        _print_row(r)
    if hidden:
        phrase = " ".join(args.text.split())
        print(f'\nHidden ({len(hidden)}, description says "without {phrase}"):')
        for r in hidden[: args.limit]:
            _print_row(r)
        print("Use --keep-negated to include them in the results.")
    return 0


def cmd_convert_file(args: argparse.Namespace) -> int:
    conn = db.connect(args.db)
    if not db.is_built(conn):
        print("error: database is empty — run `dxharmonize build` first.", file=sys.stderr)
        return 2
    output = args.output or args.input.with_name(f"{args.input.stem}_converted.csv")
    try:
        report = convert_csv(conn, args.input, output, args.column, System(args.source))
    except (KeyError, ValueError) as exc:
        print(f"error: {exc.args[0]}", file=sys.stderr)
        return 2
    if report.encoding != "utf-8-sig":
        print(f"Note: input was not UTF-8; read it as {report.encoding}.")
    print(f"Converted {report.total:,} rows → {output}")
    for kind, n in report.kinds.most_common():
        print(f"  {kind:<12} {n:>8,}")
    if report.invalid:
        print("Invalid codes (check the source data):")
        for value, n in report.invalid.most_common(10):
            print(f"  {value:<8} {n:>6,}×")
    if report.unmapped:
        print("Most frequent codes without a mapping:")
        for code, n in report.unmapped.most_common(10):
            print(f"  {code:<8} {n:>6,}×")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dxharmonize", description="Harmonise clinical datasets that mix ICD-9-CM and ICD-10-CM diagnosis codes."
    )
    p.add_argument("--version", action="version", version=f"dxharmonize {__version__}")
    p.add_argument("--db", type=Path, help="database path (default: ~/.dxharmonize/dxharmonize.db)")
    sub = p.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="build the local database from CMS files")
    b.add_argument("--from-dir", type=Path, help="folder with the extracted CMS files")
    b.add_argument("--icd9-gem", type=Path)
    b.add_argument("--icd10-gem", type=Path)
    b.add_argument("--icd9-desc", type=Path)
    b.add_argument("--icd10-desc", type=Path)
    b.set_defaults(func=cmd_build)

    c = sub.add_parser("convert", help="convert one or more codes")
    c.add_argument("codes", nargs="+")
    c.add_argument("--from", dest="source", choices=[s.value for s in System],
                   help="source system (auto-detected if omitted)")
    c.set_defaults(func=cmd_convert)

    s = sub.add_parser("search", help="search codes by description")
    s.add_argument("text")
    s.add_argument("--system", choices=[s.value for s in System])
    s.add_argument("--limit", type=int, default=20)
    s.add_argument("--keep-negated", action="store_true",
                   help='do not hide results that say "without <your search>"')
    s.set_defaults(func=cmd_search)

    f = sub.add_parser("convert-file", help="convert a column of codes in a CSV file")
    f.add_argument("input", type=Path)
    f.add_argument("--column", required=True)
    f.add_argument("--from", dest="source", required=True, choices=[s.value for s in System])
    f.add_argument("-o", "--output", type=Path)
    f.set_defaults(func=cmd_convert_file)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
