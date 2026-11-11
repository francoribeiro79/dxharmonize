# dxharmonize

**Harmonise clinical datasets that mix ICD-9-CM and ICD-10-CM diagnosis codes, and know how reliable the result is.**

> **Status:** early development, version 0.1.0. Tested with the official 2018 CMS GEMs and the FY2027 ICD-10-CM code descriptions. See [CHANGELOG.md](CHANGELOG.md) and [ROADMAP.md](ROADMAP.md).

Many countries switched hospital coding from ICD-9-CM to ICD-10-CM: the United States in October 2015, Portugal in January 2017. Any study whose data crosses that date (hospital discharge registries, MIMIC-IV, claims data) has diagnoses in two systems. Counting heart-failure admissions per year, for example, shows a false jump at the transition unless the codes are put into one system first.

Converting codes is the easy part. The hard part is knowing **how much to trust the conversion**: many ICD-9 codes have only an approximate ICD-10 equivalent, some need several codes together, and some have none. `dxharmonize` builds a local database from the official CMS General Equivalence Mappings (GEMs) and reports the mapping type for every code instead of hiding it behind a silent best guess.

No patient data is involved: the tool only uses public code tables, and your datasets never leave your computer.

## Example

Real output, using the official CMS files:

```console
$ dxharmonize convert 401.9
401.9 [ICD9]  Unspecified essential hypertension
  mapping: approximate match
  → I10  Essential (primary) hypertension
  → I16.9  Hypertensive crisis, unspecified
```

The two targets are **alternatives**, not codes to use together. A tool that silently picked one, or kept both, could turn every patient with ordinary hypertension into a hypertensive crisis.

```console
$ dxharmonize convert-file discharges.csv --column dx --from icd9
Converted 4 rows → discharges_converted.csv
  approximate         3
  not_found           1
Most frequent codes without a mapping:
  99999         1×
```

## Features

- **`convert`**: convert codes in either direction and show the mapping type
- **`convert-file`**: convert a whole CSV column, with a report of problem codes
- **`search`**: find codes by description; results that *negate* the search (e.g. "without heart failure") are hidden and listed separately
- **`build`**: create the local SQLite database from the CMS files (works offline afterwards)

## Mapping types

| Type | Meaning |
|---|---|
| `exact` | One target code with the same meaning. |
| `approximate` | Closest available code(s); meaning is not identical. Review before analysis. |
| `combination` | Several target codes are needed together. |
| `no_map` | The GEM explicitly states there is no equivalent. |
| `not_found` | Well-formed code that is not in the GEMs (unknown, or newer than 2018). |
| `invalid` | The value is not a code at all (typo, truncated code). Only in `convert-file`. |
| `empty` | The cell was empty. Only in `convert-file`. |

## CSV output

`convert-file` keeps every original column and adds three:

| Column | For | Example |
|---|---|---|
| `<col>_converted` | people | `I10 \| I16.9` |
| `<col>_mapping` | filtering | `approximate` |
| `<col>_mapping_detail` | programs (JSON) | `{"kind": "approximate", "scenarios": [[["I10", "I16.9"]]]}` |

In `<col>_converted`, **`|` means "or"** (choose one) and **`+` means "and"** (use together):

| Case | `<col>_converted` |
|---|---|
| One code | `I10` |
| Alternatives | `I10 \| I16.9` |
| Combination | `E11.29 + N18.9` |
| Combination with alternatives | `(E10.29 \| E11.29) + N18.9` |

The JSON always has the same three levels: scenarios → parts → alternatives. Use one code from each part; within a part, choose one alternative.

### Input handling

- Malformed values are reported as `invalid` and listed separately, so they are not confused with valid codes that have no mapping.
- Empty files give a clear error.
- Input may be UTF-8 or Windows-1252 (as saved by Excel on Windows); the output is always UTF-8.

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
| 2018 Diagnosis GEMs | [CMS ICD-10 archive](https://www.cms.gov/medicare/coding/icd10/archive-icd-10-cm-icd-10-pcs-gems) → 2018 ICD-10-CM files → *General Equivalence Mappings (GEMS)* | `2018_I9gem.txt`, `2018_I10gem.txt` |
| ICD-10-CM code descriptions | [CMS ICD-10 page](https://www.cms.gov/icd10) → latest *Code Descriptions in Tabular Order* | `icd10cm_codes_<year>.txt` |
| ICD-9-CM descriptions (optional) | CMS *ICD-9-CM Diagnosis and Procedure Codes: Abbreviated and Full Code Titles* → Version 32 | `CMS32_DESC_LONG_DX.txt` |

Then build the database once:

```bash
dxharmonize build --from-dir data/raw
```

The database is stored at `~/.dxharmonize/dxharmonize.db` (override with `--db` or the `DXHARMONIZE_DB` environment variable).

## Usage

```bash
dxharmonize convert 401.9 I50.9                  # system is auto-detected
dxharmonize convert V12.51 --from icd9           # force the source system for ambiguous codes
dxharmonize search "heart failure" --system icd10
dxharmonize search "heart failure" --keep-negated   # also show "without heart failure"
dxharmonize convert-file data.csv --column dx --from icd9 -o data_icd10.csv
```

## Known limitations

- **The 2018 GEMs are the final version.** CMS stopped updating them after 2018. ICD-10-CM codes created later (e.g. `U07.1`, COVID-19) are reported as `not_found` rather than mapped incorrectly.
- **Approximate mappings need review.** The GEMs are a translation aid, not a clinical judgement; which alternative is right depends on the study.
- **`convert-file` expects one coding system per column.** Files that mix ICD-9 and ICD-10 in the same column are the goal of the planned `harmonize` command.
- **Search matches words, not meaning.** Negations written as "without ..." are detected; other phrasings are not. Use search to explore, then validate code lists against published definitions.
- **Diagnosis codes only.** ICD-10-PCS / ICD-9-CM procedure codes are not supported yet.

## Development

```bash
python -m pytest     # tests use small synthetic fixtures in tests/fixtures
ruff check .         # lint
```

```
src/dxharmonize/
  codes.py     code normalisation, validation, system detection, formatting
  loaders.py   parsers for the CMS text files
  db.py        SQLite schema and loading
  mapping.py   conversion logic, output formats and search
  batch.py     CSV conversion and reporting
  cli.py       command-line interface
tests/         pytest suite + synthetic fixtures
```

## Disclaimer

`dxharmonize` is a research and data-harmonisation tool. GEMs are not a substitute for professional clinical coding, and mappings, especially approximate ones, should be reviewed for the purpose of each study.

## License

MIT
