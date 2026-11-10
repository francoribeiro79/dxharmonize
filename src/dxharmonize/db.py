"""Local SQLite database that holds the official code tables.

The database is built once from the CMS files (``dxharmonize build``) and then
queried by every other command. It is a single file, by default
``~/.dxharmonize/dxharmonize.db``; set ``DXHARMONIZE_DB`` to use another path.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from .codes import System
from .loaders import parse_descriptions, parse_gems

SCHEMA = """
CREATE TABLE IF NOT EXISTS descriptions (
    system      TEXT NOT NULL,
    code        TEXT NOT NULL,
    description TEXT NOT NULL,
    PRIMARY KEY (system, code)
);
CREATE TABLE IF NOT EXISTS gems (
    source_system TEXT NOT NULL,
    source        TEXT NOT NULL,
    target        TEXT,
    approximate   INTEGER NOT NULL,
    no_map        INTEGER NOT NULL,
    combination   INTEGER NOT NULL,
    scenario      INTEGER NOT NULL,
    choice_list   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gems_source ON gems (source_system, source);
CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def default_db_path() -> Path:
    env = os.environ.get("DXHARMONIZE_DB")
    if env:
        return Path(env)
    return Path.home() / ".dxharmonize" / "dxharmonize.db"


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def load_descriptions(conn: sqlite3.Connection, system: System, path: Path) -> int:
    rows = [(system.value, code, desc) for code, desc in parse_descriptions(path)]
    conn.executemany("INSERT OR REPLACE INTO descriptions VALUES (?, ?, ?)", rows)
    return len(rows)


def load_gems(conn: sqlite3.Connection, source_system: System, path: Path) -> int:
    conn.execute("DELETE FROM gems WHERE source_system = ?", (source_system.value,))
    rows = [
        (
            source_system.value,
            r.source,
            r.target,
            int(r.flags.approximate),
            int(r.flags.no_map),
            int(r.flags.combination),
            r.flags.scenario,
            r.flags.choice_list,
        )
        for r in parse_gems(path)
    ]
    conn.executemany("INSERT INTO gems VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)
    return len(rows)


def set_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO metadata VALUES (?, ?)", (key, value))


def is_built(conn: sqlite3.Connection) -> bool:
    return conn.execute("SELECT COUNT(*) FROM gems").fetchone()[0] > 0
