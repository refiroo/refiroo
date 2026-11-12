---
title: Production checklist
description: Check installation, access, monitoring and recovery before accepting production traffic.
reader: operator
---

Complete this checklist on the actual installation before accepting production writes. The commands
and setup steps are in the linked pages; record your outcomes and recovery contacts locally.

1. **Use the reference installation.** Build the intended source version with
   [Docker Compose](/docs/run/install-with-compose/). Keep only the entry web service public.
   PostgreSQL 17 must use ICU root `und` and the required extensions.
2. **Fix the public address and choose HTTPS.** Set the permanent HTTPS `PUBLIC_URL`, matching
   browser origins and provider callbacks. For a public name, choose [automatic HTTPS](/docs/run/https/)
   with `compose.acme.yml`: Caddy obtains and renews the certificate. Confirm DNS points here,
   TCP 443 is reachable from the internet and the `caddy-data` volume is preserved. Port 80 is
   optional for HTTP redirects; TLS-ALPN issuance and renewal work on 443 alone.
   Alternatively, supply your organisation's certificates or use its HTTPS balancer. Check
   certificate trust and renewal, plus HTTP redirection if port 80 is open. If behind a balancer, check its trusted address
   range and forwarded headers.
3. **Protect secrets.** Store the database password, sealing key and stable cursor key outside
   version control and images. Keep the same keys across processes. Associate each backup with
   its sealing key: [Secrets and keys](/docs/run/secrets-and-keys/).
4. **Confirm effective settings.** Read **Settings › This instance › Deployment**. Verify capability
   switches, limits, retention and migration revision. Recreate containers after environment
   changes; restarting alone does not apply them.
5. **Check access.** Test the first administrator, provider sign-in if used, appropriate grants,
   second-factor policy and a local recovery account. Reduce broad setup grants. Follow the
   [security checklist](/docs/run/security-checklist/).
6. **Test mail if needed.** Confirm the public link address, SMTP TLS and credentials, SPF/DKIM,
   a test message and actual receipt: [Sign-in and mail](/docs/run/sign-in-and-mail-setup/).
7. **Check readiness per workspace.** Require `/health` 200 and inspect every active workspace and
   process on **Operations**. Use `/health/live` for liveness so a database outage does not cause
   restart loops.
8. **Set monitoring.** Collect bounded/rotated logs, authenticate private metrics scrapes and alert
   on unavailable workspaces, silent processes, failed workers and growing queues. Verify that a
   reported request ID leads to its log: [Monitoring](/docs/run/monitoring/).
9. **Protect files and capacity.** Persist job files, share them if several instances run, and
   budget connections across all processes. Exercise a representative import/export and check
   disk retention. Use the [database growth checks](/docs/run/database/#watch-database-growth) and
   set external log/metric retention; job retention does not bound all storage. Production CPU, memory, throughput and recovery sizing are **not measured**
   for your workload; collect your own evidence.
10. **Check integrations.** Confirm receiver trust, signature verification, event deduplication,
    retry recovery and re-sync procedures if using [webhooks](/docs/run/webhook-delivery/).
    Review [AI send policy](/docs/run/ai/) separately before enabling AI or agents.
11. **Prove recovery.** Back up the database and source files, restore into a separate database,
    and inspect the recorded rehearsal on Operations. Keep the matching application and private
    configuration: [Back up and restore](/docs/run/backup-and-restore/).
12. **Prepare upgrades and support.** Record the cutover and restore plan, the expected model schema,
    support diagnostics and corresponding source URL for a modified build. See
    [Upgrades](/docs/run/upgrades/) and [Licence and source](/docs/run/licence-and-source/).

A container marked healthy alone is insufficient evidence for these steps. Record what you actually
checked, including any custom proxy or provider behavior that remains unverified.

## Run the checks and keep the results

You need the installed source version, private configuration, Docker access, the public DNS name,
an administrator for access/sign-in tests and an operator for Deployment and Operations. Arrange
an approved maintenance window before recovery or restart trials. This list assumes the reference
Compose installation; repeat the checks through the actual balancer if you use one. The standard
commands below use the base Compose file. Keep both `-f` arguments for automatic HTTPS and the
same alternate environment-file selection, if any.

### 1. Confirm service state and public transport

```bash
docker compose config --quiet
docker compose ps
curl -I http://refiroo.example.org/
curl -I https://refiroo.example.org/
curl -i https://refiroo.example.org/health/live
curl -i https://refiroo.example.org/health
curl -i https://refiroo.example.org/metrics
```

Use your real host. If port 80 is closed, skip the HTTP command; a failed connection there is
expected. Otherwise expect HTTP redirected to the fixed HTTPS origin. Expect valid Compose input,
running services, trusted TLS, health 200 with `{"status":"ok"}`, and **404** for public metrics.
Check container port mappings: only web (or Caddy) publishes. If an engine/database port is public,
correct that exposure before accepting users. Follow [HTTPS](/docs/run/https/#verify-from-the-callers-network)
for the response-header checks. Do not suppress certificate verification.

### 2. Confirm database, configuration and workspaces

Run the [database inspection commands](/docs/run/database/#inspect-the-reference-database).
Record PostgreSQL 17, ICU root collation, all three extensions and the current migration revision.
On Deployment confirm the intended capability groups, durable job path, stable cursor key,
permanent public origin and acceptable limits. No secret should be copied into the checklist.

On Operations inspect every active workspace and every live process. Overall readiness 200 is not
a substitute for this list: each expected workspace must be served. Confirm the expected worker
threads are running, off only for understood reasons, and none are silently failing. Record the
engine version from About and the source version you built.

### 3. Confirm a person can work and recover access

Sign in through the public origin using the recovery administrator. Sign in with the organisation's
provider as a test person if used. Check intended Browse access and refusal outside that person's
grants. Open an application and read a record; the home page should show only workspaces that
person may browse. Verify second-factor setup and the recovery procedure without taking away
the last working administrator. Deactivate the test person when no longer needed.

If mail is required, send a test and check actual receipt, then test a reset link for the test
person. Record sender, TLS mode and result without copying credentials or the link. Check
notifications/digest expectations with their recipient's saved time zone. See
[Sign-in and mail](/docs/run/sign-in-and-mail-setup/) for exact failure recovery.

### 4. Confirm retained files and background work

Run the [worker storage checks](/docs/run/background-jobs/#check-worker-storage-and-restart-one-reference-instance).
Preview a small intended reference-data workbook or use a test workspace through the normal
import workflow, then verify outcomes before committing. Run an export and confirm its download.
After a planned engine restart, check the completed export still downloads and every workspace
is ready. This checks persistence, not load capacity; use a noncritical job if checking takeover.

For webhooks, coordinate one reviewed change and confirm delivery and receiver deduplication.
Record the subscription state, receiver response and retention/re-sync owner. Do not confuse a
manual resend with recovery of the normal position. Review AI separately using its linked pages;
this checklist does not enable or validate it.

### 5. Confirm monitoring and recovery evidence

Check the private authenticated scraper, an actual log correlation reference and log retention.
Use [Monitoring](/docs/run/monitoring/) for metric/field names. Confirm an operator receives alerts
for unavailable workspaces and sustained failed background work. Store bounded diagnostic output;
never leave an unrestricted log-following process running for a checklist.

Run the [consistent backup and separate-database rehearsal](/docs/run/backup-and-restore/).
Record the backup identifier, source/configuration version, recorded **Passed** rehearsal and
file-archive inspection. A database-only rehearsal does not validate file recovery or public sign-in
on a replacement host. Rehearse those too before relying on an end-to-end recovery time.

## Decide whether to open traffic

Keep these local records with the installation, rather than secrets in the guide:

| Evidence | Record |
| --- | --- |
| Deployment | Public origin, application/source version, database revision, model releases, configuration version. |
| Security | Certificate expiry/renewal owner, recovery account custodian, access and provider test results. |
| Operations | Workspace/process readiness, file persistence and relevant integration outcomes, alert recipient. |
| Recovery | Backup identifier, key-version reference, file archive, rehearsal result, measured duration if rehearsed. |
| Capacity | Observed storage/connection use and any workload limits still unmeasured. |

If a check fails, keep writers closed, use the owning page's recovery procedure and repeat only the
failed check plus what its fix affects. A failed backup needs a fresh successful backup/rehearsal;
a proxy correction needs new public TLS and sign-in checks. Do not erase the old evidence or mark
an unexercised path as passed. A production capacity or recovery-time promise requires your own
measurements; neither follows from passing this checklist.
