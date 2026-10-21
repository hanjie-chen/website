# Web App

Flask application for the personal dashboard, the knowledge base's notes, Daily
Brief pages and APIs. The knowledge base is mirrored by
[articles-sync](../articles-sync/README.md); this service imports and renders it.
Daily Briefs are generated externally and submitted through an authenticated
publishing endpoint.

## Code Map

| Entry | Responsibility |
| --- | --- |
| [app.py](app.py) | Routes, authentication, page context and template helpers |
| [config.py](config.py) | Environment configuration |
| [models.py](models.py), [db_health.py](db_health.py) | Note metadata and deployment-time database assessment |
| [import_notes.py](import_notes.py) | Note discovery, titles and dates, incremental import and deletion cleanup |
| [markdown_render_scripts.py](markdown_render_scripts.py), [custom_md_extensions/](custom_md_extensions/) | Markdown rendering, image paths, links between notes and admonitions |
| [note_views.py](note_views.py), [navigation.py](navigation.py) | Localized note views, TOC, note links, category tree and breadcrumbs |
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
| `SQLALCHEMY_DATABASE_URI` | `sqlite:///project.db`: note metadata in the Flask instance directory; development Compose uses `project_test.db` |
| `DAILY_BRIEF_DATA_DIRECTORY` | `/daily-briefs/data`: published briefs and their index/pointer |
| `REIMPORT_ARTICLES_TOKEN` | Unset by default; enables authenticated note reindexing |
| `DAILY_BRIEF_PUBLISH_TOKEN` | Unset by default; enables authenticated brief publishing |
| `APP_ENV` | `production`; `development` or `dev` enables `/debug` and clears rendered output before each note import |

If `APP_ENV` is absent, `FLASK_ENV` is used before the production default.
Production runs Gunicorn; development Compose mounts the source and runs Flask
with debug enabled. Keep development imports away from production data volumes.
Host initialization, deployment and health checks are documented in
[scripts/deploy/README.md](../scripts/deploy/README.md).

## Note Pipeline

`articles-sync → POST /internal/reindex → import/render → SQLite + HTML → pages`

The site is the owner's window onto the
[knowledge base](https://github.com/hanjie-chen/knowledge-base): every note is
published, drafts included, and the knowledge base's own README defines how notes
are organized. This service alone decides what counts as a note. Notes live at
`/<lang>/notes`, `/<lang>/notes/<id>` and `/<lang>/notes/category/<path>`; ids are
assigned at import, so a moved note gets a new id. Infrastructure names that
predate notes (the `articles-sync` service, its volumes and environment
variables, and `/rendered-articles/`) are kept.

SQLite stores note metadata; generated HTML and copied assets live separately.
Note pages require both. The website has no public note JSON API. Note Markdown
is trusted repository content: rendered HTML is inserted into templates without
HTML sanitization. This pipeline is not an upload interface for untrusted
Markdown.

### Source Format

Every `.md` file is a note except:

- `README.md`, `AGENTS.md` and `CLAUDE.md`, which guide people and agents;
- files under hidden folders, `__template__`-style folders, and the `resources/`
  and `images/` folders that hold a note's images.

A note's path is its classification: its folder is its category. Its title is
its first `# heading` outside code blocks, which leaves the body and becomes the
page title; a note without one is titled by its file name. The body's outline
therefore starts at `##`. Front matter is optional and only `RolloutDate` is read,
as the date the owner wrote the note:

````markdown
---
RolloutDate: 2026-01-01
---

# Example note

## First section
````

The updated date is the date of the last commit that touched the file, read from
the mirror's full git history; notes without history show no updated date.
Relative image paths resolve against the note's folder, whose `images/` and
`resources/images/` folders are copied next to the rendered HTML.
Links to other notes (`../ssh/client-guide.md`, or `/tools/git/commands.md` from
the root) render as `/notes/path/<path>` and the note page points them at the
target's current id; links to notes that are gone keep that path and return 404.

Notes have one language: `/en/` switches the interface, not the note.

See [import tests](tests/test_import_notes.py) for accepted formats and edge
cases. Markdown extension configuration lives in
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
  unchanged. Missing HTML is regenerated. The hash includes `RENDERER_VERSION`
  from [markdown_render_scripts.py](markdown_render_scripts.py): bump it whenever a
  renderer change alters HTML for unchanged Markdown, and the next reindex
  re-renders every note.
- Development imports clear the rendered tree before rebuilding it.
- Source files no longer discovered are removed from the note database and
  their generated HTML is deleted. Verify the source tree before reindexing;
  an empty scan can remove existing note records.
- [scripts/init_db.py](scripts/init_db.py) **drops and recreates database tables**
  before importing notes. It can change note IDs and is not a routine
  rerender command. Deployment safeguards are described in the deploy guide.

## Daily Briefs

`external generator → POST /internal/briefs → JSON files → pages and public API`

Briefs are stored separately from the rebuildable note database. Storage uses
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
  "generation": {"status": "success", "model": "provider/model-id", "reason": "none", "reasoning_effort": "medium"}
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
- The public reason `archive_unavailable` means archive recovery found no usable
  capture. Failed Wayback retrieval shows "未找到可用存档" / "No usable archive
  found"; historical `unknown` reasons continue to show that no reason was recorded.
- Optional `generation.reasoning_effort` records the requested configuration for
  that summary call: `none`, `minimal`, `low`, `medium`, `high` or `xhigh`.
  Missing or `null` means unrecorded and is not displayed; historical payloads
  are never assigned a default. It does not measure actual reasoning usage.

The "About this summary" disclosure shows acquisition, model-reported summary
sources, generation (including recorded reasoning effort) and the existing
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

## Homepage

The homepage is the interface between the site's owner and their personal
system: the system speaking to its owner. It is not a news page and not an
introduction to the site. The time-of-day greeting opens that voice.

Today the system is the Daily Brief workflow (a scheduled pipeline with fixed
LLM steps, not an agent), the knowledge base and the site itself. A module
belongs on the homepage only when the system has something to hand the owner,
or something the owner needs to know or act on; for now that is the Daily
Brief alone. Navigation covers everything else. Add modules as the system
grows, one at a time, never to fill the page.

The brief appears without a card, in the system's voice: one sentence says
whether today's brief has arrived and how many items it has, or which day's
brief it shows instead, followed by the first two items and a link to the full
brief. How a future module is presented is decided when it arrives, from what
it is.

For direction only, not as planned work: the owner might later leave ideas
here, let agents claim the ones they can do, and be reminded of the ones only
the owner can do, such as writing down their own experience.

## Frontend Maintenance

- [base.html](templates/base.html) and [_site_topbar.html](templates/_site_topbar.html)
  own the shared shell. The site uses no CSS or JavaScript framework:
  [theme.css](static/css/theme.css) defines every site color as a role-named
  token (see [Color and Themes](#color-and-themes)),
  [base.css](static/css/base.css) is the browser reset and page shell,
  [style.css](static/css/style.css) provides navigation and homepage styles,
  and page-specific styles extend them. Use tokens from `theme.css` instead of
  color literals in component styles, including Pygments syntax colors in
  [pygment-style.css](static/css/md-css/pygment-style.css); a test enforces
  this. Lay out pages with CSS grid or flexbox in the component's stylesheet
  rather than utility classes. [site-nav.js](static/site-nav.js) drives the
  mobile navigation menu and closes it and the settings panel on an outside
  click, Escape or tabbing away.
- UI translations live in `i18n.py`. Switching the page language translates the
  interface only: notes and Daily Brief summaries keep their own language.
- Use `asset_url(...)` for direct template references to site assets. It appends
  integer-second file mtime, not a content hash. CSS-relative font/image URLs
  are not automatically versioned. Load shared `style.css` through `base.html`;
  do not re-import it with an unversioned CSS URL. Cloudflare cache policy is
  managed separately.
- Note math, code-copy, TOC and image-preview behavior belongs to the scripts
  loaded by [note_details.html](templates/note_details.html). Brief date
  navigation enhancement is loaded by [brief_detail.html](templates/brief_detail.html).
  Brief items place the "About this summary" disclosure beside source and discussion
  metadata, with its contents below that row. Material sources, statuses and
  retrieval notes align in an indented group; notes wrap below the status on
  narrow screens. It uses native `details` / `summary`.
  Keep page links and disclosures usable without JavaScript; the mobile
  navigation menu needs `site-nav.js` to open, and the theme row stays hidden
  without scripts while the page follows the system theme.
- Font configuration lives in [font.css](static/font/font.css). The PingFang UI
  subset is preloaded; full fonts provide fallback coverage.
  [build_pingfang_ui_subset.py](scripts/build_pingfang_ui_subset.py) extracts
  characters from templates and Chinese translations into a `.txt` file; it
  does not generate the `.woff2` font. A reproducible font-build command is not
  currently documented in this repository.
- The brief archive uses a centered 560px directory with localized dates and
  weekdays. The header shows the archive year (a range across New Year); rows
  include their year when the archive spans two years. Counts stay in the public
  API but are omitted from the directory. [brief-opened.js](static/brief-opened.js)
  subtly dims dates whose detail page has been opened in this browser, including
  direct visits from the homepage. This is not reading progress: it uses local
  storage shared across languages, keeps at most 14 date keys, and does not sync
  across devices. Navigation remains usable with JavaScript or storage disabled.

## Color and Themes

Pages should stay calm to read for long stretches, so most of each page uses
quiet neutrals and personality lives in a small accent.
[theme.css](static/css/theme.css) is the only place colors are defined.

### Base Palette

Backgrounds, surfaces, text and borders use warm neutrals with no hue of their
own: warm paper in light mode, warm charcoal in dark mode. They favor long
reading, and because they lean toward no hue, an accent can change without
retuning them.

| Role | Light | Dark |
| --- | --- | --- |
| Background (`--bg`) | `#f7f5f0` | `#1c1b19` |
| Body text (`--text`) | `#2a2925` | `#e3dfd6` |
| Secondary text (`--text-muted`) | `#6a665e` | `#a29d92` |
| Code background (`--code-bg`) | `#f0ece3` | `#2a2824` |

Body and secondary text meet WCAG AA (4.5:1) on every surface in both themes.
Syntax comments and `--text-faint` separators are the deliberate exceptions.

### Accents

The two accents come from the Genshin Impact 6.1 event screens: the amber
challenge-record bar and the pine-green night scenes, adjusted to stay legible
on both backgrounds.

- **Amber** (`--accent-*`, `#9a5f0e` / `#e3a548`) marks content worth noticing:
  the brand mark, links and their underlines, the rails and labels of quotes and
  supplementary admonitions (note, tip, important), and highlighted labels.
- **Pine** (`--current-*`, `#2e6b5e` / `#72b8a6`) marks where you are and what
  responds to you within a page: the table-of-contents track, selected sidebar
  items, hover feedback on cards, and focus rings.

The top bar keeps a single color, the moon. Its current page shows in bold with
a neutral rule, and its controls hover with a neutral fill.

Choose by role rather than looks: text that leads somewhere or deserves
attention takes amber, and state takes pine. Warning, caution and success
colors carry fixed meanings and stay independent of both accents. Code uses One Light
and One Dark syntax colors. To try another accent, change only the two accent
token groups in `theme.css`.

The brand mark is the full moon from the same event art. In dark mode it glows;
on light paper it is gilded (`#b8781c`) with a thin halo ring instead, the way
the event screens use glows at night and gold outlines on paper (`--moon-*`
tokens). The browser icon [moon.svg](static/icon/moon.svg) follows the
browser's own light or dark mode, with [moon.ico](static/icon/moon.ico) as the
fallback for browsers without SVG icons.

### Theme Switching

Each token holds `light-dark(light, dark)` values. Pages follow the system
theme; `data-theme="light"` or `"dark"` on `<html>` overrides it. Language and
appearance are rarely changed, so they sit behind one quiet settings button at
the end of the top bar (a native `details` panel; the mobile menu shows the
same rows). Each row lists its options and marks the current one in bold. In
the theme row ([theme-switcher.js](static/theme-switcher.js)), Light and Dark
pin a theme in `localStorage["theme"]` and Auto clears it to follow the system,
so a pinned theme survives the system's own day and night switch. An
inline script in `base.html` applies the saved choice before first paint.
Browsers without `light-dark()` support (released before mid-2024) show the
browser's default black on white; the site accepts this rather than keeping a
second copy of the dark values.

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
