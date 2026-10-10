#!/usr/bin/env python3
"""Compare XBEN eval arms against a baseline with a no-regression gate (plan T4).

Each arm's result file is JSON: {"arm": "<name>", "results": {"<challenge>": bool, ...}}
where the bool is whether that arm solved the challenge. This module only does the
comparison + threshold; running the arms is run_arm.sh (needs the benchmark repo,
Docker, and LLM keys). The threshold answers D9: does the local model or the
challenger make Strix solve meaningfully fewer challenges than the hosted baseline?

CLI:
    compare.py --baseline baseline.json --arm local.json --arm challenger.json \
               [--max-regression N] [--json]

Exit 0 = every arm within threshold; 1 = a regression beyond threshold; 2 = usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_arm(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    results = data.get("results")
    if not isinstance(results, dict):
        raise ValueError(f"{path}: missing 'results' object")
    name = str(data.get("arm") or Path(path).stem)
    return {"arm": name, "results": {str(k): bool(v) for k, v in results.items()}}


def solved(arm: dict[str, Any]) -> set[str]:
    return {c for c, ok in arm["results"].items() if ok}


def compare_arm(baseline: dict[str, Any], arm: dict[str, Any], max_regression: int) -> dict[str, Any]:
    """Compare one arm to the baseline over the challenges they share.

    Regressions are challenges the baseline solved but this arm did not. A
    challenge missing from the arm counts as unsolved (it was not demonstrated).
    New solves (arm solved, baseline did not) are reported but never gate.
    """
    base_solved = solved(baseline)
    arm_solved = solved(arm)
    shared = set(baseline["results"]) & set(arm["results"])
    missing = sorted(set(baseline["results"]) - set(arm["results"]))

    regressions = sorted(c for c in base_solved if c not in arm_solved)
    new_solves = sorted(c for c in arm_solved if c not in base_solved)
    passed = len(regressions) <= max_regression
    return {
        "arm": arm["arm"],
        "baseline_solved": len(base_solved),
        "arm_solved": len(arm_solved),
        "shared_challenges": len(shared),
        "missing_from_arm": missing,
        "regressions": regressions,
        "new_solves": new_solves,
        "max_regression": max_regression,
        "passed": passed,
    }


def _render(report: dict[str, Any]) -> str:
    status = "PASS" if report["passed"] else "REGRESSION"
    lines = [
        f"[{status}] {report['arm']}: solved {report['arm_solved']} vs baseline "
        f"{report['baseline_solved']} "
        f"(regressions {len(report['regressions'])}/{report['max_regression']} allowed)"
    ]
    if report["regressions"]:
        lines.append("  regressed: " + ", ".join(report["regressions"]))
    if report["missing_from_arm"]:
        lines.append("  not run in this arm: " + ", ".join(report["missing_from_arm"]))
    if report["new_solves"]:
        lines.append("  newly solved: " + ", ".join(report["new_solves"]))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="XBEN eval no-regression gate (plan T4)")
    ap.add_argument("--baseline", required=True, help="baseline arm results JSON")
    ap.add_argument("--arm", action="append", default=[], help="arm results JSON (repeatable)")
    ap.add_argument(
        "--max-regression",
        type=int,
        default=0,
        help="challenges the baseline solved that an arm may miss before it fails (default 0)",
    )
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args(argv)
    if not args.arm:
        ap.error("at least one --arm is required")

    baseline = load_arm(args.baseline)
    reports = [compare_arm(baseline, load_arm(a), args.max_regression) for a in args.arm]

    if args.json:
        print(json.dumps({"baseline": baseline["arm"], "arms": reports}, indent=2))
    else:
        for r in reports:
            print(_render(r))

    return 0 if all(r["passed"] for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
