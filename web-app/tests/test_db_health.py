import sqlite3

from db_health import assess_article_db


VALID_ARTICLE = """---
Title: Example Article
Author: Tester
CoverImage: ./resources/images/cover.png
RolloutDate: 2026-04-18
---

```
BriefIntroduction:
Example intro
```

<!-- split -->

# Example

Body
"""


def _write_article(article_dir, filename):
    (article_dir / "resources" / "images").mkdir(parents=True, exist_ok=True)
    (article_dir / "resources" / "images" / "cover.png").write_text(
        "fake", encoding="utf-8"
    )
    (article_dir / filename).write_text(VALID_ARTICLE, encoding="utf-8")


def _init_article_table(db_path, rows):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE article_meta_data (
            id INTEGER PRIMARY KEY,
            file_path TEXT UNIQUE
        )
        """
    )
    for file_path in rows:
        cur.execute("INSERT INTO article_meta_data (file_path) VALUES (?)", (file_path,))
    conn.commit()
    conn.close()


def test_assess_article_db_detects_count_mismatch_against_source_tree(tmp_path):
    root_dir = tmp_path / "articles"
    first_dir = root_dir / "cloud" / "terraform"
    second_dir = root_dir / "cloud" / "network"
    _write_article(first_dir, "first.md")
    _write_article(second_dir, "second.md")

    db_path = tmp_path / "project.db"
    _init_article_table(db_path, ["cloud/terraform/first.md"])

    report = assess_article_db(str(root_dir), f"sqlite:///{db_path}")

    assert report == {
        "db_exists": True,
        "table_exists": True,
        "db_count": 1,
        "expected_count": 2,
    }


def test_assess_article_db_reports_matching_counts(tmp_path):
    root_dir = tmp_path / "articles"
    article_dir = root_dir / "tools" / "shell"
    _write_article(article_dir, "guide.md")

    db_path = tmp_path / "project.db"
    _init_article_table(db_path, ["tools/shell/guide.md"])

    report = assess_article_db(str(root_dir), f"sqlite:///{db_path}")

    assert report == {
        "db_exists": True,
        "table_exists": True,
        "db_count": 1,
        "expected_count": 1,
    }
