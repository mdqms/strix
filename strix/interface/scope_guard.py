"""Approved-target allowlist check (fork plan item 33).

Deny-by-default gate: a scan runs only against a target that matches the
operator's allowlist. Enforced by the ``scripts/strix-scoped`` wrapper, which
validates every ``-t/--target`` before handing off to ``strix``. Pure functions
here so the matching is unit-testable without launching a scan.

Allowlist entry forms (one per line; ``#`` comments and blank lines ignored):

- ``example.com``            host; matches that host exactly (any scheme/port/path)
- ``*.example.com``          that host's subdomains (not the apex unless also listed)
- ``10.0.0.5``               an IP, matched exactly
- ``/srv/code``              a local path; matches that path or anything under it
- ``postman://<uuid>``       matched by exact string

Matching is host-based for URLs/domains/IPs and prefix-based for local paths. It
is intentionally strict: if you cannot tell what a target is, it is not approved.
"""

from __future__ import annotations

import ipaddress
from pathlib import PurePosixPath
from urllib.parse import urlsplit


def _host_of(target: str) -> str | None:
    """Return the host for a URL/domain/IP target, or None for non-host targets."""
    t = target.strip()
    if not t or t.startswith(("/", ".", "~")) or t.startswith("postman://"):
        return None
    if "://" in t:
        host = urlsplit(t).hostname
        return host.lower() if host else None
    # bare domain or ip, possibly host:port or host/path
    hostport = t.split("/", 1)[0]
    host = hostport.rsplit(":", 1)[0] if ":" in hostport and not hostport.endswith(":") else hostport
    host = host.strip("[]")  # IPv6 brackets
    return host.lower() or None


def _is_local_path(target: str) -> bool:
    t = target.strip()
    return t.startswith(("/", "./", "../", "~")) or t == "."


def normalize_target(target: str) -> str:
    return target.strip()


def _host_matches(host: str, entry: str) -> bool:
    entry = entry.lower()
    if entry.startswith("*."):
        suffix = entry[1:]  # ".example.com"
        return host.endswith(suffix) and host != suffix[1:]
    return host == entry


def _path_matches(target_path: str, entry: str) -> bool:
    try:
        tp = PurePosixPath(target_path.rstrip("/") or "/")
        ep = PurePosixPath(entry.rstrip("/") or "/")
    except ValueError:
        return False
    return tp == ep or ep in tp.parents


def is_authorized(target: str, allowlist: list[str]) -> bool:
    """True iff *target* matches at least one allowlist entry. Deny by default."""
    target = normalize_target(target)
    if not target:
        return False
    entries = [e.strip() for e in allowlist if e.strip() and not e.strip().startswith("#")]
    if not entries:
        return False  # empty allowlist authorizes nothing

    if _is_local_path(target):
        return any(_is_local_path(e) and _path_matches(target, e) for e in entries)

    if target.startswith("postman://"):
        return target in entries

    host = _host_of(target)
    if host is None:
        return False
    # An IP target only matches an identical IP entry.
    try:
        ipaddress.ip_address(host)
        return host in {e.strip().lower() for e in entries}
    except ValueError:
        pass
    return any(not _is_local_path(e) and "://" not in e and _host_matches(host, e) for e in entries)


def load_allowlist(path: str) -> list[str]:
    """Read an allowlist file (one entry per line). Missing file -> empty list."""
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.readlines()
    except OSError:
        return []


def unauthorized(targets: list[str], allowlist: list[str]) -> list[str]:
    """Return the targets that are NOT authorized (empty list == all approved)."""
    return [t for t in targets if not is_authorized(t, allowlist)]
