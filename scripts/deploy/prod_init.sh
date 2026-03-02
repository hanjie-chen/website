#!/usr/bin/env bash
set -euo pipefail

RUN_SMOKE_CHECK="${RUN_SMOKE_CHECK:-1}"
ARTICLES_SYNC_READY_TIMEOUT="${ARTICLES_SYNC_READY_TIMEOUT:-180}"

wait_for_articles_sync() {
  local waited=0
  while true; do
    # Health status exists because articles-sync defines a healthcheck in compose.yml.
    local status
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' articles-sync 2>/dev/null || true)"

    if [[ "${status}" == "healthy" ]]; then
      echo "[init] articles-sync is healthy."
      return 0
    fi

    if [[ "${status}" == "exited" || "${status}" == "dead" ]]; then
      echo "[init] articles-sync is not running (status=${status})." >&2
      docker compose -f compose.yml logs --tail=80 articles-sync || true
      return 1
    fi

    if (( waited >= ARTICLES_SYNC_READY_TIMEOUT )); then
      echo "[init] Timeout waiting for articles-sync health (status=${status}, waited=${waited}s)." >&2
      docker compose -f compose.yml logs --tail=80 articles-sync || true
      return 1
    fi

    sleep 2
    waited=$((waited + 2))
  done
}

echo "[init] Starting articles-sync (to sync markdown source)..."
docker compose -f compose.yml up -d articles-sync
wait_for_articles_sync

echo "[init] Initializing database and importing articles..."
docker compose -f compose.yml run --rm -T web-app python scripts/init_db.py

echo "[init] Starting all services..."
docker compose -f compose.yml up -d

if [[ "${RUN_SMOKE_CHECK}" == "1" ]]; then
  echo "[init] Running smoke checks..."
  ./scripts/deploy/smoke_check.sh
fi

echo "[init] Done."
