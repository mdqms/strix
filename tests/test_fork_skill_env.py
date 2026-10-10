"""Fork tests for the $STRIX_SKILLS_DIR startup hook (see FORK.md H1/H2).

Kept in a fork-owned file, not appended to the upstream test suite, so it never
conflicts on a weekly upstream merge.
"""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

import strix.skills as skills_mod
from strix.skills import (
    get_all_skill_names,
    load_skills,
    register_skill_dirs_from_env,
    registered_skill_dirs,
)


@pytest.fixture(autouse=True)
def _clear_extra_dirs() -> Iterator[None]:
    original = list(skills_mod._EXTRA_SKILL_DIRS)
    skills_mod._EXTRA_SKILL_DIRS.clear()
    try:
        yield
    finally:
        skills_mod._EXTRA_SKILL_DIRS[:] = original


def _write_skill(root: Path, category: str, name: str, body: str) -> None:
    category_dir = root / category
    category_dir.mkdir(parents=True, exist_ok=True)
    (category_dir / f"{name}.md").write_text(body, encoding="utf-8")


def test_env_dir_registers_and_loads_skill(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_skill(tmp_path, "custom", "fork_only", "---\ndescription: fork skill\n---\nBody here.")
    monkeypatch.setenv("STRIX_SKILLS_DIR", str(tmp_path))

    register_skill_dirs_from_env()

    assert tmp_path in registered_skill_dirs()
    assert "fork_only" in get_all_skill_names()
    assert load_skills(["custom/fork_only"]) == {"fork_only": "Body here."}


def test_env_splits_pathsep_and_ignores_blanks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    monkeypatch.setenv("STRIX_SKILLS_DIR", os.pathsep.join([str(a), "", str(b)]))

    register_skill_dirs_from_env()

    registered = registered_skill_dirs()
    assert a in registered
    assert b in registered


def test_env_unset_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIX_SKILLS_DIR", raising=False)
    register_skill_dirs_from_env()
    assert registered_skill_dirs() == ()


def test_malformed_skill_file_is_skipped_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # One good skill, one with broken YAML frontmatter, same category.
    _write_skill(tmp_path, "custom", "good", "---\ndescription: ok\n---\nGood body.")
    _write_skill(tmp_path, "custom", "broken", "---\n: : not: valid: yaml\n---\nBroken body.")
    monkeypatch.setenv("STRIX_SKILLS_DIR", str(tmp_path))

    register_skill_dirs_from_env()

    # Both are discovered; the good one loads; the broken one's bad frontmatter is
    # logged and skipped (body still returned), never raised.
    assert {"good", "broken"}.issubset(get_all_skill_names())
    assert load_skills(["custom/good"]) == {"good": "Good body."}
    assert load_skills(["custom/broken"]).get("broken") == "Broken body."
