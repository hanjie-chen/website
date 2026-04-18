"""
Articles import pipeline:
1) Scan directories that contain images/assets to locate article folders.
2) Copy images/assets into rendered output folders.
3) Parse markdown, validate metadata, compute content hash.
4) Upsert DB records by file_path, render HTML on change.
5) Remove DB records and HTML for deleted source files.
"""

import hashlib
import json
import os
import re
import shutil
from datetime import date

import frontmatter
from flask_sqlalchemy import SQLAlchemy

from config import Rendered_Articles, IS_DEV
from markdown_render_scripts import render_markdown_to_html
from models import Article_Meta_Data

# consider use python logging package to instead of print information

# regular expression pre-compile
brief_intro_pattern = re.compile(r"```.*?BriefIntroduction:\s*(.*?)```", re.DOTALL)
markdown_image_pattern = re.compile(r"!\[[^\]]*\]\([^)]+\)")
leading_markdown_images_pattern = re.compile(
    r"^\s*((?:!\[[^\]]*\]\([^)]+\)\s*(?:\n\s*)*)+)", re.DOTALL
)
ENGLISH_AUTHOR_MAP = {
    "陈翰杰": "Hanjie Chen",
}


def _is_hidden_item(item_name: str):
    # Ignore dotfiles/directories and internal placeholders such as "__template__".
    return item_name.startswith(".") or (
        item_name.startswith("__") and item_name.endswith("__")
    )


def divide_files_and_folders(path: str):
    """return the files and folders in a directory"""
    all_items = os.listdir(path)
    # ignore dotfiles and internal template folders like "__template__"
    files_and_folders = [item for item in all_items if not _is_hidden_item(item)]
    files = [
        file for file in files_and_folders if os.path.isfile(os.path.join(path, file))
    ]
    folders = [
        folder
        for folder in files_and_folders
        if os.path.isdir(os.path.join(path, folder))
    ]
    return files, folders


def find_article_assets_folder(path: str):
    """return the publishable assets folder for an article directory"""
    _files, folders = divide_files_and_folders(path)

    if "images" in folders:
        return "images"
    if "assets" in folders:
        return "assets"
    if "resources" in folders:
        _resource_files, resource_folders = divide_files_and_folders(
            os.path.join(path, "resources")
        )
        if "images" in resource_folders:
            return os.path.join("resources", "images")

    return None


def get_dst_path(current_dir: str, root_dir: str):
    """get the path of rendered file"""
    relative_path = os.path.relpath(current_dir, root_dir)
    destination_path = os.path.join(
        Rendered_Articles, relative_path.replace(os.sep, "-")
    )
    return destination_path


def _read_markdown(md_path: str):
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {md_path}: {e}. Skipped.")
        return None, None

    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return content, content_hash


def _parse_markdown_document(md_path: str, required_fields: list[str]):
    """
    validate a markdown file and extract metadata, brief introduction and body
    """
    single_article, content_hash = _read_markdown(md_path)
    if not single_article:
        return None

    divided_article = single_article.split("<!-- split -->", 1)
    if len(divided_article) != 2:
        print(
            f"file: {md_path} lacks <!-- split -->, not ready to be published, skipped"
        )
        return None

    metadata_part = divided_article[0]
    content_part = divided_article[1]

    post = frontmatter.loads(metadata_part)
    real_metadata = post.metadata
    brief_intro = post.content

    brief_intro_match = brief_intro_pattern.search(brief_intro)
    if not brief_intro_match:
        print(
            f"file {md_path} lack brief introduciton, not ready to published, skipped"
        )
        return None
    brief_intro_text = brief_intro_match.group(1).strip()

    for field in required_fields:
        if not real_metadata.get(field):
            print(
                f"file {md_path} metadata {field} is empty, not ready to published, skipped"
            )
            return None

    return brief_intro_text, real_metadata, content_part, content_hash


def _parse_article(md_path: str):
    return _parse_markdown_document(
        md_path, required_fields=["Title", "Author", "CoverImage", "RolloutDate"]
    )


def _parse_translation_sidecar(md_path: str):
    return _parse_markdown_document(md_path, required_fields=["Title"])


def find_translation_sidecar(
    current_dir: str, md_filename: str, lang: str = "en"
) -> str | None:
    basename, _ext = os.path.splitext(md_filename)
    translation_path = os.path.join(
        current_dir, "resources", "i18n", f"{basename}-{lang}.md"
    )
    if os.path.exists(translation_path):
        return translation_path
    return None


def _translation_author(source_author: str, translation_metadata: dict):
    return translation_metadata.get("Author") or ENGLISH_AUTHOR_MAP.get(
        source_author, source_author
    )


def _prepend_leading_source_images(
    translation_content: str, source_content: str
) -> str:
    """Keep the English sidecar lightweight by inheriting the source lead image.

    Sidecars are allowed to omit repeated resource markdown. When the English
    body has no markdown images of its own, preserve the source article's
    leading image block so the bilingual article pages keep the same cover/hero
    image.
    """
    if markdown_image_pattern.search(translation_content):
        return translation_content

    match = leading_markdown_images_pattern.match(source_content)
    if not match:
        return translation_content

    leading_images = match.group(1).strip()
    if not leading_images:
        return translation_content

    return f"{leading_images}\n\n{translation_content.lstrip()}"


def _remove_translation_artifacts(article_id: int, output_path: str, lang: str = "en"):
    artifact_paths = [
        os.path.join(output_path, f"{article_id}.{lang}.html"),
        os.path.join(output_path, f"{article_id}.{lang}.json"),
    ]
    for artifact_path in artifact_paths:
        if os.path.exists(artifact_path):
            os.remove(artifact_path)


def _sync_translation_sidecar(
    md_filename: str,
    current_dir: str,
    output_path: str,
    url_base_path: str,
    article_id: int,
    source_author: str,
    source_content_part: str,
):
    translation_path = find_translation_sidecar(current_dir, md_filename, lang="en")
    if not translation_path:
        _remove_translation_artifacts(article_id, output_path, lang="en")
        return

    parsed = _parse_translation_sidecar(translation_path)
    if not parsed:
        _remove_translation_artifacts(article_id, output_path, lang="en")
        return

    brief_intro_text, metadata, content_part, content_hash = parsed
    content_part = _prepend_leading_source_images(content_part, source_content_part)
    if not render_markdown_to_html(
        content_part, f"{article_id}.en", output_path, url_base_path
    ):
        print(f"English sidecar render failed for {translation_path}")
        _remove_translation_artifacts(article_id, output_path, lang="en")
        return

    payload = {
        "lang": "en",
        "title": metadata.get("Title"),
        "brief_introduction": brief_intro_text,
        "author": _translation_author(source_author, metadata),
        "source_blob": metadata.get("SourceBlob"),
        "content_hash": content_hash,
    }

    meta_path = os.path.join(output_path, f"{article_id}.en.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)


def _article_category(rel_path: str):
    # Categories are derived from the markdown path relative to the repo root.
    return os.path.split(rel_path)[0]


def _article_cover_url(category_path: str, metadata: dict):
    raw_image_path = metadata.get("CoverImage")
    normalized_category = category_path.replace(os.sep, "-")
    return f"/rendered-articles/{normalized_category}/{raw_image_path.lstrip('./')}"


def _article_url_base(category_path: str):
    return f"/rendered-articles/{category_path}/"


def process_article(md_filename: str, current_dir: str, root_dir: str, db: SQLAlchemy):
    """deal with single .md file"""

    output_path = get_dst_path(current_dir, root_dir)
    md_path = os.path.join(current_dir, md_filename)

    parsed = _parse_article(md_path)
    if not parsed:
        return
    brief_intro_text, metadata, content_part, content_hash = parsed
    print(f"file {md_path} pass validate, ready to launch")

    file_stat = os.stat(md_path)
    file_last_modified_time = date.fromtimestamp(file_stat.st_mtime)

    rel_path = os.path.relpath(md_path, root_dir)
    article_category = _article_category(rel_path)
    cover_image_url = _article_cover_url(article_category, metadata)
    url_base_path = _article_url_base(article_category.replace(os.sep, "-"))

    exist_check = db.session.execute(
        db.select(Article_Meta_Data).where(Article_Meta_Data.file_path == rel_path)
    ).scalar()

    if exist_check:
        if exist_check.content_hash == content_hash:
            html_output_file = os.path.join(output_path, f"{exist_check.id}.html")
            if os.path.exists(html_output_file):
                _sync_translation_sidecar(
                    md_filename,
                    current_dir,
                    output_path,
                    url_base_path,
                    exist_check.id,
                    exist_check.author,
                    content_part,
                )
                print(
                    f"Article {exist_check.category}/{exist_check.title} unchanged, skipped"
                )
                return

            # Keep the rendered directory self-healing: if HTML was deleted manually
            # or by a dev cleanup, regenerate it without touching DB metadata.
            if render_markdown_to_html(
                content_part, exist_check.id, output_path, url_base_path
            ):
                _sync_translation_sidecar(
                    md_filename,
                    current_dir,
                    output_path,
                    url_base_path,
                    exist_check.id,
                    exist_check.author,
                    content_part,
                )
                print(
                    f"Article {exist_check.category}/{exist_check.title} unchanged but html missing, re-rendered"
                )
            else:
                print(
                    f"Article {exist_check.category}/{exist_check.title} unchanged but html missing, render failed"
                )
            return

        try:
            with db.session.begin_nested():
                exist_check.title = metadata.get("Title")
                exist_check.author = metadata.get("Author")
                exist_check.instructor = metadata.get("Instructor", "nobody")
                exist_check.rollout_date = metadata.get("RolloutDate")
                exist_check.cover_image_url = cover_image_url
                exist_check.category = article_category
                exist_check.ultimate_modified_date = file_last_modified_time
                exist_check.brief_introduction = brief_intro_text
                exist_check.content_hash = content_hash

                html_filename = exist_check.id
                if not render_markdown_to_html(
                    content_part, html_filename, output_path, url_base_path
                ):
                    raise RuntimeError("render failed")
                _sync_translation_sidecar(
                    md_filename,
                    current_dir,
                    output_path,
                    url_base_path,
                    exist_check.id,
                    exist_check.author,
                    content_part,
                )
            print(f"Article {exist_check.category}/{exist_check.title} updated")
        except Exception as e:
            print(f"Update failed for {exist_check.category}/{exist_check.title}: {e}")
        return

    article_metadata = Article_Meta_Data(
        title=metadata.get("Title"),
        author=metadata.get("Author"),
        instructor=metadata.get("Instructor", "nobody"),
        rollout_date=metadata.get("RolloutDate"),
        cover_image_url=cover_image_url,
        category=article_category,
        file_path=rel_path,
        content_hash=content_hash,
        ultimate_modified_date=file_last_modified_time,
        brief_introduction=brief_intro_text,
    )

    try:
        with db.session.begin_nested():
            db.session.add(article_metadata)
            db.session.flush()
            print(f"Article {article_metadata.category}/{article_metadata.title} added")

            html_filename = article_metadata.id
            if not render_markdown_to_html(
                content_part, html_filename, output_path, url_base_path
            ):
                raise RuntimeError("render failed")
            _sync_translation_sidecar(
                md_filename,
                current_dir,
                output_path,
                url_base_path,
                article_metadata.id,
                article_metadata.author,
                content_part,
            )
    except Exception as e:
        print(
            f"Add failed for {article_metadata.category}/{article_metadata.title}: {e}"
        )


def _copy_assets(current_dir: str, root_dir: str, assets_folder: str):
    destination_path = get_dst_path(current_dir, root_dir)
    os.makedirs(destination_path, exist_ok=True)

    source_assets_path = os.path.join(current_dir, assets_folder)
    destination_assets_path = os.path.join(destination_path, assets_folder)
    shutil.copytree(source_assets_path, destination_assets_path, dirs_exist_ok=True)
    print(
        f"copy images from {source_assets_path} to {destination_assets_path} successfully"
    )


def _scan_articles(
    current_dir: str, root_dir: str, db: SQLAlchemy, seen_file_paths: set
):
    files, folders = divide_files_and_folders(current_dir)

    # A directory only becomes a publishable article folder if it also owns
    # an assets directory. Root-level helper markdown files such as README.md
    # are therefore ignored unless they live in a real article folder.
    assets_folder = find_article_assets_folder(current_dir)

    if assets_folder:
        _copy_assets(current_dir, root_dir, assets_folder)
        for file in files:
            if file.endswith(".md"):
                rel_path = os.path.relpath(os.path.join(current_dir, file), root_dir)
                seen_file_paths.add(rel_path)
                process_article(file, current_dir, root_dir, db)
    else:
        for folder in folders:
            _scan_articles(
                os.path.join(current_dir, folder), root_dir, db, seen_file_paths
            )


def _cleanup_rendered_dir():
    if IS_DEV and os.path.exists(Rendered_Articles):
        # Dev mode rebuilds the rendered tree from scratch to avoid stale HTML
        # masking template or markdown changes during local iteration.
        for root, dirs, files in os.walk(Rendered_Articles, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))


def _sync_deleted_articles(db: SQLAlchemy, seen_file_paths: set):
    # The database is treated as a mirror of what the scanner saw this run.
    # Anything missing from seen_file_paths is considered deleted upstream.
    existing_articles = db.session.execute(db.select(Article_Meta_Data)).scalars().all()
    for article in existing_articles:
        if article.file_path not in seen_file_paths:
            category_path = article.category.replace(os.sep, "-")
            html_path = os.path.join(
                Rendered_Articles, category_path, f"{article.id}.html"
            )
            if os.path.exists(html_path):
                os.remove(html_path)
            _remove_translation_artifacts(
                article.id, os.path.join(Rendered_Articles, category_path), lang="en"
            )
            db.session.delete(article)

            remaining_in_category = db.session.execute(
                db.select(Article_Meta_Data).where(
                    Article_Meta_Data.category == article.category
                )
            ).scalar()
            if not remaining_in_category:
                # Remove the rendered category directory once its last article
                # disappears so the output tree stays tidy.
                category_dir = os.path.join(Rendered_Articles, category_path)
                if os.path.isdir(category_dir):
                    shutil.rmtree(category_dir)


def import_articles(root_dir: str, db: SQLAlchemy):
    """
    scan articles directory and copy images file
    and rendered md file to html file
    """
    seen_file_paths = set()
    _cleanup_rendered_dir()
    _scan_articles(root_dir, root_dir, db, seen_file_paths)
    _sync_deleted_articles(db, seen_file_paths)
    db.session.commit()
    print("All articles have been imported.")
