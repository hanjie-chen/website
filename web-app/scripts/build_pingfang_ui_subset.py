#!/usr/bin/env python3
"""
Build the PingFang SC UI subset character list from user-facing templates.

This script intentionally targets fixed UI copy first:
- navbar text
- section headings
- buttons
- labels inside templates

It does not try to cover dynamic article content. The full PingFang font remains
as a fallback for article titles, rendered Markdown, and other runtime text that
is not guaranteed to be present in the template source.
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
OUTPUT_FILE = ROOT / "static" / "font" / "PingFangSC" / "PingFang-SC-UI-subset.txt"

# Keep a small punctuation reserve so fixed UI copy can evolve without instantly
# falling back to the full font for common Chinese punctuation.
MANUAL_EXTRA_CHARS = "，。！？、；：（）《》“”‘’【】—·…「」『』"


def strip_template_syntax(raw_text: str) -> str:
    text = re.sub(r"{#.*?#}", "", raw_text, flags=re.DOTALL)
    text = re.sub(r"{%.*?%}", "", text, flags=re.DOTALL)
    text = re.sub(r"{{.*?}}", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    return text


def extract_subset_chars(text: str) -> set[str]:
    chars = set()
    for char in text:
        if char.isspace():
            continue
        if ord(char) > 127:
            chars.add(char)
    chars.update(MANUAL_EXTRA_CHARS)
    return chars


def main() -> None:
    collected_chars: set[str] = set()

    for template_path in sorted(TEMPLATES_DIR.glob("*.html")):
        raw_text = template_path.read_text(encoding="utf-8")
        collected_chars.update(extract_subset_chars(strip_template_syntax(raw_text)))

    OUTPUT_FILE.write_text("".join(sorted(collected_chars)), encoding="utf-8")
    print(
        f"Wrote {len(collected_chars)} unique UI subset chars to {OUTPUT_FILE.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
