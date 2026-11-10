# Roadmap

## v0.1 — core (current)
- [x] Parse CMS GEMs and code-description files
- [x] Local SQLite database (`icdmap build`)
- [x] `convert` with mapping type (exact / approximate / combination / no map / not found)
- [x] `search` by description
- [x] `convert-file` for CSV columns with a problem report
- [x] Test suite and CI

## v0.2 — research features
- [ ] Charlson Comorbidity Index from ICD-9 and ICD-10 codes (Quan et al., 2005 coding algorithms)
- [ ] Per-patient output in `convert-file` (`--group-by patient_id`)
- [ ] Mapping strategy options for approximate/multiple targets (`--strategy all|first|review`)
- [ ] Hierarchy queries: parent category and child codes (`icdmap tree I50`)
- [ ] JSON output for every command (`--json`)

## v0.3 — usability
- [ ] Python API documented with examples (`from icdmap import convert`)
- [ ] Download helper that verifies the CMS files' checksums
- [ ] Elixhauser comorbidity groups
- [ ] Publish to PyPI

## Later
- [ ] Small REST API (FastAPI) and web search page
- [ ] ICD-10-PCS procedure codes
