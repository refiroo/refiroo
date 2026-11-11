---
title: Security checklist
description: Check transport, secrets, access and recovery boundaries before opening an installation.
reader: operator
---

Use this list before opening traffic and after a proxy, sign-in or key change. The Docker Compose
reference is the tested installation. A custom balancer or network boundary needs checks of its
own; historical security tests do not certify your deployment.

- **HTTPS and one origin:** use a valid certificate and the permanent HTTPS `PUBLIC_URL`.
  Check certificate renewal and HTTP redirection if port 80 is open. Public TCP 443 alone is
  sufficient for automatic certificates; port 80 may remain closed. See [HTTPS](/docs/run/https/).
- **Private services:** publish only `web`, or Caddy with the automatic overlay. Keep PostgreSQL,
  engine and metrics ports private. Compose trusts forwarded caller addresses only from the private
  ranges in `FORWARDED_ALLOW_IPS`, not every address. For another proxy, set that list in `.env`
  to the addresses that connect to the engine and recreate it.
- **Trusted balancers:** with `WEB_TLS=proxy`, restrict access to the balancer, replace untrusted
  forwarded headers there and set `WEB_TRUSTED_PROXIES` to its actual connecting range.
  Empty trusts nobody and combines users under the balancer's address for throttling.
- **Browser origins:** keep `CORS_ORIGINS` to the exact intended origins. The session refresh cookie is
  HttpOnly, SameSite=Strict, scoped to `/oauth`, and Secure when `PUBLIC_URL` uses HTTPS.
  Provider redirect cookies use SameSite=Lax so the external sign-in return can work.
- **Framing and scripts:** verify the application's Content Security Policy restricts scripts and
  requests to its own origin and includes `frame-ancestors 'none'`; check `X-Frame-Options: DENY`
  too. The engine's sign-in pages, guide and API reference supply their own policies. Preserve
  them through your proxy; see [content security policies](/docs/run/https/#preserve-the-content-security-policies).
- **Secrets:** never commit environment files, keys or credentials, and never bake them into
  images. Keep backup keys outside PostgreSQL. Rehearse [resealing](/docs/run/secrets-and-keys/)
  as a planned operation; changing the key voids unused recovery codes.
- **Access:** replace broad setup grants with appropriate [roles](/docs/administer/roles-and-grants/).
  Capability switches restrict deployments but do not grant permissions. Authentication cannot
  be disabled by a setting. Keep and test a local recovery administrator.
- **Passwords and sign-in:** leave `PASSWORD_MIN_LENGTH=15` in production. Choose session lifetimes
  to match policy and use the organisation's provider or second-factor requirements. Disable
  leavers in refiroo as well as at the provider.
- **Throttling:** sign-in has per-name and per-address delays; after the first five failures for
  a name or 20 for an address, delays grow up to 15 minutes. A known e-mail address can be slowed by
  another caller. Preserve real caller addresses and investigate repeated failures.
- **Outbound connections:** permit only needed providers, SMTP, webhook receivers and optional AI.
  Preserve TLS verification and supply internal CAs where needed. Check the optional assistant's
  [network and data boundaries](/docs/run/ai/) before enabling it. Webhooks refuse private and
  loopback destinations by default. Enable `WEBHOOK_PRIVATE_ADDRESSES_ALLOWED` only for intended
  internal receivers; link-local destinations remain refused. Check private receivers after an
  upgrade, as existing subscriptions are subject to the same rule.
- **Assistant sessions:** keep `AI_AGENT_SANDBOX=container` as supplied by the image and Compose.
  Size the `ASSISTANT_USERS` build argument for the engine processes (default 8). Each task keeps
  its transcript in its own folder. Permissions open that folder only to the user running the
  turn and close it between turns. Each turn takes a free session user and resets that user's
  processes, home and temporary files before and after running. Keep Compose's `init: true`, or
  use `docker run --init` with the image.
  The provider credential still reaches the session, and outbound connections are unrestricted.
  Use a dedicated credential with a spending limit and your deployment's network restrictions.
  Task isolation inside the container depends on Unix permissions and the reset; reviews are
  not proof of isolation. A separate container per session is stronger and is not built in.
  See [the assistant's session](/docs/run/ai/#the-assistants-session) for all three limits.
- **Files and logs:** protect job files, delivery payloads, database backups and debug logs as
  sensitive data. CSV exports prefix formula-like text with a single quote; keep that protection
  when opening or returning a file. Other CSV sources may lack it. XLSX exports are unaffected.
  See [CSV text rules](/docs/use/importing-and-exporting/#text-in-csv-files).
- **Recovery and updates:** test a [restore](/docs/run/backup-and-restore/) and watch
  [readiness and failures](/docs/run/monitoring/). Use a release receiving security fixes;
  before 1.0 that is the latest minor release. Keep image digests, the Claude Code build version,
  Python constraints and npm lock files with your source; move them using the
  [build-version procedure](/docs/run/upgrades/#maintain-build-versions).

## Repeat checks after a change

Check the real installation after changing a proxy, public address, identity provider, key or
permission. A sign-in test at the old address does not verify the new one. Use a narrowly granted
test person and a working recovery administrator; preserve previous configuration and a matching
backup before maintenance. Follow the linked procedures for credential rotation and recovery.

## Check the installed boundary

You need an operator shell, access administration support and a browser on the caller's network.
Perform these checks before public access and after a proxy change. They read the current
installation; they do not prove every possible attack is prevented.

```bash
docker compose ps
curl -I https://refiroo.example.org/
curl -i https://refiroo.example.org/metrics
curl -i https://refiroo.example.org/api/v1/workspaces
```

Replace the public name. Confirm no engine or PostgreSQL port mapping; framing and content-type
headers from [HTTPS](/docs/run/https/#verify-from-the-callers-network); public metrics 404; and an
unauthenticated workspace request refused with `401 AUTHENTICATION_REQUIRED` after startup.
A readiness failure or startup maintenance mode can prevent ordinary authentication handling;
resolve it before judging permissions. A 200 application page returned by a misrouted proxy is
not a successful API-authentication test: check status, content type and response content.

With a fresh browser session, sign in as a test person with narrow grants, verify only their
workspaces are offered, then sign out and confirm a protected page requires sign-in again. An
access administrator should confirm the local recovery account and second-factor recovery route.
Do not intentionally lock out the last administrator to test recovery.

## Review trust and secrets after a change

For a proxy-mode deployment, record the actual address range the balancer connects from and the
private route to web. `WEB_TRUSTED_PROXIES` must describe that route; a caller must not be able to
bypass the balancer to supply trusted forwarding headers. The base file publishes web ports, so
proxy mode also requires a host firewall/network rule restricting who can reach them. Setting a
trust variable alone does not install that firewall rule.

Keep `SECRETS_ENCRYPTION_KEY`, the database password, cursor key and TLS private key in protected
storage and test that recovery staff can retrieve the right versions. Check that backup storage
is protected as well as the live host. The application does not supply a secret store, host firewall,
SPF/DKIM, backup scheduler or deployment-wide log retention; configure these in your environment.
No hardware minimum or complete production threat assessment has been measured by this guide.

If a credential leaked, determine which one before acting. Resealing protects stored ciphertext;
it does not revoke a leaked client or webhook credential. Rotate that credential through its
administrator workflow and distribute the replacement securely. For a sealing-key change, follow
[the offline reseal procedure](/docs/run/secrets-and-keys/) and replace affected recovery codes.

A failed check should leave public writes closed until corrected. Restore the prior known-safe
proxy/configuration and recreate affected services where possible, then recheck TLS, authentication,
caller-address handling and readiness. Do not reopen a database/engine port as a temporary repair
for a proxy error. Preserve concise diagnostics and a request ID for escalation, with no secrets.
