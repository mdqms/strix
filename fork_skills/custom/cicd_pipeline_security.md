---
name: cicd-pipeline-security
description: Audit CI/CD config (GitHub Actions, GitLab CI, etc.) for untrusted-code execution with secrets, injection into run steps, and over-broad token scope
---

# CI/CD Pipeline Security

CI runs with credentials (deploy keys, cloud roles, registry tokens) and often on
attacker-influenced input (PR titles, branch names, fork code). A pipeline flaw is
a direct path from a pull request to your secrets or production. White-box scans.

## Where to look

- GitHub Actions: `.github/workflows/*.yml`
- GitLab CI: `.gitlab-ci.yml`
- Others: `Jenkinsfile`, `.circleci/config.yml`, `azure-pipelines.yml`, `bitbucket-pipelines.yml`

## High-signal issues

1. **Untrusted code with secrets (the big one).** A workflow triggered by
   `pull_request_target` (GitHub) or that runs on fork PRs AND checks out the PR
   head AND has access to secrets. Fork code then runs with repo secrets. Also:
   `workflow_run`, and self-hosted runners on public repos (fork PRs run arbitrary
   code on your infra).
2. **Script injection into `run:`.** Interpolating `${{ github.event.* }}` —
   PR title, branch name, commit message, issue body — straight into a shell
   `run:` step. Attacker controls those; it is shell injection in CI.
   Example tell: `run: echo "${{ github.event.pull_request.title }}"`.
3. **Over-scoped token.** Default `GITHUB_TOKEN` with `permissions: write-all`
   or no `permissions:` block (inherits broad default), or a long-lived PAT/cloud
   key in `secrets` where OIDC/short-lived would do.
4. **Unpinned third-party actions.** `uses: some/action@main` or `@v3` (tag,
   mutable) instead of a full commit SHA. A compromised action tag runs in your
   pipeline.
5. **`pull_request_target` + checkout of PR code** is the classic exfiltration
   combo — call it out specifically.

## Procedure

```bash
ls .github/workflows/ 2>/dev/null; cat .github/workflows/*.yml 2>/dev/null
grep -rnE 'pull_request_target|workflow_run|permissions:\s*write-all|uses:.*@(main|master|v[0-9]+)\b' .github/workflows/ 2>/dev/null
grep -rnE 'run:.*\$\{\{\s*github\.event' .github/workflows/ 2>/dev/null
cat .gitlab-ci.yml Jenkinsfile 2>/dev/null
```

## Reporting

- `create_vulnerability_report`, one per distinct pipeline flaw. Evidence is the
  workflow file + the exact trigger/step.
- `evidence_state`: `static_trace` (config read) unless you can actually run a PR
  against a test fork to prove exfiltration (`reproduced`).
- The attacker here is "anyone who can open a PR / push a branch" — state that in
  `assumptions`, and in `impact` name what the leaked token reaches.

---
Adapted from gstack CSO (MIT); see ../NOTICE.
