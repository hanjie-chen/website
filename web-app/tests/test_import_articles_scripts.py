import json
from pathlib import Path

import app as app_module
from import_articles_scripts import (
    divide_files_and_folders,
    find_article_assets_folder,
    import_articles,
)
from models import Article_Meta_Data, db


def test_divide_files_and_folders_ignores_hidden_template_dirs(tmp_path):
    (tmp_path / "__template__").mkdir()
    (tmp_path / ".drafts").mkdir()
    (tmp_path / "public").mkdir()
    (tmp_path / "article.md").write_text("content", encoding="utf-8")

    files, folders = divide_files_and_folders(str(tmp_path))

    assert files == ["article.md"]
    assert folders == ["public"]


def test_find_article_assets_folder_supports_resources_images(tmp_path):
    article_dir = tmp_path / "cloudflare-guide"
    (article_dir / "resources" / "images").mkdir(parents=True)
    (article_dir / "guide.md").write_text("content", encoding="utf-8")

    assert find_article_assets_folder(str(article_dir)) == "resources/images"


def test_import_articles_writes_english_sidecar_artifacts_for_resources_i18n(
    app, tmp_path, monkeypatch
):
    root_dir = tmp_path / "tests"
    article_dir = root_dir / "cloud-infra" / "platforms" / "cloudflare"
    (article_dir / "resources" / "images").mkdir(parents=True)
    (article_dir / "resources" / "images" / "cf.jpg").write_text(
        "fake image", encoding="utf-8"
    )
    (article_dir / "resources" / "i18n").mkdir(parents=True)

    (article_dir / "enable-cdn.md").write_text(
        """---
Title: cloudflare 使用指南
Author: 陈翰杰
Instructor: gpt
CoverImage: ./resources/images/cf.jpg
RolloutDate: 2026-04-06
---

```
BriefIntroduction:
cf 使用指南
```

<!-- split -->

# enable cloudflare cdn

中文正文
""",
        encoding="utf-8",
    )
    (article_dir / "resources" / "i18n" / "enable-cdn-en.md").write_text(
        """---
Title: Cloudflare Guide
SourceBlob: abc123
---

```
BriefIntroduction: An English guide to enabling Cloudflare CDN.
```

<!-- split -->

# Enable Cloudflare CDN

English body
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "import_articles_scripts.Rendered_Articles",
        app_module.app.config["RENDERED_ARTICLES_FOLDER"],
    )
    monkeypatch.setattr(
        "app.Rendered_Articles", app_module.app.config["RENDERED_ARTICLES_FOLDER"]
    )

    with app.app_context():
        import_articles(str(root_dir), db)
        article = db.session.execute(
            db.select(Article_Meta_Data).where(
                Article_Meta_Data.file_path
                == "cloud-infra/platforms/cloudflare/enable-cdn.md"
            )
        ).scalar_one()

    rendered_dir = (
        Path(app_module.app.config["RENDERED_ARTICLES_FOLDER"])
        / "cloud-infra-platforms-cloudflare"
    )
    english_html = rendered_dir / f"{article.id}.en.html"
    english_meta = rendered_dir / f"{article.id}.en.json"

    assert english_html.exists()
    assert "English body" in english_html.read_text(encoding="utf-8")

    payload = json.loads(english_meta.read_text(encoding="utf-8"))
    assert payload == {
        "lang": "en",
        "title": "Cloudflare Guide",
        "brief_introduction": "An English guide to enabling Cloudflare CDN.",
        "author": "Hanjie Chen",
        "source_blob": "abc123",
        "content_hash": payload["content_hash"],
    }


def test_import_articles_english_sidecar_inherits_source_leading_image_when_missing(
    app, tmp_path, monkeypatch
):
    root_dir = tmp_path / "tests"
    article_dir = root_dir / "cloud-infra" / "platforms" / "gcp" / "terraform"
    (article_dir / "resources" / "images").mkdir(parents=True)
    (article_dir / "resources" / "images" / "tf-gcp-cover.avif").write_text(
        "fake image", encoding="utf-8"
    )
    (article_dir / "resources" / "i18n").mkdir(parents=True)

    (article_dir / "set-up.md").write_text(
        """---
Title: GCP Terraform 入门设置
Author: 陈翰杰
Instructor: gpt
CoverImage: ./resources/images/tf-gcp-cover.avif
RolloutDate: 2026-04-06
---

```
BriefIntroduction:
中文简介
```

<!-- split -->

![tf gcp cover](./resources/images/tf-gcp-cover.avif)

# GCP Terraform 入门设置

中文正文
""",
        encoding="utf-8",
    )
    (article_dir / "resources" / "i18n" / "set-up-en.md").write_text(
        """---
Title: Getting Started with GCP Terraform Setup
SourceBlob: abc123
---

```
BriefIntroduction: English intro
```

<!-- split -->

# Getting Started with GCP Terraform Setup

English body
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "import_articles_scripts.Rendered_Articles",
        app_module.app.config["RENDERED_ARTICLES_FOLDER"],
    )
    monkeypatch.setattr(
        "app.Rendered_Articles", app_module.app.config["RENDERED_ARTICLES_FOLDER"]
    )

    with app.app_context():
        import_articles(str(root_dir), db)
        article = db.session.execute(
            db.select(Article_Meta_Data).where(
                Article_Meta_Data.file_path
                == "cloud-infra/platforms/gcp/terraform/set-up.md"
            )
        ).scalar_one()

    rendered_dir = (
        Path(app_module.app.config["RENDERED_ARTICLES_FOLDER"])
        / "cloud-infra-platforms-gcp-terraform"
    )
    english_html = (rendered_dir / f"{article.id}.en.html").read_text(encoding="utf-8")

    assert (
        'src="/rendered-articles/cloud-infra-platforms-gcp-terraform/resources/images/tf-gcp-cover.avif"'
        in english_html
    )
    assert "<h1>Getting Started with GCP Terraform Setup</h1>" in english_html


def test_import_articles_english_sidecar_inherits_leading_html_image_when_missing(
    app, tmp_path, monkeypatch
):
    root_dir = tmp_path / "tests"
    article_dir = root_dir / "ai" / "coding-agents" / "practice"
    (article_dir / "resources" / "images").mkdir(parents=True)
    (article_dir / "resources" / "images" / "agents-readme.jpg").write_text(
        "fake image", encoding="utf-8"
    )
    (article_dir / "resources" / "i18n").mkdir(parents=True)

    (article_dir / "context-engineering.md").write_text(
        """---
Title: AGENTS.md & README.md 使用指南
Author: 陈翰杰
Instructor: GPT-5
CoverImage: ./resources/images/agents-readme.jpg
RolloutDate: 2026-03-29
---

```
BriefIntroduction:
一些关于 AI agent 辅助编程的个人经验
```

<!-- split -->

<img src="./resources/images/agents-readme.jpg" alt="cover" style="zoom: 67%;" />

# Understand the project

中文正文
""",
        encoding="utf-8",
    )
    (article_dir / "resources" / "i18n" / "context-engineering-en.md").write_text(
        """---
Title: A Guide to Using AGENTS.md and README.md
SourceBlob: abc123
---

```
BriefIntroduction: Some personal experience with AI agent-assisted programming
```

<!-- split -->

# Understand the project

English body
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "import_articles_scripts.Rendered_Articles",
        app_module.app.config["RENDERED_ARTICLES_FOLDER"],
    )
    monkeypatch.setattr(
        "app.Rendered_Articles", app_module.app.config["RENDERED_ARTICLES_FOLDER"]
    )

    with app.app_context():
        import_articles(str(root_dir), db)
        article = db.session.execute(
            db.select(Article_Meta_Data).where(
                Article_Meta_Data.file_path
                == "ai/coding-agents/practice/context-engineering.md"
            )
        ).scalar_one()

    rendered_dir = (
        Path(app_module.app.config["RENDERED_ARTICLES_FOLDER"])
        / "ai-coding-agents-practice"
    )
    english_html = (rendered_dir / f"{article.id}.en.html").read_text(encoding="utf-8")

    assert (
        'src="/rendered-articles/ai-coding-agents-practice/resources/images/agents-readme.jpg"'
        in english_html
    )
    assert "<h1>Understand the project</h1>" in english_html


def test_import_articles_english_sidecar_keeps_source_cover_when_body_has_later_images(
    app, tmp_path, monkeypatch
):
    root_dir = tmp_path / "tests"
    article_dir = root_dir / "devops" / "linux-learn" / "services" / "ssh"
    (article_dir / "resources" / "images").mkdir(parents=True)
    (article_dir / "resources" / "images" / "ssh.png").write_text(
        "fake image", encoding="utf-8"
    )
    (article_dir / "resources" / "images" / "gcp-vm-ssh-1.png").write_text(
        "fake image", encoding="utf-8"
    )
    (article_dir / "resources" / "i18n").mkdir(parents=True)

    (article_dir / "client-guide.md").write_text(
        """---
Title: SSh 客户端完全使用指南
Author: 陈翰杰
Instructor: gemini
CoverImage: ./resources/images/ssh.png
RolloutDate: 2026-02-21
---

```
BriefIntroduction:
中文简介
```

<!-- split -->

![cover image](./resources/images/ssh.png)

# Authentication

中文正文
""",
        encoding="utf-8",
    )
    (article_dir / "resources" / "i18n" / "client-guide-en.md").write_text(
        """---
Title: Complete Guide to Using an SSH Client
SourceBlob: abc123
---

```
BriefIntroduction: SSH configuration on the client side
```

<!-- split -->

# Authentication

English body

![later screenshot](./resources/images/gcp-vm-ssh-1.png)
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "import_articles_scripts.Rendered_Articles",
        app_module.app.config["RENDERED_ARTICLES_FOLDER"],
    )
    monkeypatch.setattr(
        "app.Rendered_Articles", app_module.app.config["RENDERED_ARTICLES_FOLDER"]
    )

    with app.app_context():
        import_articles(str(root_dir), db)
        article = db.session.execute(
            db.select(Article_Meta_Data).where(
                Article_Meta_Data.file_path
                == "devops/linux-learn/services/ssh/client-guide.md"
            )
        ).scalar_one()

    rendered_dir = (
        Path(app_module.app.config["RENDERED_ARTICLES_FOLDER"])
        / "devops-linux-learn-services-ssh"
    )
    english_html = (rendered_dir / f"{article.id}.en.html").read_text(encoding="utf-8")

    assert (
        'src="/rendered-articles/devops-linux-learn-services-ssh/resources/images/ssh.png"'
        in english_html
    )
    assert (
        'src="/rendered-articles/devops-linux-learn-services-ssh/resources/images/gcp-vm-ssh-1.png"'
        in english_html
    )
