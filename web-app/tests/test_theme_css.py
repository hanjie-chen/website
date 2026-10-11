import re
from pathlib import Path

CSS_DIR = Path(__file__).resolve().parents[1] / "static/css"

# theme.css owns the color tokens.
TOKEN_SOURCES = {"theme.css"}
COLOR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|hsl)a?\(")


def test_component_styles_use_theme_color_tokens():
    for stylesheet in CSS_DIR.rglob("*.css"):
        if stylesheet.name in TOKEN_SOURCES:
            continue
        lines = stylesheet.read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            # A mask's color only sets opacity, so it is not a theme color.
            if "mask-image" in line:
                continue
            location = f"{stylesheet.name}:{number}"
            assert not COLOR_LITERAL.search(line), f"{location}: {line.strip()}"


def test_pages_load_theme_tokens_first_and_render_theme_toggles(client):
    html = client.get("/zh/").get_data(as_text=True)

    theme_css = html.index("/static/css/theme.css?v=")
    assert theme_css < html.index("/static/css/base.css?v=")
    assert 'localStorage.getItem("theme")' in html
    # One toggle in the top bar, one in the mobile menu, both revealed by script.
    assert html.count("data-theme-toggle hidden") == 2
    assert 'data-label-light="切换到浅色模式"' in html
    assert "/static/theme-toggle.js?v=" in html


def test_theme_toggle_labels_follow_page_language(client):
    html = client.get("/en/").get_data(as_text=True)

    assert 'data-label-light="Switch to light mode"' in html
    assert 'data-label-dark="Switch to dark mode"' in html
