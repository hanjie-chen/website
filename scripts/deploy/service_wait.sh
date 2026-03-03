#!/usr/bin/env bash
# Shared waiting helpers for deploy scripts.
# This file is sourced by other scripts (it is not executed directly).

wait_for_service_state() {
  # Args:
  #   1) service name (compose container name)
  #   2) desired state: healthy | running
  #   3) timeout seconds (default 180)
  #   4) poll interval seconds (default 3)
  #   5) log prefix (default "wait")
  local service="$1"
  local desired_state="$2"   # healthy | running
  local timeout_seconds="${3:-180}"
  local interval_seconds="${4:-3}"
  local log_prefix="${5:-wait}"

  # Docker inspect format differs by target state:
  # - healthy: use Health.Status when present
  # - running: use container State.Status
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

  # Poll until desired state, timeout, or fatal state.
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
