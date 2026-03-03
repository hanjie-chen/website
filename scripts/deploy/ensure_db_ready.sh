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

has_article_table() {
  # Run inside web-app container context so we check the same DB path the app uses.
  docker compose exec -T web-app python - <<'PY'
import os
import sqlite3
import sys

db_path = "/app/instance/project.db"
if not os.path.exists(db_path):
    sys.exit(2)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='article_meta_data'")
row = cur.fetchone()
conn.close()
sys.exit(0 if row else 3)
PY
}

# 1) Wait until web-app process is running so `docker compose exec` is available.
# Do not wait for healthy here: missing DB table may be the reason it cannot become healthy.
echo "[db-check] Checking article_meta_data table..."
wait_for_service_state web-app running "${DB_CHECK_WAIT_RUNNING_TIMEOUT_SECONDS}" "${DB_CHECK_WAIT_INTERVAL_SECONDS}" "db-check"
if has_article_table; then
  echo "[db-check] DB is ready."
  exit 0
fi

# 2) If table is missing, optionally repair by re-running init_db.py.
if [[ "${AUTO_INIT_ON_MISSING}" != "1" ]]; then
  echo "[db-check] DB is not ready and AUTO_INIT_ON_MISSING=${AUTO_INIT_ON_MISSING}." >&2
  exit 1
fi

echo "[db-check] DB table missing, running init_db.py..."
# Ensure article source sync finished before init_db.py imports/renders content.
wait_for_service_state articles-sync healthy "${DB_CHECK_WAIT_HEALTH_TIMEOUT_SECONDS}" "${DB_CHECK_WAIT_INTERVAL_SECONDS}" "db-check"
docker compose run --rm -T web-app python scripts/init_db.py

# 3) Verify again; fail fast if repair did not produce required table.
echo "[db-check] Re-checking DB..."
wait_for_service_state web-app running "${DB_CHECK_WAIT_RUNNING_TIMEOUT_SECONDS}" "${DB_CHECK_WAIT_INTERVAL_SECONDS}" "db-check"
has_article_table
echo "[db-check] DB recovery completed."
