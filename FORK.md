# FORK.md — Strix fork operating notes

This is a fork of [usestrix/strix](https://github.com/usestrix/strix). Upstream is
active (about 5 commits/day), so this file exists to keep the fork mergeable: it
lists every change to an **upstream-owned file** (the merge-conflict surface) and
the procedure for pulling upstream in.

Design decisions behind the fork live in `../strix_fork_proposed.md` (CEO + eng +
design reviews). Key ones: all fork work stays in **new modules** where possible;
only the hooks below touch upstream files; upstream is synced **weekly** and a
merge is gated on the upstream test suite **plus** an XBEN benchmark run (decision
D7).

## Remotes

- `origin` → https://github.com/mdqms/strix (the fork's home; `main` lives here, push here)
- `upstream` → https://github.com/usestrix/strix (the source; fetch/merge from here for the weekly sync)

## Core-file hooks (edits to upstream-owned files)

Keep this list exhaustive. Every entry is a place a weekly merge can conflict.
Prefer new modules over adding to this list.

| # | File | Change | Why it can't be a new file |
|---|------|--------|----------------------------|
| H1 | `strix/skills/__init__.py` | Added `import os`, `_SKILL_DIR_ENV_VAR`, and `register_skill_dirs_from_env()` (reads `$STRIX_SKILLS_DIR`, os.pathsep-separated, registers each dir ahead of built-ins). | The function belongs beside `register_skill_dir`/`_EXTRA_SKILL_DIRS` which live here. Additive only; no upstream lines changed. |
| H2 | `strix/interface/main.py` | Added a call to `register_skill_dirs_from_env()` at the top of `main()`, right after `setup_console_logging()`. | `main()` is the one startup path shared by view/cloud/scan; the hook must run before any skill resolution. 3-line additive block. |
| H3 | `strix/tools/reporting/tool.py` | Added `_VALID_EVIDENCE_STATE` and an optional, validated `evidence_state` param (hypothesis / static_trace / reproduced) to `create_vulnerability_report` + its impl and the update path (plan item 13). | The finding schema, its validation, and the agent tool signature all live here. Additive; existing params and assertions unchanged. |
| H4 | `strix/report/state.py` | `add_vulnerability_report`: added `evidence_state` param (item 13); sets `report["stable_id"]` from the SARIF class fingerprint (item 15); mirrors `report_status` into `run.json` from the coverage document (item 18). | Explicit-kwargs method and the single artifact-write path; these must live here to persist. All additive. |
| H5 | `strix/report/sarif.py` | Added `"evidence_state"` to `result.properties.strix.*` (13); a public `stable_finding_id()` wrapping the existing class fingerprint (15); `report_status` into `run.properties` (18). | The strix.* mapping and the fingerprint functions are the one place this logic lives; reused, not duplicated. Additive. |
| H6 | `strix/report/coverage.py` | Added a public `report_status()` (complete/partial/not_assessed) reusing the existing `_completeness`, and attached `report_status` to the coverage document. | `_completeness` and the coverage document are here; computing status anywhere else would duplicate them. Additive. |

New files added by the fork (no conflict risk, not listed above): fork skill
directories loaded via `$STRIX_SKILLS_DIR`, `scripts/sync-upstream.sh`, the
`deploy/` stack, and fork tests (`tests/test_fork_*.py`).

## Weekly upstream sync (decision D7)

Run `scripts/sync-upstream.sh`. It fetches `upstream`, merges `upstream/main`, and
then **stops** and prints the gate commands — it never declares the merge good on
its own. The merge is accepted only when both gates pass:

1. **Upstream test suite:** `uv run pytest`
2. **XBEN benchmark:** run the fork against the [usestrix/benchmarks](https://github.com/usestrix/benchmarks)
   XBEN set (needs Docker + an LLM key). Compare the pass count to the pre-merge
   run; a drop blocks the merge.

If a gate fails, fix or revert on a branch before the merge reaches `main`.

**Not yet automated:** a scheduled CI job (e.g. a weekly GitHub Actions workflow)
that runs this sync + gates. It is deferred until a hosted CI environment with
Docker and an LLM key exists. Until then the sync is run by hand on the cadence above.

## Self-hosted stack (`deploy/`)

`deploy/docker-compose.yml` runs the services Strix talks to; Strix itself runs on
the host via the `uv` env. See `deploy/README.md` for setup. In short:

- `dind` — a **throwaway** Docker daemon where scan sandboxes run (decision D1), so
  a sandbox escape reaches a disposable daemon, not the host's.
- `docker-proxy` — a restricted Docker API gateway in front of `dind` (D8.2). It is
  **surface-reduction, not an escape boundary**: it blocks volumes/networks/swarm/
  secrets/build/push but must allow `containers create`/`exec`/`images`, and an
  allowed create can still request host mounts + `SYS_ADMIN`. The real boundary is
  that the daemon it fronts is disposable.
- `memory` — Graphiti MCP + FalkorDB in one container (D3-eng), reachable by host
  Strix at `http://127.0.0.1:8000/mcp/`.

Only `127.0.0.1` ports are published (D8.3). Host Strix uses
`DOCKER_HOST=tcp://127.0.0.1:2375`. All of `deploy/` is fork-owned (no upstream-file
edits), so it is outside the merge-conflict surface above.
