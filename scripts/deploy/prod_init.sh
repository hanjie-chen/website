#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/deploy/service_wait.sh
source "${SCRIPT_DIR}/service_wait.sh"

# Wait timeout for initial article source sync.
ARTICLES_SYNC_READY_TIMEOUT="${ARTICLES_SYNC_READY_TIMEOUT:-600}"
# Wait timeout for core services to become healthy after full startup.
CORE_SERVICES_READY_TIMEOUT="${CORE_SERVICES_READY_TIMEOUT:-180}"

# 1) Start articles-sync first so markdown source is prepared in shared volume.
echo "[init] Starting articles-sync (to sync markdown source)..."
docker compose -f compose.yml up -d articles-sync
wait_for_service_state articles-sync healthy "${ARTICLES_SYNC_READY_TIMEOUT}" "2" "init"

# 2) Initialize DB and render/import articles.
# Use one-off container (`run --rm`) to avoid depending on web-app already running.
echo "[init] Initializing database and importing articles..."
docker compose -f compose.yml run --rm -T web-app python scripts/init_db.py

# 3) Start whole stack.
echo "[init] Starting all services..."
docker compose -f compose.yml up -d

# 4) Ensure core traffic path is healthy before smoke check.
wait_for_service_state web-app healthy "${CORE_SERVICES_READY_TIMEOUT}" "3" "init"
wait_for_service_state nginx-modsecurity healthy "${CORE_SERVICES_READY_TIMEOUT}" "3" "init"

# 5) Run smoke check.
echo "[init] Running smoke checks..."
./scripts/deploy/smoke_check.sh

echo "[init] Done."
