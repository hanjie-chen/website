from datetime import date
from pathlib import Path

import app as app_module
from models import Article_Meta_Data, db


def _insert_article():
    # Create one deterministic article row for route tests.
    article = Article_Meta_Data(
        title="Test Article",
        author="tester",
        instructor="mentor",
        cover_image_url="/rendered-articles/test/images/cover.png",
        rollout_date=date.today(),
        ultimate_modified_date=date.today(),
        brief_introduction="test intro",
        category="tests/category",
        file_path="tests/category/test-article.md",
        content_hash="a" * 64,
    )
    db.session.add(article)
    db.session.commit()
    return article


def test_articles_index_returns_200(client):
    # Route should render article list page even when list is empty.
    response = client.get("/articles")
    assert response.status_code == 200


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
        (html_dir / f"{article.id}.html").write_text("<h1>Test Content</h1>", encoding="utf-8")
        article_id = article.id

    response = client.get(f"/articles/{article_id}")
    assert response.status_code == 200
    assert "Test Content" in response.get_data(as_text=True)
