"""Fork tests for the viewer memory-graph source (plan T9 item 10).

The pure mapping and the unavailable paths are tested with an injected fetch; the
live Graphiti transport needs a running service and is validated separately.
"""

from __future__ import annotations

import pytest

from strix.interface.viewer import memory_graph as mg


def test_target_key_from_targets_info() -> None:
    assert mg.target_key({"targets_info": [{"original": "example.com"}]}) == "example.com"
    assert mg.target_key({"targets": ["https://app.example.com"]}) == "https://app.example.com"
    assert mg.target_key({"targets_info": [{"details": {"target_url": "u"}}]}) == "u"
    assert mg.target_key({}) is None


def test_to_reactflow_maps_nodes_and_edges() -> None:
    graph = {
        "nodes": [
            {"id": "n1", "label": "login endpoint", "type": "endpoint"},
            {"id": "n2", "name": "users table", "type": "datastore"},
        ],
        "edges": [{"source": "n1", "target": "n2", "relation": "reads"}],
    }
    out = mg.to_reactflow(graph)
    assert [n["id"] for n in out["nodes"]] == ["n1", "n2"]
    assert out["nodes"][0]["type"] == "memoryNode"
    assert out["nodes"][0]["data"] == {"label": "login endpoint", "kind": "endpoint"}
    assert out["nodes"][1]["data"]["label"] == "users table"  # falls back to name
    assert out["edges"][0]["source"] == "n1" and out["edges"][0]["label"] == "reads"


def test_to_reactflow_drops_bad_nodes_and_dangling_edges() -> None:
    graph = {
        "nodes": [{"id": "n1", "label": "a"}, {"label": "no id"}, {"id": "n1", "label": "dup"}],
        "edges": [
            {"source": "n1", "target": "missing"},  # dangling -> dropped
            {"source": "n1"},                         # no target -> dropped
        ],
    }
    out = mg.to_reactflow(graph)
    assert len(out["nodes"]) == 1          # bad + duplicate dropped
    assert out["edges"] == []


def test_fetch_uses_injected_fetch() -> None:
    captured = {}

    def fake(target: str):
        captured["target"] = target
        return {"nodes": [{"id": "x", "label": "x"}], "edges": []}

    out = mg.fetch_target_graph("example.com", fetch=fake)
    assert captured["target"] == "example.com"
    assert out["nodes"][0]["id"] == "x"


def test_fetch_no_target_is_unavailable() -> None:
    with pytest.raises(mg.MemoryUnavailable):
        mg.fetch_target_graph(None, fetch=lambda _t: {})


def test_fetch_without_memory_url_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIX_MEMORY_URL", raising=False)
    with pytest.raises(mg.MemoryUnavailable):
        mg.fetch_target_graph("example.com")  # default transport, no URL set
