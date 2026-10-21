from __future__ import annotations

import os
import re
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

from custom_md_extensions.note_link_extension import NOTE_LINK_PREFIX

# The title is the note's single `#` heading and leaves the body, so the body's
# outline starts at `##`. Those levels show as 1-3 in the table of contents.
TOC_HEADINGS = ("h2", "h3", "h4")


def _slugify_heading(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug, flags=re.UNICODE)
    return slug or "section"


def build_note_toc(note_content: str):
    """Add stable heading ids and return a shallow TOC tree for note pages."""
    soup = BeautifulSoup(note_content, "html.parser")
    toc_items = []
    slug_counts = {}
    current_top = None
    current_middle = None

    for heading in soup.find_all(TOC_HEADINGS):
        heading_text = heading.get_text(" ", strip=True)
        if not heading_text:
            continue

        base_slug = _slugify_heading(heading_text)
        slug_counts[base_slug] = slug_counts.get(base_slug, 0) + 1
        heading_id = (
            base_slug
            if slug_counts[base_slug] == 1
            else f"{base_slug}-{slug_counts[base_slug]}"
        )

        heading["id"] = heading_id
        toc_item = {
            "id": heading_id,
            "text": heading_text,
            "level": TOC_HEADINGS.index(heading.name) + 1,
            "children": [],
        }

        if toc_item["level"] == 1:
            toc_items.append(toc_item)
            current_top = toc_item
            current_middle = None
        elif toc_item["level"] == 2:
            if current_top is not None:
                current_top["children"].append(toc_item)
            else:
                toc_items.append(toc_item)
            current_middle = toc_item
        else:
            if current_middle is not None:
                current_middle["children"].append(toc_item)
            elif current_top is not None:
                current_top["children"].append(toc_item)
            else:
                toc_items.append(toc_item)

    return str(soup), toc_items


def resolve_note_links(note_content: str, note_url_for_path) -> str:
    """Point links to other notes at their pages.

    note_url_for_path(path) returns the page URL of the note at that knowledge
    base path, or None. Links to notes that are gone keep their path and 404.
    """
    soup = BeautifulSoup(note_content, "html.parser")
    for link in soup.find_all("a", href=True):
        if not link["href"].startswith(NOTE_LINK_PREFIX):
            continue
        parts = urlsplit(link["href"])
        url = note_url_for_path(unquote(parts.path[len(NOTE_LINK_PREFIX) :]))
        if url:
            link["href"] = url + (f"#{parts.fragment}" if parts.fragment else "")
    return str(soup)


def note_render_dir(rendered_dir: str, note) -> str:
    return os.path.join(rendered_dir, note.category.replace(os.sep, "-"))


def note_html_path(rendered_dir: str, note) -> str:
    return os.path.join(note_render_dir(rendered_dir, note), f"{note.id}.html")
