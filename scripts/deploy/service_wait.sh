#!/usr/bin/env bash
# Shared waiting helpers for deploy scripts.

wait_for_service_state() {
  local service="$1"
  local desired_state="$2"   # healthy | running
  local timeout_seconds="${3:-180}"
  local interval_seconds="${4:-3}"
  local log_prefix="${5:-wait}"

  local inspect_format
  case "${desired_state}" in
    healthy)
      inspect_format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}'
      ;;
    running)
      inspect_format='{{.State.Status}}'
      ;;
    *)
      echo "[${log_prefix}] Unsupported desired state: ${desired_state}" >&2
      return 2
      ;;
  esac

  local elapsed=0
  while true; do
    local status
    status="$(docker inspect --format "${inspect_format}" "${service}" 2>/dev/null || true)"

    if [[ "${status}" == "${desired_state}" ]]; then
      echo "[${log_prefix}] ${service} is ${desired_state}."
      return 0
    fi

    if [[ "${status}" == "exited" || "${status}" == "dead" ]]; then
      echo "[${log_prefix}] ${service} is not running (${status})." >&2
      docker compose logs --tail=80 "${service}" || true
      return 1
    fi

    if (( elapsed >= timeout_seconds )); then
      echo "[${log_prefix}] Timeout waiting ${service} ${desired_state} (status=${status:-unknown}, waited=${elapsed}s)." >&2
      docker compose logs --tail=80 "${service}" || true
      return 1
    fi

    sleep "${interval_seconds}"
    elapsed=$((elapsed + interval_seconds))
  done
}
