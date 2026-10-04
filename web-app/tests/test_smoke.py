import pytest


def test_root_redirects_to_canonical_language_homepage(client):
    # Smoke test: app is up and root route redirects to the preferred language home.
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/zh/"


@pytest.mark.parametrize(
    ("path", "heading"), [("/zh/", "每日简报"), ("/en/", "Daily Brief")]
)
def test_homepage_renders_daily_brief_module(client, path, heading):
    response = client.get(path)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert f'<h2 id="home-brief-heading">{heading}</h2>' in html


def test_homepage_static_assets_are_versioned(client):
    response = client.get("/zh/")
    html = response.get_data(as_text=True)

    assert "/static/css/style.css?v=" in html
    assert "/static/css/base.css?v=" in html
    assert "/static/site-nav.js?v=" in html
    assert "bootstrap" not in html.lower()


def test_about_page_renders_english_hiring_profile_content(client):
    response = client.get("/en/about")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "about-hero-name-primary" in html
    assert "Hanjie Chen" in html
    assert "Download Resume" in html
    assert "Coming Soon" in html
    assert "Codex" in html
    assert "Why I Write" in html
    assert "Who I Am" in html
    assert "How I Work" in html
    assert "github.com/hanjie-chen" in html
    assert "Personal Website as a Production-style System" in html
    assert "github.com/hanjie-chen/website" in html
    assert "我是谁" not in html
    assert "我如何工作" not in html


def test_about_page_renders_chinese_hiring_profile_content(client):
    response = client.get("/zh/about")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "about-hero-name-primary" in html
    assert "Hanjie Chen" in html
    assert "PROFILE / HIRING PAGE" in html
    assert "Download Resume" in html
    assert "Coming Soon" in html
    assert "Contact Me" in html
    assert "Open to opportunities" in html
    assert "Shanghai CN / Remote-friendly" in html
    assert "为什么写博客" in html
    assert "我是谁" in html
    assert "我如何工作" in html
    assert "下载简历" not in html
