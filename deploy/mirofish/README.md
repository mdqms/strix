# MiroFish integration (optional, fork plan items 11-12)

Two optional, security-adjacent uses of the MiroFish social-simulation engine:

- **Persona test data (item 11):** generate realistic multi-user / multi-tenant
  data to seed a staging app you own, so access-control and IDOR findings have real
  cross-user state to exercise.
- **Disclosure rehearsal (item 12):** simulate how stakeholders might react to a
  confirmed finding, as a fix-prioritisation and comms planning aid.

Both are off by default and need a running MiroFish plus LLM access. They are the
least-validated part of this fork.

## License boundary — read first

MiroFish is **AGPL-3.0**; this fork is Apache-2.0. The boundary is kept by running
MiroFish as a **separate process** and talking to it only over HTTP:

- The fork contains **no MiroFish source** — only an HTTP client
  (`strix/integrations/mirofish.py`) that imports nothing from MiroFish.
- MiroFish runs from its own published image via `deploy/mirofish.compose.yml`, as
  its own compose project.
- Do not vendor, copy, or `import` MiroFish code into this repo. Keep it a service.

If you distribute a modified MiroFish, AGPL obligations apply to *that* service, not
to this fork. If in doubt, check with a lawyer.

## Run it

```bash
# main stack first (creates the strix-fork_strixnet network)
cd deploy && docker compose up -d
# then MiroFish as its own project
docker compose -f mirofish.compose.yml -p strix-mirofish up -d
# host Strix / tooling:
export STRIX_MIROFISH_URL=http://127.0.0.1:5001
```

MiroFish needs its own config (LLM keys, Zep/graph) in `deploy/mirofish/.env`; see
the MiroFish project for what it expects.

## The adapter you must add (seam)

MiroFish's stock app has no endpoint for these two jobs. Add a thin adapter in your
MiroFish deployment exposing:

```
POST /personas  {"spec": {...}, "count": N}
  -> {"personas": [{"name": "...", "role": "...", "attributes": {...}}, ...]}

POST /rehearse  {"finding": {...}, "stakeholders": ["customers","press",...]?}
  -> {"reactions": [{"stakeholder": "...", "reaction": "...", "severity_felt": "..."}, ...],
      "summary": "..."}
```

The fork client shapes requests and parses responses to exactly this contract and
degrades to "MiroFish unavailable" if the service can't be reached. The adapter
itself, and the quality of what MiroFish returns, are yours to build and validate
against a running instance — none of that is verified here.

Only seed generated personas into applications you are authorized to test.
