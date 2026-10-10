#!/usr/bin/env bash
# Memory-graph backup + retention (fork plan item 5 / decision A5).
#
# Dumps the FalkorDB (Redis) data from the `memory` service to a timestamped
# file, then prunes: graph snapshots older than 7 days, and run reports older
# than 30 days. Run nightly (see deploy/README.md for a cron/systemd example).
set -euo pipefail

COMPOSE_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${STRIX_BACKUP_DIR:-$COMPOSE_DIR/backups}"
SERVICE="${STRIX_MEMORY_SERVICE:-memory}"
SNAPSHOT_RETENTION_DAYS="${STRIX_SNAPSHOT_RETENTION_DAYS:-7}"
REPORT_RETENTION_DAYS="${STRIX_REPORT_RETENTION_DAYS:-30}"
REPORTS_DIR="${STRIX_RUNS_DIR:-}"   # optional: path to strix_runs/ for report pruning

mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="$BACKUP_DIR/falkordb-$stamp.rdb"

cd "$COMPOSE_DIR"
# Force a fresh point-in-time dump, then copy the rdb out of the container.
docker compose exec -T "$SERVICE" redis-cli -p 6379 SAVE >/dev/null
rdb_path="$(docker compose exec -T "$SERVICE" sh -lc 'redis-cli -p 6379 CONFIG GET dir | sed -n 2p')/dump.rdb"
docker compose cp "$SERVICE:$rdb_path" "$out"
echo "backup: $out ($(wc -c < "$out") bytes)"

# Retention: snapshots by age.
find "$BACKUP_DIR" -name 'falkordb-*.rdb' -type f -mtime +"$SNAPSHOT_RETENTION_DAYS" -print -delete || true

# Retention: run reports by age (only if a runs dir was given).
if [ -n "$REPORTS_DIR" ] && [ -d "$REPORTS_DIR" ]; then
  find "$REPORTS_DIR" -mindepth 1 -maxdepth 1 -type d -mtime +"$REPORT_RETENTION_DAYS" -print -exec rm -rf {} + || true
fi
echo "retention: snapshots>${SNAPSHOT_RETENTION_DAYS}d and reports>${REPORT_RETENTION_DAYS}d pruned"
