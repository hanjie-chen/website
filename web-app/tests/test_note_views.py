from datetime import date

from models import Note
from note_views import note_html_path


def test_note_html_path_points_into_the_note_category_folder(tmp_path):
    note = Note(
        id=42,
        title="Cloudflare 指南",
        category="tests/cloudflare",
        file_path="tests/cloudflare/guide.md",
        rollout_date=date(2026, 4, 22),
        updated_date=date(2026, 4, 22),
        content_hash="a" * 64,
    )

    assert note_html_path(str(tmp_path), note) == str(
        tmp_path / "tests-cloudflare" / "42.html"
    )
