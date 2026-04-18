import io
import os
import sqlite3
from contextlib import redirect_stdout

from import_articles_scripts import divide_files_and_folders, find_article_assets_folder
from import_articles_scripts import _parse_article


def _iter_expected_article_paths(current_dir: str, root_dir: str):
    files, folders = divide_files_and_folders(current_dir)
    assets_folder = find_article_assets_folder(current_dir)

    if assets_folder:
        for file_name in files:
            if not file_name.endswith(".md"):
                continue
            md_path = os.path.join(current_dir, file_name)
            with redirect_stdout(io.StringIO()):
                parsed = _parse_article(md_path)
            if parsed:
                yield os.path.relpath(md_path, root_dir)
        return

    for folder in folders:
        yield from _iter_expected_article_paths(
            os.path.join(current_dir, folder), root_dir
        )


def expected_article_count(root_dir: str) -> int:
    if not root_dir or not os.path.isdir(root_dir):
        return 0

    return sum(1 for _ in _iter_expected_article_paths(root_dir, root_dir))


def _resolve_sqlite_path(db_uri: str) -> str:
    if not db_uri.startswith("sqlite:///"):
        raise ValueError(f"Unsupported database uri: {db_uri!r}")
    db_path = db_uri[len("sqlite:///") :]
    if os.path.isabs(db_path):
        return db_path
    return os.path.join("/app/instance", db_path)


def assess_article_db(root_dir: str, db_uri: str) -> dict[str, int | bool]:
    db_path = _resolve_sqlite_path(db_uri)
    report = {
        "db_exists": os.path.exists(db_path),
        "table_exists": False,
        "db_count": 0,
        "expected_count": expected_article_count(root_dir),
    }

    if not report["db_exists"]:
        return report

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='article_meta_data'"
        )
        if cur.fetchone() is None:
            return report

        report["table_exists"] = True
        cur.execute("SELECT COUNT(*) FROM article_meta_data")
        report["db_count"] = cur.fetchone()[0]
        return report
    finally:
        conn.close()
