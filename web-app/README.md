# Web App

This directory contains the Flask application, Daily Brief publishing and storage layer, article import pipeline, page templates, frontend assets, and tests for the website.

If `articles-sync` is responsible for keeping the Markdown source up to date, `web-app` is responsible for turning that source into rendered HTML, database records, and the end-user pages served by the site.

## Purpose

The `web-app` subsystem covers these major areas:

- serving the homepage, Daily Brief archive/detail pages, article pages, docs-style category pages, and the About page
- validating authenticated Daily Brief payloads and storing them in a dedicated persistent directory
- exposing read-only article metadata APIs for public consumption
- importing Markdown articles into the SQLite metadata database
- rendering article Markdown into static HTML files under the rendered article directory
- providing internal endpoints and helpers used by the deployment and sync flows

## Primary Entry Points

### `app.py`

Main Flask entrypoint.

What it does:

- creates and configures the Flask app
- registers `/rendered-articles/...` as an additional static route
- resolves the preferred language from the `preferred_language` cookie, then `Accept-Language`, then default `zh`
- serves the public HTML routes:
  - `/`
  - `/<lang>/`
  - `/<lang>/articles`
  - `/<lang>/articles/category/<path>`
  - `/<lang>/articles/<int:article_id>`
  - `/<lang>/briefs`
  - `/<lang>/briefs/<YYYY-MM-DD>`
  - `/<lang>/about`
  - `/set-language/<lang>`
- serves the public read-only JSON APIs:
  - `GET /api/articles`
  - `GET /api/articles/<int:article_id>`
- exposes `POST /internal/reindex` for article sync and authenticated `POST /internal/briefs` for Daily Brief publishing
- validates the language-switch `next=` target so `/set-language/...` only redirects to same-site absolute paths
- builds the article TOC for the right-hand page navigation
- injects shared template helpers for `asset_url(...)`, `t(...)`, language switching, and dynamic `html lang`

Start here when you want to change:

- application routing
- language detection and switch behavior
- API response shape for article metadata
- article page rendering context
- the internal reindex trigger
- Daily Brief route and publishing behavior
- homepage or About page view wiring

### `daily_briefs.py`

Daily Brief schema, validation, storage, and read helpers.

What it does:

- accepts only schema version 1 with fixed `ai` and `non_ai_hot` sections
- validates dates, timezone-aware generation timestamps, string bounds, item limits, HTTP(S) links, and non-negative statistics
- requires every `hn_item_id` to match its Hacker News discussion URL
- writes canonical per-date JSON with an atomic replace
- treats same-date publishing as an idempotent create, unchanged write, or update
- skips and logs corrupt persisted files instead of breaking the full archive

Daily Brief files live outside SQLite because the existing article database can be rebuilt from source. Production mounts the dedicated `daily_brief_data` volume at `/daily-briefs/data`.

### `i18n.py`

Lightweight site i18n helpers.

What it does:

- defines supported public languages (`zh`, `en`)
- parses `preferred_language` cookie and `Accept-Language`
- provides translation lookups for fixed UI copy
- builds language-aware public paths and language-switch URLs
- maps site language to document `<html lang>` values

Start here when you want to change:

- supported language codes
- default language selection behavior
- fixed template copy translations
- path switching logic between language namespaces

### `article_views.py`

Article presentation helpers.

What it does:

- resolves the rendered HTML path for an article, including optional English sidecars
- loads translated sidecar metadata (`<id>.en.json`) when present
- builds a localized article view model for docs pages and article detail pages
- generates the article heading outline / TOC used by the right-hand article navigation

Start here when you want to change:

- article page TOC generation
- how English sidecars override canonical article metadata at render time
- how article list/detail routes choose rendered HTML files

### `import_articles_scripts.py`

Article import pipeline.

What it does:

- scans the source article tree
- skips hidden/internal folders such as `__template__`
- treats an article directory as publishable when it directly contains `images/` or `assets/`, or when it contains `resources/images/`
- copies article assets into the rendered output directory
- parses frontmatter and validates required metadata
- computes a content hash to detect article changes
- upserts `Article_Meta_Data` rows
- re-renders HTML when article content changes or rendered output is missing
- recognizes optional English sidecars at `resources/i18n/<basename>-en.md`
- writes English rendered HTML (`<id>.en.html`) and English metadata sidecars (`<id>.en.json`) when those sidecars exist
- removes database rows and rendered files for deleted source articles

Current note:

- the Chinese markdown file remains the canonical metadata source
- English sidecars currently override only title, brief introduction, author, and body on `en` article/docs pages
- when an English sidecar omits markdown images, the importer prepends the Chinese article's leading image block so bilingual pages keep the same hero/cover image
- other metadata, such as rollout date, category, and cover image, still reuses the canonical Chinese article metadata

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
- converts LaTeX math delimiters into KaTeX-compatible placeholders
- writes the rendered HTML into the per-article output directory

Math rendering notes:

- inline math supports `$...$` and `\(...\)`
- block math supports `$$...$$` and `\[...\]`
- Markdown rendering uses `pymdownx.arithmatex` with generic output, so article HTML contains `arithmatex` placeholders
- the article detail template loads local KaTeX assets and `static/math-render.js` to typeset those placeholders in the browser
- existing rendered HTML files are skipped when an article content hash is unchanged, so old articles need a re-render or reindex path when renderer-only behavior changes

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
- the public article APIs currently expose metadata only, not rendered article HTML

Daily Brief publishing follows a separate flow:

1. The local `daily-brief` generator writes a schema-versioned public JSON file.
2. Its publisher sends the file to `POST /internal/briefs` with `X-DAILY-BRIEF-TOKEN`.
3. `daily_briefs.py` validates and atomically stores the normalized payload by date.
4. The homepage, archive, and detail routes read the newest valid files from the dedicated volume.

The endpoint is hidden with a 404 when `DAILY_BRIEF_PUBLISH_TOKEN` is unset. `DAILY_BRIEF_DATA_DIRECTORY` overrides the default `/daily-briefs/data` storage path.

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
- `brief_index.html` and `brief_detail.html`
  - Daily Brief archive and per-date reading pages
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
- `css/briefs.css`
  - Daily Brief content-first reading layout, single archive list, story hierarchy, and responsive presentation
- `css/title.css`
  - heading presentation inside rendered Markdown
- `css/blockquote.css`
  - blockquote styling
- `article-toc.js`
  - right-side TOC active/expand behavior
- `code-copy.js`
  - copy button for code blocks
- `math-render.js`
  - initializes KaTeX auto-render for article body math delimiters
- `search.js`
  - search-related frontend behavior
- `vendor/katex/`
  - vendored KaTeX 0.17.0 browser assets, fonts, and license used by article math rendering

There is also `StaticOverivew.md`, which can be helpful when mapping static assets at a lower level.

Important font files:

- `static/font/font.css`
  - loads JetBrains Mono, the PingFang UI subset, the full PingFang fallback, and the system fallback chain
- `static/font/PingFangSC/PingFang-SC-UI-subset.txt`
  - generated character list for the UI-only PingFang SC subset
- `static/font/PingFangSC/PingFang-SC-UI-subset.woff2`
  - lightweight Chinese font subset used for fixed UI text before falling back to the full PingFang font

### Asset versioning

Templates load site-owned static assets through `asset_url(...)`, which is injected from `app.py`.

What it does:

- looks up the static file's last-modified timestamp with `os.path.getmtime(...)`
- appends that timestamp as `?v=<mtime>` to the generated `/static/...` URL
- keeps emitting the same version while the file is unchanged
- emits a new version only after the file on disk changes

Important implication:

- this is a file-versioning mechanism, not a per-request random token
- `/static/css/about-me.css?v=123` and `/static/css/about-me.css?v=456` are different cache keys
- that lets browsers and Cloudflare keep caching old asset URLs safely while new page renders point to the new URL after a CSS/JS/image update
- production currently relies on this versioned `/static/...?...` pattern to make Cloudflare edge caching safe for site-owned CSS, JS, fonts, and images

Start in `app.py` if you want to change:

- how static asset version strings are generated
- whether assets use mtime, content hash, or some other cache-busting strategy

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
  - article, docs page, and public article API route behavior
- `test_article_toc.py`
  - TOC structure expectations
- `test_navigation.py`
  - category tree and navigation behavior
- `test_import_articles_scripts.py`
  - import pipeline edge cases
- `test_internal_reindex.py`
  - auth behavior for the internal reindex endpoint
- `test_daily_briefs.py`
  - Daily Brief schema, authenticated publishing, storage isolation, route, language, and escaping behavior
- `test_markdown_render.py`
  - rendering helper behavior
- `test_image_processor_extension.py`
  - Markdown image processing behavior

## Common Change Paths

### Change the homepage

Look at:

- `templates/index.html`
- `static/css/style.css`

### Change Daily Brief publishing or pages

Look at:

- `daily_briefs.py` and `app.py`
- `templates/brief_index.html` and `templates/brief_detail.html`
- `static/css/briefs.css`

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
  - `gfm-admonition.css` styles note/tip/warning content as restrained rail notes so they stay distinct from code blocks without becoming heavy cards

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

Ruff policy:

- `ruff.toml` declares Python 3.12 as the lint target.
- The project intentionally follows Ruff's stable default rule set instead of freezing an older hand-picked subset.
- When a Ruff update enables new stable rules, review and fix the findings as part of that dependency update.

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
