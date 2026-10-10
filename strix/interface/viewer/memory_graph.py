"""Target memory-graph source for the viewer (fork plan item 10, T9).

Fetches a target's memory graph (built by the agent during scans via the Graphiti
MCP memory service, item 6) and maps it to the React Flow shape the viewer renders
with the same stack as the agent graph.

The viewer is a separate process from both the scan and the memory service, so it
reaches memory over HTTP at ``$STRIX_MEMORY_URL``. The transport is isolated in
``_http_fetch`` and injectable, because the exact Graphiti wiring must be validated
against a running service: this module assumes a small adapter at
``$STRIX_MEMORY_URL`` that answers ``GET /graph?group_id=<target>`` with

    {"nodes": [{"id": "...", "label": "...", "type": "..."}, ...],
     "edges": [{"source": "...", "target": "...", "label": "..."}, ...]}

Graphiti's MCP server exposes search tools, not this REST shape, so that adapter is
the documented seam (see FORK.md). Everything here except the live HTTP call is
pure and unit-tested; memory being unavailable is a normal, surfaced state, never a
viewer error (matches the eng review: memory down -> keep going, say so).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

_HTTP_TIMEOUT_S = 5


class MemoryUnavailable(RuntimeError):
    """The memory service is not configured or not reachable."""


def target_key(run_record: dict[str, Any]) -> str | None:
    """Derive the per-target memory key (Graphiti group_id) for a run.

    Memory is scoped per target (decision D8.1). Use the first target's stable
    identifier from the run record; None when the run names no target.
    """
    targets = run_record.get("targets_info") or run_record.get("targets") or []
    if isinstance(targets, list):
        for t in targets:
            if isinstance(t, dict):
                key = t.get("original") or t.get("target") or (t.get("details") or {}).get(
                    "target_url"
                )
                if key:
                    return str(key)
            elif isinstance(t, str) and t:
                return t
    return None


def to_reactflow(graph: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Map a {nodes, edges} memory graph to the React Flow shape (pure).

    Node -> {id, type:"memoryNode", data:{label, kind}}; dagre lays it out client
    side, as the agent graph does. Edges get a stable id and keep their label.
    Nodes/edges missing an id are dropped rather than crashing the view.
    """
    nodes_out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for n in graph.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        nid = n.get("id")
        if not nid or str(nid) in seen:
            continue
        seen.add(str(nid))
        nodes_out.append(
            {
                "id": str(nid),
                "type": "memoryNode",
                "data": {
                    "label": str(n.get("label") or n.get("name") or nid),
                    "kind": str(n.get("type") or ""),
                },
            }
        )

    edges_out: list[dict[str, Any]] = []
    for i, e in enumerate(graph.get("edges") or []):
        if not isinstance(e, dict):
            continue
        src, dst = e.get("source"), e.get("target")
        if not src or not dst or str(src) not in seen or str(dst) not in seen:
            continue
        edges_out.append(
            {
                "id": f"e{i}-{src}-{dst}",
                "source": str(src),
                "target": str(dst),
                "label": str(e.get("label") or e.get("relation") or ""),
            }
        )
    return {"nodes": nodes_out, "edges": edges_out}


def _http_fetch(target: str) -> dict[str, Any]:
    """Default transport: GET $STRIX_MEMORY_URL/graph?group_id=<target>."""
    base = (os.environ.get("STRIX_MEMORY_URL") or "").strip().rstrip("/")
    if not base:
        raise MemoryUnavailable("STRIX_MEMORY_URL is not set")
    url = f"{base}/graph?group_id={urllib.parse.quote(target, safe='')}"
    try:
        with urllib.request.urlopen(url, timeout=_HTTP_TIMEOUT_S) as resp:  # noqa: S310
            payload = json.loads(resp.read() or b"{}")
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        raise MemoryUnavailable(f"memory service unreachable: {exc}") from exc
    if not isinstance(payload, dict):
        raise MemoryUnavailable("memory service returned a non-object payload")
    return payload


def fetch_target_graph(
    target: str | None,
    *,
    fetch: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Return the React Flow graph for *target*. Raises MemoryUnavailable when
    memory can't be reached; the caller turns that into a surfaced empty state."""
    if not target:
        raise MemoryUnavailable("run names no target to look up memory for")
    raw = (fetch or _http_fetch)(target)
    return to_reactflow(raw)
