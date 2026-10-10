---
name: blind-challenger
description: Before filing a finding, have an independent subagent try to disprove it without seeing your conclusion — a blind adversarial check that cuts false positives
---

# Blind Challenger

Before you file a finding with `create_vulnerability_report`, put it through one
independent subagent that tries to **disprove** it. The subagent must not see your
conclusion — only the facts it needs to check. A finding that survives a blind
attempt to kill it is far less likely to be a false positive.

This reuses the normal agent graph: `create_agent` to spawn the challenger,
`wait_for_agents` to get its verdict. No new tool.

## When this applies

- You have a candidate finding you are about to file (you have the locations, the
  data path, and a claim that a security boundary is crossed).
- Skip it only for a finding you have already reproduced with a working PoC against
  the live target **and** whose reproduction the challenger could not add to — say
  why in the report's counterevidence.

## The blind briefing (what the challenger may and may not see)

Spawn the challenger with `create_agent`. Its task briefing contains ONLY:

- The code locations / endpoint / request involved (file:line, route, method).
- The security **invariant** at stake, stated neutrally as a question, e.g.
  "Determine whether unauthenticated input can reach this SQL query unsanitised,"
  not "Confirm this SQL injection."
- The access it needs to check (read these files; send these requests).

It must NOT contain, anywhere in the briefing:

- Your verdict that this is a vulnerability, its severity, CVSS, or confidence.
- Your `technical_analysis` conclusion, `impact`, or `poc_description`/PoC script.
- Words that presuppose the finding ("exploit", "vulnerable", "injection flaw").

Give the challenger the opposite job: **find the control, guard, or precondition
that makes this NOT exploitable.** Tell it to report, via `agent_finish`, either
"refuted: <the specific control it found>" or "could not refute: <what it checked>".

A challenger must not spawn its own challenger. If your own task briefing is a
challenge ("determine whether…", "find the control that…"), do the check and return
your verdict; do not recurse.

## Acting on the verdict

- **Refuted with a concrete control** (a real guard, authz check, sanitizer, or
  unreachable path the challenger located): do not file. Close the candidate as
  `ruled_out` per the counterevidence skill, recording the control.
- **Could not refute:** file the finding. Put what the challenger checked and failed
  to refute into `counterevidence` — that is exactly the blind second opinion that
  field is for.
- **Challenger timed out, errored, or could not get the access it needed:** file the
  finding anyway (do not sit on a real finding because review infrastructure failed),
  but mark it clearly: begin the report's `counterevidence` with
  `UNCHALLENGED: challenger did not return a verdict (<reason>)`. A reviewer must be
  able to see the finding skipped its blind check.

The challenger reduces false positives; it is not a gate that can bury a true
finding. When in doubt between dropping and filing-as-unchallenged, file.
