"""Fork tests for the T4 XBEN eval harness: the no-regression gate (compare.py)
and the challenger A/B toggle. The arms themselves need real infra and are not
run here.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_COMPARE = Path(__file__).resolve().parent.parent / "evals" / "xben" / "compare.py"
_spec = importlib.util.spec_from_file_location("xben_compare", _COMPARE)
assert _spec and _spec.loader
compare = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(compare)


def _write(tmp: Path, name: str, results: dict[str, bool]) -> Path:
    p = tmp / f"{name}.json"
    p.write_text(json.dumps({"arm": name, "results": results}), encoding="utf-8")
    return p


# --- compare.py gate logic ------------------------------------------------

def test_no_regression_passes(tmp_path: Path) -> None:
    base = compare.load_arm(_write(tmp_path, "base", {"c1": True, "c2": True, "c3": False}))
    arm = compare.load_arm(_write(tmp_path, "arm", {"c1": True, "c2": True, "c3": False}))
    r = compare.compare_arm(base, arm, max_regression=0)
    assert r["passed"] and r["regressions"] == []


def test_regression_beyond_threshold_fails(tmp_path: Path) -> None:
    base = compare.load_arm(_write(tmp_path, "base", {"c1": True, "c2": True}))
    arm = compare.load_arm(_write(tmp_path, "arm", {"c1": True, "c2": False}))  # lost c2
    assert compare.compare_arm(base, arm, max_regression=0)["passed"] is False
    assert compare.compare_arm(base, arm, max_regression=0)["regressions"] == ["c2"]


def test_regression_within_threshold_passes(tmp_path: Path) -> None:
    base = compare.load_arm(_write(tmp_path, "base", {"c1": True, "c2": True, "c3": True}))
    arm = compare.load_arm(_write(tmp_path, "arm", {"c1": True, "c2": False, "c3": False}))
    assert compare.compare_arm(base, arm, max_regression=2)["passed"] is True


def test_new_solves_do_not_gate(tmp_path: Path) -> None:
    base = compare.load_arm(_write(tmp_path, "base", {"c1": False}))
    arm = compare.load_arm(_write(tmp_path, "arm", {"c1": True}))  # arm is better
    r = compare.compare_arm(base, arm, max_regression=0)
    assert r["passed"] and r["new_solves"] == ["c1"]


def test_missing_challenge_counts_as_unsolved(tmp_path: Path) -> None:
    base = compare.load_arm(_write(tmp_path, "base", {"c1": True, "c2": True}))
    arm = compare.load_arm(_write(tmp_path, "arm", {"c1": True}))  # c2 not run
    r = compare.compare_arm(base, arm, max_regression=0)
    assert r["missing_from_arm"] == ["c2"]
    assert "c2" in r["regressions"] and r["passed"] is False


def test_main_exit_codes(tmp_path: Path) -> None:
    base = _write(tmp_path, "base", {"c1": True, "c2": True})
    good = _write(tmp_path, "good", {"c1": True, "c2": True})
    bad = _write(tmp_path, "bad", {"c1": True, "c2": False})
    assert compare.main(["--baseline", str(base), "--arm", str(good)]) == 0
    assert compare.main(["--baseline", str(base), "--arm", str(bad)]) == 1
    assert compare.main(["--baseline", str(base), "--arm", str(bad), "--max-regression", "1"]) == 0


def test_load_arm_rejects_malformed(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"arm": "x"}), encoding="utf-8")  # no results
    with pytest.raises(ValueError, match="results"):
        compare.load_arm(p)


# --- challenger A/B toggle ------------------------------------------------

def test_challenger_toggle_removes_skill(monkeypatch: pytest.MonkeyPatch) -> None:
    from strix.agents.prompt import _resolve_skills

    monkeypatch.delenv("STRIX_DISABLE_BLIND_CHALLENGER", raising=False)
    on = _resolve_skills(requested=None, scan_mode="deep", is_whitebox=False, is_root=True,
                         is_diff_scoped=False)
    assert "coordination/blind_challenger" in on

    monkeypatch.setenv("STRIX_DISABLE_BLIND_CHALLENGER", "1")
    off = _resolve_skills(requested=None, scan_mode="deep", is_whitebox=False, is_root=True,
                          is_diff_scoped=False)
    assert "coordination/blind_challenger" not in off
