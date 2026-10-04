# Article Sync Service

Maintains a shallow mirror of the knowledge-base repository in the shared source
volume and notifies the web app when its checked-out commit changes. Article
validation, database import and HTML rendering belong to
[web-app](../web-app/README.md#article-pipeline).

## Files

| File | Responsibility |
| --- | --- |
| [Dockerfile](Dockerfile) | Alpine image with Git, curl, dcron, tini and su-exec; creates `appuser` and the source directory |
| [init.sh](init.sh) | Initial clone or update, cron installation and foreground cron daemon |
| [update-articles.sh](update-articles.sh) | Fetch/reset the mirror and conditionally request reindexing |
| [cron-heartbeat-sync.sh](cron-heartbeat-sync.sh) | Log a scheduled run and execute the update as `appuser` |

The container starts through tini. Root installs/runs cron; initialization and
scheduled Git operations switch to `appuser`. The source directory must be
writable by that user (image build defaults: UID/GID 1000).

## Startup and Updates

- **Empty source directory:** initialization clones the configured branch with
  depth 1, then starts cron. This initial clone does not request reindexing;
  [production initialization](../scripts/deploy/README.md#initial-setup) imports
  the source through the web app's database initializer.
- **Existing source directory:** initialization runs the update script before
  starting cron. An update failure that returns nonzero stops initialization.
- **Triggered update:** the website's [Content Sync workflow](../.github/workflows/content-sync.yml)
  runs the update inside the container over SSH. It can be dispatched by the
  knowledge-base publishing flow or manually; it follows the configured branch,
  not the workflow's informational `source_sha` input. This run must end with a
  successful reindex; see [Reindex Trigger](#reindex-trigger).
- **Scheduled update:** Compose sets a daily fallback at 03:00 UTC. Cron and sync
  messages include the timezone and are written to container logs.

An update sets the configured origin, fetches the branch at depth 1, then uses
`git reset --hard FETCH_HEAD` and `git clean -fd`. This is a disposable content
mirror: tracked local changes and untracked files/directories can be discarded.
Do not use the source volume as a developer working copy.

The script attempts a replacement shallow clone when `.git` is missing, origin
cannot be updated, or fetch fails. This requires access to the directory's parent
and the ability to replace the source directory; a successful fallback is not
guaranteed for every permissions or mount failure. Reset/clean failures return
nonzero rather than triggering another reclone.

### Reindex Trigger

If both the before/after HEAD values are non-empty and equal, the script exits
without reindexing. Otherwise, when `WEB_APP_REINDEX_URL` is configured, it sends
an HTTP POST with `X-REIMPORT-ARTICLES-TOKEN` if a token is configured.

Use the same non-empty `REIMPORT_ARTICLES_TOKEN` in both services. The client can
omit the header, but the web app rejects anonymous reindexing; see
[Reindex Authentication](../web-app/README.md#reindex-authentication).

Content Sync runs the script with `REQUIRE_REINDEX=1`: it reindexes even when HEAD
is unchanged, and a failed POST or missing `WEB_APP_REINDEX_URL` fails the run.
After fixing the endpoint or token, rerun Content Sync to recover; unchanged
articles are skipped by the web app's incremental import.

Startup and cron runs leave `REQUIRE_REINDEX` unset. They only log a failed POST,
so a web app that is still starting cannot stop the container. There is no retry
queue: a later cron run that sees the same HEAD skips the request.

## Configuration

[compose.yml](../compose.yml) mounts `source_md_articles` read-write here and
read-only in the web app.

| Variable | Script default / deployment setting |
| --- | --- |
| `GITHUB_REPO` | `https://github.com/hanjie-chen/knowledge-base.git` |
| `REPO_BRANCH` | `main` |
| `SOURCE_ARTICLES_DIRECTORY` | `/articles/src`; a custom location must exist and be writable at startup |
| `CRON_SCHEDULE` | Script default: `0 */4 * * *`; Compose overrides it with `0 3 * * *` |
| `TZ` | Compose sets `UTC` |
| `WEB_APP_REINDEX_URL` | Unset in the script; Compose sets `http://web-app:5000/internal/reindex` |
| `REIMPORT_ARTICLES_TOKEN` | Unset by default; must match the web app token for successful reindexing |
| `REQUIRE_REINDEX` | Unset by default; Content Sync passes `1` to always reindex and fail on reindex errors |

If changing the source mount path, update the Compose health check too: it
currently checks the literal `/articles/src/.git` path.

## Operational Checks

Run from the repository root:

```bash
# Inspect recent sync and cron messages.
docker compose logs --tail=100 articles-sync

# Inspect the local mirror's revision without updating it.
docker compose exec -T articles-sync sh -lc 'su-exec appuser git -C "$SOURCE_ARTICLES_DIRECTORY" rev-parse HEAD'

# Update the mirror; this can discard local changes and trigger web-app writes.
docker compose exec -T articles-sync su-exec appuser /usr/local/bin/update-articles.sh
```

The health check only verifies that `.git` exists and `crond` is running. It does
not prove Git integrity, successful remote fetching, successful reindexing or
fresh rendered pages. For stale content, inspect the fetch/reset and reindex log
messages separately, then check web-app logs and token configuration without
printing the token. Web-app import may also skip unchanged canonical HTML; see
[Rebuild Behavior](../web-app/README.md#rebuild-behavior).

The update script has no synchronization lock. Workflow concurrency coordinates
GitHub-triggered production jobs, but does not serialize the container's cron or
manual invocations with them; avoid overlapping updates when troubleshooting.

When editing shell scripts, run from the repository root:

```bash
shellcheck -x scripts/deploy/*.sh articles-sync/*.sh
```
