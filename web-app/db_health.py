import os
import sqlite3

from import_notes import note_paths


def expected_note_count(root_dir: str) -> int:
    if not root_dir or not os.path.isdir(root_dir):
        return 0
    return len(note_paths(root_dir))


def _resolve_sqlite_path(db_uri: str) -> str:
    if not db_uri.startswith("sqlite:///"):
        raise ValueError(f"Unsupported database uri: {db_uri!r}")
    db_path = db_uri[len("sqlite:///") :]
    if os.path.isabs(db_path):
        return db_path
    return os.path.join("/app/instance", db_path)


def assess_note_db(root_dir: str, db_uri: str) -> dict[str, int | bool]:
    db_path = _resolve_sqlite_path(db_uri)
    report = {
        "db_exists": os.path.exists(db_path),
        "table_exists": False,
        "db_count": 0,
        "expected_count": expected_note_count(root_dir),
    }

    if not report["db_exists"]:
        return report

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='notes'")
        if cur.fetchone() is None:
            return report

        report["table_exists"] = True
        cur.execute("SELECT COUNT(*) FROM notes")
        report["db_count"] = cur.fetchone()[0]
        return report
    finally:
        conn.close()
