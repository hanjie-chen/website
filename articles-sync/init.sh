#!/bin/sh
set -e

ARTICLES_DIR="${SOURCE_ARTICLES_DIRECTORY:-/articles/src}"
GITHUB_REPO="${GITHUB_REPO:-https://github.com/hanjie-chen/knowledge-base.git}"
REPO_BRANCH="${REPO_BRANCH:-main}"
SU_EXEC_BIN="${SU_EXEC_BIN:-}"

# record the time
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INIT] $1"
}
# record the repo and branch message
log_message "Using GITHUB_REPO: $GITHUB_REPO"
log_message "Using REPO_BRANCH: $REPO_BRANCH"
if [ -z "$SU_EXEC_BIN" ]; then
    SU_EXEC_BIN="$(command -v su-exec || true)"
fi
if [ -z "$SU_EXEC_BIN" ]; then
    log_message "su-exec command not found"
    exit 1
fi

# initial the repo or update the repo
if [ -z "$(ls -A "$ARTICLES_DIR")" ]; then
    log_message "Initializing articles directory..."
    cd "$ARTICLES_DIR"
    # Only the latest tree is needed for article rendering, so keep the clone shallow.
    if ! "$SU_EXEC_BIN" appuser git clone --depth=1 -b "$REPO_BRANCH" "$GITHUB_REPO" .; then
        log_message "Git clone failed"
        exit 1
    fi
    log_message "Repository cloned successfully"
else
    log_message "Articles directory exists, performing update..."
    if ! "$SU_EXEC_BIN" appuser /usr/local/bin/update-articles.sh; then
        log_message "run update-articles.sh scripts failed"
        exit 1
    fi
fi

# Create a temporary crontab file
cat << EOF > /tmp/crontab
0 16 * * * /usr/local/bin/cron-heartbeat-sync.sh >> /proc/1/fd/1 2>&1
EOF

# Install crontab for root, then delete it
crontab -u root /tmp/crontab
rm /tmp/crontab

# 设置 umask
umask 022

# set crond as main process
exec crond -f -L /dev/stdout -l 6
