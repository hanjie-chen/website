from pathlib import Path

from markdown_render_scripts import render_markdown_to_html


def _render(markdown_content: str, tmp_path: Path) -> str:
    assert render_markdown_to_html(
        markdown_content=markdown_content,
        filename="article",
        destination_folder=str(tmp_path),
        url_base_path="/rendered-articles/test-category/",
    )

    return (tmp_path / "article.html").read_text(encoding="utf-8")


def test_github_style_emoji_shortcodes_render_to_unicode(tmp_path):
    html = _render(":x: :heavy_check_mark:", tmp_path)

    assert "❌" in html
    assert "✔️" in html
    assert ":x:" not in html
    assert ":heavy_check_mark:" not in html


def test_unknown_emoji_shortcode_is_left_as_plain_text(tmp_path):
    html = _render(":not_a_real_emoji:", tmp_path)

    assert ":not_a_real_emoji:" in html


def test_fenced_code_keeps_raw_emoji_shortcode_text(tmp_path):
    html = _render("```text\n:x:\n```", tmp_path)

    assert ":x:" in html
    assert "❌" not in html
