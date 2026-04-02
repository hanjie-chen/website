# Article Sync Service

This directory contains the container image and runtime scripts for the article synchronization service.

The service is responsible for keeping the Markdown source repository up to date inside the shared article volume and notifying the Flask app when a content refresh is required.

## Purpose

`articles-sync` covers three responsibilities:

- bootstrap the shared article source directory on first start
- periodically sync the latest branch state from the upstream Git repository
- trigger the web app reindex endpoint only when the repository HEAD changes

The local checkout is intentionally shallow. The service only keeps the latest branch state needed for rendering and import, not the full Git history.

This service is part of the production content pipeline. It does not render or import articles itself. That work happens inside the `web-app` service after a successful reindex trigger.

## Files

### `Dockerfile`

Builds the lightweight Alpine-based runtime image used by the `articles-sync` service.

What it installs:

- `git` for repository sync
- `dcron` for scheduled pulls
- `tini` as PID 1
- `curl` for the reindex request
- `su-exec` so Git operations run as the non-root application user

### `init.sh`

Container entry flow.

What it does:

- resolves the article source directory and repo settings
- resolves the cron schedule used for periodic syncs
- verifies that `su-exec` is available
- shallow-clones the source repository into `/articles/src` if the directory is empty
- otherwise runs an immediate update via `update-articles.sh`
- installs the root crontab entry for scheduled syncs
- starts `crond` in the foreground

### `update-articles.sh`

Main sync workflow.

What it does:

- enters the shared article source directory
- verifies that the directory is a Git repository
- records the current `HEAD`
- updates `origin` to the configured repository URL
- runs `git fetch --depth=1 origin "$REPO_BRANCH"`
- hard-resets the working tree to `FETCH_HEAD`
- removes stale untracked files with `git clean -fd`
- compares the previous and current `HEAD`
- skips reindex if nothing changed
- sends a `POST` request to the web app reindex endpoint when new content is detected
- falls back to a fresh shallow clone if the local mirror is missing or cannot be updated safely

### `cron-heartbeat-sync.sh`

Thin cron wrapper around `update-articles.sh`.

What it does:

- writes a scheduled-sync log line
- executes `update-articles.sh` as `appuser`

## Runtime Flow

### Initial Start

When the container starts for the first time:

1. `init.sh` checks whether `/articles/src` is empty.
2. If empty, the upstream article repository is shallow-cloned into the shared volume.
3. If not empty, the service performs an immediate sync with `update-articles.sh`.
4. A recurring cron job is installed.
5. `crond` stays in the foreground so the container remains alive.

### Scheduled Sync

The default cron entry configured by `init.sh` is:

```cron
0 */4 * * * /usr/local/bin/cron-heartbeat-sync.sh >> /proc/1/fd/1 2>&1
```

This means the container performs one scheduled sync every 4 hours and writes cron output to container stdout.

The schedule can be overridden with `CRON_SCHEDULE`.

### Reindex Trigger

`update-articles.sh` only notifies the web app when the Git `HEAD` changes.

This avoids unnecessary reindex work when the upstream branch has no new commits.

The update flow mirrors the latest remote branch state instead of preserving local history. This makes the sync resilient to force-pushes or to recreating the upstream repository with the same name.

If the reindex endpoint is configured, the service sends:

- `POST $WEB_APP_REINDEX_URL`
- optionally with `X-REIMPORT-ARTICLES-TOKEN` when the token is present

### Why Not `git pull`?

This service is not a developer working copy. It is a disposable mirror of the latest branch state used for rendering and import.

`git pull` is designed for continuing local branch history through merge or rebase. That makes it a weaker fit for this service because the upstream repository may be force-pushed, rewritten, or even deleted and recreated with the same name.

The current sync flow is intentionally mirror-oriented:

- `git fetch --depth=1` downloads only the latest remote state
- `git reset --hard FETCH_HEAD` makes the local checkout match that state exactly
- `git clean -fd` removes stale local files that no longer exist upstream

This keeps disk usage low, avoids carrying full history, and makes the sync resilient when the upstream repository history is replaced entirely.

## Environment Variables

### Repository Settings

- `GITHUB_REPO`
  - upstream Markdown repository URL
- `REPO_BRANCH`
  - branch to clone and pull
- `SOURCE_ARTICLES_DIRECTORY`
  - shared directory used by both `articles-sync` and `web-app`
- `CRON_SCHEDULE`
  - cron expression used by `crond`; default is `0 */4 * * *`
- `TZ`
  - optional container timezone for cron and log timestamps; `compose.yml` sets this service to `UTC`

### Reindex Settings

- `WEB_APP_REINDEX_URL`
  - internal endpoint used to trigger content refresh
- `REIMPORT_ARTICLES_TOKEN`
  - optional shared secret passed as `X-REIMPORT-ARTICLES-TOKEN`

## Service Behavior Notes

- Git operations run as `appuser`, not as root.
- Cron is installed for root, but the actual sync command switches to `appuser`.
- The service treats `/articles/src` as a disposable mirror of the latest branch state.
- Sync and cron log lines include the timezone offset and timezone name to make commit-time comparisons easier.
- The Compose health check for `articles-sync` only verifies:
  - `/articles/src/.git` exists
  - `crond` is running
- A healthy `articles-sync` container does not guarantee that the last pull changed content. It only means the sync service is ready to operate.
- Reindex is best-effort after a successful pull. If the POST fails, the failure is logged, but the sync script itself still completes.

## Related Files

- [`compose.yml`](../compose.yml)
  - service definition, environment variables, and health check
- [`web-app/app.py`](../web-app/app.py)
  - exposes the `/internal/reindex` endpoint used by this service
- [`scripts/deploy/prod_init.sh`](../scripts/deploy/prod_init.sh)
  - waits for `articles-sync` before initializing the rest of the stack
- [`scripts/deploy/ensure_db_ready.sh`](../scripts/deploy/ensure_db_ready.sh)
  - also waits for `articles-sync` before DB repair work

## Common Operational Notes

If content seems stale in production, the first things to check are:

1. whether `articles-sync` is healthy
2. whether `/articles/src` is still a valid Git repository
3. whether the local mirror can still fetch the configured branch from the remote repository
4. whether the web app reindex endpoint is reachable from the container
5. whether `REIMPORT_ARTICLES_TOKEN` matches the web app configuration
