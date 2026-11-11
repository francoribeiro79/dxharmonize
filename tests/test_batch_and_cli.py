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
    assert rows[1]["dx_mapping_detail"] == '{"kind": "exact", "scenarios": [[["I10"]]]}'


def test_convert_csv_keeps_or_and_meaning(conn, tmp_path):
    src = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    _write_csv(src, [["1", "401.1"], ["2", "250.40"]])
    convert_csv(conn, src, out, "dx", System.ICD9)
    rows = list(csv.DictReader(out.open()))
    assert rows[0]["dx_converted"] == "I10 | I16.9"     # alternatives: one OR the other
    assert rows[1]["dx_converted"] == "E11.29 + N18.9"  # combination: both together


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


def test_build_ignores_addenda_files(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "2018_I9gem.txt").write_text((FIXTURES / "I9gem_sample.txt").read_text())
    (raw / "icd10cm_codes_2027.txt").write_text((FIXTURES / "icd10cm_codes_sample.txt").read_text())
    # an addenda file sorts after the real one and has a different format
    (raw / "icd10cm_codes_addenda_2027.txt").write_text("Add:    I509    Heart failure\nDelete:\n")
    assert main(["--db", str(tmp_path / "a.db"), "build", "--from-dir", str(raw)]) == 0


def test_build_reports_bad_file_without_traceback(tmp_path, capsys):
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "2018_I9gem.txt").write_text("42800 I509\n")  # missing flags column
    assert main(["--db", str(tmp_path / "b.db"), "build", "--from-dir", str(raw)]) == 2
    assert "could not read 2018_I9gem.txt" in capsys.readouterr().err


def test_cli_search_hides_negated_results(built_db, capsys):
    assert main(["--db", str(built_db), "search", "heart failure", "--system", "icd10"]) == 0
    out = capsys.readouterr().out
    main_part, hidden_part = out.split("Hidden")
    assert "I11.0" in main_part and "I11.9" not in main_part
    assert "I11.9" in hidden_part


def test_cli_search_keep_negated(built_db, capsys):
    assert main(["--db", str(built_db), "search", "heart failure", "--keep-negated"]) == 0
    out = capsys.readouterr().out
    assert "I11.9" in out and "Hidden" not in out


def test_convert_csv_flags_invalid_codes(conn, tmp_path):
    src = tmp_path / "in.csv"
    out = tmp_path / "out.csv"
    _write_csv(src, [["1", "401.9"], ["2", "abc"], ["3", "42"], ["4", "abc"]])
    report = convert_csv(conn, src, out, "dx", System.ICD9)
    assert report.kinds["invalid"] == 3
    assert report.invalid == {"abc": 2, "42": 1}
    assert report.unmapped == {}  # invalid values are not "codes without a mapping"
    rows = list(csv.DictReader(out.open()))
    assert rows[1]["dx_mapping"] == "invalid"


def test_convert_csv_empty_file(conn, tmp_path):
    src = tmp_path / "empty.csv"
    src.write_text("")
    with pytest.raises(ValueError, match="empty"):
        convert_csv(conn, src, tmp_path / "out.csv", "dx", System.ICD9)


def test_convert_csv_reads_windows_1252(conn, tmp_path):
    # Excel on Windows often saves CSVs like this; "São João" is not valid UTF-8 here
    src = tmp_path / "excel.csv"
    src.write_bytes("hospital,dx\nSão João,401.9\n".encode("cp1252"))
    out = tmp_path / "out.csv"
    report = convert_csv(conn, src, out, "dx", System.ICD9)
    assert report.encoding == "cp1252"
    rows = list(csv.DictReader(out.open(encoding="utf-8")))
    assert rows[0]["hospital"] == "São João"  # accents preserved, output is UTF-8
    assert rows[0]["dx_converted"] == "I10"


def test_cli_convert_file_empty(built_db, tmp_path, capsys):
    src = tmp_path / "empty.csv"
    src.write_text("")
    args = ["--db", str(built_db), "convert-file", str(src), "--column", "dx", "--from", "icd9"]
    assert main(args) == 2
    assert "empty" in capsys.readouterr().err
