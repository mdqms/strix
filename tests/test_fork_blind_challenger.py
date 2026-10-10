"""Fork tests for the blind-challenger protocol (plan T6, item 14).

The challenger is an always-loaded coordination skill that drives the existing
create_agent / wait_for_agents mechanism. These tests lock the two things that
make it correct: it is loaded for every agent that can file a finding, and its
briefing withholds the original conclusion (E2). Fork-owned file.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from strix.agents.prompt import _resolve_skills, render_system_prompt
from strix.skills import load_skills

_SKILL = "coordination/blind_challenger"


@pytest.mark.parametrize(
    ("is_root", "is_whitebox"),
    [(True, False), (False, False), (False, True)],
)
def test_challenger_loads_for_every_agent_kind(is_root: bool, is_whitebox: bool) -> None:
    resolved = _resolve_skills(
        requested=None,
        scan_mode="deep",
        is_whitebox=is_whitebox,
        is_root=is_root,
        is_diff_scoped=False,
    )
    assert _SKILL in resolved


def test_challenger_renders_into_system_prompt() -> None:
    prompt = render_system_prompt(scan_mode="deep", is_root=True, include_scope=False)
    assert "Blind Challenger" in prompt


def test_skill_file_exists_in_fork_tree() -> None:
    assert Path("strix/skills/coordination/blind_challenger.md").is_file()


def test_skill_enforces_the_blind_contract() -> None:
    body = load_skills([_SKILL])["blind_challenger"]
    lowered = body.lower()
    # It reuses the existing agent-graph mechanism, not new blocking code.
    assert "create_agent" in body
    assert "wait_for_agents" in body
    # E2: the briefing must withhold the original conclusion.
    assert "must not" in lowered
    for withheld in ("severity", "confidence", "conclusion"):
        assert withheld in lowered
    # The three verdict paths exist, including the timeout -> unchallenged label.
    assert "refuted" in lowered
    assert "unchallenged" in lowered
    # A challenger must not recurse into another challenger.
    assert "not spawn its own challenger" in lowered or "do not recurse" in lowered
