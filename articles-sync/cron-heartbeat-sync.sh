#!/bin/sh
set -e

echo "[$(/bin/date '+%Y-%m-%d %H:%M:%S %z %Z')] [CRON] scheduled sync triggered"
exec /sbin/su-exec appuser /usr/local/bin/update-articles.sh
