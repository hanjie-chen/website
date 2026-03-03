#!/bin/sh

ARTICLES_DIR="${SOURCE_ARTICLES_DIRECTORY:-/articles/src}"
REPO_BRANCH="${REPO_BRANCH:-main}"
WEB_APP_REINDEX_URL="${WEB_APP_REINDEX_URL:-}"
REIMPORT_ARTICLES_TOKEN="${REIMPORT_ARTICLES_TOKEN:-}"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SYNC] $1"
}

echo "----------------------------------------"
log_message "Starting articles synchronization"
log_message "Using REPO_BRANCH: $REPO_BRANCH"

# go to articles dir
cd "$ARTICLES_DIR" || {
    log_message "Failed to change directory to /articles/src"
    exit 1
}

# check if it is a git repo
if [ ! -d ".git" ]; then
    log_message "/articles/src is not a git repository"
    exit 1
fi

# get current HEAD
before_head="$(/usr/bin/git rev-parse HEAD 2>/dev/null || true)"

# 执行 git pull
if /usr/bin/git pull origin "$REPO_BRANCH"; then
    log_message "Git pull successful"
else
    log_message "Git pull failed with exit code $?"
    exit 1
fi

# check if repo changed
after_head="$(/usr/bin/git rev-parse HEAD 2>/dev/null || true)"
if [ -n "$before_head" ] && [ -n "$after_head" ] && [ "$before_head" = "$after_head" ]; then
    log_message "No changes detected, skip reindex"
    log_message "Articles synchronization completed"
    echo "----------------------------------------"
    exit 0
fi

if [ -n "$WEB_APP_REINDEX_URL" ]; then
    log_message "Triggering reindex: $WEB_APP_REINDEX_URL"
    if [ -n "$REIMPORT_ARTICLES_TOKEN" ]; then
        if curl -fsS -X POST -H "X-REIMPORT-ARTICLES-TOKEN: $REIMPORT_ARTICLES_TOKEN" "$WEB_APP_REINDEX_URL" >/dev/null; then
            log_message "Reindex triggered successfully"
        else
            log_message "Reindex trigger failed"
        fi
    else
        if curl -fsS -X POST "$WEB_APP_REINDEX_URL" >/dev/null; then
            log_message "Reindex triggered successfully"
        else
            log_message "Reindex trigger failed"
        fi
    fi
else
    log_message "WEB_APP_REINDEX_URL is not set, skip reindex"
fi

log_message "Articles synchronization completed"
echo "----------------------------------------"
