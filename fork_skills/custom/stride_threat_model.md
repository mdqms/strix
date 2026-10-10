---
name: stride-threat-model
description: A STRIDE pass over the target to drive coverage — enumerate trust boundaries and, per boundary, the Spoofing/Tampering/Repudiation/Info-disclosure/DoS/Elevation threats worth probing
---

# STRIDE Threat Model

Use early, especially on white-box or whole-product scans, to turn "poke at it"
into deliberate coverage. STRIDE is a checklist against each trust boundary so you
don't only test the vuln classes that came to mind. It feeds the existing
`threat_model` tool and your coverage ledger; it does not replace per-finding
validation.

## Step 1 — Map trust boundaries

A boundary is any place data or control crosses a trust level: internet → app,
app → database, service → service, user → admin, tenant → tenant, app → third
party, CI → prod. List them from the architecture, routes, and service map.

## Step 2 — STRIDE per boundary

For each boundary ask the six questions; each maps to a vuln class Strix already
knows how to exploit:

| STRIDE | The question at this boundary | Typical class to probe |
|---|---|---|
| **S**poofing | Can someone pretend to be another identity/service? | auth bypass, weak/forgeable tokens (JWT), missing mTLS |
| **T**ampering | Can inputs or stored data be altered in transit/at rest? | injection, mass assignment, insecure deserialization |
| **R**epudiation | Can an action be denied / is it unlogged? | missing audit log on sensitive ops |
| **I**nfo disclosure | Can data leak across this boundary? | IDOR/BOLA, excessive data exposure, verbose errors, SSRF |
| **D**enial of service | Can one actor exhaust a shared resource? | unbounded queries, no rate limit, zip/regex bombs |
| **E**levation | Can a lower privilege become higher? | broken function-level authz, sandbox escape, path traversal |

## Step 3 — Prioritise and record

- Rank cells by reachability and impact; attacker-reachable boundaries first.
- Record each cell you decide to test in the coverage ledger (`record_coverage`)
  so a deliberately skipped cell is visible as a gap, not a silent omission.
- Then test with the matching vulnerability skill. STRIDE picks the targets; it
  proves nothing on its own — findings still need real evidence.

## Reporting

STRIDE produces candidates, not findings. File confirmed issues with
`create_vulnerability_report` as usual. Use the ledger to show which STRIDE cells
were covered and which remain `not_assessed`, so the run's completeness is honest.

---
Adapted from gstack CSO (MIT); see ../NOTICE.
