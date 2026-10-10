"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  type Node,
  type Edge,
} from "@xyflow/react";
import dagre from "@dagrejs/dagre";
import { Network, ChevronUp, ChevronDown } from "lucide-react";
import { fetchMemoryGraph, type MemoryGraphResult } from "@/data/serverSource";
import "@xyflow/react/dist/style.css";

// Fork plan item 10 (T9): a view of the target's memory graph, built during scans
// via the Graphiti memory service. Reuses React Flow + dagre, like AgentGraph.
// D6: a warm empty state when there's no memory yet; also a clear state when the
// memory service is unreachable. D7: keyboard pan/zoom via React Flow controls +
// a focusable canvas.

const NODE_W = 180;
const NODE_H = 44;

function layout(
  nodes: { id: string; data: { label: string; kind: string } }[],
  edges: { id: string; source: string; target: string; label: string }[]
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 40, ranksep: 90 });
  for (const n of nodes) g.setNode(n.id, { width: NODE_W, height: NODE_H });
  for (const e of edges) g.setEdge(e.source, e.target);
  dagre.layout(g);

  const rfNodes: Node[] = nodes.map((n) => {
    const p = g.node(n.id);
    return {
      id: n.id,
      position: p ? { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2 } : { x: 0, y: 0 },
      data: { label: n.data.kind ? `${n.data.label}  ·  ${n.data.kind}` : n.data.label },
      style: {
        width: NODE_W,
        fontSize: 12,
        color: "#ddd",
        background: "#111",
        border: "1px solid #2a2a2a",
        borderRadius: 8,
        padding: "6px 10px",
      },
    };
  });
  const rfEdges: Edge[] = edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label || undefined,
    labelStyle: { fill: "#888", fontSize: 10 },
    style: { stroke: "#2a2a2a", strokeWidth: 1.5 },
  }));
  return { nodes: rfNodes, edges: rfEdges };
}

export function MemoryGraph({ runName }: { runName: string | null }) {
  const [open, setOpen] = useState(false);
  const [state, setState] = useState<MemoryGraphResult | null>(null);
  const [loading, setLoading] = useState(false);
  const loadedFor = useRef<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    fetchMemoryGraph(runName)
      .then(setState)
      .catch(() => setState({ available: false, target: null, reason: "request failed" }))
      .finally(() => setLoading(false));
  }, [runName]);

  // Load lazily the first time the panel is opened for this run.
  useEffect(() => {
    if (open && loadedFor.current !== runName) {
      loadedFor.current = runName;
      load();
    }
  }, [open, runName, load]);

  const rf = state && state.available ? layout(state.nodes, state.edges) : null;

  return (
    <div className="rounded-xl border border-[#222] bg-[rgba(255,255,255,0.02)] p-5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full cursor-pointer items-center gap-2 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#3b82f6]"
      >
        <Network className="h-4 w-4 text-[#888]" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-white">Target memory graph</h2>
        {open ? (
          <ChevronUp className="ml-auto h-4 w-4 text-[#666]" aria-hidden="true" />
        ) : (
          <ChevronDown className="ml-auto h-4 w-4 text-[#666]" aria-hidden="true" />
        )}
      </button>

      {open && (
        <div className="mt-4">
          {loading && <p className="text-sm text-[#888]">Loading memory…</p>}

          {!loading && state && !state.available && (
            <p className="text-sm text-[#888]">
              No memory for this target yet. Run a scan to start building it.
              <span className="mt-1 block text-[11px] text-[#555]">({state.reason})</span>
            </p>
          )}

          {!loading && rf && rf.nodes.length === 0 && (
            <p className="text-sm text-[#888]">
              No memory for this target yet. Run a scan to start building it.
            </p>
          )}

          {!loading && rf && rf.nodes.length > 0 && (
            <div
              className="h-[26rem] w-full overflow-hidden rounded-lg border border-[#222]"
              tabIndex={0}
              role="group"
              aria-label="Target memory graph. Use the on-canvas controls to zoom; drag to pan."
            >
              <ReactFlowProvider>
                <ReactFlow
                  nodes={rf.nodes}
                  edges={rf.edges}
                  fitView
                  fitViewOptions={{ padding: 0.2 }}
                  minZoom={0.2}
                  proOptions={{ hideAttribution: true }}
                >
                  <Background color="#1a1a1a" gap={16} />
                  <Controls position="bottom-right" showInteractive={false} />
                </ReactFlow>
              </ReactFlowProvider>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
