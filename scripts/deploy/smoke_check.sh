#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://127.0.0.1}"
HOST_HEADER="${HOST_HEADER:-hanjie-chen.com}"
SMOKE_TIMEOUT_SECONDS="${SMOKE_TIMEOUT_SECONDS:-20}"
SMOKE_INTERVAL_SECONDS="${SMOKE_INTERVAL_SECONDS:-2}"

request() {
  local path="$1"
  curl -kfsS "${BASE_URL}${path}" -H "Host: ${HOST_HEADER}"
}

wait_request_ok() {
  local path="$1"
  local elapsed=0

  while true; do
    if request "${path}" >/dev/null; then
      return 0
    fi

    if (( elapsed >= SMOKE_TIMEOUT_SECONDS )); then
      echo "[smoke] ${path} failed after ${SMOKE_TIMEOUT_SECONDS}s." >&2
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
