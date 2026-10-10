"""Fork tests for evidence_state (plan T5, decision D13).

evidence_state is a judgment separate from confidence/severity: what KIND of
proof backs a finding (reproduced / static_trace / hypothesis). Optional and
additive, so existing callers are unaffected. Kept in a fork-owned file so it
never conflicts on a weekly upstream merge.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from strix.report.sarif import build_sarif_report
from strix.report.state import ReportState, set_global_report_state
from strix.tools.reporting.tool import (
    _VALID_EVIDENCE_STATE,
    _collect_update_changes,
    _do_create,
    create_vulnerability_report,
)

_CVSS = {
    "attack_vector": "N",
    "attack_complexity": "L",
    "privileges_required": "N",
    "user_interaction": "N",
    "scope": "U",
    "confidentiality": "H",
    "integrity": "N",
    "availability": "N",
}


@pytest.fixture
def report_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ReportState:
    monkeypatch.chdir(tmp_path)
    state = ReportState(run_name="test-run")
    set_global_report_state(state)
    return state


def _create_kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "title": "Reflected XSS in search",
        "description": "q reflects unencoded input.",
        "impact": "Session theft.",
        "target": "https://app.example.com",
        "technical_analysis": "Input interpolated into HTML.",
        "poc_description": "1. open /search?q=<payload>",
        "poc_script_code": "GET /search?q=<script>alert(1)</script>",
        "remediation_steps": "Context-encode output.",
        "evidence": "Response echoes the payload verbatim.",
        "assumptions": "Assumes a victim opens a crafted link.",
        "counterevidence": "No output encoding or CSP observed.",
        "confidence": "HIGH",
        "severity_change_conditions": "A strict CSP would lower the severity.",
        "fix_effort": "LOW",
        "cvss_breakdown": _CVSS,
        "endpoint": "/search",
        "method": "GET",
        "cve": None,
        "cwe": "CWE-79",
        "code_locations": None,
    }
    base.update(overrides)
    return base


async def test_evidence_state_persisted_and_normalized(report_state: ReportState) -> None:
    result = await _do_create(**_create_kwargs(evidence_state="REPRODUCED"))
    assert result["success"] is True
    assert report_state.vulnerability_reports[0]["evidence_state"] == "reproduced"


async def test_evidence_state_optional_absent_when_omitted(report_state: ReportState) -> None:
    result = await _do_create(**_create_kwargs())
    assert result["success"] is True
    assert "evidence_state" not in report_state.vulnerability_reports[0]


async def test_invalid_evidence_state_rejected(report_state: ReportState) -> None:
    result = await _do_create(**_create_kwargs(evidence_state="proven"))
    assert result["success"] is False
    assert any("evidence_state" in e for e in result["errors"])
    assert report_state.vulnerability_reports == []


def test_update_accepts_valid_and_rejects_invalid() -> None:
    changes, errors = _collect_update_changes({"evidence_state": "Static_Trace"})
    assert errors == []
    assert changes["evidence_state"] == "static_trace"

    changes, errors = _collect_update_changes({"evidence_state": "guess"})
    assert any("evidence_state" in e for e in errors)
    assert "evidence_state" not in changes


def test_evidence_state_surfaces_in_sarif(report_state: ReportState) -> None:
    report_state.add_vulnerability_report(
        title="XSS",
        severity="high",
        cwe="CWE-79",
        evidence_state="static_trace",
    )
    sarif = build_sarif_report(report_state.vulnerability_reports)
    strix_props = sarif["runs"][0]["results"][0]["properties"]["strix"]
    assert strix_props["evidence_state"] == "static_trace"


def test_tool_param_documented() -> None:
    schema = create_vulnerability_report.params_json_schema["properties"]
    assert "evidence_state" in schema
    desc = schema["evidence_state"]["description"]
    assert desc.strip()
    assert "reproduced" in desc


def test_valid_set_is_the_three_states() -> None:
    assert _VALID_EVIDENCE_STATE == {"hypothesis", "static_trace", "reproduced"}
