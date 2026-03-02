#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/service_wait.sh"

WAIT_HEALTH_TIMEOUT_SECONDS="${WAIT_HEALTH_TIMEOUT_SECONDS:-180}"
WAIT_HEALTH_INTERVAL_SECONDS="${WAIT_HEALTH_INTERVAL_SECONDS:-3}"

if [[ "$#" -eq 0 ]]; then
  set -- web-app nginx-modsecurity
fi

for svc in "$@"; do
  wait_for_service_state "${svc}" healthy "${WAIT_HEALTH_TIMEOUT_SECONDS}" "${WAIT_HEALTH_INTERVAL_SECONDS}" "wait"
done

echo "[wait] All target services are healthy."
