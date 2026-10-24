"""
Notes import pipeline: every Markdown note in the knowledge base becomes a page.

1) Walk the tree, skipping hidden, template, resource and auxiliary files.
2) Copy each folder's image folders into the rendered tree.
3) Read the title, `RolloutDate` and body; render HTML when the source changed.
4) Take each note's updated date from git history.
5) Remove records and HTML for notes that disappeared upstream.
6) Render each folder's README, which opens the folder in the notes browser.
"""

import hashlib
import os
import re
import shutil
import subprocess
from datetime import date, datetime

import frontmatter
import yaml
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

from config import IS_DEV, Rendered_Articles
from markdown_render_scripts import RENDERER_VERSION, render_markdown_to_html
from models import Note
from note_views import FOLDER_README_HTML, folder_readme_path

# Folders that hold a note's images rather than notes, as the knowledge base
# README lays them out: `images/` for drafts, `resources/images/` otherwise.
NON_NOTE_FOLDERS = {"resources", "images"}
# Image folders copied next to the rendered HTML, relative to a note's folder.
ASSET_FOLDERS = ("images", os.path.join("resources", "images"))
# Repository and folder guides for people and agents, not notes.
AUXILIARY_FILES = {"README.md", "AGENTS.md", "CLAUDE.md"}
# A folder's README is what its owner says about the folder; it opens the folder
# in the notes browser. The root README is the repository guide and stays out.
FOLDER_README = "README.md"

TITLE_MAX_LENGTH = 255

fence_pattern = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
title_pattern = re.compile(r"^#\s+(.+?)\s*#*\s*$")


def _is_hidden_item(item_name: str):
    # Dotfiles and internal placeholders such as "__template__" never publish.
    return item_name.startswith(".") or (
        item_name.startswith("__") and item_name.endswith("__")
    )


def iter_note_folders(root_dir: str):
    """Yield (folder, note file names) for every folder that may hold notes."""
    for current_dir, folders, files in os.walk(root_dir):
        folders[:] = sorted(
            folder
            for folder in folders
            if not _is_hidden_item(folder) and folder not in NON_NOTE_FOLDERS
        )
        note_files = sorted(
            file
            for file in files
            if file.endswith(".md")
            and file not in AUXILIARY_FILES
            and not _is_hidden_item(file)
        )
        yield current_dir, note_files


def note_category(rel_path: str) -> str:
    # The path is the classification: a note's category is its folder.
    return os.path.dirname(rel_path)


def rendered_folder_name(category: str) -> str:
    return category.replace(os.sep, "-")


def get_dst_path(category: str) -> str:
    return os.path.join(Rendered_Articles, rendered_folder_name(category))


def _rendered_url_base(category: str) -> str:
    folder = rendered_folder_name(category)
    return f"/rendered-articles/{folder}/" if folder else "/rendered-articles/"


def split_title(body: str):
    """Return the first `# heading` outside code blocks and the body without it."""
    lines = body.splitlines(keepends=True)
    open_fence = None  # (character, length) of the code fence being read
    for index, line in enumerate(lines):
        fence = fence_pattern.match(line)
        if open_fence is None and fence:
            open_fence = (fence.group(1)[0], len(fence.group(1)))
            continue
        if open_fence is not None:
            # As in CommonMark, only a bare fence of the same character, at
            # least as long, closes the block, so shorter fences inside stay code.
            if (
                fence
                and fence.group(1)[0] == open_fence[0]
                and len(fence.group(1)) >= open_fence[1]
                and not fence.group(2).strip()
            ):
                open_fence = None
            continue
        match = title_pattern.match(line)
        if match:
            # Titles show as plain text, so inline code marks are dropped.
            title = " ".join(match.group(1).replace("`", "").split())
            return title, "".join(lines[:index] + lines[index + 1 :])
    return None, body


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def parse_note(md_path: str):
    """Read a note and return (title, rollout_date, body, content_hash).

    Returns None only when the file cannot be read as UTF-8 text.
    """
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeError) as e:
        print(f"Error reading file {md_path}: {e}. Skipped.")
        return None

    content_hash = hashlib.sha256(f"{RENDERER_VERSION}\n{content}".encode()).hexdigest()

    try:
        post = frontmatter.loads(content)
        metadata, body = post.metadata, post.content
    except (ValueError, yaml.YAMLError) as e:
        # Broken front matter must not hide the note: show it as written.
        print(f"Front matter of {md_path} could not be parsed: {e}")
        metadata, body = {}, content

    title, body = split_title(body)
    if not title:
        title = os.path.splitext(os.path.basename(md_path))[0]

    rollout_date = _as_date(metadata.get("RolloutDate"))
    return title[:TITLE_MAX_LENGTH], rollout_date, body, content_hash


def note_paths(root_dir: str) -> list[str]:
    """Relative paths of every readable note, as an import would see them."""
    paths = []
    for current_dir, note_files in iter_note_folders(root_dir):
        for file in note_files:
            md_path = os.path.join(current_dir, file)
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    f.read()
            except (OSError, UnicodeError):
                continue
            paths.append(os.path.relpath(md_path, root_dir))
    return paths


def git_updated_dates(root_dir: str) -> dict[str, date]:
    """Map each path to the date of the last commit that touched it.

    The log lists commits newest first, so the first date seen for a path is its
    latest. Without git or history every note simply has no updated date.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                "safe.directory=*",
                "-c",
                "core.quotePath=false",
                "-C",
                root_dir,
                "log",
                "--format=%x00%cs",
                "--name-only",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )
    except (OSError, subprocess.SubprocessError) as e:
        print(f"Git history unavailable for {root_dir}: {e}")
        return {}

    dates = {}
    current = None
    for line in result.stdout.splitlines():
        if line.startswith("\x00"):
            current = date.fromisoformat(line[1:])
        elif line and current and line not in dates:
            dates[line] = current
    return dates


def _render_note(note: Note, body: str) -> bool:
    return render_markdown_to_html(
        body,
        note.id,
        get_dst_path(note.category),
        _rendered_url_base(note.category),
        note.category,
    )


def process_note(
    md_filename: str,
    current_dir: str,
    root_dir: str,
    db: SQLAlchemy,
    updated_dates: dict[str, date],
):
    """Add, update or keep one note."""
    md_path = os.path.join(current_dir, md_filename)
    parsed = parse_note(md_path)
    if not parsed:
        return
    title, rollout_date, body, content_hash = parsed

    rel_path = os.path.relpath(md_path, root_dir)
    category = note_category(rel_path)
    updated_date = updated_dates.get(rel_path.replace(os.sep, "/"))

    note = db.session.execute(
        db.select(Note).where(Note.file_path == rel_path)
    ).scalar()

    if note and note.content_hash == content_hash:
        # History can move without the text changing (a rebuilt mirror, say).
        note.updated_date = updated_date
        html_path = os.path.join(get_dst_path(category), f"{note.id}.html")
        if os.path.exists(html_path):
            return
        # Keep the rendered tree self-healing when HTML went missing.
        if not _render_note(note, body):
            print(f"Note {rel_path} unchanged but html missing, render failed")
        return

    try:
        with db.session.begin_nested():
            if note is None:
                note = Note(file_path=rel_path)
                db.session.add(note)
            note.title = title
            note.category = category
            note.rollout_date = rollout_date
            note.updated_date = updated_date
            note.content_hash = content_hash
            db.session.flush()
            if not _render_note(note, body):
                raise RuntimeError("render failed")
        print(f"Note {rel_path} imported")
    except (OSError, UnicodeError, RuntimeError, SQLAlchemyError) as e:
        print(f"Import failed for {rel_path}: {e}")


def _copy_assets(current_dir: str, category: str):
    for assets_folder in ASSET_FOLDERS:
        source = os.path.join(current_dir, assets_folder)
        if os.path.isdir(source):
            destination = os.path.join(get_dst_path(category), assets_folder)
            shutil.copytree(source, destination, dirs_exist_ok=True)


def _cleanup_rendered_dir():
    if IS_DEV and os.path.exists(Rendered_Articles):
        # Dev mode rebuilds the rendered tree from scratch so stale HTML never
        # masks template or Markdown changes during local iteration.
        for root, dirs, files in os.walk(Rendered_Articles, topdown=False):
            for file in files:
                os.remove(os.path.join(root, file))
            for dir in dirs:
                os.rmdir(os.path.join(root, dir))


def _render_folder_readmes(root_dir: str):
    """Render every folder README below the root and drop ones that disappeared."""
    rendered = set()
    for current_dir, _note_files in iter_note_folders(root_dir):
        readme = os.path.join(current_dir, FOLDER_README)
        if current_dir == root_dir or not os.path.isfile(readme):
            continue
        try:
            with open(readme, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeError) as e:
            print(f"Error reading folder README {readme}: {e}. Skipped.")
            continue
        category = os.path.relpath(current_dir, root_dir)
        _copy_assets(current_dir, category)
        # The folder's name heads its page, so the README's own title leaves.
        _title, body = split_title(content)
        if render_markdown_to_html(
            body,
            os.path.splitext(FOLDER_README_HTML)[0],
            get_dst_path(category),
            _rendered_url_base(category),
            category,
        ):
            rendered.add(folder_readme_path(Rendered_Articles, category))

    for current, _dirs, files in os.walk(Rendered_Articles):
        if FOLDER_README_HTML in files:
            path = os.path.join(current, FOLDER_README_HTML)
            if path not in rendered:
                os.remove(path)


def _sync_deleted_notes(db: SQLAlchemy, seen_file_paths: set):
    # The database mirrors what this run saw: anything missing was deleted
    # upstream, or moved, which reads as a deletion plus a new note.
    for note in db.session.execute(db.select(Note)).scalars().all():
        if note.file_path in seen_file_paths:
            continue
        output_path = get_dst_path(note.category)
        html_path = os.path.join(output_path, f"{note.id}.html")
        if os.path.exists(html_path):
            os.remove(html_path)
        db.session.delete(note)
        db.session.flush()

        remaining = db.session.execute(
            db.select(Note).where(Note.category == note.category)
        ).scalar()
        if not remaining and note.category and os.path.isdir(output_path):
            # Drop the rendered folder with its last note to keep the tree tidy.
            shutil.rmtree(output_path)


def import_notes(root_dir: str, db: SQLAlchemy):
    """Import every note under root_dir and render it to HTML."""
    seen_file_paths = set()
    _cleanup_rendered_dir()
    updated_dates = git_updated_dates(root_dir)

    for current_dir, note_files in iter_note_folders(root_dir):
        if not note_files:
            continue
        category = note_category(
            os.path.relpath(os.path.join(current_dir, "_"), root_dir)
        )
        _copy_assets(current_dir, category)
        for file in note_files:
            seen_file_paths.add(
                os.path.relpath(os.path.join(current_dir, file), root_dir)
            )
            process_note(file, current_dir, root_dir, db, updated_dates)

    _sync_deleted_notes(db, seen_file_paths)
    _render_folder_readmes(root_dir)
    db.session.commit()
    print("All notes have been imported.")
