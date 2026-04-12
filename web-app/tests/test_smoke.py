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
    assert "START HERE" not in html
    assert "About" in html
    assert "About Me" not in html
    assert "Current Focus" in html
    assert "CURRENT FOCUS" not in html
    assert "Why This Site Exists" in html
    assert "WHY THIS SITE EXISTS" not in html
    assert "Explore the site" not in html
    assert "Open Articles" not in html
    assert "earth online 的一名NPC" not in html
    assert "原神玩家" not in html


def test_homepage_renders_chinese_landing_content(client):
    response = client.get("/zh/")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Build, Learn, Document." in html
    assert "PERSONAL SITE / KNOWLEDGE BASE" in html
    assert "Read Articles" in html
    assert "这里记录我的工程实践、技术笔记，以及正在持续推进的项目。" in html
    assert (
        "我主要关注 Cloud、DevOps、Full-stack、Python 和 AI-assisted workflow。" in html
    )
    assert "START HERE" not in html
    assert "What you&#39;ll find here" in html
    assert "Articles" in html
    assert "About" in html
    assert (
        "技术笔记、部署记录、实践文章，以及围绕 Cloud / DevOps / Full-stack 的持续整理。"
        in html
    )
    assert "更完整的个人介绍、当前关注、工作方式，以及与求职相关的信息。" in html
    assert "Current Focus" in html
    assert "CURRENT FOCUS" not in html
    assert "围绕 Terraform、GCP、Cloudflare 和 deployment workflow 持续实践。" in html
    assert "Why This Site Exists" in html
    assert "WHY THIS SITE EXISTS" not in html
    assert (
        "这个网站既是我的技术知识库，也是我整理项目、验证理解和持续输出的地方。" in html
    )
    assert (
        "我希望它是一份长期可维护、可复用、可迭代的工程记录，而不只是零散文章的集合。"
        in html
    )


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
