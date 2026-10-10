---
name: data-classification
description: Find where sensitive data (PII, secrets, payment, health, auth material) lives and flows, so access-control and disclosure findings are weighted by what is actually at risk
---

# Data Classification

A security finding's severity depends on *what data it exposes*. An IDOR on a
list of public blog slugs is minor; the same IDOR on SSNs or auth tokens is
critical. This skill maps the sensitive data in the target so other findings can
be weighted correctly, and so unprotected sensitive stores become findings in
their own right. White-box scans (and informs black-box severity).

## Step 1 — Find sensitive data

Look in the data model, migrations, serializers/DTOs, logs, and fixtures for:

- **Identity / PII:** name, email, phone, address, DOB, government IDs (SSN,
  passport), IP addresses.
- **Auth material:** passwords/hashes, API keys, session tokens, OAuth
  refresh tokens, MFA secrets, recovery codes.
- **Payment:** card numbers/PAN, CVV, bank/IBAN, billing details.
- **Health / special category:** medical, biometric, precise geolocation.
- **Business-sensitive:** internal pricing, other tenants' data.

```bash
grep -rniE 'ssn|social_security|passport|credit_?card|card_?number|cvv|iban|routing|\bdob\b|date_of_birth|password|api_?key|secret|token|mfa|biometric|medical|diagnosis' \
  --include=*.py --include=*.rb --include=*.js --include=*.ts --include=*.sql --include=*.prisma . 2>/dev/null | head -50
# schema/migrations are the highest-signal place
find . -path '*migrat*' -o -name '*.sql' -o -name 'schema.*' 2>/dev/null | head
```

## Step 2 — Trace its flow

For each sensitive field, note: where it enters, where it is stored (encrypted?),
where it leaves (API responses, logs, analytics, third parties, exports). The
leaks are usually at the edges:

- **Over-exposed in responses:** a serializer returning the whole user row
  (password hash, other users' fields) — pair with IDOR/BOLA and mass-assignment.
- **In logs / errors:** sensitive values written to logs or stack traces.
- **To third parties:** PII sent to analytics/monitoring/LLM providers.
- **At rest unencrypted:** card/health/auth material in plaintext columns.

## Step 3 — Use it

- Raise the severity of access-control / disclosure findings that touch classified
  data; say which class in `impact` and `severity_change_conditions`.
- File unprotected sensitive data as its own finding (plaintext secrets at rest,
  PII in logs, PAN stored in violation of PCI) via `create_vulnerability_report`,
  `evidence_state: static_trace`.
- Record which data stores you reviewed in the coverage ledger.

---
Adapted from gstack CSO (MIT); see ../NOTICE.
