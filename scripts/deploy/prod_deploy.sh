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

# Pull only first-party app images built by CI.
docker compose pull web-app articles-sync

# Apply compose changes for all services.
docker compose up -d --remove-orphans

# nginx can keep stale upstream target after web-app container recreation.
# Reload nginx so upstream DNS/cache state is refreshed to current container IPs.
echo "[deploy] Reloading nginx-modsecurity..."
docker compose exec -T nginx-modsecurity nginx -s reload || docker compose restart nginx-modsecurity

docker compose ps
