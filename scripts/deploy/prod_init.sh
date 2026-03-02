#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/service_wait.sh"

RUN_SMOKE_CHECK="${RUN_SMOKE_CHECK:-1}"
ARTICLES_SYNC_READY_TIMEOUT="${ARTICLES_SYNC_READY_TIMEOUT:-180}"

echo "[init] Starting articles-sync (to sync markdown source)..."
docker compose -f compose.yml up -d articles-sync
wait_for_service_state articles-sync healthy "${ARTICLES_SYNC_READY_TIMEOUT}" "2" "init"

echo "[init] Initializing database and importing articles..."
docker compose -f compose.yml run --rm -T web-app python scripts/init_db.py

echo "[init] Starting all services..."
docker compose -f compose.yml up -d

if [[ "${RUN_SMOKE_CHECK}" == "1" ]]; then
  echo "[init] Running smoke checks..."
  ./scripts/deploy/smoke_check.sh
fi

echo "[init] Done."
