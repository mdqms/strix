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
| H7 | `strix/agents/prompt.py` | `_resolve_skills` loads `coordination/blind_challenger` (T6) unless `STRIX_DISABLE_BLIND_CHALLENGER` is set (the T4 A/B toggle); added `import os`. | `_resolve_skills` is the one selector that decides which coordination skills reach an agent's system prompt. Additive + an env guard. |
| H8 | `strix/interface/scope_guard.py` | New module: deny-by-default approved-target matcher (plan item 33, T10). | New file; importable + unit-tested. No existing file changed. (Listed for completeness; not a conflict point.) |
| H9 | `strix/interface/viewer/server.py` | Added `/api/chat` POST (`_handle_chat`, item 9) and `/api/memory-graph` GET (`_handle_memory_graph`, item 10), both session-gated. Logic lives in new files `chat.py` / `memory_graph.py`. | `do_POST`/`_handle_api` dispatch is the one place to add viewer routes. Additive; heavy logic in new files. |

New packaged skill (new file, minimal conflict risk): `strix/skills/coordination/blind_challenger.md` — the blind-challenger protocol driven through the existing `create_agent`/`wait_for_agents` tools.

## Fork skills directory (`fork_skills/`, plan T8)

`fork_skills/` holds CSO-derived audit skills (items 21-29), loaded via the T2
`$STRIX_SKILLS_DIR` hook — no upstream-file edits. Host Strix must export:

```bash
export STRIX_SKILLS_DIR="$PWD/fork_skills"   # from the repo root
```

They appear as user-selectable `custom/` skills an agent loads on demand with
`load_skill`: `secrets_git_history`, `dependency_supply_chain`,
`cicd_pipeline_security`, `infrastructure_as_code`, `integrations_webhooks`,
`llm_agent_mcp_config`, `agent_skill_supply_chain`, `stride_threat_model`,
`data_classification`. Content is adapted from gstack CSO (MIT); see
`fork_skills/NOTICE`.

## Viewer run-chat (plan T9, item 9)

Backend slice done: `strix/interface/viewer/chat.py` assembles a run's artifacts
(status, findings, report) into a bounded context and answers a question with the
configured LLM (`STRIX_LLM` / `LLM_API_KEY` / `LLM_BASE_URL`); `POST /api/chat`
(hook H9) is session-gated. Chat is 503 "unavailable" when no model is set.

Frontend slice done: `frontend/src/components/ChatPanel.tsx` is a collapsible panel
(D4) rendered beside `RunDetails` in `App.tsx`, using the shared `Markdown`
renderer so answers are flat markdown blocks, not bubbles (D5); warm empty state
(D6); keyboard send (Enter), visible focus rings, 44px targets (D7). `askRun()` in
`serverSource.ts` posts to `/api/chat`; a 503 shows a "no model configured" notice.
The committed SPA bundle (`static/assets/*`) is rebuilt from this source with
`cd frontend && npm install && npm run build` — rerun that after any frontend edit.

Graph view done (item 10): `frontend/src/components/MemoryGraph.tsx` renders the
target's memory graph with React Flow + dagre (reusing the AgentGraph stack), a warm
"no memory yet" empty state (D6), and keyboard pan/zoom controls (D7). Backend:
`strix/interface/viewer/memory_graph.py` + `GET /api/memory-graph` returns the
target's graph, or `{available:false}` when memory can't be reached (surfaced, never
an error).

**Memory-adapter seam (needs live validation):** the viewer reaches memory over HTTP
at `$STRIX_MEMORY_URL`, expecting `GET /graph?group_id=<target>` to return
`{nodes:[{id,label,type}], edges:[{source,target,label}]}`. The Graphiti MCP server
exposes *search tools*, not this REST shape, so a thin adapter in front of it is
required. `to_reactflow()` and the unavailable paths are unit-tested; the live
Graphiti query must be validated against a running service. This is the data source
item 6 never grew (memory was wired as an MCP server the scan agent writes to, not a
queryable module) — building that query module is the remaining memory work.

## MiroFish integration (optional, plan items 11-12)

Two optional, security-adjacent uses of the MiroFish simulation engine: persona
test-data for a staging app (11) and disclosure-reaction rehearsal (12).

- **License boundary:** MiroFish is AGPL-3.0; this fork is Apache-2.0. The fork
  contains **no MiroFish source** — only `strix/integrations/mirofish.py`, an HTTP
  client that imports nothing from MiroFish and calls a **separate** MiroFish process
  at `$STRIX_MIROFISH_URL`. MiroFish runs from its own image via
  `deploy/mirofish.compose.yml` as its own compose project. Never vendor or import
  it. (A test asserts no top-level `mirofish` module is imported.)
- **Adapter seam (needs live validation):** MiroFish's stock app has no endpoint for
  these jobs, so the separate service must expose a thin adapter
  (`POST /personas`, `POST /rehearse`); the contract is in
  `deploy/mirofish/README.md`. The client's request/response shaping and the
  unavailable paths are unit-tested; the live calls and the adapter are built and
  verified against a running MiroFish.

This is the last plan item. Validation gaps that remain across the fork (all need a
live stack): the memory-graph adapter (`$STRIX_MEMORY_URL`), the MiroFish adapter
above, and the T4 XBEN runs.

### Adapters submodule

Both seam adapters live in a separate repo referenced here as the
`strix-fork-adapters/` submodule (github.com/mdqms/strix-fork-adapters): an
Apache-2.0 memory-graph adapter and an AGPL-3.0 MiroFish adapter. Keeping them in
their own repo keeps the AGPL code out of this Apache tree (the submodule stores
only a pointer, not the code). Run `git submodule update --init` (or
`git clone --recursive`) to materialise it; the `memory-adapter` compose service
builds from `strix-fork-adapters/memory-graph-adapter`.

## Operations (plan T10)

Fork-owned ops live in `deploy/` + the scope-guard module; see `deploy/README.md`
for usage and cron/systemd examples.

- **Telemetry off (31):** `scripts/strix-scoped` defaults `STRIX_TELEMETRY=false`.
- **Approved-target guard (33):** `scripts/strix-scoped` validates every
  `-t/--target` against the allowlist via `strix/interface/scope_guard.py`;
  deny by default.
- **Backups + retention (5):** `deploy/backup.sh` / `deploy/restore.sh`
  (restore kills-without-save then starts — a plain restart clobbers the rdb).
- **Scheduled diff scans (32):** `deploy/scheduled-scan.sh`, run through the guard.

## XBEN eval (plan T4)

`evals/xben/` is before/after eval scaffolding (decision D9): run XBEN three ways —
baseline (hosted model), local model, challenger on — and gate on a no-regression
threshold. `compare.py` is the gate (pure + unit-tested); `run_arm.sh` +
`arms.example.sh` run the arms and need the benchmark repo, Docker, and LLM keys.
The challenger arm toggles with `STRIX_DISABLE_BLIND_CHALLENGER`. See
`evals/xben/README.md`. Not runnable without that infra — it is real-infra eval
scaffolding, not a unit test.

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
