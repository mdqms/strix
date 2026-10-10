---
name: dependency-supply-chain
description: Supply-chain risks beyond known CVEs — typosquats, unpinned or floating deps, install-time scripts, and compromised or abandoned packages
---

# Dependency Supply Chain

Complements the packaged `dependency-cve-scanning` skill (which matches lockfiles
against known CVEs). This one covers the supply-chain risks a CVE scanner misses:
how a dependency can harm you even with zero known CVEs. White-box / repository
scans.

## What to look for

1. **Typosquats / confusable names.** A package one character off a popular one
   (`reqeusts`, `lodahs`, `python-dateutil` vs a look-alike) or an internal name
   that also exists on a public registry (dependency confusion). Check direct
   deps in `package.json`, `requirements.txt`, `pyproject.toml`, `go.mod`, `Gemfile`
   against the real upstream name.
2. **Unpinned / floating versions.** `^`, `~`, `*`, `latest`, no lockfile, or a
   lockfile not committed. A floating dep means the build is not reproducible and a
   future malicious release lands silently. Report missing/!committed lockfiles.
3. **Install-time code execution.** npm `preinstall`/`postinstall`/`install`
   scripts, Python `setup.py` with network/exec at build, `pip` VCS or URL deps.
   These run on every `npm ci` / `pip install`, including in CI with secrets.
4. **Abandoned / low-trust packages.** A direct dep with a single maintainer, no
   releases in years, or very low downloads carries takeover risk. Note it; it is a
   risk rating, not a confirmed vuln.
5. **Source other than the registry.** Deps pulled from a git URL, a tarball URL,
   or an alternate registry (`.npmrc`/`pip.conf` pointing elsewhere) bypass the
   usual trust path.

## Procedure

```bash
# npm: list install scripts that will execute
jq '.scripts, .dependencies, .devDependencies' package.json 2>/dev/null
grep -rnE '"(pre|post)?install"\s*:' package.json 2>/dev/null
# pins / lockfile presence
ls package-lock.json yarn.lock pnpm-lock.yaml poetry.lock uv.lock Gemfile.lock go.sum 2>/dev/null
grep -nE '[\^~*]|latest' package.json requirements.txt 2>/dev/null | head
# alternate registries
cat .npmrc pip.conf .pip/pip.conf 2>/dev/null
```

## Reporting

- Known-CVE deps → use `create_dependency_report` (see the packaged SCA skill).
- The risks above → `create_vulnerability_report`. Evidence is the manifest entry +
  the published fact (typosquat name, missing pin, install script body).
- `evidence_state`: `static_trace`. These are reachable at build/install time;
  say so in `counterevidence` rather than claiming runtime exploitation.
- Severity scales with where it installs (a CI runner with deploy creds is worse
  than a dev laptop) — name that in `severity_change_conditions`.

---
Adapted from gstack CSO (MIT); see ../NOTICE.
