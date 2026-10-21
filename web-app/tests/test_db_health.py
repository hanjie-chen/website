import sqlite3

from db_health import assess_note_db


def _write_note(root_dir, rel_path):
    path = root_dir / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Example\n\nBody\n", encoding="utf-8")


def _init_note_table(db_path, rows, table="notes"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(f"CREATE TABLE {table} (id INTEGER PRIMARY KEY, file_path TEXT UNIQUE)")
    for file_path in rows:
        cur.execute(f"INSERT INTO {table} (file_path) VALUES (?)", (file_path,))
    conn.commit()
    conn.close()


def test_assess_note_db_detects_count_mismatch_against_source_tree(tmp_path):
    root_dir = tmp_path / "kb"
    _write_note(root_dir, "cloud/terraform/first.md")
    _write_note(root_dir, "cloud/network/second.md")
    _write_note(root_dir, "cloud/README.md")

    db_path = tmp_path / "project.db"
    _init_note_table(db_path, ["cloud/terraform/first.md"])

    report = assess_note_db(str(root_dir), f"sqlite:///{db_path}")

    assert report == {
        "db_exists": True,
        "table_exists": True,
        "db_count": 1,
        "expected_count": 2,
    }


def test_assess_note_db_reports_matching_counts(tmp_path):
    root_dir = tmp_path / "kb"
    _write_note(root_dir, "tools/shell/guide.md")

    db_path = tmp_path / "project.db"
    _init_note_table(db_path, ["tools/shell/guide.md"])

    report = assess_note_db(str(root_dir), f"sqlite:///{db_path}")

    assert report == {
        "db_exists": True,
        "table_exists": True,
        "db_count": 1,
        "expected_count": 1,
    }


def test_assess_note_db_treats_an_article_era_database_as_missing_its_table(tmp_path):
    # A database from before notes has only the old table, so deploy rebuilds it.
    root_dir = tmp_path / "kb"
    _write_note(root_dir, "tools/shell/guide.md")

    db_path = tmp_path / "project.db"
    _init_note_table(db_path, ["tools/shell/guide.md"], table="article_meta_data")

    report = assess_note_db(str(root_dir), f"sqlite:///{db_path}")

    assert report["table_exists"] is False
