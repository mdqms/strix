"""Chat-with-a-finished-run backend for the viewer (fork plan item 9, T9).

Assembles a run's own artifacts (findings, executive report, run status) into a
bounded context and answers a question about it with the configured LLM. Kept
separate from the HTTP handler so the context assembly and the answer path are
unit-testable with an injected completion function (no LLM key needed).

Model config reuses Strix's: ``STRIX_LLM`` (a LiteLLM model id) plus
``LLM_API_KEY`` / ``LLM_BASE_URL``. Chat is unavailable (not an error) when no
model is configured.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

MAX_QUESTION_CHARS = 4000
_MAX_REPORT_CHARS = 12000
_MAX_FINDING_CHARS = 1500
_MAX_FINDINGS = 40

_SYSTEM_PROMPT = (
    "You are a security analyst assistant answering questions about ONE finished "
    "Strix scan. Use only the run data provided below; do not invent findings, "
    "severities, or endpoints. If the data does not answer the question, say so. "
    "Be concise and concrete: cite finding ids, severities, and locations from the "
    "data. This run is read-only history; you cannot run new scans or tools."
)


class ChatUnavailableError(RuntimeError):
    """No LLM is configured, so run-chat cannot answer."""


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _finding_line(f: dict[str, Any]) -> str:
    bits = [
        str(f.get("id") or "?"),
        str(f.get("severity") or "?"),
        str(f.get("title") or "untitled"),
    ]
    loc = f.get("endpoint") or f.get("target") or ""
    if loc:
        bits.append(str(loc))
    extra = {
        k: f[k]
        for k in ("confidence", "evidence_state", "stable_id", "cwe")
        if f.get(k) not in (None, "")
    }
    head = " | ".join(bits)
    tail = f"  ({', '.join(f'{k}={v}' for k, v in extra.items())})" if extra else ""
    return (head + tail)[:_MAX_FINDING_CHARS]


def build_run_context(run_dir: Path) -> str:
    """Assemble a bounded text context from a run's own artifacts."""
    parts: list[str] = []

    run_record = _load_json(run_dir / "run.json", default={})
    if isinstance(run_record, dict):
        status = run_record.get("report_status") or run_record.get("status") or "unknown"
        parts.append(f"RUN STATUS: {status}")
        targets = run_record.get("targets_info") or run_record.get("targets")
        if targets:
            parts.append(f"TARGETS: {json.dumps(targets, default=str)[:1000]}")

    findings = _load_json(run_dir / "vulnerabilities.json", default=[])
    if isinstance(findings, list) and findings:
        shown = findings[:_MAX_FINDINGS]
        lines = "\n".join(f"- {_finding_line(f)}" for f in shown if isinstance(f, dict))
        more = f"\n(+{len(findings) - len(shown)} more not shown)" if len(findings) > len(shown) else ""
        parts.append(f"FINDINGS ({len(findings)}):\n{lines}{more}")
    else:
        parts.append("FINDINGS: none filed in this run.")

    report = run_dir / "penetration_test_report.md"
    try:
        text = report.read_text(encoding="utf-8")
        parts.append("REPORT (truncated):\n" + text[:_MAX_REPORT_CHARS])
    except OSError:
        pass

    return "\n\n".join(parts)


def _model_config() -> dict[str, Any]:
    model = (os.environ.get("STRIX_LLM") or "").strip()
    if not model:
        raise ChatUnavailableError("no model configured (set STRIX_LLM)")
    cfg: dict[str, Any] = {"model": model}
    if api_key := os.environ.get("LLM_API_KEY"):
        cfg["api_key"] = api_key
    if base_url := os.environ.get("LLM_BASE_URL"):
        cfg["base_url"] = base_url
    return cfg


def answer_question(
    question: str,
    run_dir: Path,
    *,
    completion: Callable[..., Any] | None = None,
) -> str:
    """Answer *question* about the run at *run_dir*. ``completion`` is injected in
    tests; by default LiteLLM's sync ``completion`` is used (the handler is a
    threaded sync HTTP worker, so no async)."""
    question = (question or "").strip()
    if not question:
        raise ValueError("empty question")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError("question too long")

    cfg = _model_config()  # raises ChatUnavailableError when unset
    context = build_run_context(run_dir)
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"RUN DATA:\n{context}\n\nQUESTION: {question}"},
    ]

    if completion is None:
        import litellm

        completion = litellm.completion

    resp = completion(messages=messages, **cfg)
    # LiteLLM returns an OpenAI-shaped response.
    try:
        return str(resp["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError):
        content = getattr(resp.choices[0].message, "content", None)  # object form
        return str(content or "").strip()
