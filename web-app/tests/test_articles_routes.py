from datetime import date
from pathlib import Path

import app as app_module
from models import Article_Meta_Data, db


def _insert_article(
    title="Test Article",
    category="tests/category",
    file_path="tests/category/test-article.md",
):
    # Create one deterministic article row for route tests.
    article = Article_Meta_Data(
        title=title,
        author="tester",
        instructor="mentor",
        cover_image_url="/rendered-articles/test/images/cover.png",
        rollout_date=date.today(),
        ultimate_modified_date=date.today(),
        brief_introduction="test intro",
        category=category,
        file_path=file_path,
        content_hash="a" * 64,
    )
    db.session.add(article)
    db.session.commit()
    return article


def test_articles_index_returns_200(client):
    # Route should render article list page even when list is empty.
    response = client.get("/articles")
    assert response.status_code == 200
    assert "Top-Level Categories" in response.get_data(as_text=True)


def test_article_category_returns_200(client, app):
    with app.app_context():
        _insert_article(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform-intro.md",
        )

    response = client.get("/articles/category/tests/infra")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Terraform Intro" in body
    assert "Articles" in body


def test_parent_category_hides_empty_articles_section(client, app):
    with app.app_context():
        _insert_article(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform-intro.md",
        )

    response = client.get("/articles/category/tests")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Subcategories" in body
    assert "Infra" in body
    assert "Articles in This Section" not in body


def test_view_article_returns_404_for_missing_article(client):
    # Unknown article id should return 404.
    response = client.get("/articles/999999")
    assert response.status_code == 404


def test_view_article_returns_200_for_existing_article(client, app):
    # /articles/<id> requires both DB metadata and rendered HTML file.
    with app.app_context():
        article = _insert_article()
        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            "<h1>Test Content</h1>", encoding="utf-8"
        )
        article_id = article.id

    response = client.get(f"/articles/{article_id}")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Test Content" in body
    assert 'href="/articles/category/tests"' in body
    assert 'href="/articles/category/tests/category"' in body


def test_view_article_left_nav_lists_same_category_articles(client, app):
    with app.app_context():
        article = _insert_article(
            title="Primary Article",
            category="tests/shared",
            file_path="tests/shared/primary.md",
        )
        _insert_article(
            title="Sibling Article",
            category="tests/shared",
            file_path="tests/shared/sibling.md",
        )

        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            "<h1>Primary Content</h1>", encoding="utf-8"
        )

    response = client.get(f"/articles/{article.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Sibling Article" in body


def test_view_article_left_nav_highlights_only_current_article(client, app):
    with app.app_context():
        article = _insert_article(
            title="Primary Article",
            category="tests/shared",
            file_path="tests/shared/primary.md",
        )

        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            "<h1>Primary Content</h1>", encoding="utf-8"
        )

    response = client.get(f"/articles/{article.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert body.count("docs-tree-link is-active") == 0
    assert body.count("docs-tree-article-link is-active") == 1
