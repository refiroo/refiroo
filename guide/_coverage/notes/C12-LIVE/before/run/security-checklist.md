---
title: Security checklist
description: Check transport, secrets, access and recovery boundaries before opening an installation.
reader: operator
---

Use this list before opening traffic and after a proxy, sign-in or key change. The Docker Compose
reference is the tested installation. A custom balancer or network boundary needs checks of its
own; historical security tests do not certify your deployment.

- **HTTPS and one origin:** use a valid certificate and the permanent HTTPS `PUBLIC_URL`.
  Check HTTP redirection and certificate renewal. See [HTTPS](/docs/run/https/).
- **Private services:** publish only `web`, or Caddy with the automatic overlay. Keep PostgreSQL,
  engine and metrics ports private. The engine trusts forwarded caller addresses from web.
- **Trusted balancers:** with `WEB_TLS=proxy`, restrict access to the balancer, replace untrusted
  forwarded headers there and set `WEB_TRUSTED_PROXIES` to its actual connecting range.
  Empty trusts nobody and combines users under the balancer's address for throttling.
- **Browser origins:** keep `CORS_ORIGINS` to the exact intended origins. The session refresh cookie is
  HttpOnly, SameSite=Strict, scoped to `/oauth`, and Secure when `PUBLIC_URL` uses HTTPS.
  Provider redirect cookies use SameSite=Lax so the external sign-in return can work.
- **Framing and scripts:** verify `Content-Security-Policy: frame-ancestors 'none'` and
  `X-Frame-Options: DENY` on the web application. The engine's sign-in and API-reference pages
  supply their own script policies. Keep these headers through your proxy.
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
  a name or 20 for an address, delays grow up to 15 minutes. A known username can be slowed by
  another caller. Preserve real caller addresses and investigate repeated failures.
- **Outbound connections:** permit only needed providers, SMTP, webhook receivers and optional AI.
  Preserve TLS verification and supply internal CAs where needed. Check the optional assistant's
  [network and data boundaries](/docs/run/ai/) before enabling it.
- **Files and logs:** protect job files, delivery payloads, database backups and debug logs as
  sensitive data. Prefer XLSX when opening untrusted text exports in spreadsheet software; CSV
  text can be interpreted as formulas.
- **Recovery and updates:** test a [restore](/docs/run/backup-and-restore/) and watch
  [readiness and failures](/docs/run/monitoring/). Use a release receiving security fixes;
  before 1.0 that is the latest minor release.

## What the recorded security sweep covers

The repository records an authorization sweep across API operations and predefined roles, including
unauthenticated requests and caller-without-grants refusals. It also records deployment checks for
forwarded addresses and framing, and a generic provider trial with Keycloak. These are bounded
project checks, not an assurance about every provider and proxy. The recorded review excludes,
among other areas, real passkey ceremonies in the sweep, person/group consumer grants, and a full
review of workbook parsing and webhook delivery. Verify your chosen provider, network and recovery
procedures rather than treating that sweep as a production certificate.

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
