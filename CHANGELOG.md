# Changelog

All notable changes to this project are listed here.

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
