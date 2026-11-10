import csv

import pytest

from dxharmonize.batch import convert_csv
from dxharmonize.cli import main
from dxharmonize.codes import System

from .conftest import FIXTURES


def _write_csv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["patient", "dx"])
        w.writerows(rows)


def test_convert_csv(conn, tmp_path):
    src = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    _write_csv(src, [["1", "428.0"], ["2", "401.9"], ["3", "999.99"], ["4", ""], ["5", "401.9"]])
    # note: "428.0" is not "428.00" — the sample GEM only has 42800, so it is not found
    report = convert_csv(conn, src, out, "dx", System.ICD9)

    assert report.total == 5
    assert report.kinds["exact"] == 2
    assert report.unmapped == {"4280": 1, "99999": 1}
    rows = list(csv.DictReader(out.open()))
    assert rows[1]["dx_converted"] == "I10"
    assert rows[1]["dx_mapping"] == "exact"
    assert rows[3]["dx_mapping"] == "empty"


def test_convert_csv_missing_column(conn, tmp_path):
    src = tmp_path / "in.csv"
    _write_csv(src, [["1", "401.9"]])
    with pytest.raises(KeyError):
        convert_csv(conn, src, tmp_path / "out.csv", "nope", System.ICD9)


@pytest.fixture
def built_db(tmp_path):
    path = tmp_path / "cli.db"
    assert main(["--db", str(path), "build", "--from-dir", str(FIXTURES),
                 "--icd9-desc", str(FIXTURES / "icd9_desc_sample.txt"),
                 "--icd10-desc", str(FIXTURES / "icd10cm_codes_sample.txt")]) == 0
    return path


def test_cli_convert(built_db, capsys):
    assert main(["--db", str(built_db), "convert", "401.9", "I50.9"]) == 0
    out = capsys.readouterr().out
    assert "→ I10" in out and "→ 428.9" in out


def test_cli_convert_invalid_code(built_db, capsys):
    assert main(["--db", str(built_db), "convert", "hello"]) == 1


def test_cli_requires_build(tmp_path, capsys):
    assert main(["--db", str(tmp_path / "empty.db"), "convert", "401.9"]) == 2
    assert "dxharmonize build" in capsys.readouterr().err


def test_cli_search(built_db, capsys):
    assert main(["--db", str(built_db), "search", "hypertension", "--system", "icd10"]) == 0
    assert "I10" in capsys.readouterr().out


def test_cli_ambiguous_code_uses_system_that_knows_it(built_db, capsys):
    # V12.51 only exists in the sample ICD-9 GEM, so ICD-9 is chosen
    assert main(["--db", str(built_db), "convert", "V12.51"]) == 0
    assert "[ICD9]" in capsys.readouterr().out
