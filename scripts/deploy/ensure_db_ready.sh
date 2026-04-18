#!/usr/bin/env bash
set -euo pipefail

# Ensure DB schema is usable after deployment.
# This script is intended to run after `prod_deploy.sh` and before strict healthy/smoke checks.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/deploy/service_wait.sh
source "${SCRIPT_DIR}/service_wait.sh"

DEPLOY_SHA="${1:-}"
AUTO_INIT_ON_MISSING="${AUTO_INIT_ON_MISSING:-1}"
DB_CHECK_WAIT_RUNNING_TIMEOUT_SECONDS="${DB_CHECK_WAIT_RUNNING_TIMEOUT_SECONDS:-90}"
DB_CHECK_WAIT_HEALTH_TIMEOUT_SECONDS="${DB_CHECK_WAIT_HEALTH_TIMEOUT_SECONDS:-180}"
DB_CHECK_WAIT_INTERVAL_SECONDS="${DB_CHECK_WAIT_INTERVAL_SECONDS:-3}"

if [[ -n "${DEPLOY_SHA}" ]]; then
  # Keep compose image tag resolution consistent with the current deployment target.
  export WEB_APP_IMAGE_TAG="${DEPLOY_SHA}"
  export ARTICLES_SYNC_IMAGE_TAG="${DEPLOY_SHA}"
fi

inspect_article_db() {
  # Run inside web-app container context so we inspect the same DB path and source tree
  # the app uses at runtime.
  docker compose exec -T web-app python - <<'PY'
import json
import sys

from config import Articles_Directory, SQLALCHEMY_DATABASE_URI
from db_health import assess_article_db

report = assess_article_db(Articles_Directory, SQLALCHEMY_DATABASE_URI)
print(json.dumps(report, ensure_ascii=False))

if not report["db_exists"]:
    sys.exit(2)
if not report["table_exists"]:
    sys.exit(3)
if report["expected_count"] == 0:
    sys.exit(5)
if report["db_count"] != report["expected_count"]:
    sys.exit(6)
sys.exit(0)
PY
}

# 1) Wait until the article source mirror is healthy so count-based checks see a stable tree.
echo "[db-check] Waiting for articles-sync source mirror..."
wait_for_service_state articles-sync healthy "${DB_CHECK_WAIT_HEALTH_TIMEOUT_SECONDS}" "${DB_CHECK_WAIT_INTERVAL_SECONDS}" "db-check"

# 2) Wait until web-app process is running so `docker compose exec` is available.
# Do not wait for healthy here: a bad DB may be the reason it cannot become healthy.
echo "[db-check] Checking article DB consistency..."
wait_for_service_state web-app running "${DB_CHECK_WAIT_RUNNING_TIMEOUT_SECONDS}" "${DB_CHECK_WAIT_INTERVAL_SECONDS}" "db-check"
if db_report="$(inspect_article_db)"; then
  echo "[db-check] DB is ready: ${db_report}"
  exit 0
else
  db_status=$?
fi

# 3) Decide whether the DB can be repaired safely.
case "${db_status}" in
  2)
    echo "[db-check] DB file is missing."
    ;;
  3)
    echo "[db-check] article_meta_data table is missing."
    ;;
  5)
    echo "[db-check] Source article count resolved to 0; refusing destructive DB repair." >&2
    exit 1
    ;;
  6)
    echo "[db-check] Article count mismatch detected: ${db_report}" >&2
    ;;
  *)
    echo "[db-check] Unexpected DB inspection failure (${db_status})." >&2
    exit 1
    ;;
esac

# 4) If DB is missing, incomplete, or stale, optionally repair by re-running init_db.py.
if [[ "${AUTO_INIT_ON_MISSING}" != "1" ]]; then
  echo "[db-check] DB is not ready and AUTO_INIT_ON_MISSING=${AUTO_INIT_ON_MISSING}." >&2
  exit 1
fi

echo "[db-check] Repairing DB with init_db.py..."
docker compose run --rm -T web-app python scripts/init_db.py

# 5) Verify again; fail fast if repair did not produce the expected article set.
echo "[db-check] Re-checking DB..."
wait_for_service_state web-app running "${DB_CHECK_WAIT_RUNNING_TIMEOUT_SECONDS}" "${DB_CHECK_WAIT_INTERVAL_SECONDS}" "db-check"
inspect_article_db
echo "[db-check] DB recovery completed."
