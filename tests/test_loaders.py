import pytest

from dxharmonize.loaders import GemFlags, parse_descriptions, parse_gems

from .conftest import FIXTURES


def test_flags_parse():
    f = GemFlags.parse("10112")
    assert (f.approximate, f.no_map, f.combination, f.scenario, f.choice_list) == (
        True, False, True, 1, 2,
    )


@pytest.mark.parametrize("bad", ["1011", "abcde", "101123"])
def test_flags_reject_bad_input(bad):
    with pytest.raises(ValueError):
        GemFlags.parse(bad)


def test_parse_gems_handles_no_map():
    rows = {r.source: r for r in parse_gems(FIXTURES / "I9gem_sample.txt")}
    assert rows["99999"].target is None
    assert rows["99999"].flags.no_map
    assert rows["42800"].target == "I509"


def test_parse_descriptions():
    d = dict(parse_descriptions(FIXTURES / "icd10cm_codes_sample.txt"))
    assert d["I509"] == "Heart failure, unspecified"


def test_parse_gems_reports_line_number(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("42800 I509 10000\n42800 I509\n")
    with pytest.raises(ValueError, match="bad.txt:2"):
        list(parse_gems(bad))


def test_latin1_file(tmp_path):
    f = tmp_path / "desc.txt"
    f.write_bytes("0010 Cholera d\xfb to vibrio\n".encode("latin-1"))
    assert dict(parse_descriptions(f))["0010"] == "Cholera dû to vibrio"
