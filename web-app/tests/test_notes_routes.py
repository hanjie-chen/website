from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

import app as app_module
from models import Note, db
from note_views import folder_readme_path

TEST_DATE = date(2026, 1, 1)


def _insert_note(
    title="Test Note",
    category="tests/category",
    file_path="tests/category/test-note.md",
    rollout_date=TEST_DATE,
    updated_date=TEST_DATE,
):
    # Create one deterministic note row for route tests.
    note = Note(
        title=title,
        category=category,
        file_path=file_path,
        rollout_date=rollout_date,
        updated_date=updated_date,
        content_hash="a" * 64,
    )
    db.session.add(note)
    db.session.commit()
    return note


def _write_html(note, html_body):
    html_dir = Path(app_module.Rendered_Articles) / note.category.replace("/", "-")
    html_dir.mkdir(parents=True, exist_ok=True)
    (html_dir / f"{note.id}.html").write_text(html_body, encoding="utf-8")


def test_notes_index_returns_200(client):
    # Route should render note list page even when list is empty.
    response = client.get("/zh/notes")
    assert response.status_code == 200


def test_notes_root_lists_recently_edited_notes_with_their_folders(client, app):
    with app.app_context():
        _insert_note(title="Older", file_path="tests/category/older.md")
        _insert_note(
            title="Newer",
            category="tests/infra",
            file_path="tests/infra/newer.md",
            updated_date=date(2026, 2, 1),
        )

    response = client.get("/zh/notes")
    soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")

    assert response.status_code == 200
    assert soup.select_one("h1.notes-pane-title").get_text(strip=True) == "最近修改"
    rows = soup.select(".notes-rows-recent .notes-row")
    assert [row.select_one(".notes-row-name").get_text(strip=True) for row in rows] == [
        "Newer",
        "Older",
    ]
    assert rows[0].select_one(".notes-row-folder-path").get_text() == "tests/infra"
    # The root opens no folder: the sidebar shows only the top level.
    sidebar = soup.select_one(".notes-sidebar")
    assert sidebar.select_one('a[aria-current="page"]')["href"] == "/zh/notes"
    assert [link.get_text() for link in sidebar.select(".notes-tree a")] == ["tests"]


def test_notes_root_uses_english_labels(client):
    soup = BeautifulSoup(client.get("/en/notes").get_data(as_text=True), "html.parser")

    assert (
        soup.select_one("h1.notes-pane-title").get_text(strip=True) == "Recently Edited"
    )
    assert soup.select_one(".notes-tree-recent").get_text(strip=True) == "Recent"


def test_notes_index_uses_shared_english_topbar_and_marks_notes_active(client):
    response = client.get("/zh/notes")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    soup = BeautifulSoup(body, "html.parser")
    brand = soup.select_one("a.site-nav-brand")
    assert brand["href"] == "/zh/"
    assert brand.get_text(strip=True) == "hanjie site"
    for selector in (".site-nav-menu", "#site-nav-dropdown"):
        navigation = soup.select_one(selector)
        links = navigation.select("a.site-nav-link")
        assert [(link["href"], link.get_text(strip=True)) for link in links] == [
            ("/zh/notes", "Notes"),
            ("/zh/briefs", "Brief"),
            ("/zh/about", "About"),
        ]
        active_links = navigation.select("a.site-nav-link.is-active")
        assert len(active_links) == 1
        assert active_links[0]["href"] == "/zh/notes"
        assert active_links[0]["aria-current"] == "page"
    assert soup.select_one("#site-nav-toggle").get_text(strip=True) == "Notes"


def test_unprefixed_notes_index_route_returns_404(client):
    response = client.get("/notes")

    assert response.status_code == 404


def test_article_routes_are_gone(client, app):
    # Ids were reassigned when notes replaced articles, so old links are not redirected.
    with app.app_context():
        note = _insert_note()
        _write_html(note, "<p>Body</p>")

    for path in (
        "/zh/articles",
        f"/zh/articles/{note.id}",
        "/zh/articles/category/tests/category",
    ):
        assert client.get(path).status_code == 404


def test_note_category_returns_200(client, app):
    with app.app_context():
        _insert_note(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform-intro.md",
        )

    response = client.get("/zh/notes/category/tests/infra")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Terraform Intro" in body


def test_unprefixed_note_category_route_returns_404(client, app):
    with app.app_context():
        _insert_note(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform-intro.md",
        )

    response = client.get("/notes/category/tests/infra")

    assert response.status_code == 404


def test_folder_page_expands_its_path_and_lists_subfolders_then_notes(client, app):
    with app.app_context():
        _insert_note(
            title="Terraform Intro",
            category="tests/infra",
            file_path="tests/infra/terraform.md",
        )
        _insert_note(title="Loose Note", category="tests", file_path="tests/loose.md")
        _insert_note(
            title="Elsewhere",
            category="other/deep",
            file_path="other/deep/elsewhere.md",
        )

    response = client.get("/zh/notes/category/tests")
    soup = BeautifulSoup(response.get_data(as_text=True), "html.parser")

    assert response.status_code == 200
    assert soup.select_one("h1.notes-pane-title").get_text(strip=True) == "tests"
    current = soup.select_one('.notes-sidebar a[aria-current="page"]')
    assert current["href"] == "/zh/notes/category/tests"
    # Only the open folder expands; other folders keep their children hidden.
    tree_links = [link.get_text() for link in soup.select(".notes-tree a")]
    assert tree_links == ["other", "tests", "infra"]
    rows = soup.select(".notes-rows .notes-row")
    assert [row.select_one(".notes-row-name").get_text(strip=True) for row in rows] == [
        "infra",
        "Loose Note",
    ]
    assert "notes-row-folder" in rows[0]["class"]
    assert rows[0]["href"] == "/zh/notes/category/tests/infra"
    assert rows[0].select_one(".notes-row-meta").get_text(strip=True) == "1"


def test_nested_folder_page_links_its_ancestors(client, app):
    with app.app_context():
        _insert_note(
            title="Deep", category="tests/infra/deep", file_path="tests/infra/deep/a.md"
        )

    soup = BeautifulSoup(
        client.get("/zh/notes/category/tests/infra/deep").get_data(as_text=True),
        "html.parser",
    )

    assert [(a.get_text(), a["href"]) for a in soup.select(".notes-trail a")] == [
        ("tests", "/zh/notes/category/tests"),
        ("infra", "/zh/notes/category/tests/infra"),
    ]


def test_unknown_folder_returns_404(client, app):
    with app.app_context():
        _insert_note()

    assert client.get("/zh/notes/category/tests/missing").status_code == 404


def test_folder_page_opens_with_its_readme(client, app):
    with app.app_context():
        target_id = _insert_note(
            title="Target", file_path="tests/category/target.md"
        ).id
        readme = Path(
            folder_readme_path(app_module.Rendered_Articles, "tests/category")
        )
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(
            '<p>Why this folder exists. <a href="/notes/path/tests/category/target.md">Target</a></p>',
            encoding="utf-8",
        )

    soup = BeautifulSoup(
        client.get("/zh/notes/category/tests/category").get_data(as_text=True),
        "html.parser",
    )

    intro = soup.select_one(".notes-readme")
    assert "Why this folder exists." in intro.get_text()
    assert intro.a["href"] == f"/zh/notes/{target_id}"


def test_view_note_returns_404_for_missing_note(client):
    # Unknown note id should return 404.
    response = client.get("/zh/notes/999999")
    assert response.status_code == 404


def test_unprefixed_note_detail_route_returns_404(client, app):
    with app.app_context():
        note = _insert_note()
        _write_html(note, "<h2>Test Content</h2>")

    response = client.get(f"/notes/{note.id}")

    assert response.status_code == 404


def test_view_note_returns_200_for_existing_note(client, app):
    # /<lang>/notes/<id> requires both DB metadata and rendered HTML file.
    with app.app_context():
        note = _insert_note()
        _write_html(note, "<h2>Test Content</h2>")
        note_id = note.id

    response = client.get(f"/en/notes/{note_id}")
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Test Content" in body
    assert 'href="/en/notes/category/tests"' in body
    assert 'href="/en/notes/category/tests/category"' in body


def test_english_view_note_shows_the_note_as_written(client, app):
    # Notes have one language; /en/ only switches the interface.
    with app.app_context():
        note = _insert_note(title="中文标题", file_path="tests/category/guide.md")
        _write_html(note, "<p>中文内容</p>")
        note_id = note.id

    body = client.get(f"/en/notes/{note_id}").get_data(as_text=True)

    assert "<title>中文标题</title>" in body
    assert "中文内容" in body


def test_view_note_uses_chinese_shell_labels(client, app):
    with app.app_context():
        note = _insert_note(
            title="Chinese Shell Note",
            category="tests/chinese",
            file_path="tests/chinese/shell.md",
        )
        note.updated_date = date(2026, 2, 1)
        db.session.commit()
        _write_html(note, "<h2>中文内容</h2>")

    response = client.get(f"/zh/notes/{note.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "作者" not in body
    assert '发布 <time datetime="2026-01-01">' in body
    assert '更新 <time datetime="2026-02-01">' in body
    assert "本页目录" in body


def test_view_note_renders_nested_toc_markup(client, app):
    with app.app_context():
        note = _insert_note(
            title="Nested TOC Note",
            category="tests/nested",
            file_path="tests/nested/toc.md",
        )
        _write_html(note, "<h2>Intro</h2><h3>Setup</h3><h4>Git Add</h4>")

    response = client.get(f"/zh/notes/{note.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "data-article-toc" in body
    assert 'data-toc-id="intro"' in body
    assert 'data-toc-id="setup"' in body
    assert 'data-toc-id="git-add"' in body
    assert "article-toc-subtree" in body
    # Narrow screens get a folded copy that the scroll tracking leaves alone.
    soup = BeautifulSoup(body, "html.parser")
    disclosure = soup.select_one("details.article-toc-disclosure")
    assert disclosure.summary.get_text(strip=True) == "本页目录"
    assert disclosure.select_one('a[href="#git-add"]') is not None
    assert disclosure.select("[data-toc-node], [data-toc-link]") == []


def test_view_note_includes_image_preview_modal_and_script(client, app):
    with app.app_context():
        note = _insert_note(
            title="Image Preview Note",
            category="tests/images",
            file_path="tests/images/preview.md",
        )
        _write_html(
            note,
            '<p><img src="/rendered-articles/tests-images/resources/images/cover.png" alt="架构图"></p>',
        )

    response = client.get(f"/zh/notes/{note.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert (
        '<dialog class="image-preview" aria-label="图片预览" data-image-preview-modal>'
        in body
    )
    assert "data-image-preview-target" in body
    assert "/static/article-image-preview.js?v=" in body
    assert 'aria-label="关闭图片预览"' in body


def test_view_note_includes_katex_assets(client, app):
    with app.app_context():
        note = _insert_note(
            title="Math Note",
            category="tests/math",
            file_path="tests/math/note.md",
        )
        _write_html(
            note,
            '<p>尺寸：140cm <span class="arithmatex">\\(\\times\\)</span> 80cm</p>',
        )

    response = client.get(f"/zh/notes/{note.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "/static/vendor/katex/katex.min.css?v=" in body
    assert "/static/vendor/katex/katex.min.js?v=" in body
    assert "/static/vendor/katex/contrib/auto-render.min.js?v=" in body
    assert "/static/math-render.js?v=" in body


def test_view_note_leaves_category_browsing_to_breadcrumbs(client, app):
    with app.app_context():
        note = _insert_note(
            title="Primary Note",
            category="tests/shared",
            file_path="tests/shared/primary.md",
        )
        _insert_note(
            title="Sibling Note",
            category="tests/shared",
            file_path="tests/shared/sibling.md",
        )

        _write_html(note, "<h2>Primary Content</h2>")

    response = client.get(f"/zh/notes/{note.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "notes-tree" not in body
    assert "Sibling Note" not in body
    trail = BeautifulSoup(body, "html.parser").select_one("nav.docs-breadcrumb")
    assert [link["href"] for link in trail.select("a")][-1] == (
        "/zh/notes/category/tests/shared"
    )
    assert "Primary Note" not in trail.get_text()
    # Released and last updated on the same day: the date shows once.
    assert body.count('<time datetime="2026-01-01">') == 1
    assert "更新" not in body


def test_note_page_keeps_internal_links_in_same_language_namespace(client, app):
    with app.app_context():
        note = _insert_note(
            title="Language Scoped Note",
            category="tests/category",
            file_path="tests/category/language-scoped.md",
        )

        _write_html(note, "<h2>Scoped Content</h2>")

    response = client.get(f"/en/notes/{note.id}")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'href="/en/notes"' in body
    assert 'href="/en/notes/category/tests"' in body
    assert 'href="/en/notes/category/tests/category"' in body


def test_view_note_shows_only_the_dates_it_knows(client, app):
    with app.app_context():
        undated = _insert_note(
            title="Draft",
            file_path="tests/category/draft.md",
            rollout_date=None,
            updated_date=date(2026, 3, 4),
        )
        bare = _insert_note(
            title="No History",
            file_path="tests/category/bare.md",
            rollout_date=None,
            updated_date=None,
        )
        _write_html(undated, "<p>Draft body</p>")
        _write_html(bare, "<p>Bare body</p>")

    body = client.get(f"/zh/notes/{undated.id}").get_data(as_text=True)
    meta = BeautifulSoup(body, "html.parser").select_one(".article-meta")
    assert " ".join(meta.get_text().split()) == "更新 2026-03-04"

    body = client.get(f"/zh/notes/{bare.id}").get_data(as_text=True)
    assert BeautifulSoup(body, "html.parser").select_one(".article-meta") is None


def test_view_note_points_links_between_notes_at_their_pages(client, app):
    with app.app_context():
        source = _insert_note(title="SSH", file_path="tests/category/ssh.md")
        target = _insert_note(
            title="Server", category="tests/other", file_path="tests/other/server.md"
        )
        _write_html(
            source,
            '<p><a href="/notes/path/tests/other/server.md#setup">server</a>'
            ' <a href="/notes/path/tests/gone.md">gone</a></p>',
        )
        source_id, target_id = source.id, target.id

    body = client.get(f"/en/notes/{source_id}").get_data(as_text=True)
    links = {
        link.get_text(): link["href"]
        for link in BeautifulSoup(body, "html.parser").select(".article-body p a")
    }

    assert links["server"] == f"/en/notes/{target_id}#setup"
    # A link to a note that no longer exists keeps its path and 404s.
    assert links["gone"] == "/notes/path/tests/gone.md"
