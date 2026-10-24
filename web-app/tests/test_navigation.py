from datetime import date
from types import SimpleNamespace

import pytest

from navigation import build_breadcrumbs, build_category_tree, recent_notes

TEST_DATE = date(2026, 1, 1)


def _note(category, title, updated_date=TEST_DATE, file_name=None):
    return SimpleNamespace(
        id=1,
        title=title,
        rollout_date=None,
        updated_date=updated_date,
        category=category,
        file_path=f"{category}/{file_name or title}.md",
    )


def test_recent_notes_put_the_latest_update_first_and_undated_notes_last():
    notes = [
        _note("tools/git", "Older", updated_date=date(2026, 1, 1)),
        _note("tools/git", "Undated", updated_date=None),
        _note("cloud-infra/terraform", "Newer", updated_date=date(2026, 2, 1)),
    ]

    assert [note.title for note in recent_notes(notes, limit=2)] == ["Newer", "Older"]


def test_category_tree_keeps_folders_and_notes_in_their_order_on_disk():
    nav_root, lookup = build_category_tree(
        [
            _note("devops/docker-learn/02-containers", "Docker command"),
            _note("devops/docker-learn/01-fundamentals", "Docker Basic"),
            _note("devops/k8s", "Zeta", file_name="a-first"),
            _note("devops/k8s", "Alpha", file_name="b-second"),
            _note("Ai", "Agents"),
        ]
    )

    assert [node.segment for node in nav_root.children] == ["Ai", "devops"]
    assert [node.segment for node in lookup["devops/docker-learn"].children] == [
        "01-fundamentals",
        "02-containers",
    ]
    # Notes follow their file names, not their titles.
    assert [note.title for note in lookup["devops/k8s"].notes] == ["Zeta", "Alpha"]
    assert lookup["devops"].note_count == 4
    assert lookup[""] is nav_root


def test_note_breadcrumbs_link_every_folder_above_the_note_by_its_name():
    note = _note("cloud-infra/terraform", "Terraform Intro")

    assert build_breadcrumbs(note.category, lang="en") == [
        {"label": "cloud-infra", "url": "/en/notes/category/cloud-infra"},
        {"label": "terraform", "url": "/en/notes/category/cloud-infra/terraform"},
    ]


@pytest.mark.parametrize("lang", ["", "en-US", "fr", " zh "])
def test_breadcrumbs_reject_non_canonical_languages(lang):
    with pytest.raises(ValueError):
        build_breadcrumbs("cloud-infra", lang=lang)
