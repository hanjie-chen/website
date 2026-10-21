import json
import os
import subprocess
from datetime import date
from pathlib import Path

import pytest

import app as app_module
from import_notes import import_notes, note_paths, parse_note, split_title
from models import Note, db


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture()
def rendered_root(app, monkeypatch):
    root = app_module.app.config["RENDERED_ARTICLES_FOLDER"]
    monkeypatch.setattr("import_notes.Rendered_Articles", root)
    monkeypatch.setattr("import_notes.IS_DEV", False)
    return Path(root)


def _notes():
    return {
        note.file_path: note
        for note in db.session.execute(db.select(Note)).scalars().all()
    }


def test_note_paths_cover_every_note_and_skip_auxiliary_files(tmp_path):
    for path in (
        "tools/git/commands.md",
        "devops/linux/user.md",  # a folder without any images
        "draft.md",
        "README.md",
        "AGENTS.md",
        "tools/README.md",
        "tools/CLAUDE.md",
        "tools/git/resources/i18n/commands-en.md",
        "tools/git/images/notes.md",
        "__template__/template.md",
        ".kb-tools/translator/README.md",
        ".github/workflows/notes.md",
    ):
        _write(tmp_path / path, "# Title\n")
    (tmp_path / "tools/git/latin1.md").write_bytes("caf\xe9".encode("latin-1"))

    assert sorted(note_paths(str(tmp_path))) == [
        "devops/linux/user.md",
        "draft.md",
        "tools/git/commands.md",
    ]


def test_split_title_takes_the_first_heading_outside_code_blocks():
    body = (
        "![cover](./images/cover.png)\n\n"
        "```shell\n# not a title\n```\n\n"
        "# `compose.yml` services\n\n"
        "## Section\n\n"
        "# A later heading\n"
    )

    title, rest = split_title(body)

    assert title == "compose.yml services"
    assert "# `compose.yml` services" not in rest
    assert "# not a title" in rest
    assert "# A later heading" in rest


def test_parse_note_reads_rollout_date_and_falls_back_to_the_file_name(tmp_path):
    dated = tmp_path / "dated.md"
    _write(dated, "---\nRolloutDate: 2026-03-06\n---\n\n# Terraform 入门指南\n\n正文\n")
    plain = tmp_path / "remote-backend.md"
    _write(plain, "## only sections\n\n正文\n")
    broken = tmp_path / "broken.md"
    _write(broken, "---\nRolloutDate: [unclosed\n---\n\n# Kept\n")

    title, rollout_date, body, _hash = parse_note(str(dated))
    assert (title, rollout_date) == ("Terraform 入门指南", date(2026, 3, 6))
    assert "Terraform 入门指南" not in body

    assert parse_note(str(plain))[:2] == ("remote-backend", None)
    # Broken front matter never hides a note.
    assert parse_note(str(broken))[0] == "Kept"


def test_import_notes_stores_metadata_and_renders_bodies_with_assets(
    app, tmp_path, rendered_root
):
    root = tmp_path / "kb"
    _write(
        root / "tools/git/commands.md",
        "---\nRolloutDate: 2026-01-02\n---\n\n"
        "# Git Command 速查指南\n\n![flow](images/flow.png)\n\n## Local Workflow\n\n正文\n",
    )
    _write(root / "tools/git/images/flow.png", "fake image")
    _write(root / "devops/linux/user.md", "## 创建用户\n\nuseradd\n")

    with app.app_context():
        import_notes(str(root), db)
        notes = _notes()

    commands = notes["tools/git/commands.md"]
    assert (commands.title, commands.category) == ("Git Command 速查指南", "tools/git")
    assert commands.rollout_date == date(2026, 1, 2)
    user = notes["devops/linux/user.md"]
    assert (user.title, user.rollout_date) == ("user", None)

    html = (rendered_root / "tools-git" / f"{commands.id}.html").read_text("utf-8")
    assert "Git Command 速查指南" not in html
    assert 'src="/rendered-articles/tools-git/images/flow.png"' in html
    assert (rendered_root / "tools-git" / "images" / "flow.png").exists()


def test_import_notes_removes_notes_that_disappear(app, tmp_path, rendered_root):
    root = tmp_path / "kb"
    _write(root / "tools/git/commands.md", "# Commands\n")
    _write(root / "tools/git/hooks.md", "# Hooks\n")

    with app.app_context():
        import_notes(str(root), db)
        hooks = _notes()["tools/git/hooks.md"]
        hooks_html = rendered_root / "tools-git" / f"{hooks.id}.html"
        assert hooks_html.exists()

        (root / "tools/git/hooks.md").unlink()
        import_notes(str(root), db)

        assert set(_notes()) == {"tools/git/commands.md"}
    assert not hooks_html.exists()


def test_import_notes_writes_english_sidecar_with_its_own_title(
    app, tmp_path, rendered_root
):
    root = tmp_path / "kb"
    note_dir = root / "cloud-infra/platforms/cloudflare"
    _write(
        note_dir / "enable-cdn.md",
        "![cf](./resources/images/cf.jpg)\n\n# cloudflare 使用指南\n\n中文正文\n",
    )
    _write(note_dir / "resources/images/cf.jpg", "fake image")
    _write(
        note_dir / "resources/i18n/enable-cdn-en.md",
        "# Cloudflare Guide\n\nEnglish body\n",
    )

    with app.app_context():
        import_notes(str(root), db)
        note = _notes()["cloud-infra/platforms/cloudflare/enable-cdn.md"]

    rendered_dir = rendered_root / "cloud-infra-platforms-cloudflare"
    english_html = (rendered_dir / f"{note.id}.en.html").read_text("utf-8")
    payload = json.loads((rendered_dir / f"{note.id}.en.json").read_text("utf-8"))

    assert "English body" in english_html
    assert "Cloudflare Guide" not in english_html
    # The sidecar inherits the source note's leading image.
    assert "resources/images/cf.jpg" in english_html
    assert payload["title"] == "Cloudflare Guide"


def test_import_notes_rerenders_unchanged_sources_after_renderer_version_bump(
    app, tmp_path, rendered_root, monkeypatch
):
    root = tmp_path / "kb"
    _write(root / "tools/git/guide.md", "# git guide\n\n正文\n")

    with app.app_context():
        import_notes(str(root), db)
        note = db.session.execute(db.select(Note)).scalar_one()
        html_path = rendered_root / "tools-git" / f"{note.id}.html"
        html_path.write_text("stale renderer output", encoding="utf-8")

        import_notes(str(root), db)
        assert html_path.read_text(encoding="utf-8") == "stale renderer output"

        monkeypatch.setattr("import_notes.RENDERER_VERSION", "next")
        import_notes(str(root), db)

    assert "正文" in html_path.read_text(encoding="utf-8")


def _git(root: Path, *args, when: str | None = None):
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{when}T12:00:00+00:00"
    subprocess.run(["git", "-C", str(root), *args], check=True, env=env)


def test_import_notes_dates_notes_by_their_last_commit(app, tmp_path, rendered_root):
    root = tmp_path / "kb"
    root.mkdir()
    _git(root, "init", "-q")
    _write(root / "tools/git/commands.md", "# Commands\n")
    _write(root / "personal/关于自律.md", "# 关于自律\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "add notes", when="2026-01-01")
    _write(root / "tools/git/commands.md", "# Commands\n\nmore\n")
    _git(root, "commit", "-q", "-am", "edit commands", when="2026-02-03")
    _write(root / "tools/git/untracked.md", "# Untracked\n")

    with app.app_context():
        import_notes(str(root), db)
        notes = _notes()

    assert notes["tools/git/commands.md"].updated_date == date(2026, 2, 3)
    assert notes["personal/关于自律.md"].updated_date == date(2026, 1, 1)
    assert notes["tools/git/untracked.md"].updated_date is None
