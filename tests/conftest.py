from pathlib import Path

import pytest

from icdmap import db
from icdmap.codes import System

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def conn(tmp_path):
    c = db.connect(tmp_path / "test.db")
    with c:
        db.load_descriptions(c, System.ICD9, FIXTURES / "icd9_desc_sample.txt")
        db.load_descriptions(c, System.ICD10, FIXTURES / "icd10cm_codes_sample.txt")
        db.load_gems(c, System.ICD9, FIXTURES / "I9gem_sample.txt")
        db.load_gems(c, System.ICD10, FIXTURES / "I10gem_sample.txt")
    yield c
    c.close()
