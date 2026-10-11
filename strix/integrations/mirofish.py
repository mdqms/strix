"""MiroFish integration client (fork plan items 11-12).

MiroFish is a multi-agent social-simulation engine. This fork uses it for two
optional, security-adjacent jobs:

- item 11: generate realistic persona / test-user data to seed a staging app you
  own, so access-control and multi-tenant findings have real cross-user state.
- item 12: rehearse how stakeholders might react to a confirmed disclosure, to
  help prioritise fixes and plan communications.

LICENSE BOUNDARY (important): MiroFish is AGPL-3.0; this fork is Apache-2.0. This
module imports NO MiroFish code. It calls a SEPARATE MiroFish process over HTTP at
``$STRIX_MIROFISH_URL`` (run it as its own service — see
``deploy/mirofish/README.md``). Keeping it a network service, never a linked
library, is what keeps the AGPL and Apache code apart.

ADAPTER SEAM (needs live validation): MiroFish's stock app has no endpoint for
these two jobs, so the separate service must expose a thin adapter:

    POST /personas  {"spec": <object>, "count": <int>}
        -> {"personas": [{"name","role","attributes": {...}}, ...]}
    POST /rehearse  {"finding": <object>, "stakeholders": [<str>, ...]?}
        -> {"reactions": [{"stakeholder","reaction","severity_felt"?}, ...],
            "summary": <str>}

The request/response shaping and the unavailable paths here are unit-tested with an
injected transport; the live calls and that adapter are yours to build and verify
against a running MiroFish.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

_HTTP_TIMEOUT_S = 30  # simulations are slow; give them room


class MiroFishUnavailable(RuntimeError):
    """MiroFish is not configured or not reachable."""


Transport = Callable[[str, dict[str, Any]], dict[str, Any]]


def _http_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    base = (os.environ.get("STRIX_MIROFISH_URL") or "").strip().rstrip("/")
    if not base:
        raise MiroFishUnavailable("STRIX_MIROFISH_URL is not set")
    req = urllib.request.Request(  # noqa: S310
        f"{base}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_S) as resp:  # noqa: S310
            body = json.loads(resp.read() or b"{}")
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
        raise MiroFishUnavailable(f"MiroFish unreachable: {exc}") from exc
    if not isinstance(body, dict):
        raise MiroFishUnavailable("MiroFish returned a non-object payload")
    return body


def generate_personas(
    spec: dict[str, Any],
    count: int = 10,
    *,
    transport: Transport | None = None,
) -> list[dict[str, Any]]:
    """Item 11: ask MiroFish for *count* personas matching *spec* (roles, tenants,
    attributes). Returns the persona list; raises MiroFishUnavailable if the
    service can't be reached. Only ever seed these into an app you are authorized
    to test."""
    if count < 1:
        raise ValueError("count must be >= 1")
    body = (transport or _http_post)("/personas", {"spec": spec, "count": count})
    personas = body.get("personas")
    if not isinstance(personas, list):
        raise MiroFishUnavailable("MiroFish /personas returned no 'personas' list")
    return [p for p in personas if isinstance(p, dict)]


def rehearse_disclosure(
    finding: dict[str, Any],
    stakeholders: list[str] | None = None,
    *,
    transport: Transport | None = None,
) -> dict[str, Any]:
    """Item 12: ask MiroFish to simulate stakeholder reactions to *finding*.
    Returns {"reactions": [...], "summary": str}; raises MiroFishUnavailable if the
    service can't be reached. This is a planning aid, not a prediction."""
    if not isinstance(finding, dict) or not finding:
        raise ValueError("finding must be a non-empty object")
    payload: dict[str, Any] = {"finding": finding}
    if stakeholders:
        payload["stakeholders"] = stakeholders
    body = (transport or _http_post)("/rehearse", payload)
    reactions = body.get("reactions")
    if not isinstance(reactions, list):
        raise MiroFishUnavailable("MiroFish /rehearse returned no 'reactions' list")
    return {
        "reactions": [r for r in reactions if isinstance(r, dict)],
        "summary": str(body.get("summary") or ""),
    }
