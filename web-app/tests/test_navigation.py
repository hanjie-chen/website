from datetime import date
from types import SimpleNamespace

from navigation import build_docs_context, is_hidden_category_path


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
        ]
    )

    assert len(docs_context["category_children"]) == 1
    assert docs_context["category_children"][0].path == "cloud-infra"
