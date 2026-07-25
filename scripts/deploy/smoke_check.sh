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

echo "[smoke] Checking /zh/articles"
wait_request_ok "/zh/articles"

echo "[smoke] Checking /zh/briefs"
wait_request_ok "/zh/briefs"

if [[ -n "${BRIEF_WAF_TEST_TOKEN:-}" ]]; then
  echo "[smoke] Checking Daily Brief JSON through ModSecurity"
  # shellcheck disable=SC2016
  brief_status="$(curl -ksS -o /dev/null -w '%{http_code}' \
    "${BASE_URL}/internal/briefs" \
    -H "Host: ${HOST_HEADER}" \
    -H "Content-Type: application/json" \
    -H "X-DAILY-BRIEF-TOKEN: ${BRIEF_WAF_TEST_TOKEN}" \
    --data-binary '{"schema_version":1,"date":"2026-07-25","generated_at":"2026-07-25T08:00:00+08:00","timezone":"Asia/Singapore","sections":{"ai":{"note":"special: `code` <tag> \"quotes\" 中文。","items":[{"hn_item_id":"49038433","title":"Claude <script> test","summary":"支持 `code`、引号、<尖括号> 与中文标点。","why":"keywords: Claude","source_url":"https://example.com/story","discussion_url":"https://news.ycombinator.com/item?id=49038433","points":1,"comments":2}]},"non_ai_hot":{"note":"","items":[]}}}' \
    2>/dev/null)"
  if [[ "${brief_status}" != "200" && "${brief_status}" != "201" ]]; then
    echo "[smoke] Daily Brief WAF false-positive probe returned HTTP ${brief_status}." >&2
    exit 1
  fi

  echo "[smoke] Confirming non-excluded WAF rules remain active"
  sqli_status="$(curl -ksS -o /dev/null -w '%{http_code}' \
    "${BASE_URL}/internal/briefs" \
    -H "Host: ${HOST_HEADER}" \
    -H "Content-Type: application/json" \
    -H "X-DAILY-BRIEF-TOKEN: ${BRIEF_WAF_TEST_TOKEN}" \
    --data-binary '{"note":"1 OR 1=1 UNION SELECT password FROM users"}' \
    2>/dev/null)"
  if [[ "${sqli_status}" != "403" ]]; then
    echo "[smoke] SQL injection probe returned HTTP ${sqli_status}; expected WAF 403." >&2
    exit 1
  fi
fi

echo "[smoke] All checks passed."
