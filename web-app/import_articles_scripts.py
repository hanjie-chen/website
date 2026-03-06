"""
Articles import pipeline:
1) Scan directories that contain images/assets to locate article folders.
2) Copy images/assets into rendered output folders.
3) Parse markdown, validate metadata, compute content hash.
4) Upsert DB records by file_path, render HTML on change.
5) Remove DB records and HTML for deleted source files.
"""

import os
import re
import frontmatter
import hashlib
import shutil
from datetime import date
from flask_sqlalchemy import SQLAlchemy
from config import Rendered_Articles, IS_DEV
from models import Article_Meta_Data
from markdown_render_scripts import render_markdown_to_html

# future considered: use pathlib.Path instead of os.path
# consider use python logging package to instead of print information

# regular expression pre-compile
brief_intro_pattern = re.compile(r"```.*?BriefIntroduction:\s*(.*?)```", re.DOTALL)


def _is_hidden_item(item_name: str):
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


def _parse_article(md_path: str):
    """
    validate a md file whether read to lanch on the webiste
    extract ymal-metadata, brief introduction, content_part which need to render
    if validate pass, return brief_intro_text, metadata, content_part, content_hash
    if validate failed, return None
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

    required_fields = ["Title", "Author", "CoverImage", "RolloutDate"]
    for field in required_fields:
        if not real_metadata.get(field):
            print(
                f"file {md_path} metadata {field} is empty, not ready to published, skipped"
            )
            return None

    return brief_intro_text, real_metadata, content_part, content_hash


def _article_category(rel_path: str):
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
                print(
                    f"Article {exist_check.category}/{exist_check.title} unchanged, skipped"
                )
                return

            # Hash unchanged but rendered HTML is missing (e.g. dev cleanup or manual deletion).
            # Re-render to keep DB state and filesystem output consistent.
            if render_markdown_to_html(
                content_part, exist_check.id, output_path, url_base_path
            ):
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

    if "images" in folders:
        assets_folder = "images"
    elif "assets" in folders:
        assets_folder = "assets"
    else:
        assets_folder = None

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
        for root, dirs, files in os.walk(Rendered_Articles, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))


def _sync_deleted_articles(db: SQLAlchemy, seen_file_paths: set):
    existing_articles = db.session.execute(db.select(Article_Meta_Data)).scalars().all()
    for article in existing_articles:
        if article.file_path not in seen_file_paths:
            category_path = article.category.replace(os.sep, "-")
            html_path = os.path.join(
                Rendered_Articles, category_path, f"{article.id}.html"
            )
            if os.path.exists(html_path):
                os.remove(html_path)
            db.session.delete(article)

            remaining_in_category = db.session.execute(
                db.select(Article_Meta_Data).where(
                    Article_Meta_Data.category == article.category
                )
            ).scalar()
            if not remaining_in_category:
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
