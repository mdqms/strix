# XBEN before/after eval (plan T4, decision D9)

Measures whether two fork changes make Strix solve **fewer** XBEN challenges than a
hosted-model baseline:

1. the **local model** (item 4) — is a self-hosted model much weaker on Strix's task?
2. the **blind challenger** (item 14) — does it suppress true findings?

XBEN is the 104-challenge black-box benchmark (upstream reports 96% on v0.4.0). This
harness runs it three times and gates on a no-regression threshold.

## What's here

- `compare.py` — the no-regression gate. Pure comparison of per-arm result JSONs;
  unit-tested. Exit 0 if every arm is within the allowed regression, else 1.
- `run_arm.sh` — runs one arm over the XBEN challenges and writes its result JSON.
  Needs real infra (below).
- `arms.example.sh` — the three arms' env (baseline-hosted / local-model /
  challenger-on). The challenger is toggled with `STRIX_DISABLE_BLIND_CHALLENGER`.

## Prerequisites (you provide these)

- The XBEN challenges: clone `https://github.com/usestrix/benchmarks` and point
  `XBEN_DIR` at its `XBEN/` directory.
- The self-hosted stack up (`deploy/`), so sandboxes run in the throwaway daemon.
- LLM access per arm (a hosted model for the baseline, your local model for the
  others), set via `arms.example.sh`.

This cannot run in a sandbox without those; it is real-infra eval scaffolding.

## Run it

```bash
source evals/xben/arms.example.sh      # edit the model ids / keys first
baseline_hosted && XBEN_DIR=/path/to/XBEN ./evals/xben/run_arm.sh   # against UPSTREAM strix
local_model     && XBEN_DIR=/path/to/XBEN ./evals/xben/run_arm.sh
challenger_on   && XBEN_DIR=/path/to/XBEN ./evals/xben/run_arm.sh

python3 evals/xben/compare.py \
  --baseline evals/xben/results/baseline-hosted.json \
  --arm evals/xben/results/local-model.json \
  --arm evals/xben/results/challenger-on.json \
  --max-regression 3
```

`--max-regression N` is the threshold: how many challenges the baseline solved that
an arm may miss before that arm fails the gate. Start strict (0–3) and set it from
what you learn; record the chosen number with the results.

## Pass detection

XBEN is CTF-style: a challenge is solved when the agent extracts the flag. By
default `run_arm.sh` treats headless exit code `2` (vulnerabilities found) as
solved. If the benchmark ships a flag checker, set `XBEN_PASS_CMD` to it (it runs
per challenge with `$CHAL` / `$CHAL_DIR` set and must exit 0 on solved) for a
precise signal. Adjust `XBEN_TARGET_PREFIX` / the target line in `run_arm.sh` to how
XBEN exposes each challenge (URL vs local dir vs compose).

## Interpreting

- `local-model` regressing a lot vs baseline → the local model is too weak for
  Strix's task; keep a hosted model or pick a stronger local one before shipping.
- `challenger-on` regressing vs `local-model` → the blind challenger is killing
  true findings; tighten its skill or disable it (`STRIX_DISABLE_BLIND_CHALLENGER=1`).
- Neither regressing beyond threshold → both changes are safe to ship (the D9 gate).
