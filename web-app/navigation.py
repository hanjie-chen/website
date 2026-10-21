from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from i18n import SUPPORTED_LANGUAGES, public_path

SPECIAL_LABELS = {
    "api": "API",
    "ci": "CI",
    "cli": "CLI",
    "cd": "CD",
    "css": "CSS",
    "gcp": "GCP",
    "git": "Git",
    "html": "HTML",
    "http": "HTTP",
    "https": "HTTPS",
    "ip": "IP",
    "js": "JS",
    "json": "JSON",
    "llm": "LLM",
    "rdp": "RDP",
    "ssh": "SSH",
    "sql": "SQL",
    "terraform": "Terraform",
    "tls": "TLS",
    "toml": "TOML",
    "url": "URL",
    "vm": "VM",
    "vpn": "VPN",
    "vscode": "VSCode",
    "waf": "WAF",
    "yaml": "YAML",
}


@dataclass
class CategoryNode:
    path: str
    segment: str
    label: str
    depth: int
    children: list[CategoryNode] = field(default_factory=list)
    notes: list = field(default_factory=list)
    active: bool = False
    expanded: bool = False
    note_count: int = 0


def split_category_path(category_path: str) -> list[str]:
    if not category_path:
        return []
    return [segment for segment in category_path.split("/") if segment]


def humanize_segment(segment: str) -> str:
    words = []
    for raw_word in segment.replace("_", "-").split("-"):
        lower_word = raw_word.lower()
        if lower_word in SPECIAL_LABELS:
            words.append(SPECIAL_LABELS[lower_word])
        elif raw_word.isupper():
            words.append(raw_word)
        elif raw_word:
            words.append(raw_word.capitalize())
    return " ".join(words) or segment


def _require_canonical_language(lang: str) -> str:
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(
            f"Expected canonical language in {SUPPORTED_LANGUAGES}, got {lang!r}"
        )

    return lang


def build_breadcrumbs(category_path: str, lang: str | None = None):
    """Link each level of category_path.

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
                "label": humanize_segment(part),
                "url": public_path(lang, f"notes/category/{'/'.join(walked_parts)}"),
            }
        )

    return breadcrumbs


def _note_sort_key(note):
    # Most recently touched first; notes without history sink to the end.
    touched = note.updated_date or note.rollout_date or date.min
    return (-(touched.toordinal()), note.title.casefold())


def _category_sort_key(node: CategoryNode):
    return (node.label.casefold(), node.path)


def build_category_tree(notes: Iterable, current_category: str = ""):
    root = {
        "path": "",
        "segment": "",
        "label": "Notes",
        "depth": 0,
        "children": {},
        "notes": [],
    }

    for note in notes:
        current = root
        parts = split_category_path(note.category)
        walked_parts = []

        for depth, part in enumerate(parts, start=1):
            walked_parts.append(part)
            current = current["children"].setdefault(
                part,
                {
                    "path": "/".join(walked_parts),
                    "segment": part,
                    "label": humanize_segment(part),
                    "depth": depth,
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
            label=raw_node["label"],
            depth=raw_node["depth"],
            notes=sorted(raw_node["notes"], key=_note_sort_key),
        )

        is_current = node.path == current_category
        is_ancestor = bool(node.path and current_category.startswith(f"{node.path}/"))
        node.active = is_current
        node.expanded = node.path == "" or is_current or is_ancestor

        children = [finalize(child) for child in raw_node["children"].values()]
        node.children = sorted(children, key=_category_sort_key)
        node.note_count = len(node.notes) + sum(
            child.note_count for child in node.children
        )
        lookup[node.path] = node
        return node

    return finalize(root), lookup


def build_docs_context(
    notes: Iterable, current_category: str = "", lang: str | None = None
):
    lang = _require_canonical_language(lang)
    notes = list(notes)
    nav_root, lookup = build_category_tree(notes, current_category=current_category)
    current_node = lookup.get(current_category, nav_root)

    return {
        "current_lang": lang,
        "nav_root": nav_root,
        "current_node": current_node,
        "current_category": current_category,
        "current_category_label": current_node.label,
        "breadcrumbs": build_breadcrumbs(
            "/".join(split_category_path(current_category)[:-1]), lang=lang
        ),
        "category_children": current_node.children,
        "category_notes": current_node.notes,
        "recent_notes": sorted(notes, key=_note_sort_key)[:12],
    }
