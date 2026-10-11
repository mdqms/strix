# Strix — self-hosted fork (in active development)

> **This is an unofficial, personal fork of [usestrix/strix](https://github.com/usestrix/strix),
> under active development. It is not the official Strix project and is not
> affiliated with or endorsed by Strix / usestrix.** For the official tool and its
> docs, go to [usestrix/strix](https://github.com/usestrix/strix) and
> [docs.strix.ai](https://docs.strix.ai).

Strix is an open-source autonomous AI penetration-testing tool: teams of LLM agents
that run a target in a sandbox, find vulnerabilities, and validate them with working
proofs-of-concept. This fork keeps that engine and adds a **self-hosted,
memory-aware setup** meant to run entirely on your own box with your own models.

**Status: work in progress.** Some pieces depend on a live stack (a local LLM,
Docker, the memory service) and are not fully validated end to end yet. Expect rough
edges and breaking changes; this is not a stable release. Every fork change, and
every edit to an upstream file, is tracked in **[FORK.md](FORK.md)**.

---

## Capabilities this fork adds (vs upstream)

| Capability | Upstream | This fork |
|---|---|---|
| Autonomous multi-agent pentest, sandboxed, with PoCs | ✅ | ✅ (inherited) |
| **Cross-scan memory** — per-target knowledge graph the agents read/write | ✖ | ✅ via a self-hosted Graphiti + FalkorDB memory service (MCP) |
| **Blind challenger** — an independent subagent tries to disprove a finding before it's filed | ✖ | ✅ always-on; toggle with `STRIX_DISABLE_BLIND_CHALLENGER` |
| **Evidence state** per finding (`hypothesis` / `static_trace` / `reproduced`), separate from confidence | ✖ | ✅ in JSON + SARIF |
| **Stable cross-run finding id** (survives file renames) | partial (SARIF fingerprint) | ✅ surfaced on the finding as `stable_id` |
| **Run report status** (`complete` / `partial` / `not_assessed`) | internal only | ✅ top-level in `run.json` + SARIF |
| **Extra audit skills** — secrets-in-git-history, dependency supply chain, CI/CD, IaC, integrations/webhooks, LLM/agent/MCP config, agent-skill supply chain, STRIDE, data classification | ✖ | ✅ 9 on-demand skills (`fork_skills/`) |
| **Sandbox isolation** — scans run in a throwaway Docker-in-Docker daemon behind a restricted socket proxy | raw Docker socket | ✅ `deploy/` stack |
| **Telemetry off by default** + **approved-target allowlist** gate | telemetry on; no target gate | ✅ `scripts/strix-scoped` |
| **Viewer: ask questions about a finished run** | ✖ | ✅ chat panel |
| **Viewer: target memory-graph view** | agent graph only | ✅ memory graph |
| **Backups + retention**, **scheduled diff scans** | ✖ | ✅ `deploy/` scripts |
| **Before/after XBEN eval** with a no-regression gate | ✖ | ✅ `evals/xben/` |
| **MiroFish integration** — persona test-data + disclosure rehearsal (optional) | ✖ | ✅ via a separate service (`strix-fork-adapters`) |

Items needing a live stack to be fully exercised: cross-scan memory + the graph
view (need the memory service), MiroFish, and the XBEN runs. See FORK.md.

---

## Requirements

Deploy these before the fork is useful:

1. **A Linux (or macOS) host with Docker + Docker Compose running.** The scan
   sandboxes and the self-hosted services are containers.
   Install Docker from [docs.docker.com](https://docs.docker.com/engine/install/);
   confirm with `docker version`.
2. **Python 3.12 and [`uv`](https://docs.astral.sh/uv/).** The fork pins 3.12
   (`.python-version`); `uv` installs it for you.
   `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. **An LLM reachable through LiteLLM** — either
   - a **local** model (recommended for self-hosting): e.g. [Ollama](https://ollama.com)
     (`ollama serve` + `ollama pull <model>`) or vLLM, or
   - a **hosted** provider (OpenRouter, OpenAI, Anthropic, …) and its API key.
   You set `STRIX_LLM` (a LiteLLM model id) + `LLM_API_KEY` (+ `LLM_BASE_URL` for a
   local server) when you run.
4. **The self-hosted stack** (`deploy/`), deployed in the step below: a throwaway
   DinD daemon, a socket proxy, the Graphiti + FalkorDB memory service, and the
   memory-graph adapter.
5. **(Optional) MiroFish**, only for items 11-12 (personas / disclosure rehearsal),
   run as its own service — see `deploy/mirofish/README.md`.

---

## How to deploy

Run from the repo root unless noted. `$REPO` is your clone of this fork.

```bash
# 1. Clone WITH the adapters submodule, and enter it
git clone --recursive https://github.com/mdqms/strix.git
cd strix                                   # this is $REPO
# (if you already cloned without --recursive:)
git submodule update --init

# 2. Build the Python env (uv installs Python 3.12 from .python-version)
uv sync

# 3. Configure the stack: set STRIX_WORKSPACE (dir that holds the code you scan)
#    and, for Graphiti's graph ingestion, an LLM for the memory service.
cp deploy/.env.example deploy/.env
$EDITOR deploy/.env                        # set STRIX_WORKSPACE + the memory LLM vars

# 4. Bring up the stack (dind + socket proxy + memory + memory-adapter),
#    internal network, only 127.0.0.1 ports published.
cd deploy && docker compose up -d && cd ..
#   proxy    -> 127.0.0.1:2375   (sandbox Docker API)
#   memory   -> 127.0.0.1:8000   (Graphiti MCP, the agents' memory read/write)
#   adapter  -> 127.0.0.1:8070   (memory graph for the viewer)

# 5. Approved-target allowlist (deny by default) — list only what you may test.
cp deploy/approved-targets.txt.example deploy/approved-targets.txt
$EDITOR deploy/approved-targets.txt

# 6. Point host Strix at the stack (put these in your shell profile or an env file).
source .venv/bin/activate                  # so `strix` and strix-scoped resolve
export DOCKER_HOST=tcp://127.0.0.1:2375                 # scans run in the throwaway daemon
export STRIX_SKILLS_DIR="$PWD/fork_skills"              # the 9 audit skills
export STRIX_MEMORY_URL=http://127.0.0.1:8070           # viewer memory-graph view
export STRIX_LLM="ollama_chat/llama3.1"                 # your LiteLLM model id
export LLM_API_KEY="local"                              # or your hosted key
# export LLM_BASE_URL="http://127.0.0.1:11434/v1"       # for a local server if needed

# 7. Wire cross-scan MEMORY into scans: the agents read/write it via the Graphiti
#    MCP server. Create ~/.strix/mcp-servers.json:
mkdir -p ~/.strix
cat > ~/.strix/mcp-servers.json <<'JSON'
[
  { "name": "memory", "transport": "http", "url": "http://127.0.0.1:8000/mcp/" }
]
JSON
```

Optional — MiroFish (items 11-12):

```bash
docker compose -f deploy/mirofish.compose.yml -p strix-mirofish up -d
export STRIX_MIROFISH_URL=http://127.0.0.1:5001
# then add the adapter blueprint to your MiroFish app — see
# strix-fork-adapters/mirofish-adapter/README.md
```

> Memory read vs write: the **agents write** memory through the MCP server
> (`:8000`) during a scan; the **viewer reads** the graph through the adapter
> (`:8070`). Both point at the same FalkorDB.

---

## How to run

With the venv active and the env from step 6 set:

```bash
# A scan, gated by the approved-target allowlist, telemetry off (strix-scoped
# forces STRIX_TELEMETRY=false). Headless (-n) is the supported mode.
scripts/strix-scoped -n -t example.com --scan-mode quick --max-budget 10

# White-box scan of local code. The target must live under $STRIX_WORKSPACE so the
# sandbox (in the throwaway daemon) can bind-mount it.
scripts/strix-scoped -n -t "$STRIX_WORKSPACE/myapp" --scan-mode standard

# Diff-scoped scan of a repo (what a scheduled run uses):
deploy/scheduled-scan.sh "$STRIX_WORKSPACE/myapp"

# Results land in strix_runs/<run>/ : penetration_test_report.md,
# vulnerabilities.json, findings.sarif (with evidence_state / stable_id /
# report_status), run.json. Exit codes: 0 clean, 1 fatal, 2 vulnerabilities found.

# Open the run viewer — the report, plus the run-chat panel and the target
# memory-graph view (needs STRIX_MEMORY_URL set):
strix view

# Back up / restore the memory graph:
deploy/backup.sh
deploy/restore.sh deploy/backups/falkordb-<stamp>.rdb

# Before/after benchmark (needs the XBEN set + keys): see evals/xben/README.md
```

The 9 audit skills load on demand: an agent picks one up with its `load_skill`
tool when it hits that surface (they're discoverable because `STRIX_SKILLS_DIR` is
set). Run `strix --help` for the full base CLI (inherited from upstream).

Only scan targets you are authorized to test.

---

## Relationship to upstream

This fork tracks `usestrix/strix` as the `upstream` remote and merges it in
periodically (`scripts/sync-upstream.sh`; see FORK.md). Most fork code lives in new
files to keep merges cheap; the few edits to upstream files are the hook list in
FORK.md. The engine, CLI, and base usage are upstream's.

## License

Apache-2.0, same as upstream; see [LICENSE](LICENSE). Strix's copyright and notices
are retained. The `strix-fork-adapters` submodule is mixed-license by folder: the
memory-graph adapter is Apache-2.0, the MiroFish adapter is AGPL-3.0 (it derives
from MiroFish) and is deliberately kept out of this Apache tree. Content adapted
from gstack CSO is MIT (`fork_skills/NOTICE`).
