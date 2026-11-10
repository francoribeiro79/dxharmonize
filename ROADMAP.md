# Roadmap

## v0.1 — conversion core (current)
- [x] Parse CMS GEMs and code-description files
- [x] Local SQLite database (`dxharmonize build`)
- [x] `convert` with mapping type (exact / approximate / combination / no map / not found)
- [x] `search` by description
- [x] `convert-file` for CSV columns with a report of unmapped codes
- [x] Test suite and CI

## v0.2 — harmonisation
- [ ] `harmonize` command: detect ICD-9 vs ICD-10 per row (by code pattern or a date column with a configurable transition date, e.g. 2015-10-01 for the US, 2017-01-01 for Portugal) and convert everything to ICD-10-CM
- [ ] Harmonisation quality report: share of exact / approximate / lost codes, and the clinical categories most affected
- [ ] Strategy options for approximate and one-to-many mappings (`--strategy all|first|review`)
- [ ] JSON output for every command (`--json`)

## v0.3 — clinical scores
- [ ] Charlson Comorbidity Index from ICD-9 and ICD-10 codes (Quan et al., 2005 coding algorithms)
- [ ] Per-patient aggregation (`--group-by patient_id`)
- [ ] Before/after-transition comparison of comorbidity prevalence, to flag artificial jumps

## Later
- [ ] Elixhauser comorbidity groups
- [ ] Documented Python API and publication on PyPI
- [ ] Small web interface for non-programmers
