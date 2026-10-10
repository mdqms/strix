# Strix fork self-hosted stack

Services-only Docker Compose stack (plan T3). Strix itself runs **on the host**
via the `uv` env; this stack provides the sandbox daemon, the Docker API gateway,
and the memory graph.

## What's here

| Service | Image | Role | Host port |
|---|---|---|---|
| `dind` | `docker:28-dind` (pinned by digest) | Throwaway Docker daemon for scan sandboxes (D1). Disposable: a sandbox escape reaches this, not the host daemon. | none |
| `docker-proxy` | `tecnativa/docker-socket-proxy:0.3.0` (digest) | Restricted Docker API gateway in front of `dind` (D8.2). | `127.0.0.1:2375` |
| `memory` | `zepai/knowledge-graph-mcp` | Graphiti MCP + FalkorDB in one container (D3-eng). | `127.0.0.1:8000` (MCP) |

Everything talks over the internal `strixnet` bridge; the only published ports
bind to `127.0.0.1`, so nothing is reachable off this machine (D8.3).

## Run it

```bash
cp deploy/.env.example deploy/.env    # set STRIX_WORKSPACE and the LLM vars
cd deploy
docker compose up -d
```

Then point host-run Strix at the stack:

```bash
export DOCKER_HOST=tcp://127.0.0.1:2375         # sandboxes run in the throwaway daemon
export STRIX_SKILLS_DIR="$(git rev-parse --show-toplevel)/fork_skills"  # CSO audit skills (T8)
# memory MCP: add http://127.0.0.1:8000/mcp/ to ~/.strix/mcp-servers.json
```

## Security posture — read before trusting it

**The socket proxy is surface-reduction, not an escape boundary.** It filters
Docker API calls by *endpoint category*, not by the *parameters* inside an allowed
call. Strix's sandbox client legitimately needs `containers create` + `exec` +
`images`, and a `containers create` call can request host bind mounts and
`SYS_ADMIN` — so anything with proxy access can create an escape-capable container.
The proxy still blocks volumes, networks, swarm, secrets, services, build and
image push, which is real surface reduction, but it does **not** stop a sandbox
escape from reaching the daemon it fronts.

The boundary that matters here is `dind`: because sandboxes run in a **throwaway**
daemon (D1), an escape reaches a disposable container, not the host's Docker.
Reset it any time with `docker compose down -v` (wipes `dind-storage`). Do not
repoint `DOCKER_HOST` at the host daemon to "simplify" — that removes the only
real boundary.

Verified on 2026-10-10: through the proxy, `docker run` and image pull succeed
while `docker volume ls` / `docker network ls` are refused, and created containers
land in `dind` (empty `docker ps`), not on the host.

## Known gap (needs a real scan to close)

Strix bind-mounts scan source trees into sandbox containers **by host path**, and
the `dind` daemon resolves those paths on *its* filesystem. The compose mounts
`$STRIX_WORKSPACE` into `dind` at the identical absolute path so they line up, but
this has only been reasoned through, not proven end to end (a real scan needs an
LLM key). First real scan: confirm the sandbox sees the target source at the
expected path; if not, the `$STRIX_WORKSPACE` mount or the scan's working dir is
the thing to adjust.
