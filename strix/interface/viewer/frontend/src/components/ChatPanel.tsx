"use client";

import { useRef, useState } from "react";
import { MessageSquare, ChevronUp, ChevronDown, Send } from "lucide-react";
import Markdown from "@/components/live/tool-renderers/Markdown";
import { askRun } from "@/data/serverSource";

// Fork plan item 9 (T9), design decisions D4-D7: a collapsible panel docked to the
// right of the run report. Chat is a helper; the findings stay primary. Messages
// render as flat markdown blocks (reusing Markdown, like AgentTranscript), never
// chat bubbles, so code/paths/finding-ids stay readable (D5). Desktop-first with
// keyboard access and visible focus rings (D7).

type Turn = { role: "you" | "assistant"; text: string };

export function ChatPanel({ runName }: { runName: string | null }) {
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  async function send() {
    const q = input.trim();
    if (!q || busy) return;
    setError(null);
    setBusy(true);
    setTurns((t) => [...t, { role: "you", text: q }]);
    setInput("");
    const res = await askRun(runName, q);
    if (res.ok) {
      setTurns((t) => [...t, { role: "assistant", text: res.answer }]);
    } else {
      setError(
        res.error === "unavailable"
          ? "Chat is unavailable: no model is configured for this viewer (set STRIX_LLM)."
          : "Couldn't answer that — the model call failed. Try again."
      );
    }
    setBusy(false);
    requestAnimationFrame(() => logRef.current?.scrollTo({ top: logRef.current.scrollHeight }));
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter is a newline.
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  }

  return (
    <div className="rounded-xl border border-[#222] bg-[rgba(255,255,255,0.02)] p-5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full cursor-pointer items-center gap-2 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#3b82f6]"
      >
        <MessageSquare className="h-4 w-4 text-[#888]" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-white">Ask about this run</h2>
        {open ? (
          <ChevronUp className="ml-auto h-4 w-4 text-[#666]" aria-hidden="true" />
        ) : (
          <ChevronDown className="ml-auto h-4 w-4 text-[#666]" aria-hidden="true" />
        )}
      </button>

      {open && (
        <div className="mt-4">
          <div
            ref={logRef}
            className="max-h-[22rem] space-y-4 overflow-y-auto"
            aria-live="polite"
          >
            {turns.length === 0 ? (
              <p className="text-sm text-[#888]">
                Ask about this scan&rsquo;s findings, coverage, or status — for example
                &ldquo;why is the SQLi finding rated high?&rdquo; or &ldquo;what was left
                unassessed?&rdquo;. Answers come from this run&rsquo;s own data.
              </p>
            ) : (
              turns.map((t, i) => (
                <div key={i}>
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-[#555]">
                    {t.role === "you" ? "You" : "Assistant"}
                  </div>
                  {t.role === "you" ? (
                    <p className="whitespace-pre-wrap text-sm text-[#ddd]">{t.text}</p>
                  ) : (
                    <Markdown text={t.text} />
                  )}
                </div>
              ))
            )}
          </div>

          {error && (
            <p role="alert" className="mt-3 text-sm text-[#f87171]">
              {error}
            </p>
          )}

          <div className="mt-4 flex items-end gap-2">
            <label htmlFor="run-chat-input" className="sr-only">
              Your question about this run
            </label>
            <textarea
              id="run-chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              rows={2}
              placeholder="Ask a question…"
              disabled={busy}
              className="min-h-[44px] flex-1 resize-y rounded-lg border border-[#2a2a2a] bg-[rgba(0,0,0,0.3)] px-3 py-2 text-sm text-[#ddd] placeholder:text-[#555] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#3b82f6]"
            />
            <button
              type="button"
              onClick={() => void send()}
              disabled={busy || !input.trim()}
              aria-label="Send question"
              className="inline-flex h-11 min-w-[44px] items-center justify-center gap-1.5 rounded-lg border border-[#2a2a2a] bg-[rgba(255,255,255,0.04)] px-3 text-sm text-[#ddd] hover:bg-[rgba(255,255,255,0.08)] disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#3b82f6]"
            >
              <Send className="h-4 w-4" aria-hidden="true" />
              {busy ? "…" : "Send"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
