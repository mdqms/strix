---
name: infrastructure-as-code
description: Audit Dockerfiles, Compose, Kubernetes manifests, and Terraform/IaC for insecure defaults — exposed services, over-privilege, and secrets baked into config
---

# Infrastructure as Code & Containers

Config is code. A Dockerfile running as root, a Compose port bound to `0.0.0.0`, a
Terraform security group open to the world, or a K8s pod with `privileged: true`
is a reachable weakness even when the app code is clean. White-box scans.

## What to look for

**Containers (`Dockerfile`, `*.dockerfile`):**
- Runs as root (no `USER` directive, or `USER root`).
- Secrets baked in: `ENV`/`ARG` with a token/password, `COPY` of a `.env`/key.
- `latest` or unpinned base images (non-reproducible, unpatched).
- `ADD` from a URL, or `curl … | sh` build steps (supply chain).

**Compose (`docker-compose*.yml`):**
- Ports published to all interfaces (`"5432:5432"` with no `127.0.0.1:` bind) —
  the DB/admin UI is on the network.
- `privileged: true`, the docker socket mounted (`/var/run/docker.sock`), host
  network mode, or broad host bind mounts.
- Hardcoded passwords in `environment:`.

**Kubernetes (`*.yaml` with `kind:`):**
- `securityContext` missing or `privileged: true`, `runAsNonRoot: false`,
  `allowPrivilegeEscalation: true`, host namespaces (`hostNetwork`/`hostPID`).
- Secrets as plain env or in the manifest; overly broad RBAC (`*` verbs/resources).

**Terraform / cloud IaC (`*.tf`):**
- Security group / firewall `0.0.0.0/0` on sensitive ports (22, 3389, DB ports).
- Public storage buckets, unencrypted volumes, secrets in `.tf` or `.tfvars`.

## Procedure

```bash
# fast structural grep across IaC
grep -rnE 'privileged:\s*true|0\.0\.0\.0/0|hostNetwork|runAsNonRoot:\s*false|/var/run/docker\.sock' . 2>/dev/null | head -40
grep -rniE '^(USER|ENV|ARG).*(pass|secret|token|key)=' Dockerfile* 2>/dev/null
# if available, a dedicated IaC scanner surfaces more with checked rules:
trivy config . --format json 2>/dev/null | head -c 4000
```

## Reporting

- `create_vulnerability_report`, one per misconfiguration class.
- `evidence_state`: `static_trace` (config read). If the deployment is live and you
  confirm the exposed port/bucket is reachable, that is `reproduced`.
- Distinguish "insecure default present in config" from "reachable in this
  deployment" — a port bound wide on an internal-only host is lower severity. Put
  the reachability question in `severity_change_conditions`.

---
Adapted from gstack CSO (MIT); see ../NOTICE.
