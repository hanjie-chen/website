def test_root_redirects_to_canonical_language_homepage(client):
    # Smoke test: app is up and root route redirects to the preferred language home.
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"] == "/zh/"


def test_homepage_renders_english_landing_content(client):
    response = client.get("/en/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Build, Learn, Document." in html
    assert "PERSONAL SITE / KNOWLEDGE BASE" in html
    assert "Read Articles" in html
    assert "What you&#39;ll find here" in html
    assert "Current Focus" in html
    assert "Why This Site Exists" in html
    assert "Explore the site" not in html
    assert "Open Articles" not in html
    assert "earth online 的一名NPC" not in html
    assert "原神玩家" not in html


def test_homepage_renders_chinese_landing_content(client):
    response = client.get("/zh/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "构建、学习、记录。" in html
    assert "个人网站 / 知识库" in html
    assert "阅读文章" in html
    assert "你可以在这里看到什么" in html


def test_homepage_static_assets_are_versioned(client):
    response = client.get("/zh/")
    html = response.get_data(as_text=True)

    assert "/static/css/style.css?v=" in html
    assert "/static/bootstrap5/js/bootstrap.bundle.min.js?v=" in html
    assert "/static/images/headavatar/head_avatar_problem.png?v=" in html


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
    assert "下载简历" in html
    assert "敬请期待" in html
    assert "为什么写博客" in html
    assert "我是谁" in html
    assert "我如何工作" in html
    assert "联系我" in html
    assert "Download Resume" not in html
