import pytest

from dxharmonize.codes import System
from dxharmonize.mapping import convert, is_negated, search, split_negated


def test_exact(conn):
    res = convert(conn, "401.9", System.ICD9)
    assert res.kind == "exact"
    assert res.target_codes == ["I10"]
    assert res.targets[0].description == "Essential (primary) hypertension"


def test_approximate(conn):
    res = convert(conn, "428.00", System.ICD9)
    assert res.kind == "approximate"
    assert res.target_codes == ["I509"]
    assert res.source_description == "Congestive heart failure, unspecified"


def test_backward_mapping(conn):
    res = convert(conn, "I50.9", System.ICD10)
    assert res.target_codes == ["4289"]


def test_combination(conn):
    res = convert(conn, "250.40", System.ICD9)
    assert res.kind == "combination"
    assert [[t.code for t in cl] for cl in res.scenarios[1]] == [["E1129"], ["N189"]]


def test_no_map(conn):
    assert convert(conn, "999.99", System.ICD9).kind == "no_map"


def test_not_found(conn):
    res = convert(conn, "U07.1", System.ICD10)  # COVID-19, created after the 2018 GEMs
    assert res.kind == "not_found"
    assert res.target_codes == []


def test_search_all_words(conn):
    codes = [r["code"] for r in search(conn, "heart failure")]
    assert {"I509", "42800", "4289"} <= set(codes)
    assert "I501" not in codes  # "Left ventricular failure" lacks the word "heart"


def test_search_filters_system(conn):
    rows = search(conn, "heart failure", System.ICD10)
    assert {r["system"] for r in rows} == {"icd10"}


def test_search_empty_text(conn):
    assert search(conn, "   ") == []


@pytest.mark.parametrize(
    "description, expected",
    [
        ("Hypertensive heart disease without heart failure", True),
        ("Hypertensive heart disease with heart failure", False),
        ("Heart failure, unspecified", False),
        ("Hypertension, with or without heart failure", False),  # may be present
        ("HYPERTENSIVE HEART DISEASE WITHOUT HEART FAILURE", True),  # case does not matter
    ],
)
def test_is_negated(description, expected):
    assert is_negated(description, "heart failure") is expected


def test_split_negated(conn):
    kept, hidden = split_negated(search(conn, "heart failure", System.ICD10), "heart failure")
    assert "I110" in [r["code"] for r in kept]
    assert "O1000" in [r["code"] for r in kept]
    assert [r["code"] for r in hidden] == ["I119"]


# --- how a conversion is represented in the CSV output -------------------
# "|" means "or" (choose one), "+" means "and" (use together)


def test_output_single_code(conn):
    res = convert(conn, "401.9", System.ICD9)
    assert res.structure() == [[["I10"]]]
    assert res.to_text() == "I10"


def test_output_alternatives_use_or(conn):
    res = convert(conn, "401.1", System.ICD9)
    assert res.structure() == [[["I10", "I16.9"]]]
    assert res.to_text() == "I10 | I16.9"


def test_output_combination_uses_and(conn):
    res = convert(conn, "250.40", System.ICD9)
    assert res.structure() == [[["E11.29"], ["N18.9"]]]
    assert res.to_text() == "E11.29 + N18.9"


def test_output_combination_with_alternatives(conn):
    res = convert(conn, "250.41", System.ICD9)
    assert res.to_text() == "(E10.29 | E11.29) + N18.9"


def test_output_no_conversion(conn):
    res = convert(conn, "999.99", System.ICD9)
    assert res.structure() == []
    assert res.to_text() == ""


def test_output_json(conn):
    import json

    res = convert(conn, "401.1", System.ICD9)
    assert json.loads(res.to_json()) == {"kind": "approximate", "scenarios": [[["I10", "I16.9"]]]}
