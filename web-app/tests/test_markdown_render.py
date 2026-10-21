from pathlib import Path

from markdown_render_scripts import render_markdown_to_html


def _render(markdown_content: str, tmp_path: Path, note_dir: str = "") -> str:
    assert render_markdown_to_html(
        markdown_content=markdown_content,
        filename="note",
        destination_folder=str(tmp_path),
        url_base_path="/rendered-articles/test-category/",
        note_dir=note_dir,
    )

    return (tmp_path / "note.html").read_text(encoding="utf-8")


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


def test_fenced_code_highlights_only_labeled_languages(tmp_path):
    output = "Note: You didn't use the -out option, so Terraform can't guarantee"
    unlabeled = _render(f"```\n{output}\n```", tmp_path)
    labeled = _render("```python\ndef f():\n    return 'x'\n```", tmp_path)

    # Without a label the block is plain text, with no guessed token spans.
    assert f"<code>{output}\n</code>" in unlabeled
    assert '<span class="k">def</span>' in labeled
    # No line-number gutter in either case.
    assert "linenos" not in unlabeled + labeled


def test_links_to_other_notes_become_knowledge_base_paths(tmp_path):
    html = _render(
        "[server](./server-guide.md) [vm](../../azure/vm.md#size)"
        " [root](/tools/git/commands.md) [outside](../../../../x.md)"
        " [site](https://example.com/a.md) [section](#setup)",
        tmp_path,
        note_dir="devops/linux/ssh",
    )

    assert 'href="/notes/path/devops/linux/ssh/server-guide.md"' in html
    assert 'href="/notes/path/devops/azure/vm.md#size"' in html
    assert 'href="/notes/path/tools/git/commands.md"' in html
    assert 'href="../../../../x.md"' in html
    assert 'href="https://example.com/a.md"' in html
    assert 'href="#setup"' in html


def test_latex_delimiters_render_as_math_placeholders(tmp_path):
    html = _render(
        r"Inline dollar math: $\times$"
        "\n\n"
        r"Inline paren math: \(x^2\)"
        "\n\n"
        "$$\n"
        r"\sum_{i=1}^{n} i"
        "\n$$\n\n"
        r"\[\int_0^1 x\,dx\]",
        tmp_path,
    )

    assert '<span class="arithmatex">\\(\\times\\)</span>' in html
    assert '<span class="arithmatex">\\(x^2\\)</span>' in html
    assert '<div class="arithmatex">\\[' in html
    assert "\\sum_{i=1}^{n} i" in html
    assert "\\]</div>" in html
    assert '<div class="arithmatex">\\[\\int_0^1 x\\,dx\\]</div>' in html
