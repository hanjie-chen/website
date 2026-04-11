from datetime import date
from types import SimpleNamespace

import pytest

from navigation import (
    build_article_shell_context,
    build_breadcrumbs,
    build_docs_context,
    is_hidden_category_path,
)


def _article(category, title):
    return SimpleNamespace(
        id=1,
        title=title,
        author="tester",
        rollout_date=date.today(),
        ultimate_modified_date=date.today(),
        brief_introduction="intro",
        category=category,
    )


def test_is_hidden_category_path_detects_internal_templates():
    assert is_hidden_category_path("__template__") is True
    assert is_hidden_category_path("tools/__template__/drafts") is True
    assert is_hidden_category_path("cloud-infra/terraform") is False


def test_build_docs_context_filters_hidden_categories():
    docs_context = build_docs_context(
        [
            _article("__template__", "Template"),
            _article("cloud-infra/terraform", "Terraform Intro"),
        ],
        lang="en",
    )

    assert len(docs_context["category_children"]) == 1
    assert docs_context["category_children"][0].path == "cloud-infra"


def test_build_docs_context_prefixes_breadcrumb_urls_with_language():
    docs_context = build_docs_context(
        [
            _article("cloud-infra/terraform", "Terraform Intro"),
        ],
        current_category="cloud-infra/terraform",
        lang="en",
    )

    assert docs_context["breadcrumbs"] == [
        {"label": "Articles", "url": "/en/articles"},
        {"label": "Cloud Infra", "url": "/en/articles/category/cloud-infra"},
        {
            "label": "Terraform",
            "url": "/en/articles/category/cloud-infra/terraform",
        },
    ]


def test_build_article_shell_context_prefixes_breadcrumb_urls_with_language():
    article = _article("cloud-infra/terraform", "Terraform Intro")

    shell_context = build_article_shell_context([article], article, lang="en")

    assert shell_context["breadcrumbs"] == [
        {"label": "Articles", "url": "/en/articles"},
        {"label": "Cloud Infra", "url": "/en/articles/category/cloud-infra"},
        {
            "label": "Terraform",
            "url": "/en/articles/category/cloud-infra/terraform",
        },
        {"label": "Terraform Intro", "url": None},
    ]


@pytest.mark.parametrize("lang", ["", "en-US", "fr", " zh "])
def test_navigation_helpers_reject_non_canonical_languages(lang):
    article = _article("cloud-infra/terraform", "Terraform Intro")

    with pytest.raises(ValueError):
        build_breadcrumbs("cloud-infra", lang=lang)

    with pytest.raises(ValueError):
        build_docs_context([article], current_category="cloud-infra", lang=lang)

    with pytest.raises(ValueError):
        build_article_shell_context([article], article, lang=lang)
