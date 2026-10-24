from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from i18n import SUPPORTED_LANGUAGES, public_path


@dataclass
class CategoryNode:
    """A knowledge base folder. Its path is the category; names show as on disk."""

    path: str
    segment: str
    children: list[CategoryNode] = field(default_factory=list)
    notes: list = field(default_factory=list)
    note_count: int = 0


def split_category_path(category_path: str) -> list[str]:
    if not category_path:
        return []
    return [segment for segment in category_path.split("/") if segment]


def _require_canonical_language(lang: str) -> str:
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Expected canonical language in {SUPPORTED_LANGUAGES}, got {lang!r}"
        )

    return lang


def build_breadcrumbs(category_path: str, lang: str | None = None):
    """Link each level of category_path to its folder in the notes browser.

    Callers pass the path above the current page: its own title follows the trail.
    The knowledge base root is left to the top bar's Notes link.
    """
    lang = _require_canonical_language(lang)
    breadcrumbs = []
    walked_parts = []
    for part in split_category_path(category_path):
        walked_parts.append(part)
        breadcrumbs.append(
            {
                "label": part,
                "url": public_path(lang, f"notes/category/{'/'.join(walked_parts)}"),
            }
        )

    return breadcrumbs


def _recent_sort_key(note):
    # Most recently touched first; notes without history sink to the end.
    touched = note.updated_date or note.rollout_date or date.min
    return (-(touched.toordinal()), note.title.casefold())


def recent_notes(notes: Iterable, limit: int):
    return sorted(notes, key=_recent_sort_key)[:limit]


def build_category_tree(notes: Iterable):
    """Return the folder tree and a lookup of every folder by path.

    Folders and notes keep their order on disk, so numbered names stay in sequence.
    """
    root = {"path": "", "segment": "", "children": {}, "notes": []}

    for note in notes:
        current = root
        walked_parts = []
        for part in split_category_path(note.category):
            walked_parts.append(part)
            current = current["children"].setdefault(
                part,
                {
                    "path": "/".join(walked_parts),
                    "segment": part,
                    "children": {},
                    "notes": [],
                },
            )
        current["notes"].append(note)

    lookup: dict[str, CategoryNode] = {}

    def finalize(raw_node):
        node = CategoryNode(
            path=raw_node["path"],
            segment=raw_node["segment"],
            notes=sorted(raw_node["notes"], key=lambda note: note.file_path.casefold()),
            children=sorted(
                (finalize(child) for child in raw_node["children"].values()),
                key=lambda child: child.segment.casefold(),
            ),
        )
        node.note_count = len(node.notes) + sum(
            child.note_count for child in node.children
        )
        lookup[node.path] = node
        return node

    return finalize(root), lookup
