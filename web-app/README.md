# Web App

This directory contains the Flask application, article import pipeline, page templates, frontend assets, and tests for the website.

If `articles-sync` is responsible for keeping the Markdown source up to date, `web-app` is responsible for turning that source into rendered HTML, database records, and the end-user pages served by the site.

## Purpose

The `web-app` subsystem covers four major areas:

- serving the homepage, article pages, docs-style category pages, and the About page
- importing Markdown articles into the SQLite metadata database
- rendering article Markdown into static HTML files under the rendered article directory
- providing internal endpoints and helpers used by the deployment and sync flows

## Primary Entry Points

### `app.py`

Main Flask entrypoint.

What it does:

- creates and configures the Flask app
- registers `/rendered-articles/...` as an additional static route
- serves the public routes:
  - `/`
  - `/articles`
  - `/articles/category/<path>`
  - `/articles/<int:article_id>`
  - `/about`
- exposes the internal `POST /internal/reindex` endpoint used by `articles-sync`
- builds the article TOC for the right-hand page navigation

Start here when you want to change:

- application routing
- article page rendering context
- the internal reindex trigger
- homepage or About page view wiring

### `import_articles_scripts.py`

Article import pipeline.

What it does:

- scans the source article tree
- skips hidden/internal folders such as `__template__`
- copies article assets into the rendered output directory
- parses frontmatter and validates required metadata
- computes a content hash to detect article changes
- upserts `Article_Meta_Data` rows
- re-renders HTML when article content changes or rendered output is missing
- removes database rows and rendered files for deleted source articles

Start here when you want to change:

- metadata validation rules
- article discovery behavior
- image/asset copy behavior
- article deletion cleanup

### `markdown_render_scripts.py`

Markdown-to-HTML rendering helper.

What it does:

- converts Markdown article bodies to HTML
- applies custom Markdown extensions
- writes the rendered HTML into the per-article output directory

Start here when you want to change:

- Markdown extension setup
- renderer behavior
- output generation details

### `navigation.py`

Docs-shell navigation builder.

What it does:

- builds the category tree from article metadata
- generates breadcrumbs
- humanizes category segments such as `gcp`, `ssh`, `llm`, and `waf`
- prepares sidebar context for both the docs index and article detail pages

Start here when you want to change:

- left-hand section navigation
- breadcrumb behavior
- category labels
- docs shell tree expansion rules

## Data and Rendering Flow

High-level flow:

1. `articles-sync` updates the Markdown repository.
2. `articles-sync` calls `POST /internal/reindex`.
3. `app.py` routes that request to `import_articles(...)`.
4. `import_articles_scripts.py` scans source folders, copies assets, validates metadata, and updates the database.
5. `markdown_render_scripts.py` renders article bodies into HTML files under the rendered article directory.
6. Public article routes read the rendered HTML file back from disk and combine it with database metadata for display.

Important implication:

- article metadata lives in SQLite
- article body HTML lives in the rendered article directory
- the public article page needs both

## Directory Map

### `templates/`

Jinja templates used by the Flask app.

Most important files:

- `base.html`
  - shared document shell and global asset loading
- `index.html`
  - homepage / landing page
- `about_me.html`
  - profile / hiring page
- `article_index.html`
  - docs-style category and article index page
- `article_details.html`
  - article detail page with left section nav and right TOC
- `_docs_tree.html`
  - recursive partial for the left docs sidebar tree
- `404.html`
  - not-found page

### `static/`

Frontend assets used by the templates.

Commonly touched files:

- `css/style.css`
  - homepage styles
- `css/about-me.css`
  - About page styles
- `css/docs-shell.css`
  - docs index layout and docs shell styling
- `css/article-details.css`
  - article page layout, TOC card styling, and article-body presentation rules
- `css/title.css`
  - heading presentation inside rendered Markdown
- `css/blockquote.css`
  - blockquote styling
- `article-toc.js`
  - right-side TOC active/expand behavior
- `code-copy.js`
  - copy button for code blocks
- `search.js`
  - search-related frontend behavior

There is also `StaticOverivew.md`, which can be helpful when mapping static assets at a lower level.

Important font files:

- `static/font/font.css`
  - loads JetBrains Mono, the PingFang UI subset, the full PingFang fallback, and the system fallback chain
- `static/font/PingFangSC/PingFang-SC-UI-subset.txt`
  - generated character list for the UI-only PingFang SC subset
- `static/font/PingFangSC/PingFang-SC-UI-subset.woff2`
  - lightweight Chinese font subset used for fixed UI text before falling back to the full PingFang font

### `custom_md_extensions/`

Custom Markdown extension implementations.

This is where site-specific rendering behavior lives, such as:

- image post-processing
- GFM-style admonition handling

Start here when you want to change rendered Markdown semantics rather than just page-level CSS.

### `scripts/`

Small helper scripts that support the web app but are not part of the Flask request path itself.

Current scripts:

- `init_db.py`
  - initializes the SQLite schema used by the application
- `build_pingfang_ui_subset.py`
  - extracts fixed UI copy from templates and generates the character list used to build the lightweight PingFang UI subset font

Start here when you want to change:

- database bootstrap behavior
- UI font subset generation inputs

### `tests/`

Pytest coverage for the Flask app and content pipeline.

Important test files:

- `test_smoke.py`
  - high-level page content checks
- `test_articles_routes.py`
  - article and docs page route behavior
- `test_article_toc.py`
  - TOC structure expectations
- `test_navigation.py`
  - category tree and navigation behavior
- `test_import_articles_scripts.py`
  - import pipeline edge cases
- `test_internal_reindex.py`
  - auth behavior for the internal reindex endpoint
- `test_markdown_render.py`
  - rendering helper behavior
- `test_image_processor_extension.py`
  - Markdown image processing behavior

## Common Change Paths

### Change the homepage

Look at:

- `templates/index.html`
- `static/css/style.css`

### Change the About page

Look at:

- `templates/about_me.html`
- `static/css/about-me.css`

### Change docs index or category pages

Look at:

- `templates/article_index.html`
- `static/css/docs-shell.css`
- `navigation.py`

### Change article detail layout

Look at:

- `templates/article_details.html`
- `static/css/article-details.css`
- `static/article-toc.js`
- `navigation.py`

### Change Markdown rendering behavior

Look at:

- `markdown_render_scripts.py`
- `custom_md_extensions/`
- `static/css/title.css`
- `static/css/blockquote.css`
- `static/css/md-css/` if you are changing code blocks, tables, or admonitions

### Change article import rules

Look at:

- `import_articles_scripts.py`
- `models.py`

### Change article metadata model or database behavior

Look at:

- `models.py`
- `app.py`
- `import_articles_scripts.py`

## Running and Testing

The usual local development/test workflow is driven from the repository root with Docker Compose.

Common commands:

```bash
docker compose -f compose.yml -f compose.dev.yml build web-app
docker compose -f compose.yml -f compose.dev.yml run --rm --no-deps -T web-app pytest -q
docker compose -f compose.yml -f compose.dev.yml run --rm --no-deps -T web-app ruff check .
docker compose -f compose.yml -f compose.dev.yml run --rm --no-deps -T web-app ruff format --check .
```

## Font Notes

The site uses a layered font loading strategy:

1. `JetBrainsMono` for Latin, code-heavy UI, and the general site monospace look
2. `PingFang-SC-UI-subset.woff2` for fixed Chinese UI copy
3. `PingFang-SC-Regular.woff2` and `PingFang-SC-Regular.ttf` as broader Chinese fallbacks
4. system Chinese fonts as the final fallback

The UI subset is preloaded from `templates/base.html` so fixed labels, navigation text, and section headings can settle earlier on first paint.

If template copy changes significantly, regenerate the UI subset character list and font artifact so the preload stays useful.

## Related Files

- [`../compose.yml`](../compose.yml)
  - service wiring, environment variables, health checks, and shared volumes
- [`../compose.dev.yml`](../compose.dev.yml)
  - development overrides for local iteration
- [`../articles-sync/README.md`](../articles-sync/README.md)
  - explains how the Markdown source is cloned, synced, and reindexed
- [`../scripts/deploy/README.md`](../scripts/deploy/README.md)
  - explains deploy-time orchestration around this service
