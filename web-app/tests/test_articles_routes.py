from datetime import date
import json
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


def _write_english_sidecar(article, html_body="<h1>English Content</h1>"):
    category_path = article.category.replace("/", "-")
    html_dir = Path(app_module.Rendered_Articles) / category_path
    html_dir.mkdir(parents=True, exist_ok=True)
    (html_dir / f"{article.id}.en.html").write_text(html_body, encoding="utf-8")
    (html_dir / f"{article.id}.en.json").write_text(
        json.dumps(
            {
                "lang": "en",
                "title": f"{article.title} EN",
                "brief_introduction": "English intro",
                "author": "Hanjie Chen",
                "source_blob": "abc123",
                "content_hash": "b" * 64,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_articles_index_returns_200(client):
    # Route should render article list page even when list is empty.
    response = client.get("/zh/articles")
    assert response.status_code == 200


def test_articles_index_uses_chinese_shell_labels(client):
    response = client.get("/zh/articles")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "浏览" in body
    assert "主要分类" in body
    assert "最新文章" in body


def test_articles_index_uses_shared_english_topbar_and_marks_articles_active(client):
    response = client.get("/zh/articles")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<a href="/zh/" class="site-nav-brand">hanjie site</a>' in body
    assert '<a class="nav-link site-nav-link" href="/zh/">Home</a>' in body
    assert (
        '<a class="nav-link site-nav-link is-active" href="/zh/articles">Articles</a>'
        in body
    )
    assert '<a class="nav-link site-nav-link" href="/zh/about">About</a>' in body
    assert body.count("site-nav-link is-active") == 1


def test_english_articles_index_uses_sidecar_title_and_brief(client, app):
    with app.app_context():
        article = _insert_article(
            title="Cloudflare 指南",
            category="tests/cloudflare",
            file_path="tests/cloudflare/guide.md",
        )
        _write_english_sidecar(article)

    response = client.get("/en/articles")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Cloudflare 指南 EN" in body
    assert "English intro" in body
    assert "Cloudflare 指南</h3>" not in body


def test_legacy_articles_index_route_returns_404(client):
    response = client.get("/articles")

    assert response.status_code == 404


def test_api_articles_returns_minimal_summary_fields(client, app):
    with app.app_context():
        first = _insert_article(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform-intro.md",
        )
        second = _insert_article(
            title="Ansible Ping",
            category="tests/ansible",
            file_path="tests/ansible/ping.md",
        )
        expected_items = [
            {
                "id": first.id,
                "title": "Terraform Intro",
                "category": "tests/infra",
                "brief": "test intro",
            },
            {
                "id": second.id,
                "title": "Ansible Ping",
                "category": "tests/ansible",
                "brief": "test intro",
            },
        ]

    response = client.get("/api/articles")

    assert response.status_code == 200
    actual_items = [
        item
        for item in response.get_json()["items"]
        if item["id"] in {first.id, second.id}
    ]
    assert actual_items == expected_items


def test_api_articles_keeps_chinese_text_readable(client, app):
    with app.app_context():
        _insert_article(
            title="docker volume 使用基础",
            category="tests/docker",
            file_path="tests/docker/volume.md",
        )

    response = client.get("/api/articles")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "docker volume 使用基础" in body
    assert "\\u4f7f\\u7528" not in body


def test_api_article_detail_returns_expanded_metadata_only(client, app):
    with app.app_context():
        article = _insert_article(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform-intro.md",
        )
        article_id = article.id
        expected_payload = {
            "id": article.id,
            "title": "Terraform Intro",
            "author": "tester",
            "instructor": "mentor",
            "category": "tests/infra",
            "brief": "test intro",
            "rollout_date": article.rollout_date.isoformat(),
            "ultimate_modified_date": article.ultimate_modified_date.isoformat(),
        }

    response = client.get(f"/api/articles/{article_id}")

    assert response.status_code == 200
    assert response.get_json() == expected_payload


def test_api_article_detail_returns_404_for_missing_article(client):
    response = client.get("/api/articles/999999")
    assert response.status_code == 404


def test_article_category_returns_200(client, app):
    with app.app_context():
        _insert_article(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform-intro.md",
        )

    response = client.get("/zh/articles/category/tests/infra")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Terraform Intro" in body


def test_legacy_article_category_route_returns_404(client, app):
    with app.app_context():
        _insert_article(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform-intro.md",
        )

    response = client.get("/articles/category/tests/infra")

    assert response.status_code == 404


def test_parent_category_hides_empty_articles_section(client, app):
    with app.app_context():
        _insert_article(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform-intro.md",
        )

    response = client.get("/zh/articles/category/tests")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "子分类" in body
    assert "Infra" in body
    assert "本节文章" not in body


def test_view_article_returns_404_for_missing_article(client):
    # Unknown article id should return 404.
    response = client.get("/zh/articles/999999")
    assert response.status_code == 404


def test_legacy_article_detail_route_returns_404(client, app):
    with app.app_context():
        article = _insert_article()
        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            "<h1>Test Content</h1>", encoding="utf-8"
        )

    response = client.get(f"/articles/{article.id}")

    assert response.status_code == 404


def test_view_article_returns_200_for_existing_article(client, app):
    # /<lang>/articles/<id> requires both DB metadata and rendered HTML file.
    with app.app_context():
        article = _insert_article()
        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            "<h1>Test Content</h1>", encoding="utf-8"
        )
        article_id = article.id

    response = client.get(f"/en/articles/{article_id}")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Test Content" in body
    assert 'href="/en/articles/category/tests"' in body
    assert 'href="/en/articles/category/tests/category"' in body


def test_english_view_article_uses_sidecar_title_author_and_body(client, app):
    with app.app_context():
        article = _insert_article(
            title="中文标题",
            category="tests/english",
            file_path="tests/english/guide.md",
        )
        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            "<h1>中文内容</h1>", encoding="utf-8"
        )
        _write_english_sidecar(article, html_body="<h1>English Sidecar Body</h1>")

    response = client.get(f"/en/articles/{article.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "<title>中文标题 EN</title>" in body
    assert "Hanjie Chen" in body
    assert "English Sidecar Body" in body
    assert "中文内容" not in body


def test_view_article_uses_chinese_shell_labels(client, app):
    with app.app_context():
        article = _insert_article(
            title="Chinese Shell Article",
            category="tests/chinese",
            file_path="tests/chinese/shell.md",
        )
        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            "<h1>中文内容</h1>", encoding="utf-8"
        )

    response = client.get(f"/zh/articles/{article.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "本节内容" in body
    assert "作者:" in body
    assert "发布:" in body
    assert "更新:" in body
    assert "本页目录" in body


def test_view_article_renders_nested_toc_markup(client, app):
    with app.app_context():
        article = _insert_article(
            title="Nested TOC Article",
            category="tests/nested",
            file_path="tests/nested/toc.md",
        )
        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            "<h1>Intro</h1><h2>Setup</h2><h3>Git Add</h3>",
            encoding="utf-8",
        )

    response = client.get(f"/zh/articles/{article.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "data-article-toc" in body
    assert 'data-toc-id="intro"' in body
    assert 'data-toc-id="setup"' in body
    assert 'data-toc-id="git-add"' in body
    assert "article-toc-subtree" in body


def test_view_article_includes_image_preview_modal_and_script(client, app):
    with app.app_context():
        article = _insert_article(
            title="Image Preview Article",
            category="tests/images",
            file_path="tests/images/preview.md",
        )
        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            '<p><img src="/rendered-articles/tests-images/resources/images/cover.png" alt="架构图"></p>',
            encoding="utf-8",
        )

    response = client.get(f"/zh/articles/{article.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "data-image-preview-modal" in body
    assert "data-image-preview-target" in body
    assert "/static/article-image-preview.js?v=" in body
    assert 'aria-label="关闭图片预览"' in body


def test_view_article_includes_katex_assets(client, app):
    with app.app_context():
        article = _insert_article(
            title="Math Article",
            category="tests/math",
            file_path="tests/math/article.md",
        )
        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            '<p>尺寸：140cm <span class="arithmatex">\\(\\times\\)</span> 80cm</p>',
            encoding="utf-8",
        )

    response = client.get(f"/zh/articles/{article.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "/static/vendor/katex/katex.min.css?v=" in body
    assert "/static/vendor/katex/katex.min.js?v=" in body
    assert "/static/vendor/katex/contrib/auto-render.min.js?v=" in body
    assert "/static/math-render.js?v=" in body


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

    response = client.get(f"/zh/articles/{article.id}")
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

    response = client.get(f"/zh/articles/{article.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert body.count("docs-tree-link is-active") == 0
    assert body.count("docs-tree-article-link is-active") == 1


def test_article_page_keeps_internal_links_in_same_language_namespace(client, app):
    with app.app_context():
        article = _insert_article(
            title="Language Scoped Article",
            category="tests/category",
            file_path="tests/category/language-scoped.md",
        )

        category_path = article.category.replace("/", "-")
        html_dir = Path(app_module.Rendered_Articles) / category_path
        html_dir.mkdir(parents=True, exist_ok=True)
        (html_dir / f"{article.id}.html").write_text(
            "<h1>Scoped Content</h1>", encoding="utf-8"
        )

    response = client.get(f"/en/articles/{article.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/en/articles"' in body
    assert 'href="/en/articles/category/tests"' in body
    assert 'href="/en/articles/category/tests/category"' in body
