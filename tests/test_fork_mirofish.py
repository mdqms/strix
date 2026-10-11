"""Fork tests for the MiroFish integration client (plan items 11-12).

Request/response shaping and the unavailable paths are tested with an injected
transport. The live HTTP calls and the MiroFish-side adapter need a running service
and are validated separately. No MiroFish code is imported (AGPL boundary).
"""

from __future__ import annotations

from typing import Any

import pytest

from strix.integrations import mirofish


def test_generate_personas_shapes_request_and_parses(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake(path: str, payload: dict[str, Any]) -> dict[str, Any]:
        captured["path"] = path
        captured["payload"] = payload
        return {"personas": [{"name": "Ada", "role": "admin"}, "junk", {"name": "Bob"}]}

    out = mirofish.generate_personas({"roles": ["admin", "user"]}, count=3, transport=fake)
    assert captured["path"] == "/personas"
    assert captured["payload"] == {"spec": {"roles": ["admin", "user"]}, "count": 3}
    assert out == [{"name": "Ada", "role": "admin"}, {"name": "Bob"}]  # non-dicts dropped


def test_generate_personas_bad_count() -> None:
    with pytest.raises(ValueError):
        mirofish.generate_personas({}, count=0, transport=lambda p, b: {})


def test_generate_personas_missing_list_is_unavailable() -> None:
    with pytest.raises(mirofish.MiroFishUnavailable):
        mirofish.generate_personas({}, transport=lambda p, b: {"oops": 1})


def test_rehearse_disclosure_shapes_and_parses() -> None:
    captured: dict[str, Any] = {}

    def fake(path: str, payload: dict[str, Any]) -> dict[str, Any]:
        captured["path"] = path
        captured["payload"] = payload
        return {"reactions": [{"stakeholder": "customers", "reaction": "concern"}],
                "summary": "Patch fast, notify customers."}

    out = mirofish.rehearse_disclosure(
        {"title": "SQLi", "severity": "high"}, stakeholders=["customers", "press"], transport=fake
    )
    assert captured["path"] == "/rehearse"
    assert captured["payload"]["finding"]["title"] == "SQLi"
    assert captured["payload"]["stakeholders"] == ["customers", "press"]
    assert out["reactions"][0]["stakeholder"] == "customers"
    assert out["summary"] == "Patch fast, notify customers."


def test_rehearse_requires_finding() -> None:
    with pytest.raises(ValueError):
        mirofish.rehearse_disclosure({}, transport=lambda p, b: {})


def test_unavailable_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRIX_MIROFISH_URL", raising=False)
    with pytest.raises(mirofish.MiroFishUnavailable):
        mirofish.generate_personas({"roles": []})  # default transport, no URL
    with pytest.raises(mirofish.MiroFishUnavailable):
        mirofish.rehearse_disclosure({"title": "x"})


def test_no_mirofish_code_imported() -> None:
    # AGPL boundary: the client must not pull in any MiroFish module.
    import sys

    assert not any(m == "mirofish" or m.startswith("mirofish.") for m in sys.modules)
