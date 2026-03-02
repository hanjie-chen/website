#!/usr/bin/env bash
set -euo pipefail

DEPLOY_SHA="${1:-}"
AUTO_INIT_ON_MISSING="${AUTO_INIT_ON_MISSING:-1}"

if [[ -n "${DEPLOY_SHA}" ]]; then
  export WEB_APP_IMAGE_TAG="${DEPLOY_SHA}"
  export ARTICLES_SYNC_IMAGE_TAG="${DEPLOY_SHA}"
fi

has_article_table() {
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

echo "[db-check] Checking article_meta_data table..."
if has_article_table; then
  echo "[db-check] DB is ready."
  exit 0
fi

if [[ "${AUTO_INIT_ON_MISSING}" != "1" ]]; then
  echo "[db-check] DB is not ready and AUTO_INIT_ON_MISSING=${AUTO_INIT_ON_MISSING}." >&2
  exit 1
fi

echo "[db-check] DB table missing, running init_db.py..."
docker compose run --rm -T web-app python scripts/init_db.py

echo "[db-check] Re-checking DB..."
has_article_table
echo "[db-check] DB recovery completed."
