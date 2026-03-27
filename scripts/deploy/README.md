# Deploy Scripts

This directory contains the production deployment helpers used by the website stack.

The scripts here are designed for a Docker Compose based deployment on the production VM. They are used by GitHub Actions CD as well as by manual operational workflows such as first-time setup, health validation, and post-deploy cleanup.

## Purpose

The deploy scripts cover four main areas:

- first-time environment initialization
- routine production deploys by immutable image tag
- health and smoke verification after deploy
- cleanup of old first-party images on the production host

## Script Overview

### `prod_init.sh`

Initial bootstrap flow for a fresh production host.

What it does:

- starts `articles-sync` first
- waits until article source sync is healthy
- runs `scripts/init_db.py` in a one-off `web-app` container
- starts the full stack
- waits for `web-app` and `nginx-modsecurity` to become healthy
- runs smoke checks

Use this when:

- bringing up production for the first time
- recreating the host from scratch
- re-initializing the stack after persistent state was removed

### `prod_deploy.sh <deploy_sha>`

Regular production deploy by immutable image tag.

What it does:

- exports `WEB_APP_IMAGE_TAG` and `ARTICLES_SYNC_IMAGE_TAG`
- pulls first-party application images for the given SHA
- applies Compose changes with `docker compose up -d --remove-orphans`
- reloads `nginx-modsecurity` so upstream resolution stays fresh

Use this when:

- deploying a new CI-built release to production

### `ensure_db_ready.sh <deploy_sha>`

Post-deploy schema safety check for the SQLite database.

What it does:

- waits until `web-app` is at least running
- checks whether the `article_meta_data` table exists
- optionally re-runs `init_db.py` if the table is missing
- waits for `articles-sync` health before repair, because article import depends on synced source content

Use this when:

- a deploy has completed but the app may still be missing required DB state
- you want a safe recovery step before strict health and smoke validation

### `wait_services_healthy.sh [services...]`

Wrapper around the shared wait helpers.

What it does:

- waits until the target services reach `healthy`
- defaults to `web-app nginx-modsecurity` when no explicit services are passed

Use this when:

- validating the core traffic path after deploy
- waiting on a subset of services during troubleshooting

### `smoke_check.sh`

Short post-deploy public-path verification.

What it does:

- hits `https://127.0.0.1/` with the production `Host` header
- checks `/`
- checks `/articles`
- retries briefly to tolerate warm-up jitter

Use this when:

- confirming that the production HTTP path is actually serving traffic

### `cleanup_old_images.sh <deploy_sha>`

Post-deploy cleanup for first-party images on the production VM.

What it does:

- keeps `latest`
- keeps the current deployed SHA
- keeps a small number of previous SHA tags for rollback cache
- removes older `website-web-app` and `website-articles-sync` images

Use this when:

- you want to prevent old release images from consuming disk space on the VM

### `service_wait.sh`

Shared helper library sourced by other deploy scripts.

What it provides:

- `wait_for_service_state <service> <healthy|running> [timeout] [interval] [prefix]`

This file is not meant to be executed directly.

## Execution Flow

### Initial Production Setup

Use this path on a new host:

```bash
./scripts/deploy/prod_init.sh
```

High-level sequence:

1. sync markdown source
2. initialize DB and render/import content
3. start full stack
4. wait for core services
5. run smoke checks

### Regular Production Deploy

This is the routine deployment path used by CD:

```bash
./scripts/deploy/prod_deploy.sh <deploy_sha>
./scripts/deploy/ensure_db_ready.sh <deploy_sha>
./scripts/deploy/wait_services_healthy.sh web-app nginx-modsecurity
./scripts/deploy/smoke_check.sh
./scripts/deploy/cleanup_old_images.sh <deploy_sha>
```

GitHub Actions runs this sequence remotely over SSH from `.github/workflows/cd.yml`.

### Rollback-Oriented Notes

`cleanup_old_images.sh` keeps a limited rollback buffer by default. If you need to be more aggressive about disk usage, set:

```bash
KEEP_PREVIOUS_RELEASES=0
```

This reduces retained old images but removes the on-host rollback cache.

## Common Operations

### Deploy a Specific Release

```bash
DEPLOY_SHA=<commit_sha>
./scripts/deploy/prod_deploy.sh "${DEPLOY_SHA}"
./scripts/deploy/ensure_db_ready.sh "${DEPLOY_SHA}"
./scripts/deploy/wait_services_healthy.sh web-app nginx-modsecurity
./scripts/deploy/smoke_check.sh
```

### Run Only Health Waits

```bash
./scripts/deploy/wait_services_healthy.sh
./scripts/deploy/wait_services_healthy.sh web-app
```

### Run Only Smoke Checks

```bash
./scripts/deploy/smoke_check.sh
```

### Manually Clean Old First-Party Images

```bash
./scripts/deploy/cleanup_old_images.sh <deploy_sha>
```

More aggressive cleanup:

```bash
KEEP_PREVIOUS_RELEASES=0 ./scripts/deploy/cleanup_old_images.sh <deploy_sha>
```

## Environment Notes

### Required Inputs

- `prod_deploy.sh` requires a deploy SHA
- `ensure_db_ready.sh` accepts the deploy SHA so Compose resolves the same image tags
- `cleanup_old_images.sh` requires the active deploy SHA

### Key Environment Variables

- `WEB_APP_IMAGE_TAG`
- `ARTICLES_SYNC_IMAGE_TAG`
- `ARTICLES_SYNC_READY_TIMEOUT`
- `CORE_SERVICES_READY_TIMEOUT`
- `WAIT_HEALTH_TIMEOUT_SECONDS`
- `SMOKE_TIMEOUT_SECONDS`
- `KEEP_PREVIOUS_RELEASES`

### Assumptions

These scripts assume:

- Docker Compose is available on the production host
- the current working directory is the repository root
- Compose service names match `compose.yml`
- production traffic is served through `nginx-modsecurity`

## Related Files

- `.github/workflows/cd.yml`
- `compose.yml`
- `scripts/init_db.py`
