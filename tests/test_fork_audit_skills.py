"""Fork tests for the CSO-derived audit skills (plan T8, items 21-29).

They live in fork_skills/ and load via the T2 $STRIX_SKILLS_DIR hook. These
tests prove the directory loads exactly as the deployment wires it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import strix.skills as skills_mod
from strix.skills import get_all_skill_names, get_available_skills, load_skills

_FORK_SKILLS_DIR = Path(__file__).resolve().parent.parent / "fork_skills"
_EXPECTED = [
    "secrets_git_history",
    "dependency_supply_chain",
    "cicd_pipeline_security",
    "infrastructure_as_code",
    "integrations_webhooks",
    "llm_agent_mcp_config",
    "agent_skill_supply_chain",
    "stride_threat_model",
    "data_classification",
]


@pytest.fixture(autouse=True)
def _env_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    original = list(skills_mod._EXTRA_SKILL_DIRS)
    skills_mod._EXTRA_SKILL_DIRS.clear()
    monkeypatch.setenv("STRIX_SKILLS_DIR", str(_FORK_SKILLS_DIR))
    skills_mod.register_skill_dirs_from_env()
    try:
        yield
    finally:
        skills_mod._EXTRA_SKILL_DIRS[:] = original


def test_all_nine_discovered() -> None:
    names = get_all_skill_names()
    assert set(_EXPECTED).issubset(names)


def test_all_nine_load_with_body_and_mit_notice() -> None:
    loaded = load_skills([f"custom/{n}" for n in _EXPECTED])
    assert set(loaded) == set(_EXPECTED)
    for name, body in loaded.items():
        assert body.strip(), name
        assert "MIT" in body, name  # attribution preserved per the plan


def test_all_nine_have_descriptions() -> None:
    avail = {d["name"]: d["description"] for d in get_available_skills().get("custom", [])}
    for name in _EXPECTED:
        assert avail.get(name, "").strip(), name


def test_notice_file_present() -> None:
    assert (_FORK_SKILLS_DIR / "NOTICE").is_file()
