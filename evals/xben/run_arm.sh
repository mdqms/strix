#!/usr/bin/env bash
# Run one XBEN eval arm and emit a results JSON (plan T4).
#
# Runs headless Strix against each XBEN challenge target and records whether the
# arm solved it, into the shape compare.py expects:
#   {"arm": "<name>", "results": {"<challenge>": true|false, ...}}
#
# Prerequisites (NOT provided here — this needs real infra):
#   - the XBEN challenges from https://github.com/usestrix/benchmarks (XBEN/)
#   - the self-hosted stack up (DOCKER_HOST -> the throwaway daemon)
#   - an LLM configured for this arm (STRIX_LLM / LLM_API_KEY), set by arms.example.sh
#
# Pass detection is pluggable. Default: a challenge is "solved" if the headless
# run exits 2 (vulnerabilities found). Override with $XBEN_PASS_CMD, a command
# run per challenge that exits 0 on solved (e.g. the benchmark's own flag checker
# against the run dir). See evals/xben/README.md.
set -euo pipefail

ARM_NAME="${ARM_NAME:?set ARM_NAME (e.g. baseline-hosted, local-model, challenger-on)}"
XBEN_DIR="${XBEN_DIR:?set XBEN_DIR to the checked-out XBEN challenges directory}"
OUT="${OUT:-evals/xben/results/${ARM_NAME}.json}"
STRIX_BIN="${STRIX_BIN:-strix}"              # or scripts/strix-scoped
SCAN_MODE="${XBEN_SCAN_MODE:-standard}"
MAX_BUDGET="${XBEN_MAX_BUDGET:-10}"

mkdir -p "$(dirname "$OUT")"
printf '{\n  "arm": "%s",\n  "results": {\n' "$ARM_NAME" > "$OUT"
first=1

# Each immediate subdir of XBEN_DIR is one challenge. Adapt the target line to how
# the benchmark exposes each challenge (a URL, a compose target, a local dir).
for chal_dir in "$XBEN_DIR"/*/; do
  [ -d "$chal_dir" ] || continue
  chal="$(basename "$chal_dir")"
  target="${XBEN_TARGET_PREFIX:-}$chal_dir"   # override XBEN_TARGET_PREFIX for URL targets

  rc=0
  "$STRIX_BIN" -n -t "$target" --scan-mode "$SCAN_MODE" --max-budget "$MAX_BUDGET" >/dev/null 2>&1 || rc=$?

  if [ -n "${XBEN_PASS_CMD:-}" ]; then
    solved=false; CHAL="$chal" CHAL_DIR="$chal_dir" bash -c "$XBEN_PASS_CMD" && solved=true || solved=false
  else
    # default: exit 2 == vulnerabilities found == solved
    [ "$rc" = "2" ] && solved=true || solved=false
  fi

  [ $first -eq 1 ] || printf ',\n' >> "$OUT"
  first=0
  printf '    "%s": %s' "$chal" "$solved" >> "$OUT"
  echo "  $chal -> $solved (exit $rc)" >&2
done

printf '\n  }\n}\n' >> "$OUT"
echo "wrote $OUT" >&2
