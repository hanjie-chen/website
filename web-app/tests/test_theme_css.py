import re
from pathlib import Path

CSS_DIR = Path(__file__).resolve().parents[1] / "static/css"

# theme.css owns the color tokens; Pygments colors are a generated theme.
TOKEN_SOURCES = {"theme.css", "pygment-style.css"}
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
