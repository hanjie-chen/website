import json
from datetime import date

from models import Note
from note_views import note_html_path, note_view_model


def _make_note():
    return Note(
        id=42,
        title="Cloudflare 指南",
        category="tests/cloudflare",
        file_path="tests/cloudflare/guide.md",
        rollout_date=date(2026, 4, 22),
        updated_date=date(2026, 4, 22),
        content_hash="a" * 64,
    )


def test_note_html_path_prefers_english_render_when_present(tmp_path):
    note = _make_note()
    render_dir = tmp_path / "tests-cloudflare"
    render_dir.mkdir(parents=True, exist_ok=True)
    (render_dir / "42.en.html").write_text("<p>English</p>", encoding="utf-8")
    (render_dir / "42.html").write_text("<p>Chinese</p>", encoding="utf-8")

    assert note_html_path(str(tmp_path), note, "en") == str(render_dir / "42.en.html")


def test_note_view_model_uses_the_english_sidecar_title(tmp_path):
    note = _make_note()
    render_dir = tmp_path / "tests-cloudflare"
    render_dir.mkdir(parents=True, exist_ok=True)
    (render_dir / "42.en.json").write_text(
        json.dumps({"title": "Cloudflare Guide EN"}), encoding="utf-8"
    )

    localized = note_view_model(str(tmp_path), note, "en")

    assert localized.title == "Cloudflare Guide EN"
    assert localized.category == note.category
    assert localized.updated_date == note.updated_date


def test_note_view_model_keeps_the_source_title_without_a_translated_one(tmp_path):
    note = _make_note()
    render_dir = tmp_path / "tests-cloudflare"
    render_dir.mkdir(parents=True, exist_ok=True)
    (render_dir / "42.en.json").write_text(json.dumps({"title": None}), "utf-8")

    assert note_view_model(str(tmp_path), note, "en") is note
    assert note_view_model(str(tmp_path / "missing"), note, "en") is note
