import os

import markdown
import pymdownx.emoji

from custom_md_extensions import Gfm_Admonition_Extension, Image_Processor_Extension


def render_markdown_to_html(
    markdown_content: str, filename: str, destination_folder: str, url_base_path: str
) -> bool:
    """generate html file to destination folder

    Args:
        markdown_content: The markdown string need to convert
        filename: The name for the output html file
        destination_folder: The folder path to save the rendered HTML
    """
    # use entry point to specified the extension I need
    my_articles_extensions = [
        "fenced_code",
        "footnotes",
        "tables",
        "md_in_html",
        "sane_lists",
        "codehilite",
        "pymdownx.emoji",
        "pymdownx.arithmatex",
        Gfm_Admonition_Extension(),
        Image_Processor_Extension(base_url=url_base_path),
    ]

    my_extension_configs = {
        "codehilite": {"linenums": True},
        "pymdownx.emoji": {
            "emoji_index": pymdownx.emoji.gemoji,
            "emoji_generator": pymdownx.emoji.to_alt,
            "alt": "unicode",
        },
        "pymdownx.arithmatex": {
            "generic": True,
            "tex_inline_wrap": ["\\(", "\\)"],
            "tex_block_wrap": ["\\[", "\\]"],
            "inline_syntax": ["dollar", "round"],
            "block_syntax": ["dollar", "square"],
        },
    }

    # Configure markdown converter with extensions
    md = markdown.Markdown(
        extensions=my_articles_extensions, extension_configs=my_extension_configs
    )

    # Convert markdown to HTML
    html_content = md.convert(markdown_content)

    # Only include necessary styles for markdown-specific elements
    html_template = f"""
    {html_content}
    """

    try:
        # Ensure destination folder exists and write the HTML file.
        os.makedirs(destination_folder, exist_ok=True)
        output_path = os.path.join(destination_folder, f"{filename}.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"Successfully rendered HTML to {destination_folder}")
        return True
    except (OSError, UnicodeError) as e:
        print(f"Error writing HTML file: {e}")
        return False
