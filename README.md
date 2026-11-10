# icdmap

**Convert and search ICD-9-CM / ICD-10-CM diagnosis codes from the terminal — and know how good each conversion is.**

Clinical datasets that span many years (MIMIC-IV, hospital registries, claims data) mix ICD-9-CM and ICD-10-CM codes. Harmonising them by hand is slow and error-prone. `icdmap` builds a local database from the official CMS General Equivalence Mappings (GEMs) and lets you:

- convert single codes in either direction,
- convert a whole CSV column and get a report of problem codes,
- search codes by description,
- see **what kind of mapping** you got — exact, approximate, a combination of several codes, or no equivalent — instead of a silent best guess.

No patient data is involved: `icdmap` only uses public code tables.

```console
$ icdmap convert 428.00
428.00 [ICD9]  Congestive heart failure, unspecified
  mapping: approximate match
  → I50.9  Heart failure, unspecified

$ icdmap convert-file diagnoses.csv --column dx --from icd9
Converted 48,210 rows → diagnoses_converted.csv
  approximate    31,904
  exact          15,877
  no_map            312
  ...
```

## Installation

```bash
git clone https://github.com/<your-username>/icdmap.git
cd icdmap
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

Requires Python 3.10+. No runtime dependencies.

## Getting the data

`icdmap` does not ship the official files; download them from CMS (free, published by the U.S. government) and extract them into `data/raw/`:

| File | Where | Contents |
|---|---|---|
| 2018 Diagnosis GEMs | [CMS ICD-10 archive](https://www.cms.gov/medicare/coding/icd10/archive-icd-10-cm-icd-10-pcs-gems) → *2018 General Equivalence Mappings (GEMS)* | `2018_I9gem.txt`, `2018_I10gem.txt` |
| ICD-10-CM code descriptions | [CMS ICD-10 page](https://www.cms.gov/medicare/coding/icd10) → latest year → *Code Descriptions in Tabular Order* | `icd10cm_codes_<year>.txt` |
| ICD-9-CM descriptions (final, v32) | CMS *ICD-9-CM Diagnosis and Procedure Codes* page | `CMS32_DESC_LONG_DX.txt` |

The 2018 GEMs are the **final** version: CMS stopped updating them after 2018. ICD-10-CM codes created later (e.g. `U07.1`, COVID-19) are reported as `not_found` rather than mapped incorrectly.

Then build the database (once):

```bash
icdmap build --from-dir data/raw
```

The database is stored at `~/.icdmap/icdmap.db` (override with `--db` or the `ICDMAP_DB` environment variable).

## Usage

```bash
icdmap convert 401.9 I50.9           # system is auto-detected
icdmap convert V12.51 --from icd9    # force the source system for ambiguous codes
icdmap search "heart failure" --system icd10
icdmap convert-file data.csv --column dx --from icd9 -o data_icd10.csv
```

### Mapping types

| Type | Meaning |
|---|---|
| `exact` | One target code with the same meaning. |
| `approximate` | Closest available code(s); meaning is not identical. |
| `combination` | Several target codes are needed together. Grouped by scenario; pick one code from each list. |
| `no_map` | The GEM explicitly states there is no equivalent. |
| `not_found` | Code is not in the GEMs (invalid, or newer than 2018). |

## Development

```bash
pytest          # run the tests (they use small synthetic fixtures in tests/fixtures)
ruff check .    # lint
```

Project layout:

```
src/icdmap/
  codes.py     code normalisation, system detection, formatting
  loaders.py   parsers for the CMS text files
  db.py        SQLite schema and loading
  mapping.py   conversion logic and search
  batch.py     CSV conversion and reporting
  cli.py       command-line interface
tests/         pytest suite + synthetic fixtures
```

See [ROADMAP.md](ROADMAP.md) for planned features.

## Disclaimer

`icdmap` is a research and data-harmonisation tool. GEMs are not a substitute for professional clinical coding, and mappings — especially approximate ones — should be reviewed for the purpose of each study.

## License

MIT
