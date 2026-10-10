# FORK.md — Strix fork operating notes

This is a fork of [usestrix/strix](https://github.com/usestrix/strix). Upstream is
active (about 5 commits/day), so this file exists to keep the fork mergeable: it
lists every change to an **upstream-owned file** (the merge-conflict surface) and
the procedure for pulling upstream in.

Design decisions behind the fork live in `../strix_fork_proposed.md` (CEO + eng +
design reviews). Key ones: all fork work stays in **new modules** where possible;
only the hooks below touch upstream files; upstream is synced **weekly** and a
merge is gated on the upstream test suite **plus** an XBEN benchmark run (decision
D7).

## Remotes

- `origin` → https://github.com/mdqms/strix (the fork's home; `main` lives here, push here)
- `upstream` → https://github.com/usestrix/strix (the source; fetch/merge from here for the weekly sync)

## Core-file hooks (edits to upstream-owned files)

Keep this list exhaustive. Every entry is a place a weekly merge can conflict.
Prefer new modules over adding to this list.

| # | File | Change | Why it can't be a new file |
|---|------|--------|----------------------------|
| H1 | `strix/skills/__init__.py` | Added `import os`, `_SKILL_DIR_ENV_VAR`, and `register_skill_dirs_from_env()` (reads `$STRIX_SKILLS_DIR`, os.pathsep-separated, registers each dir ahead of built-ins). | The function belongs beside `register_skill_dir`/`_EXTRA_SKILL_DIRS` which live here. Additive only; no upstream lines changed. |
| H2 | `strix/interface/main.py` | Added a call to `register_skill_dirs_from_env()` at the top of `main()`, right after `setup_console_logging()`. | `main()` is the one startup path shared by view/cloud/scan; the hook must run before any skill resolution. 3-line additive block. |

New files added by the fork (no conflict risk, not listed above): fork skill
directories loaded via `$STRIX_SKILLS_DIR`, and `scripts/sync-upstream.sh`.

## Weekly upstream sync (decision D7)

Run `scripts/sync-upstream.sh`. It fetches `upstream`, merges `upstream/main`, and
then **stops** and prints the gate commands — it never declares the merge good on
its own. The merge is accepted only when both gates pass:

1. **Upstream test suite:** `uv run pytest`
2. **XBEN benchmark:** run the fork against the [usestrix/benchmarks](https://github.com/usestrix/benchmarks)
   XBEN set (needs Docker + an LLM key). Compare the pass count to the pre-merge
   run; a drop blocks the merge.

If a gate fails, fix or revert on a branch before the merge reaches `main`.

**Not yet automated:** a scheduled CI job (e.g. a weekly GitHub Actions workflow)
that runs this sync + gates. It is deferred until `origin` exists on GitHub,
because the schedule and the XBEN run need a hosted CI environment with Docker and
an LLM key. Until then the sync is run by hand on the cadence above.
