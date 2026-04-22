from datetime import date
import json

from article_views import article_html_path, article_view_model
from models import Article_Meta_Data


def _make_article():
    return Article_Meta_Data(
        id=42,
        title="Cloudflare 指南",
        author="陈翰杰",
        instructor="mentor",
        cover_image_url="/rendered-articles/tests-cloudflare/resources/images/cover.png",
        rollout_date=date(2026, 4, 22),
        ultimate_modified_date=date(2026, 4, 22),
        brief_introduction="中文简介",
        category="tests/cloudflare",
        file_path="tests/cloudflare/guide.md",
        content_hash="a" * 64,
    )


def test_article_html_path_prefers_english_render_when_present(tmp_path):
    article = _make_article()
    render_dir = tmp_path / "tests-cloudflare"
    render_dir.mkdir(parents=True, exist_ok=True)
    (render_dir / "42.en.html").write_text("<h1>English</h1>", encoding="utf-8")
    (render_dir / "42.html").write_text("<h1>Chinese</h1>", encoding="utf-8")

    actual = article_html_path(str(tmp_path), article, "en")

    assert actual == str(render_dir / "42.en.html")


def test_article_view_model_uses_english_sidecar_fields_when_available(tmp_path):
    article = _make_article()
    render_dir = tmp_path / "tests-cloudflare"
    render_dir.mkdir(parents=True, exist_ok=True)
    (render_dir / "42.en.json").write_text(
        json.dumps(
            {
                "title": "Cloudflare Guide EN",
                "brief_introduction": "English intro",
                "author": "Hanjie Chen",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    localized = article_view_model(str(tmp_path), article, "en")

    assert localized.title == "Cloudflare Guide EN"
    assert localized.brief_introduction == "English intro"
    assert localized.author == "Hanjie Chen"
    assert localized.category == article.category


def test_article_view_model_falls_back_to_canonical_article_when_sidecar_missing(
    tmp_path,
):
    article = _make_article()

    localized = article_view_model(str(tmp_path), article, "en")

    assert localized is article
