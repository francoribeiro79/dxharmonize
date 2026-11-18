These are small **synthetic samples** written in the same format as the CMS
files, used only by the test suite. They are not the official data (except the 24951 lines, copied from the
official 2018 GEMs because they exposed a real edge case); a few
lines (e.g. the 25040/25041 combination entries and the 4011 alternatives) were invented to exercise edge cases.

The `real/` folder is different: it holds a stratified sample of the
**official** CMS files, copied byte for byte by `scripts/make_real_sample.py`.
Nothing in it is invented. See `tests/test_real_data.py`.
