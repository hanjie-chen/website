# Web App

Flask application for the personal dashboard, article reader, Daily Brief pages
and APIs. Article sources are maintained by [articles-sync](../articles-sync/README.md);
this service imports and renders them. Daily Briefs are generated externally and
submitted through an authenticated publishing endpoint.

## Code Map

| Entry | Responsibility |
| --- | --- |
| [app.py](app.py) | Routes, authentication, page context and template helpers |
| [config.py](config.py) | Environment configuration |
| [models.py](models.py), [db_health.py](db_health.py) | Article metadata and deployment-time database assessment |
| [import_articles_scripts.py](import_articles_scripts.py) | Source discovery, incremental import, translations and deletion cleanup |
| [markdown_render_scripts.py](markdown_render_scripts.py), [custom_md_extensions/](custom_md_extensions/) | Markdown rendering, image processing and admonitions |
| [article_views.py](article_views.py), [navigation.py](navigation.py) | Localized article views, TOC, category tree and breadcrumbs |
| [daily_briefs.py](daily_briefs.py) | Brief validation, JSON storage, current pointer and archive index |
| [daily_brief_cleanup.py](daily_brief_cleanup.py) | Optional one-off retention cleanup |
| [i18n.py](i18n.py) | Supported languages, UI translations and language-aware URLs |
| [templates/](templates/), [static/](static/) | Jinja pages, styles and browser scripts |
| [scripts/](scripts/), [tests/](tests/) | Maintenance helpers and automated checks |

HTML pages use `/zh/` and `/en/` prefixes. `/` chooses a language from the
`preferred_language` cookie, then `Accept-Language`, then `zh`. The language
switch accepts only same-site absolute redirect paths. API and internal routes
have no language prefix. See `app.py` for the complete route list.

## Configuration

Settings are read at import time by `config.py`. Docker Compose supplies the
runtime mounts and overrides; see [compose.yml](../compose.yml) and
[compose.dev.yml](../compose.dev.yml).

| Variable | Default / purpose |
| --- | --- |
| `SOURCE_ARTICLES_DIRECTORY` | `/articles/src`: synchronized Markdown and assets |
| `RENDERED_ARTICLES_DIRECTORY` | `/articles/rendered`: generated HTML and copied assets |
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///project.db`: article metadata in the Flask instance directory; development Compose uses `project_test.db` |
| `DAILY_BRIEF_DATA_DIRECTORY` | `/daily-briefs/data`: published briefs and their index/pointer |
| `REIMPORT_ARTICLES_TOKEN` | Unset by default; enables authenticated article reindexing |
| `DAILY_BRIEF_PUBLISH_TOKEN` | Unset by default; enables authenticated brief publishing |
| `APP_ENV` | `production`; `development` or `dev` enables `/debug` and clears rendered output before each article import |

If `APP_ENV` is absent, `FLASK_ENV` is used before the production default.
Production runs Gunicorn; development Compose mounts the source and runs Flask
with debug enabled. Keep development imports away from production data volumes.
Host initialization, deployment and health checks are documented in
[scripts/deploy/README.md](../scripts/deploy/README.md).

## Article Pipeline

`articles-sync → POST /internal/reindex → import/render → SQLite + HTML → pages`

SQLite stores article metadata; generated HTML and copied assets live separately.
Article pages require both. The website has no public article JSON API.
Article Markdown is trusted repository content: rendered HTML is inserted into
templates without HTML sanitization. This pipeline is not an upload interface
for untrusted Markdown.

### Source Format

The importer discovers article directories containing `images/`, `assets/`, or
`resources/images/`. It skips hidden and internal directories such as
`__template__`. Once it finds an article directory, it processes its Markdown
files rather than recursively treating its resource directories as articles.

A canonical article needs YAML frontmatter with `Title`, `Author`, `CoverImage`
and `RolloutDate`, a fenced `BriefIntroduction:` block, and `<!-- split -->`
before the body. For example, with a sibling `images/cover.png`:

````markdown
---
Title: Example article
Author: Example author
CoverImage: images/cover.png
RolloutDate: 2026-01-01
---

```text
BriefIntroduction: A short introduction.
```

<!-- split -->
# Article body
````

Categories and article identity derive from the source path. Optional English
translations live at `resources/i18n/<basename>-en.md`, use the same introduction
and body separators, and require `Title` in frontmatter. They provide translated
body and display metadata without creating another database article. Missing
English output falls back to the canonical Chinese content. If the English body
has no leading image block, it inherits the source's leading images.

See [import tests](tests/test_import_articles_scripts.py) for accepted formats
and edge cases. Markdown extension configuration lives in
[markdown_render_scripts.py](markdown_render_scripts.py); math uses local KaTeX
through [math-render.js](static/math-render.js).

### Reindex Authentication

`POST /internal/reindex` requires `X-REIMPORT-ARTICLES-TOKEN` matching the web app's
`REIMPORT_ARTICLES_TOKEN`. The sync service must use the same secret.

- Unset or empty server token: HTTP 404.
- Missing or incorrect request token: HTTP 403.
- Completed import: HTTP 200 with `{"status":"ok"}`.

This credential is separate from the Daily Brief publishing token. The
`/internal/` prefix does not itself provide network access control.

### Rebuild Behavior

- Production imports skip existing canonical HTML when the source hash is
  unchanged. Missing HTML is regenerated; English sidecars are refreshed during
  import. The hash includes `RENDERER_VERSION` from
  [markdown_render_scripts.py](markdown_render_scripts.py): bump it whenever a
  renderer change alters HTML for unchanged Markdown, and the next reindex
  re-renders every article.
- Development imports clear the rendered tree before rebuilding it.
- Source files no longer discovered are removed from the article database and
  their generated HTML is deleted. Verify the source tree before reindexing;
  an empty scan can remove existing article records.
- [scripts/init_db.py](scripts/init_db.py) **drops and recreates database tables**
  before importing articles. It can change article IDs and is not a routine
  rerender command. Deployment safeguards are described in the deploy guide.

## Daily Briefs

`external generator → POST /internal/briefs → JSON files → pages and public API`

Briefs are stored separately from the rebuildable article database. Storage uses
one `YYYY-MM-DD.json` payload per date, `current.json` for the latest date and
`archive-index.json` for archive metadata. Writes are serialized with a file lock;
each file is replaced atomically, but the files are not one database transaction.

Same-date publishing replaces that date's content; older backfills join the
archive without moving the current pointer backward. Retention is a rolling
14-calendar-day window in `Asia/Singapore`: today and the previous 13 days,
based on the payload's `date`, not its upload time or `generated_at`. Publishing
dates outside this window (including future dates) returns HTTP 400. Republishing
does not extend a date's retention.

Pages, homepage links and public APIs enforce this window on every read, even
if no new brief is uploaded or physical cleanup is delayed. Reads use the
pointer/index or an exact date file, with no fallback directory scan. Expired
detail URLs return HTTP 404; an expired current brief produces the empty state.

Successful publishing also cleans expired files and refreshes the archive index
and current pointer under the same file lock. Cleanup scans canonical dated
filenames to also remove expired orphan files and legacy future-dated files;
unrelated files are left alone. Corrupt archive metadata causes cleanup to fail
rather than discard metadata.

There is no scheduled cleanup service. When publishing pauses, expired files may
remain on disk but are never served; the next successful publish removes them.
Without new uploads, the stored brief count does not grow.

For an optional one-off cleanup using the deployed application image:

```bash
docker compose run --rm --no-deps -T web-app python -m daily_brief_cleanup
```

Cleanup deletes expired JSON payloads permanently from the active volume. Backups
and the external generator's own storage are outside this retention policy.

### Publishing API

`POST /internal/briefs` takes JSON and requires `X-DAILY-BRIEF-TOKEN` matching
`DAILY_BRIEF_PUBLISH_TOKEN`. The request body limit is 128 KiB in Flask and in the
Nginx publishing location.

Only strict schema v2 is accepted: `date`, timezone-aware `generated_at`,
`timezone: "Asia/Singapore"`, and `ai` / `non_ai_hot` sections. Items contain
summary, source/discussion links, counts, selection basis and content status.
Optional `generation_info` records per-source acquisition, model-declared summary
sources and the generation outcome; legacy `provenance` remains supported.
Unknown fields are rejected. Exact fields, limits and allowed values are defined in
[daily_briefs.py](daily_briefs.py), with examples in
[test_daily_briefs.py](tests/test_daily_briefs.py).

| Result | HTTP response |
| --- | --- |
| Server token unset or empty | 404 |
| Missing or incorrect request token | 403 |
| Non-JSON content type | 415 |
| Invalid JSON/schema, expired date or future date | 400 with an `error` field |
| Body exceeds the configured limit | 413 |
| New date | 201 with `{"status":"created","date":"YYYY-MM-DD"}` |
| Existing date | 200 with `status` of `updated` or `unchanged`, plus `date` |

Nginx's WAF exception and compensating controls are documented in
[nginx-modsecurity/README.md](../nginx-modsecurity/README.md#security-notes).

### Generation Information

`generation_info` is an optional additive schema v2 item field. Its exact shape is:

```json
{
  "materials": {
    "webpage": {"status": "success", "method": "direct", "origin": "original", "reason": "none"},
    "hn_post": {"status": "empty", "reason": "none"},
    "hn_comments": {"status": "success", "reason": "none"}
  },
  "summary_sources": ["web_body", "hn_comments"],
  "generation": {"status": "success", "model": "provider/model-id", "reason": "none"}
}
```

- Acquisition distinguishes `success`, `empty`, `failed`, `not_attempted`,
  `not_needed` and `unknown`. A webpage failure can coexist with a successful
  summary based on HN material. A recovered webpage retains its final method and
  material origin, with the original failure reason as recovery context.
- `summary_sources` contains unique model-declared source codes: `web_metadata`,
  `web_body`, `hn_post`, `hn_comments`. It is not the input material inventory or
  independently verified attribution. `null` means usage was not recorded; an
  empty list records no sources used for a summary that was not produced.
- Generation distinguishes `success`, `insufficient`, `failed`, `not_attempted`
  and `unknown`. `model` is the actual last model identifier, or `null` if not
  recorded. Reasons are allowlisted public codes; raw errors, prompts and
  provider responses remain in the generator's private audit.

The disclosure shows acquisition, summary sources, generation and the existing
selection basis, using `generation_info` when present. Historical items fall back
to their recorded `provenance` or just selection basis; missing diagnostics are
never reconstructed from `content_status` or other legacy fields.

Deploy this accepting website version **before** enabling the corresponding
Daily Brief generator output: older website validators reject the new field.
Readers and publishers continue to accept historical schema v2 items without it.

### Public Daily Brief API

These endpoints require no token and return published content only:

| Endpoint | Response |
| --- | --- |
| `GET /api/briefs` | `{"items":[...]}` with `date`, `generated_at`, `ai_items` and `non_ai_hot_items`, newest first; an empty archive returns `{"items":[]}` |
| `GET /api/briefs/latest` | Latest published schema v2 payload; its date may be earlier than today |
| `GET /api/briefs/YYYY-MM-DD` | Published schema v2 payload for that date |

Missing, invalid or unreadable detail payloads return HTTP 404 with
`{"error":"brief_not_found"}`. Writes return HTTP 405. Summaries are Chinese;
responses contain neither original article full text nor private generator
logs. Same-date content can change on republishing, so dated responses are not
immutable. Use the date and `hn_item_id` together to identify an item.

## Frontend Maintenance

- [base.html](templates/base.html) and [_site_topbar.html](templates/_site_topbar.html)
  own the shared shell. The site uses no CSS or JavaScript framework:
  [base.css](static/css/base.css) is the browser reset and page shell,
  [style.css](static/css/style.css) provides global theme, navigation and
  homepage styles, and page-specific styles extend them. Lay out pages with
  CSS grid or flexbox in the component's stylesheet rather than utility classes.
  [site-nav.js](static/site-nav.js) drives the mobile navigation menu.
- UI translations live in `i18n.py`. Article translations use the sidecars above;
  switching the page language does not translate Daily Brief summaries.
- Use `asset_url(...)` for direct template references to site assets. It appends
  integer-second file mtime, not a content hash. CSS-relative font/image URLs
  are not automatically versioned. Load shared `style.css` through `base.html`;
  do not re-import it with an unversioned CSS URL. Cloudflare cache policy is
  managed separately.
- Article math, code-copy, TOC and image-preview behavior belongs to the scripts
  loaded by [article_details.html](templates/article_details.html). Brief date
  navigation enhancement is loaded by [brief_detail.html](templates/brief_detail.html).
  Brief items place the "Generation info" disclosure beside source and discussion
  metadata, with its contents below that row. It uses native `details` / `summary`.
  Keep page links and disclosures usable without JavaScript; the mobile
  navigation menu is the exception and needs `site-nav.js` to open.
- Font configuration lives in [font.css](static/font/font.css). The PingFang UI
  subset is preloaded; full fonts provide fallback coverage.
  [build_pingfang_ui_subset.py](scripts/build_pingfang_ui_subset.py) extracts
  characters from templates and Chinese translations into a `.txt` file; it
  does not generate the `.woff2` font. A reproducible font-build command is not
  currently documented in this repository.

## Running and Testing

Run these commands from the repository root with Docker Compose available:

```bash
docker compose -f compose.yml -f compose.dev.yml build web-app
docker compose -f compose.yml -f compose.dev.yml run --rm --no-deps -T web-app pytest -q
docker compose -f compose.yml -f compose.dev.yml run --rm --no-deps -T web-app ruff check .
docker compose -f compose.yml -f compose.dev.yml run --rm --no-deps -T web-app ruff format --check .
```

These commands build and check the application without starting the full stack.
Tests isolate the database and rendered/brief data from development state; see
[tests/conftest.py](tests/conftest.py). Ruff targets Python 3.12 and uses its stable
default rule set. CI adds coverage and full runtime checks; see
[workflow documentation](../.github/workflows/README.md).

A complete first-time local stack setup guide is still missing. Starting the
whole stack also requires TLS material, source synchronization and database
initialization; the commands above do not perform those steps.
