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

if [[ -n "${BRIEF_INGEST_TEST_TOKEN:-}" ]]; then
  echo "[smoke] Checking technical prose on the WAF-bypassed Daily Brief endpoint"
  # shellcheck disable=SC2016
  brief_status="$(curl -ksS -o /dev/null -w '%{http_code}' \
    "${BASE_URL}/internal/briefs" \
    -H "Host: ${HOST_HEADER}" \
    -H "Content-Type: application/json" \
    -H "X-DAILY-BRIEF-TOKEN: ${BRIEF_INGEST_TEST_TOKEN}" \
    --data-binary '{"schema_version":2,"date":"2026-07-25","generated_at":"2026-07-25T08:00:00+08:00","timezone":"Asia/Singapore","sections":{"ai":{"note":"special: `code` <tag> \"quotes\" 中文。","items":[{"hn_item_id":"49038433","title":"Claude <script> test","summary":"Yorishiro 是一个开源的 macOS 终端项目；技术讨论可能包含 1 OR 1=1 UNION SELECT password FROM users 等纯文本示例，但这些内容只会经过严格校验后作为文本存储并由 Jinja 转义。","content_status":"ok","why":"keywords: Claude","source_url":"https://example.com/story","discussion_url":"https://news.ycombinator.com/item?id=49038433","points":1,"comments":2}]},"non_ai_hot":{"note":"","items":[]}}}' \
    2>/dev/null)"
  if [[ "${brief_status}" != "200" && "${brief_status}" != "201" ]]; then
    echo "[smoke] Daily Brief ingestion probe returned HTTP ${brief_status}." >&2
    exit 1
  fi

  echo "[smoke] Confirming the 128 KiB Nginx body limit"
  oversized_body="$(mktemp)"
  trap 'rm -f "${oversized_body}"' EXIT
  dd if=/dev/zero of="${oversized_body}" bs=131073 count=1 status=none
  oversized_status="$(curl -ksS -o /dev/null -w '%{http_code}' \
    "${BASE_URL}/internal/briefs" \
    -H "Host: ${HOST_HEADER}" \
    -H "Content-Type: application/json" \
    -H "X-DAILY-BRIEF-TOKEN: ${BRIEF_INGEST_TEST_TOKEN}" \
    --data-binary "@${oversized_body}" \
    2>/dev/null)"
  rm -f "${oversized_body}"
  trap - EXIT
  if [[ "${oversized_status}" != "413" ]]; then
    echo "[smoke] Oversized Daily Brief returned HTTP ${oversized_status}; expected 413." >&2
    exit 1
  fi

  echo "[smoke] Confirming WAF protection remains active on public routes"
  public_waf_status="$(curl -ksS -o /dev/null -w '%{http_code}' \
    "${BASE_URL}/zh/articles?probe=1%20OR%201%3D1%20UNION%20SELECT%20password%20FROM%20users" \
    -H "Host: ${HOST_HEADER}" \
    2>/dev/null)"
  if [[ "${public_waf_status}" != "403" ]]; then
    echo "[smoke] Public-route SQLi probe returned HTTP ${public_waf_status}; expected WAF 403." >&2
    exit 1
  fi
fi

echo "[smoke] All checks passed."
