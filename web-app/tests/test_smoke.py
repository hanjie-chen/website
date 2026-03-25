def test_homepage_returns_200(client):
    # Smoke test: app is up and root route is reachable.
    response = client.get("/")
    assert response.status_code == 200


def test_homepage_renders_landing_content(client):
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Build, Learn, Document." in html
    assert "PERSONAL SITE / KNOWLEDGE BASE" in html
    assert "Read Articles" in html
    assert "What you'll find here" in html
    assert "Current Focus" in html
    assert "Why This Site Exists" in html
    assert "Explore the site" not in html
    assert "Open Articles" not in html
    assert "earth online 的一名NPC" not in html
    assert "原神玩家" not in html


def test_homepage_static_assets_are_versioned(client):
    response = client.get("/")
    html = response.get_data(as_text=True)

    assert "/static/css/style.css?v=" in html
    assert "/static/bootstrap5/js/bootstrap.bundle.min.js?v=" in html
    assert "/static/images/headavatar/head_avatar_problem.png?v=" in html


def test_about_page_renders_hiring_profile_content(client):
    response = client.get("/about")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "about-hero-name-primary" in html
    assert "Hanjie Chen" in html
    assert "Download Resume" in html
    assert "Coming Soon" in html
    assert "Codex" in html
    assert "Why I Write" in html
    assert "Who I Am" in html
    assert "我是谁" in html
    assert "How I Work" in html
    assert "我如何工作" in html
    assert "github.com/hanjie-chen" in html
    assert "Personal Website as a Production-style System" in html
    assert "github.com/hanjie-chen/website" in html
