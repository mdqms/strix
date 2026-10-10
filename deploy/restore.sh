#!/usr/bin/env bash
# Restore a FalkorDB backup produced by backup.sh (fork plan item 5).
# Usage: ./restore.sh <path-to-falkordb-*.rdb>
set -euo pipefail

[ $# -eq 1 ] || { echo "usage: $0 <backup.rdb>" >&2; exit 2; }
SRC="$1"; [ -f "$SRC" ] || { echo "no such backup: $SRC" >&2; exit 2; }

COMPOSE_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE="${STRIX_MEMORY_SERVICE:-memory}"
cd "$COMPOSE_DIR"

dir="$(docker compose exec -T "$SERVICE" sh -lc 'redis-cli -p 6379 CONFIG GET dir | sed -n 2p')"
# Kill WITHOUT a shutdown save, then swap the rdb while the service is down, then
# start so it loads the restored snapshot. A `restart` would save-on-shutdown and
# overwrite the rdb we just copied in with the live (lost) data before reloading —
# verified the hard way; do not change this to stop/restart.
docker compose kill "$SERVICE" >/dev/null
docker compose cp "$SRC" "$SERVICE:$dir/dump.rdb"
docker compose start "$SERVICE" >/dev/null
echo "restored $SRC into $SERVICE; it loaded dump.rdb on startup."
