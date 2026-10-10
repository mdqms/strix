---
name: integrations-webhooks
description: Audit inbound webhooks and third-party integrations for missing signature verification, SSRF via integration URLs, and replay/spoofing of external events
---

# Integrations & Webhooks

Webhook endpoints and third-party integrations are an attack surface that normal
crawling misses: they are called by external systems, often skip the app's auth,
and are trusted to carry real events. Works on both black-box (probe the endpoint)
and white-box (read the handler) scans.

## What to look for

1. **Missing / broken signature verification.** A handler for Stripe, GitHub,
   Slack, Twilio, etc. that does not verify the provider's HMAC signature (or
   verifies it wrong: no constant-time compare, signature read from an
   attacker-controlled field, verification behind a feature flag that is off).
   Anyone who learns the URL can POST forged events. Look for the webhook route,
   then check whether the raw body + a shared secret are actually checked.
2. **Replay.** Signature checked but no timestamp/nonce freshness → a captured
   valid request can be replayed (e.g. re-trigger a "payment succeeded").
3. **SSRF via integration config.** A feature that fetches a user-supplied URL
   (webhook target, avatar URL, "import from URL", OAuth redirect/metadata) with no
   egress allow-list → SSRF to cloud metadata (`169.254.169.254`), internal hosts,
   or `file://`. See the packaged SSRF knowledge for exploitation.
4. **Secrets / over-trust.** Integration tokens stored in plaintext, or the
   integration granted far more scope than the feature needs.

## Procedure

```bash
# white-box: find webhook handlers and whether they verify signatures
grep -rniE 'webhook|/hooks?/|x-hub-signature|stripe-signature|x-slack-signature|hmac|verify.*signature' \
  --include=*.py --include=*.js --include=*.ts --include=*.rb --include=*.go . 2>/dev/null | head -40
# find user-supplied-URL fetches (SSRF candidates)
grep -rniE 'requests\.get\(|httpx\.|fetch\(|urllib|net/http|open-uri' . 2>/dev/null | grep -iE 'url|endpoint|callback|target' | head -30
```

Black-box: POST a plausible but unsigned/forged event to the webhook route and see
if it is accepted and acted on (only against authorized targets).

## Reporting

- `create_vulnerability_report`, one per issue. For a forged-event finding, the PoC
  is the accepted unsigned request; for SSRF, the request reaching an internal host.
- `evidence_state`: `reproduced` if you landed a forged/replayed request or an SSRF
  callback; `static_trace` if you only read that verification is absent.
- `assumptions`: state whether the webhook URL is guessable/known (it usually is).

---
Adapted from gstack CSO (MIT); see ../NOTICE.
