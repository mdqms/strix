"""Fork tests for ops guards (plan T10): approved-target allowlist (33) and
telemetry-off (31). The backup/restore drill (5) is verified separately against a
live FalkorDB container, not here.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from strix.interface.scope_guard import is_authorized, load_allowlist, unauthorized

_REPO = Path(__file__).resolve().parent.parent
_SCOPED = _REPO / "scripts" / "strix-scoped"

_ALLOW = [
    "# comment",
    "example.com",
    "*.staging.example.com",
    "10.0.0.5",
    "/srv/code",
    "postman://abc-123",
]


@pytest.mark.parametrize(
    "target",
    [
        "example.com",
        "https://example.com/login",
        "http://example.com:8080/x",
        "api.staging.example.com",
        "https://a.b.staging.example.com/p",
        "10.0.0.5",
        "/srv/code",
        "/srv/code/sub/dir",
        "postman://abc-123",
    ],
)
def test_authorized(target: str) -> None:
    assert is_authorized(target, _ALLOW)


@pytest.mark.parametrize(
    "target",
    [
        "evil.com",
        "https://evil.com",
        "notexample.com",
        "example.com.evil.com",
        "staging.example.com",        # apex of a *.subdomain rule is not covered
        "10.0.0.6",
        "/etc/passwd",
        "/srv/other",
        "postman://different",
        "",
    ],
)
def test_denied(target: str) -> None:
    assert not is_authorized(target, _ALLOW)


def test_empty_allowlist_denies_everything() -> None:
    assert not is_authorized("example.com", [])
    assert not is_authorized("/srv/code", ["# only comments"])


def test_unauthorized_reports_each_bad_target() -> None:
    bad = unauthorized(["example.com", "evil.com", "/srv/code", "/etc"], _ALLOW)
    assert bad == ["evil.com", "/etc"]


def test_load_allowlist_missing_file_is_empty() -> None:
    assert load_allowlist("/no/such/allowlist.txt") == []


# --- telemetry off (item 31) ---------------------------------------------

def test_telemetry_env_disables_posthog_and_scarf(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRIX_TELEMETRY", "false")
    from strix.config import loader
    from strix.telemetry import posthog, scarf

    monkeypatch.setattr(loader, "_cached", None)  # settings memoize; force a re-read
    try:
        assert posthog._is_enabled() is False
        assert scarf._is_enabled() is False
    finally:
        loader._cached = None  # don't leak the forced state to other tests


# --- wrapper end to end (deny path, no strix needed) ---------------------

def test_strix_scoped_refuses_unapproved_target(tmp_path: Path) -> None:
    allow = tmp_path / "approved.txt"
    allow.write_text("example.com\n", encoding="utf-8")
    env = {**os.environ, "STRIX_APPROVED_TARGETS": str(allow), "STRIX_PYTHON": sys.executable}
    # the guard rejects before ever exec-ing strix.
    proc = subprocess.run(
        ["bash", str(_SCOPED), "-t", "evil.com", "-n"],
        capture_output=True, text=True, env=env,
    )
    assert proc.returncode == 3
    assert "not in the approved list" in proc.stderr


def test_strix_scoped_requires_a_target(tmp_path: Path) -> None:
    proc = subprocess.run(
        ["bash", str(_SCOPED)], capture_output=True, text=True,
        env={**os.environ, "STRIX_APPROVED_TARGETS": str(tmp_path / "x.txt")},
    )
    assert proc.returncode == 2
