# Deploy Scripts

Production initialization, release deployment and validation helpers for the
Docker Compose stack. GitHub Actions calls these scripts over SSH; trigger and
credential setup live in the [workflow guide](../../.github/workflows/README.md).

## Prerequisites

Run commands from the repository root on the target host. Prepare Docker Compose,
Bash, curl, Python 3, access to the configured images, production environment
variables and Nginx TLS files. These scripts do not provision the host or create
credentials. See [compose.yml](../../compose.yml),
[application configuration](../../web-app/README.md#configuration) and
[Nginx documentation](../../nginx-modsecurity/README.md).

Use the production Compose configuration. Most helpers resolve the active Compose
configuration from the environment; `prod_init.sh` explicitly uses `compose.yml`
for startup. Wait helpers inspect container names directly, so the fixed names
in Compose must match the service names passed to them.

## Initialize or Deploy

### Initial Setup

On a prepared new host:

```bash
./scripts/deploy/prod_init.sh
```

[prod_init.sh](prod_init.sh) starts `articles-sync`, waits for its health check,
runs the application database initializer, then starts the full stack and checks
web-app/brief-cleanup/Nginx health plus HTTP smoke paths. Images use the tags
resolved from
Compose and the environment, defaulting to `latest` for application images.

**Initialization drops and recreates article database tables before importing
sources.** It can change article IDs and URLs. Do not use this as a routine
restart or rerender command. Daily Brief data is stored separately.

### Release Deployment

Use an existing CI-published commit SHA:

```bash
DEPLOY_SHA=<commit_sha>
./scripts/deploy/prod_deploy.sh "$DEPLOY_SHA"
./scripts/deploy/cleanup_old_images.sh "$DEPLOY_SHA"
```

[prod_deploy.sh](prod_deploy.sh) selects the `web-app` and `articles-sync` image
tags (`daily-brief-cleanup` shares the web-app tag), records running third-party
image references, explicitly pulls all five service images, applies Compose,
reloads Nginx, then checks database readiness,
service health, HTTP smoke paths and third-party image references.

Deployment and rollback reload Nginx with
`docker compose exec -T nginx-modsecurity nginx -s reload`. This refreshes the
active configuration without marking the container as manually stopped in
Docker, preserving automatic startup under its `unless-stopped` restart policy.
Deployment falls back to a container restart if the reload command fails.

The cleanup service removes expired Daily Brief files immediately on startup
and daily thereafter. Deploying retention therefore also removes existing briefs
older than the rolling 14-day window. Data retention and manual cleanup are
documented in the [web app guide](../../web-app/README.md#daily-briefs).

The script does not check out Git revisions. CD updates the host checkout to
latest `main` before invoking it with the successful CI run's SHA; host scripts,
Compose and mounted configuration may therefore be newer than the application
images. For manual deployment, verify the host checkout and environment as well
as the image tag. Run cleanup only after deployment succeeds.

## Database Repair and Rollback

[ensure_db_ready.sh](ensure_db_ready.sh) runs inside the deployment flow. It waits
for `articles-sync` to be healthy and `web-app` to be running, then uses
[db_health.py](../../web-app/db_health.py) to check the SQLite file/table and
compare article row count with valid discoverable source articles.

- Missing database/table or a count mismatch can trigger a rebuild through
  [init_db.py](../../web-app/scripts/init_db.py), which drops and recreates tables.
- `AUTO_INIT_ON_MISSING=0` disables automatic rebuilds and fails the readiness
  check instead. The default is `1`, including repair of count mismatches.
- When the database/table exists and the expected source count is zero, the
  check refuses repair. Missing database/table checks occur first; this is not
  an unconditional zero-source guard on every initialization path.
- Matching counts do not prove content freshness or generated HTML correctness.
  The sync health check also does not prove that the latest source fetch succeeded.

After Compose application begins, failures in apply, reload or validation cause
an attempt to restore the previous Nginx and Dozzle image references. Rollback
then waits for those services and reruns smoke checks. A service without a
recorded previous image is skipped; rollback itself can fail. The deployment
returns failure even when rollback succeeds.

This rollback does not restore application images, database contents, Git files
or mounted configuration. A pull failure before Compose apply exits without
attempting rollback. Keep database/source backups and recovery decisions separate
from this limited image rollback.

## Independent Checks

| Command | Scope |
| --- | --- |
| `./scripts/deploy/wait_services_healthy.sh [services...]` | Wait for Docker health; defaults to `web-app nginx-modsecurity` |
| `./scripts/deploy/smoke_check.sh` | Request `/`, `/zh/articles` and `/zh/briefs` through local Nginx |
| `./scripts/deploy/verify_image_refs.sh [services...]` | Compare running container image references with resolved Compose configuration; defaults to `nginx-modsecurity dozzle` |
| `./scripts/deploy/ensure_db_ready.sh [deploy_sha]` | Check and potentially rebuild the article DB as described above |

[service_wait.sh](service_wait.sh) is a sourced helper, not a standalone command.
[verify_image_refs.sh](verify_image_refs.sh) checks the container's configured
image reference string; it does not independently attest image contents.

### Smoke Check Boundaries

[smoke_check.sh](smoke_check.sh) defaults to `https://127.0.0.1` with
`Host: hanjie-chen.com`. It skips TLS certificate verification and does not follow
redirects. These checks exercise the host's Nginx/application path, not public DNS,
Cloudflare Access/cache rules or end-to-end certificate validity.

For an already prepared development stack:

```bash
COMPOSE_FILE=compose.yml:compose.dev.yml BASE_URL=https://127.0.0.1:8444 ./scripts/deploy/smoke_check.sh
```

Setting `BRIEF_INGEST_TEST_TOKEN` enables additional publishing, 128 KiB body-limit
and WAF-blocking probes. **The publishing probe writes or replaces today's brief
in `Asia/Singapore` and does not clean it up.** Use it with disposable test data,
as CI does; do not treat it as a read-only production check.

## Image Cleanup

[cleanup_old_images.sh](cleanup_old_images.sh) handles only the hardcoded
`website-web-app` and `website-articles-sync` GHCR repositories. Supply the actual
active release SHA. It keeps that tag, `latest` and one additional recent tag per
repository by default. `KEEP_PREVIOUS_RELEASES` changes the additional tag count.

Cleanup does not prune volumes, build cache, dangling images or third-party
images. Failed removals produce warnings and do not fail the script, so a
successful exit does not guarantee that disk space was reclaimed. Retained tags
are a local image cache, not a complete application rollback mechanism.

## Configuration Reference

| Variable | Default / use |
| --- | --- |
| `WEB_APP_IMAGE_TAG`, `ARTICLES_SYNC_IMAGE_TAG` | Set to the supplied SHA by release deployment; Compose defaults to `latest` |
| `ARTICLES_SYNC_READY_TIMEOUT`, `CORE_SERVICES_READY_TIMEOUT` | Initialization waits: 600 / 180 seconds |
| `AUTO_INIT_ON_MISSING` | `1`; set to `0` to disable automatic database rebuild |
| `WAIT_HEALTH_TIMEOUT_SECONDS`, `WAIT_HEALTH_INTERVAL_SECONDS` | Health wrapper: 180 / 3 seconds per service |
| `BASE_URL`, `HOST_HEADER` | Smoke target: `https://127.0.0.1`, `hanjie-chen.com` |
| `SMOKE_TIMEOUT_SECONDS`, `SMOKE_INTERVAL_SECONDS` | Basic smoke-path retries: 60 / 2 seconds per path |
| `BRIEF_INGEST_TEST_TOKEN` | Unset; enables probes that include a persistent test write |
| `KEEP_PREVIOUS_RELEASES` | `1`; additional local application image tags to retain |

Database-specific wait settings are defined at the top of `ensure_db_ready.sh`.
When editing scripts, run the repository's ShellCheck command and validate the
relevant deployment behavior; see the root [AGENTS.md](../../AGENTS.md).
