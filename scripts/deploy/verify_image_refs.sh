#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -eq 0 ]]; then
  set -- nginx-modsecurity dozzle
fi

status=0

for service in "$@"; do
  expected_image="$(
    docker compose config --format json \
      | python3 -c '
import json
import sys

service = sys.argv[1]
config = json.load(sys.stdin)
print(config["services"][service]["image"])
' "${service}"
  )"
  container_id="$(docker compose ps -q "${service}")"

  if [[ -z "${container_id}" ]]; then
    echo "[image-ref] ${service}: container is not running." >&2
    status=1
    continue
  fi

  actual_image="$(docker inspect "${container_id}" --format '{{.Config.Image}}')"

  if [[ "${actual_image}" != "${expected_image}" ]]; then
    echo "[image-ref] ${service}: mismatch" >&2
    echo "[image-ref]   expected: ${expected_image}" >&2
    echo "[image-ref]   actual:   ${actual_image}" >&2
    status=1
    continue
  fi

  echo "[image-ref] ${service}: ${actual_image}"
done

exit "${status}"
