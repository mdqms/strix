"""Fork tests for the viewer run-chat backend (plan T9, item 9).

The context assembly and answer path are tested with an injected completion
function, so no LLM key is needed. The frontend panel is a separate slice.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from strix.interface.viewer import chat


def _run(tmp: Path, *, findings: list[dict] | None = None, report: str | None = None,
         run_record: dict | None = None) -> Path:
    d = tmp / "run-abc"
    d.mkdir()
    (d / "run.json").write_text(json.dumps(run_record or {"status": "completed",
                                                           "report_status": "complete"}),
                                encoding="utf-8")
    (d / "vulnerabilities.json").write_text(json.dumps(findings or []), encoding="utf-8")
    if report is not None:
        (d / "penetration_test_report.md").write_text(report, encoding="utf-8")
    return d


def test_context_includes_status_findings_and_report(tmp_path: Path) -> None:
    run = _run(
        tmp_path,
        findings=[{"id": "vuln-1", "severity": "high", "title": "SQLi in login",
                   "endpoint": "/login", "evidence_state": "reproduced", "stable_id": "abc"}],
        report="# Executive summary\nOne high finding.",
        run_record={"report_status": "partial"},
    )
    ctx = chat.build_run_context(run)
    assert "RUN STATUS: partial" in ctx
    assert "vuln-1" in ctx and "high" in ctx and "SQLi in login" in ctx
    assert "evidence_state=reproduced" in ctx
    assert "Executive summary" in ctx


def test_context_handles_no_findings(tmp_path: Path) -> None:
    ctx = chat.build_run_context(_run(tmp_path, findings=[]))
    assert "FINDINGS: none filed" in ctx


def test_context_is_bounded(tmp_path: Path) -> None:
    big = [{"id": f"vuln-{i}", "severity": "low", "title": "x" * 50} for i in range(100)]
    ctx = chat.build_run_context(_run(tmp_path, findings=big, report="y" * 50000))
    assert "not shown" in ctx                 # finding list capped
    assert len(ctx) < 40000                    # report truncated


def test_answer_uses_injected_completion_and_passes_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STRIX_LLM", "test/model")
    monkeypatch.setenv("LLM_API_KEY", "k")
    run = _run(tmp_path, findings=[{"id": "vuln-1", "severity": "high", "title": "XSS"}])
    captured: dict[str, Any] = {}

    def fake_completion(*, model: str, messages: list[dict], **kw: Any) -> dict:
        captured["model"] = model
        captured["messages"] = messages
        captured["kw"] = kw
        return {"choices": [{"message": {"content": "There is 1 high finding: vuln-1 (XSS)."}}]}

    out = chat.answer_question("summarize the findings", run, completion=fake_completion)
    assert out == "There is 1 high finding: vuln-1 (XSS)."
    assert captured["model"] == "test/model"
    user_msg = captured["messages"][-1]["content"]
    assert "vuln-1" in user_msg and "summarize the findings" in user_msg


def test_unavailable_without_model(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIX_LLM", raising=False)
    run = _run(tmp_path)
    with pytest.raises(chat.ChatUnavailableError):
        chat.answer_question("hi", run, completion=lambda **_: {})


def test_empty_and_overlong_questions_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIX_LLM", "test/model")
    run = _run(tmp_path)
    with pytest.raises(ValueError):
        chat.answer_question("   ", run, completion=lambda **_: {})
    with pytest.raises(ValueError):
        chat.answer_question("x" * (chat.MAX_QUESTION_CHARS + 1), run, completion=lambda **_: {})
