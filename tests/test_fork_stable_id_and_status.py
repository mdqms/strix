"""Fork tests for stable finding ids (item 15) and run report status (item 18).

Both reuse existing mechanisms rather than rebuild them: stable_id is SARIF's
class fingerprint surfaced on the finding; report_status reuses coverage's
completeness. Fork-owned file so it never conflicts on an upstream merge.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from strix.report.coverage import build_coverage_document, report_status
from strix.report.sarif import stable_finding_id
from strix.report.state import ReportState, set_global_report_state


@pytest.fixture
def report_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ReportState:
    monkeypatch.chdir(tmp_path)
    state = ReportState(run_name="test-run")
    set_global_report_state(state)
    return state


# --- item 15: stable_id --------------------------------------------------

def test_stable_id_added_to_finding_and_matches_sarif_fingerprint(
    report_state: ReportState,
) -> None:
    rid = report_state.add_vulnerability_report(
        title="SQL injection in login", severity="high", cwe="CWE-89"
    )
    report = next(r for r in report_state.vulnerability_reports if r["id"] == rid)
    assert "stable_id" in report
    # vuln-N stays the mutable local handle; stable_id is the cross-run identity.
    assert report["id"].startswith("vuln-")
    assert report["stable_id"] == stable_finding_id(report)


def test_stable_id_is_file_rename_independent(report_state: ReportState) -> None:
    # Same class + CWE, different file location -> same stable id (the whole point).
    a = report_state.add_vulnerability_report(
        title="SQL injection in login", severity="high", cwe="CWE-89",
        code_locations=[{"file": "a.py", "start_line": 1}],
    )
    b = report_state.add_vulnerability_report(
        title="SQL injection in login", severity="high", cwe="CWE-89",
        code_locations=[{"file": "b.py", "start_line": 9}],
    )
    ra = next(r for r in report_state.vulnerability_reports if r["id"] == a)
    rb = next(r for r in report_state.vulnerability_reports if r["id"] == b)
    assert ra["stable_id"] == rb["stable_id"]


# --- item 18: report_status ----------------------------------------------

def _doc(run_record: dict, agents_graph: dict, findings: list) -> dict:
    return build_coverage_document(
        run_record=run_record,
        entries=[],
        agent_graph=agents_graph,
        vulnerability_reports=findings,
        exit_reason=run_record.get("exit_reason"),
    )


def test_status_not_assessed_when_nothing_ran() -> None:
    doc = _doc({"status": "running"}, {}, [])
    assert doc["report_status"] == "not_assessed"
    assert report_status(doc) == "not_assessed"


def test_status_partial_when_scan_did_not_complete() -> None:
    graph = {"statuses": {"root": "completed"}, "edges": []}
    doc = _doc({"status": "interrupted"}, graph, [{"id": "vuln-1"}])
    assert doc["report_status"] == "partial"


def test_status_complete_on_clean_finish() -> None:
    graph = {"statuses": {"root": "completed"}, "edges": []}
    doc = _doc(
        {"status": "completed", "exit_reason": "finished_by_tool"},
        graph,
        [{"id": "vuln-1"}],
    )
    assert doc["report_status"] == "complete"
