#!/usr/bin/env bash
set -euo pipefail

# Wrapper script: wait until target services become healthy.
# Core waiting logic lives in service_wait.sh.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/service_wait.sh"

# Per-service wait timeout/interval (seconds).
WAIT_HEALTH_TIMEOUT_SECONDS="${WAIT_HEALTH_TIMEOUT_SECONDS:-180}"
WAIT_HEALTH_INTERVAL_SECONDS="${WAIT_HEALTH_INTERVAL_SECONDS:-3}"

# If no services are passed, use core traffic path services by default.
if [[ "$#" -eq 0 ]]; then
  set -- web-app nginx-modsecurity
fi

# Wait each target service in sequence; fail fast on first timeout/error.
for svc in "$@"; do
  wait_for_service_state "${svc}" healthy "${WAIT_HEALTH_TIMEOUT_SECONDS}" "${WAIT_HEALTH_INTERVAL_SECONDS}" "wait"
done

echo "[wait] All target services are healthy."
