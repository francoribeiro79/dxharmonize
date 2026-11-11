import pytest

from dxharmonize.codes import (
    System,
    candidate_systems,
    compact,
    detect_system,
    format_code,
    is_valid,
)


@pytest.mark.parametrize("raw, expected", [("428.0", "4280"), (" i50.9 ", "I509"), ("E11.9", "E119")])
def test_compact(raw, expected):
    assert compact(raw) == expected


@pytest.mark.parametrize(
    "code, system",
    [
        ("428.0", System.ICD9),
        ("001.0", System.ICD9),
        ("E888.9", System.ICD9),  # point after 4 chars → ICD-9 E-code
        ("I50.9", System.ICD10),
        ("Z86.718", System.ICD10),
        ("E11.9", System.ICD10),  # ambiguous E-code: modern ICD-10 preferred
    ],
)
def test_detect_system(code, system):
    assert detect_system(code) is system


def test_ambiguous_code_lists_both_systems():
    assert candidate_systems("V12.51") == [System.ICD10, System.ICD9]


@pytest.mark.parametrize("code", ["", "hello", "12", "I5", "ZZZ.9"])
def test_detect_system_invalid(code):
    assert detect_system(code) is None


@pytest.mark.parametrize(
    "code, system, expected",
    [
        ("42800", System.ICD9, "428.00"),
        ("4019", System.ICD9, "401.9"),
        ("E8889", System.ICD9, "E888.9"),
        ("V1251", System.ICD9, "V12.51"),
        ("I509", System.ICD10, "I50.9"),
        ("I10", System.ICD10, "I10"),
        ("W19XXXA", System.ICD10, "W19.XXXA"),
    ],
)
def test_format_code(code, system, expected):
    assert format_code(code, system) == expected


@pytest.mark.parametrize(
    "code, system, expected",
    [
        ("428.0", System.ICD9, True),
        ("V12.51", System.ICD9, True),
        ("I50.9", System.ICD10, True),
        ("abc", System.ICD9, False),   # typo
        ("42", System.ICD9, False),    # truncated
        ("I50.9", System.ICD9, False),  # right shape, wrong system
        ("428.0", System.ICD10, False),
    ],
)
def test_is_valid(code, system, expected):
    assert is_valid(code, system) is expected
