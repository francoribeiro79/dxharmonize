from dxharmonize.codes import System
from dxharmonize.mapping import convert, search


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
