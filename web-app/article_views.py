from __future__ import annotations

import json
import os
import re
from types import SimpleNamespace

from bs4 import BeautifulSoup


def _slugify_heading(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug, flags=re.UNICODE)
    return slug or "section"


def build_article_toc(article_content: str):
    """Add stable heading ids and return a shallow TOC tree for article pages."""
    soup = BeautifulSoup(article_content, "html.parser")
    toc_items = []
    slug_counts = {}
    current_h1 = None
    current_h2 = None

    for heading in soup.find_all(["h1", "h2", "h3"]):
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
            "level": int(heading.name[1]),
            "children": [],
        }

        if toc_item["level"] == 1:
            toc_items.append(toc_item)
            current_h1 = toc_item
            current_h2 = None
        elif toc_item["level"] == 2:
            if current_h1 is not None:
                current_h1["children"].append(toc_item)
            else:
                toc_items.append(toc_item)
            current_h2 = toc_item
        else:
            if current_h2 is not None:
                current_h2["children"].append(toc_item)
            elif current_h1 is not None:
                current_h1["children"].append(toc_item)
            else:
                toc_items.append(toc_item)

    return str(soup), toc_items


def article_render_dir(rendered_articles_dir: str, article) -> str:
    return os.path.join(rendered_articles_dir, article.category.replace(os.sep, "-"))


def article_html_path(rendered_articles_dir: str, article, lang: str) -> str:
    render_dir = article_render_dir(rendered_articles_dir, article)
    if lang == "en":
        localized_path = os.path.join(render_dir, f"{article.id}.en.html")
        if os.path.exists(localized_path):
            return localized_path
    return os.path.join(render_dir, f"{article.id}.html")


def article_translation_meta_path(rendered_articles_dir: str, article, lang: str):
    if lang != "en":
        return None
    return os.path.join(
        article_render_dir(rendered_articles_dir, article), f"{article.id}.en.json"
    )


def load_article_translation(rendered_articles_dir: str, article, lang: str):
    meta_path = article_translation_meta_path(rendered_articles_dir, article, lang)
    if not meta_path or not os.path.exists(meta_path):
        return None

    try:
        with open(meta_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def article_view_model(rendered_articles_dir: str, article, lang: str):
    """Overlay optional translated metadata on top of the canonical DB article row."""
    if lang != "en":
        return article

    translation = load_article_translation(rendered_articles_dir, article, lang)
    if not translation:
        return article

    return SimpleNamespace(
        id=article.id,
        title=translation.get("title") or article.title,
        author=translation.get("author") or article.author,
        instructor=article.instructor,
        cover_image_url=article.cover_image_url,
        rollout_date=article.rollout_date,
        ultimate_modified_date=article.ultimate_modified_date,
        brief_introduction=translation.get("brief_introduction")
        or article.brief_introduction,
        category=article.category,
        file_path=article.file_path,
        content_hash=article.content_hash,
    )


def localized_articles(rendered_articles_dir: str, articles, lang: str):
    return [
        article_view_model(rendered_articles_dir, article, lang) for article in articles
    ]
