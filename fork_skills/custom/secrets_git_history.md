---
name: secrets-git-history
description: Find live secrets in a repository's git history, not just its working tree — a committed-then-deleted key is still valid and still a finding
---

# Secrets in Git History

The working tree is clean, but a credential committed in 2023 and deleted in the
next commit is still in `git log` and usually still works. Scan **history**, not
just HEAD. Use on white-box / repository scans.

## Why this matters

Deleting a secret in a later commit does not remove it from history; anyone who
clones the repo gets every past version. Rotation, not deletion, is the fix. So a
secret anywhere in history is a finding until proven rotated.

## Procedure

Run from the repo root in the sandbox:

```bash
# Full-history secret scan. gitleaks reads the whole log, not just the tree.
gitleaks detect --source . --report-format json --report-path /workspace/.gitleaks.json --redact || true

# If gitleaks is unavailable, grep history for high-signal patterns:
git log -p --all \
  | grep -nE 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-|gh[pousr]_[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{35}' \
  | head -50
```

Also check: `.env*`, `*.pem`, `id_rsa`, `*.pfx`, cloud credential files, and
CI config across history.

## Triage before reporting

A match is a candidate, not a finding. Establish:

1. **Reachability of the secret itself:** is the commit in a branch an attacker
   can clone (public repo, shared mirror)? A secret in a never-pushed local branch
   is not exposed.
2. **Still valid?** A rotated/expired key is a hygiene note, not a live finding.
   You usually cannot test validity safely — do NOT authenticate with a found
   credential. State it as "unverified; rotation unconfirmed" in counterevidence.
3. **What it grants:** scope the blast radius (read-only token vs cloud admin key).

## Reporting

File with `create_vulnerability_report`. In the report:

- Give the commit hash + path, never the raw secret value in full — redact the
  middle (`AKIA…XMPL`). The PoC is the history location, not a working login.
- `evidence_state`: `static_trace` (found in history, not used) unless you have
  out-of-band confirmation it is live.
- `counterevidence`: state whether the branch is reachable and whether rotation
  was confirmed; "found in history" alone over-claims if the key is dead.
- Remediation: rotate the credential, then (optionally) rewrite history. Deleting
  the commit alone does not fix it.

---
Adapted from gstack CSO (MIT); see ../NOTICE.
