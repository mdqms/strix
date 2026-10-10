#!/usr/bin/env bash
# Scheduled diff scan of your own repo(s) (fork plan item 32).
#
# Runs a headless diff-scoped Strix scan through the scope guard (strix-scoped),
# so it only ever scans an approved target. Intended for cron/systemd (see
# deploy/README.md). Needs the self-hosted stack up and an LLM configured for
# the host Strix env.
set -euo pipefail

REPO="${1:-${STRIX_SCAN_REPO:?set STRIX_SCAN_REPO or pass a repo path}}"
SCOPED="$(cd "$(dirname "$0")/.." && pwd)/scripts/strix-scoped"

cd "$REPO"
git fetch --quiet origin 2>/dev/null || true

# -n headless; diff scan mode keeps it to what changed. The scope guard refuses
# if $REPO is not in the approved-target allowlist.
exec "$SCOPED" -n -t "$REPO" --scan-mode diff "$@"
