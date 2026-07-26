#!/usr/bin/env bash
set -euo pipefail

DEPLOY_SHA="${1:-}"

if [[ -z "${DEPLOY_SHA}" ]]; then
  echo "Usage: $0 <deploy_sha>" >&2
  exit 2
fi

echo "[deploy] Using image tag: ${DEPLOY_SHA}"

export WEB_APP_IMAGE_TAG="${DEPLOY_SHA}"
export ARTICLES_SYNC_IMAGE_TAG="${DEPLOY_SHA}"

# This non-secret rule file is bind-mounted into an unprivileged Nginx
# container. Ensure the container user can read it regardless of the checkout
# umask or permissions retained by an older deployment.
BRIEF_EXCLUSIONS_FILE="nginx-modsecurity/modsecurity/briefs-exclusions.conf"
if [[ ! -f "${BRIEF_EXCLUSIONS_FILE}" ]]; then
  echo "[deploy] Missing ${BRIEF_EXCLUSIONS_FILE}." >&2
  exit 1
fi
chmod 0644 "${BRIEF_EXCLUSIONS_FILE}"

running_image_ref() {
  local service="$1"
  local container_id

  container_id="$(docker compose ps -q "${service}" 2>/dev/null || true)"
  if [[ -z "${container_id}" ]]; then
    return 0
  fi

  docker inspect "${container_id}" --format '{{.Config.Image}}'
}

previous_nginx_image="$(running_image_ref nginx-modsecurity)"
previous_dozzle_image="$(running_image_ref dozzle)"

rollback_service() {
  local service="$1"
  local image_ref="$2"

  if [[ -z "${image_ref}" ]]; then
    echo "[rollback] No previous image recorded for ${service}; skipping." >&2
    return 0
  fi

  if [[ ! "${image_ref}" =~ ^[a-zA-Z0-9._/@:-]+$ ]]; then
    echo "[rollback] Refusing unsafe image reference for ${service}." >&2
    return 1
  fi

  echo "[rollback] Restoring ${service} to ${image_ref}..." >&2
  printf '{"services":{"%s":{"image":"%s"}}}\n' "${service}" "${image_ref}" \
    | docker compose -f compose.yml -f - up -d --no-deps "${service}"
}

rollback_third_party() {
  local rollback_status=0

  echo "[rollback] Restoring previous third-party container images..." >&2
  rollback_service dozzle "${previous_dozzle_image}" || rollback_status=1
  rollback_service nginx-modsecurity "${previous_nginx_image}" || rollback_status=1

  docker compose kill -s HUP nginx-modsecurity >/dev/null 2>&1 || true
  ./scripts/deploy/wait_services_healthy.sh nginx-modsecurity dozzle || rollback_status=1
  ./scripts/deploy/smoke_check.sh || rollback_status=1

  return "${rollback_status}"
}

fail_after_apply() {
  local reason="$1"

  echo "[deploy] ${reason}" >&2
  if ! rollback_third_party; then
    echo "[rollback] Automatic third-party rollback also failed." >&2
  fi
  exit 1
}

# Pull every production image explicitly. First-party services resolve to the
# deploy SHA; third-party services resolve to immutable digests from compose.yml.
if ! docker compose pull --policy always web-app articles-sync nginx-modsecurity dozzle; then
  echo "[deploy] Image pull failed before applying Compose changes." >&2
  exit 1
fi

# Apply compose changes for all services.
if ! docker compose up -d --remove-orphans; then
  fail_after_apply "Compose apply failed."
fi

# nginx can keep stale upstream target after web-app container recreation.
# Reload nginx so upstream DNS/cache state is refreshed to current container IPs.
echo "[deploy] Reloading nginx-modsecurity..."
if ! docker compose kill -s HUP nginx-modsecurity \
  && ! docker compose restart nginx-modsecurity; then
  fail_after_apply "Nginx reload/restart failed."
fi

if ! ./scripts/deploy/ensure_db_ready.sh "${DEPLOY_SHA}"; then
  fail_after_apply "Database readiness check failed."
fi

if ! ./scripts/deploy/wait_services_healthy.sh web-app nginx-modsecurity dozzle; then
  fail_after_apply "Service health validation failed."
fi

if ! ./scripts/deploy/smoke_check.sh; then
  fail_after_apply "Smoke validation failed."
fi

if ! ./scripts/deploy/verify_image_refs.sh nginx-modsecurity dozzle; then
  fail_after_apply "Running third-party image references do not match compose.yml."
fi

docker compose ps
