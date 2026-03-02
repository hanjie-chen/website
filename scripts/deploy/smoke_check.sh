#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://127.0.0.1}"
HOST_HEADER="${HOST_HEADER:-hanjie-chen.com}"

request() {
  local path="$1"
  curl -kfsS "${BASE_URL}${path}" -H "Host: ${HOST_HEADER}"
}

echo "[smoke] Checking /"
request "/" >/dev/null

echo "[smoke] Checking /articles"
request "/articles" >/dev/null

echo "[smoke] All checks passed."
