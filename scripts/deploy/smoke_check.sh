#!/usr/bin/env bash
set -euo pipefail

# Post-deploy smoke checks for the public web path.
# Intended to run after services are healthy; keeps a short retry window for brief startup jitter.
BASE_URL="${BASE_URL:-https://127.0.0.1}"
HOST_HEADER="${HOST_HEADER:-hanjie-chen.com}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-60}"
SMOKE_INTERVAL_SECONDS="${SMOKE_INTERVAL_SECONDS:-2}"

request() {
  # Use in-host HTTPS endpoint with Host header so nginx server_name routing is exercised.
  local path="$1"
  curl -kfsS "${BASE_URL}${path}" -H "Host: ${HOST_HEADER}"
}

wait_request_ok() {
  # Retry each path for a short period to avoid flaky false negatives during warm-up.
  local path="$1"
  local elapsed=0

  while true; do
    if request "${path}" >/dev/null; then
      return 0
    fi

    if (( elapsed >= SMOKE_TIMEOUT_SECONDS )); then
      echo "[smoke] ${path} failed after ${SMOKE_TIMEOUT_SECONDS}s." >&2
      echo "[smoke] Recent web-app / nginx logs for troubleshooting:" >&2
      docker compose logs --tail=80 web-app nginx-modsecurity || true
      return 1
    fi

    sleep "${SMOKE_INTERVAL_SECONDS}"
    elapsed=$((elapsed + SMOKE_INTERVAL_SECONDS))
  done
}

echo "[smoke] Checking /"
wait_request_ok "/"

echo "[smoke] Checking /articles"
wait_request_ok "/articles"

echo "[smoke] All checks passed."
