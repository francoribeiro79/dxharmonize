# dxharmonize

**Harmonise clinical datasets that mix ICD-9-CM and ICD-10-CM diagnosis codes — and know how reliable the result is.**

Many countries switched hospital coding from ICD-9-CM to ICD-10-CM: the United States in October 2015, Portugal in January 2017. Any study whose data crosses that date — hospital discharge registries, MIMIC-IV, claims data — has diagnoses in two systems. Counting heart-failure admissions per year, for example, shows a false jump at the transition unless the codes are put into one system first.

Converting codes is the easy part. The hard part is knowing **how much to trust the conversion**: many ICD-9 codes have only an approximate ICD-10 equivalent, some need several codes together, and some have none. `dxharmonize` builds a local database from the official CMS General Equivalence Mappings (GEMs) and reports the mapping type for every code instead of hiding it behind a silent best guess.

No patient data is involved: the tool only uses public code tables, and your datasets never leave your computer.

```console
$ dxharmonize convert 428.00
428.00 [ICD9]  Congestive heart failure, unspecified
  mapping: approximate match
  → I50.9  Heart failure, unspecified

$ dxharmonize convert-file discharges.csv --column dx --from icd9
Converted 48,210 rows → discharges_converted.csv
  approximate    31,904
  exact          15,877
  no_map            312
```

## Features

Available now:

- Convert single codes in either direction (`convert`), with the mapping type: exact, approximate, combination, no equivalent, or not found
- Convert a whole CSV column and get a report of the codes that could not be mapped (`convert-file`)
- Search codes by description (`search`)
- Works offline from a single SQLite file

Next (see [ROADMAP.md](ROADMAP.md)): a `harmonize` command for files with *mixed* ICD-9/ICD-10 codes, a harmonisation quality report, and Charlson comorbidity scores computed consistently across both systems.

## Installation

```bash
git clone https://github.com/francoribeiro79/dxharmonize.git
cd dxharmonize
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.10+. No runtime dependencies.

## Getting the data

`dxharmonize` does not ship the official files. Download them from CMS (free, published by the U.S. government) and extract them into `data/raw/`:

| File | Where | Contents |
|---|---|---|
| 2018 Diagnosis GEMs | [CMS ICD-10 archive](https://www.cms.gov/medicare/coding/icd10/archive-icd-10-cm-icd-10-pcs-gems) → *2018 General Equivalence Mappings (GEMS)* | `2018_I9gem.txt`, `2018_I10gem.txt` |
| ICD-10-CM code descriptions | [CMS ICD-10 page](https://www.cms.gov/icd10) → latest *Code Descriptions in Tabular Order* | `icd10cm-codes-<year>.txt` |
| ICD-9-CM descriptions (optional, final v32) | CMS *ICD-9-CM Diagnosis and Procedure Codes: Abbreviated and Full Code Titles* | `CMS32_DESC_LONG_DX.txt` |

The 2018 GEMs are the **final** version: CMS stopped updating them after 2018. ICD-10-CM codes created later (e.g. `U07.1`, COVID-19) are reported as `not_found` rather than mapped incorrectly.

Then build the database once:

```bash
dxharmonize build --from-dir data/raw
```

The database is stored at `~/.dxharmonize/dxharmonize.db` (override with `--db` or the `DXHARMONIZE_DB` environment variable).

## Usage

```bash
dxharmonize convert 401.9 I50.9           # system is auto-detected
dxharmonize convert V12.51 --from icd9    # force the source system for ambiguous codes
dxharmonize search "heart failure" --system icd10
dxharmonize convert-file data.csv --column dx --from icd9 -o data_icd10.csv
```

### Mapping types

| Type | Meaning |
|---|---|
| `exact` | One target code with the same meaning. |
| `approximate` | Closest available code(s); meaning is not identical. Review before analysis. |
| `combination` | Several target codes are needed together. Grouped by scenario; pick one code from each list. |
| `no_map` | The GEM explicitly states there is no equivalent. |
| `not_found` | Code is not in the GEMs (invalid, or newer than 2018). |

## Development

```bash
python -m pytest     # tests use small synthetic fixtures in tests/fixtures
ruff check .         # lint
```

```
src/dxharmonize/
  codes.py     code normalisation, system detection, formatting
  loaders.py   parsers for the CMS text files
  db.py        SQLite schema and loading
  mapping.py   conversion logic and search
  batch.py     CSV conversion and reporting
  cli.py       command-line interface
tests/         pytest suite + synthetic fixtures
```

## Disclaimer

`dxharmonize` is a research and data-harmonisation tool. GEMs are not a substitute for professional clinical coding, and mappings — especially approximate ones — should be reviewed for the purpose of each study.

## License

MIT
