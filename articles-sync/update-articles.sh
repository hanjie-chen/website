#!/bin/sh
set -e

ARTICLES_DIR="${SOURCE_ARTICLES_DIRECTORY:-/articles/src}"
GITHUB_REPO="${GITHUB_REPO:-https://github.com/hanjie-chen/knowledge-base.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
WEB_APP_REINDEX_URL="${WEB_APP_REINDEX_URL:-}"
REIMPORT_ARTICLES_TOKEN="${REIMPORT_ARTICLES_TOKEN:-}"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SYNC] $1"
}

reclone_repository() {
    parent_dir="$(dirname "$ARTICLES_DIR")"
    repo_name="$(basename "$ARTICLES_DIR")"
    tmp_dir="${parent_dir}/.${repo_name}.reclone.$$"

    log_message "Recloning article repository from scratch"

    rm -rf "$tmp_dir"
    mkdir -p "$parent_dir"

    if /usr/bin/git clone --depth=1 -b "$REPO_BRANCH" "$GITHUB_REPO" "$tmp_dir"; then
        rm -rf "$ARTICLES_DIR"
        mv "$tmp_dir" "$ARTICLES_DIR"
    else
        rm -rf "$tmp_dir"
        log_message "Repository reclone failed"
        exit 1
    fi
}

echo "----------------------------------------"
log_message "Starting articles synchronization"
log_message "Using GITHUB_REPO: $GITHUB_REPO"
log_message "Using REPO_BRANCH: $REPO_BRANCH"

# This service mirrors the latest branch state only. It does not preserve local history.
if [ ! -d "$ARTICLES_DIR/.git" ]; then
    log_message "$ARTICLES_DIR is not a git repository, rebuilding local mirror"
    reclone_repository
fi

# go to articles dir
cd "$ARTICLES_DIR" || {
    log_message "Failed to change directory to $ARTICLES_DIR"
    exit 1
}

# get current HEAD
before_head="$(/usr/bin/git rev-parse HEAD 2>/dev/null || true)"

# Track the configured remote explicitly so a recreated repository with the same name
# can still be mirrored without depending on local branch history.
if ! /usr/bin/git remote set-url origin "$GITHUB_REPO"; then
    log_message "Failed to update origin URL, rebuilding local mirror"
    reclone_repository
    cd "$ARTICLES_DIR" || {
        log_message "Failed to change directory to $ARTICLES_DIR after reclone"
        exit 1
    }
fi

if /usr/bin/git fetch --depth=1 origin "$REPO_BRANCH"; then
    log_message "Git fetch successful"
else
    log_message "Git fetch failed, rebuilding local mirror"
    reclone_repository
    cd "$ARTICLES_DIR" || {
        log_message "Failed to change directory to $ARTICLES_DIR after reclone"
        exit 1
    }
fi

if /usr/bin/git reset --hard FETCH_HEAD && /usr/bin/git clean -fd; then
    log_message "Local mirror reset to remote branch state"
else
    log_message "Failed to reset working tree to fetched state"
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
