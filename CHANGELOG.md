# Changelog

All notable changes to this project are listed here.

## [Unreleased]

### Added
- Integration tests against the official CMS files: a stratified, reproducible sample (`scripts/make_real_sample.py`) that runs everywhere, and a check of all 86,271 GEM source codes when the full files are present.
- README: validation section and the distribution of mapping types in the official GEMs.

### Fixed
- Codes whose GEM rows mix a combination with plain alternatives (e.g. ICD-9 249.51) no longer crash; the plain rows become an extra scenario (`E08.39 | E09.39 || (...) + E08.65`).
- Rows marked "no equivalent" are skipped when the same code also has real targets.
- `build --from-dir` prefers files closest to the given folder, so a sample in a subfolder never replaces the main file.

## [0.1.0] - 2026-11-11

First version.

### Added
- `build`: create a local SQLite database from the CMS GEMs and code-description files.
- `convert`: convert ICD-9-CM ↔ ICD-10-CM codes and report the mapping type (exact, approximate, combination, no map, not found).
- `search`: find codes by description. Results that negate the search ("without heart failure") are hidden and listed separately; `--keep-negated` shows them.
- `convert-file`: convert a CSV column, with a report of problem codes.
- CSV output keeps the meaning of each conversion: `|` for alternatives ("or"), `+` for combinations ("and"), plus a JSON column for programs.
- Malformed values are reported as `invalid`, separately from valid codes without a mapping.
- CSV files saved as Windows-1252 (Excel on Windows) are read correctly; output is always UTF-8.

### Fixed
- `build` no longer picks the CMS "addenda" files (this year's changes only) instead of the full code list.
- Unreadable or empty files give a short error message instead of a Python traceback.
