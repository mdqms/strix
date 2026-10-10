# Strix — self-hosted fork (in active development)

> **This is an unofficial, personal fork of [usestrix/strix](https://github.com/usestrix/strix),
> under active development. It is not the official Strix project and is not
> affiliated with or endorsed by Strix / usestrix.** For the official tool, its
> docs, and its cloud service, go to [usestrix/strix](https://github.com/usestrix/strix)
> and [docs.strix.ai](https://docs.strix.ai).

Strix is an open-source autonomous AI penetration-testing tool: teams of LLM agents
that run a target in a sandbox, find vulnerabilities, and validate them with working
proofs-of-concept. This fork keeps that engine and adds a **self-hosted, memory-aware
setup** aimed at running everything on your own Linux box with your own models.

**Status: work in progress.** Pieces are landing incrementally; some depend on
infrastructure (a local LLM, Docker, a running memory service) and are not fully
validated end to end yet. Expect rough edges and breaking changes. Do not treat this
as a stable release.

## What this fork adds

All fork-specific changes, and every edit to an upstream file (the merge-conflict
surface), are tracked in **[FORK.md](FORK.md)**. In brief:

- **Self-hosted stack** (`deploy/`) — Docker Compose running scan sandboxes in a
  throwaway Docker-in-Docker daemon behind a restricted socket proxy, plus a
  Graphiti + FalkorDB memory service, all on an internal network with only the
  viewer published. See [`deploy/README.md`](deploy/README.md).
- **Cross-scan memory** — the agent reads/writes a per-target knowledge graph via
  the memory service (MCP), so later scans build on earlier ones.
- **Extra audit skills** (`fork_skills/`) — nine on-demand skills for areas the base
  tool covers less (git-history secrets, dependency supply chain, CI/CD, IaC,
  integrations/webhooks, LLM/agent/MCP config, agent-skill supply chain, STRIDE,
  data classification), loaded via `$STRIX_SKILLS_DIR`. Adapted from gstack CSO
  (MIT); see [`fork_skills/NOTICE`](fork_skills/NOTICE).
- **Blind challenger** — before a finding is filed, an independent subagent tries to
  disprove it without seeing the original conclusion, to cut false positives.
- **Stronger reporting** — each finding carries a separate `evidence_state`
  (hypothesis / static_trace / reproduced) and a stable cross-run id; each run gets a
  top-level `complete` / `partial` / `not_assessed` status. All in JSON and SARIF.
- **Viewer additions** — ask questions about a finished run, and view the target's
  memory graph, in the run viewer.
- **Ops** — a scoped launcher (`scripts/strix-scoped`) that enforces an
  approved-target allowlist and turns telemetry off, plus backup/retention and
  scheduled-scan scripts in `deploy/`.
- **XBEN eval harness** (`evals/xben/`) — before/after benchmark runs with a
  no-regression gate, to check the local model and the challenger don't lower results.

## Relationship to upstream

This fork tracks `usestrix/strix` as the `upstream` remote and merges it in
periodically (see [FORK.md](FORK.md) and `scripts/sync-upstream.sh`). Most fork code
lives in new files to keep merges cheap. The underlying engine, CLI, and usage are
upstream's — read upstream's docs for how to actually run a scan.

## Running it

The base tool runs as upstream documents (Python 3.12, `uv`, Docker). For the
self-hosted fork setup — the memory service, the sandbox isolation, the scoped
launcher, and the viewer additions — follow [`deploy/README.md`](deploy/README.md).

## License

Apache-2.0, the same as upstream Strix; see [LICENSE](LICENSE). This fork retains
Strix's copyright and notices. Content adapted from other MIT-licensed projects keeps
its own notice (e.g. [`fork_skills/NOTICE`](fork_skills/NOTICE)).

Only scan targets you are authorized to test.
