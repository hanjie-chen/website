from datetime import date
from types import SimpleNamespace

import pytest

from navigation import build_breadcrumbs, build_docs_context

TEST_DATE = date(2026, 1, 1)


def _note(category, title, updated_date=TEST_DATE):
    return SimpleNamespace(
        id=1,
        title=title,
        rollout_date=None,
        updated_date=updated_date,
        category=category,
    )


def test_recent_notes_put_the_latest_update_first_and_undated_notes_last():
    docs_context = build_docs_context(
        [
            _note("tools/git", "Older", updated_date=date(2026, 1, 1)),
            _note("tools/git", "Undated", updated_date=None),
            _note("cloud-infra/terraform", "Newer", updated_date=date(2026, 2, 1)),
        ],
        lang="en",
    )

    assert [note.title for note in docs_context["recent_notes"]] == [
        "Newer",
        "Older",
        "Undated",
    ]
    assert [node.path for node in docs_context["category_children"]] == [
        "cloud-infra",
        "tools",
    ]


def test_category_breadcrumbs_link_the_ancestors_with_language_prefixes():
    docs_context = build_docs_context(
        [
            _note("cloud-infra/terraform", "Terraform Intro"),
        ],
        current_category="cloud-infra/terraform",
        lang="en",
    )

    # The page title names the current category, so the trail stops above it.
    assert docs_context["breadcrumbs"] == [
        {"label": "Cloud Infra", "url": "/en/notes/category/cloud-infra"},
    ]


def test_top_level_category_has_no_breadcrumbs():
    docs_context = build_docs_context(
        [_note("cloud-infra/terraform", "Terraform Intro")],
        current_category="cloud-infra",
        lang="en",
    )

    assert docs_context["breadcrumbs"] == []


def test_note_breadcrumbs_link_every_category_above_the_note():
    note = _note("cloud-infra/terraform", "Terraform Intro")

    breadcrumbs = build_breadcrumbs(note.category, lang="en")

    assert breadcrumbs == [
        {"label": "Cloud Infra", "url": "/en/notes/category/cloud-infra"},
        {
            "label": "Terraform",
            "url": "/en/notes/category/cloud-infra/terraform",
        },
    ]


@pytest.mark.parametrize("lang", ["", "en-US", "fr", " zh "])
def test_navigation_helpers_reject_non_canonical_languages(lang):
    note = _note("cloud-infra/terraform", "Terraform Intro")

    with pytest.raises(ValueError):
        build_breadcrumbs("cloud-infra", lang=lang)

    with pytest.raises(ValueError):
        build_docs_context([note], current_category="cloud-infra", lang=lang)
