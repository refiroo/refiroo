---
title: Troubleshooting
description: Find the failing boundary and follow its recovery message without losing data.
reader: operator
---

Start by checking the public address, then liveness and readiness. Use your own host:

```bash
curl --fail https://refiroo.example.org/health/live
curl --fail https://refiroo.example.org/health
docker compose ps
docker compose logs --tail=100 engine
docker compose logs --tail=100 web
```

If liveness answers but readiness does not, investigate the database or model readiness. Restarting
a healthy process repeatedly does not restore its database. With Operations access, open
**Settings › Administration › Operations** for workspace and process detail.

## Requests and startup

| What you see | Meaning and recovery |
| --- | --- |
| A plain `502 Bad Gateway` or `504 Gateway Time-out` page, or a failing request with no engine error body | The engine is down, web cannot reach it, or the engine did not answer within the proxy’s time limit. Check `docker compose ps` and `docker compose logs --tail=100 engine`. Check that web’s `ENGINE_UPSTREAM` names the engine (`http://engine:8000` in the supplied Compose file). After an upgrade, confirm that the engine finished starting; see [startup checks](/docs/run/health-and-startup-checks/). |
| `503 DATABASE_UNAVAILABLE`, `unreachable` | Database connectivity failed. Check server state, network and credentials. Workers retry; service recovers without restarting when the database returns. |
| `503 DATABASE_UNAVAILABLE`, `poolExhausted` | The process waited for its pool. Inspect active work and [pool settings](/docs/run/database/) before increasing connections. Honor `Retry-After`. |
| `503 DATABASE_UNAVAILABLE`, `tooManyConnections` | PostgreSQL reached its connection ceiling. Budget all instances, workers and maintenance clients together. |
| `503 DATABASE_UNAVAILABLE`, `transactionEnded` | PostgreSQL ended an idle transaction. Retry after checking a stalled or frozen process and its timeout. |
| `/health` is 503 | Database unavailable, no workspace can be served, or a selected model failed to load. Read startup diagnostics and workspace readiness. |
| `503 MODEL_REGISTRY_UNAVAILABLE` for one workspace | That workspace's selected release cannot be served. Inspect its schema/validation reason; other workspaces may remain usable. |
| `500 INVALID_INSTALLED_MODEL` | An installed release failed validation during comparison. Record its release identifier and diagnostic, check the matching engine version and escalate. Do not repeatedly retry or edit the stored release JSON. |
| `409 MODEL_RELEASE_CHANGED` | The workspace changed models during a read. Read again. |
| `401 AUTHENTICATION_REQUIRED` or `TOKEN_INVALID` | Obtain a valid token or sign in again. Check expiry, API scope, deactivation and shared `PUBLIC_URL` if repeated across processes. |
| `403 FORBIDDEN` | Authentication succeeded but the caller lacks the named action. Ask a security administrator to check grants in the named workspace. |
| Unknown migration revision or failed migration | Keep traffic closed and follow [Upgrades](/docs/run/upgrades/). Never edit revision rows to suppress the check. |
| After an upgrade or a settings change with automatic HTTPS, the site does not answer; web's log says port 80 or 443 is already allocated, or names missing certificate files | The command ran without `compose.acme.yml`, so web was recreated without Caddy in front. Run `docker compose -f compose.yml -f compose.acme.yml up -d`, or set `COMPOSE_FILE=compose.yml:compose.acme.yml` as in [Install](/docs/run/install-with-compose/#5-start-with-automatic-https) and rerun the command. |
| Named invalid or retired environment setting | Correct that setting, then recreate the container. Use [startup checks](/docs/run/health-and-startup-checks/). |

If a workspace schema is older than supported, use the reviewed raising procedure. If newer, run
the later engine that reads it. If activation committed but a process could not load the release,
restart that process and inspect the model error if it persists.

## Jobs, files, delivery and mail

- **Queued or apparently stuck job:** inspect its state, worker thread and lease owner on Jobs and
  Operations. Check `INTEGRATION_JOBS_ENABLED`, database reachability and file storage. After a
  crash, allow `JOB_LEASE_SECONDS` (default 120) for takeover. A preview awaiting confirmation is
  waiting for a person, not a worker. [Background jobs](/docs/run/background-jobs/) explains resumes.
- **`JOB_OUTPUT_MISSING`:** export output was removed; rerun the export. For `IMPORT_FILE_MISSING`
  or `SOURCE_FILE_MISSING`, upload again and check volume persistence and cross-instance sharing.
- **`413` upload or batch refusal:** inspect the named engine limit and web's `WEB_MAX_BODY`.
  Raise only the needed limits after capacity checks, then recreate the affected container.
- **Failed webhook:** inspect Deliveries, the pending attempt and receiver logs. Check HTTPS,
  certificates, destination address, body limits and ten-second response time. Resume only after
  fixing the suspension cause. Expired events need reset followed by re-sync; see
  [Webhook delivery](/docs/run/webhook-delivery/).
- **Mail test fails:** its message identifies connection, TLS, login or address failure. Check the
  SMTP host, port and certificate trust. A changed host or port requires entering the password
  again in the same save. Check the Mail messages list for retries, and SPF/DKIM or junk filtering
  if SMTP accepted mail that the person did not receive.
- **Provider sign-in fails:** check the exact issuer, callback address, outbound HTTPS and credentials.
  Use a local recovery administrator if the provider is unavailable. Browser setup belongs in
  [Sign-in](/docs/administer/sign-in/).
- **AI or assistant fails:** use the separate diagnosis steps in [Set up AI](/docs/run/set-up-ai/).

## A page cannot load its pinned model

A publication or change set can depend on a release different from the workspace's current one.
An unsupported pinned schema stays blocked; substituting the current release would misinterpret
the data. Use a compatible engine or the reviewed stored-release raising procedure instead of
repeatedly retrying. A release-changed message is different: reload that current view when offered.

A failed request shows an operation-specific message and any available request or correlation
reference. If a proxy returns an HTML error page, the browser does not display that HTML as the
error. Inspect the proxy and the underlying HTTP response separately; preserve the reference for
support. A successful public liveness response alone does not prove the failing API route works.

## Escalate with evidence

Include the application version, failing action and workspace, time, HTTP status and error code,
request ID or correlation ID, and concise log messages. Include migration revisions or process and
job identifiers when relevant. Never include credentials, sealed values, full environment files or
sensitive file contents. Temporarily use `LOG_LEVEL=DEBUG` only when the normal diagnostic is
insufficient, protect its output, and return to the normal level afterwards.

## Work through a failure once

You need the public address, the approximate failure time and the affected workspace, action or
job ID. Operators need Docker log access and Operations access; changes to people, providers,
mail and subscriptions require their own administrative grants. Collect facts before changing
settings, and keep the old configuration for an ordinary reversible adjustment.

1. Probe the public path with `curl -i` rather than only `--fail` when you need the failed body:

   ```bash
   curl -i https://refiroo.example.org/health/live
   curl -i https://refiroo.example.org/health
   docker compose ps
   ```

   No HTTP response means DNS, TLS, network, proxy or process failure. Liveness 200 with readiness
   503 means inspect database/model readiness. Both 200 means follow the specific failed route:
   a single workspace, permission or external receiver can still fail.
2. Read recent bounded logs from the affected service, including the period of failure:

   ```bash
   docker compose logs --since=15m --tail=200 engine
   docker compose logs --since=15m --tail=100 web
   docker compose logs --since=15m --tail=100 database
   ```

   Prefer the normal one-line diagnostic. The [startup message reference](/docs/run/health-and-startup-checks/#recognise-the-startup-diagnostic)
   and [web refusal reference](/docs/run/https/#correct-a-web-startup-refusal) quote messages and
   give recovery. A container health flag alone does not distinguish maintenance mode.
3. If Operations is reachable, inspect the named workspace, process, thread and last report.
   A 403 there is an access problem for your operator account, not proof that the service is down.
   Ask for Operations access instead of changing deployment capability switches.
4. Correct the named cause. For an edited `.env`, run `docker compose up -d engine` (and web if
   its environment changed). For corrected mounted certificate files, restart web. For a
   running database outage restore connectivity and wait for retries; for an initial database
   startup refusal restart the engine after repair. These cases have different recovery paths.
5. Repeat the failing action, check its outcome and verify adjacent readiness/sign-in if the fix
   changed shared configuration. Keep the failure and recovery times in your incident record.
   Repeatedly sending the same failed batch is not verification; inspect the existing job first.

## Investigate a browser that signs in but cannot stay signed in

Check the public issuer in OAuth metadata and the browser's API address on Deployment. The normal
reference installation uses one HTTPS origin. A different host, plain-HTTP hop exposed to the
browser, wrong origins or an untrusted balancer scheme can break the session path. A public-host
change also invalidates passkeys bound to the previous host. Correct the deployment origin and
callbacks, recreate the affected services and start a fresh browser sign-in. Changing the sealing
key is not a session-cookie repair.

If every person is slowed at once, inspect caller addresses in sign-in failures. In proxy mode,
an empty `WEB_TRUSTED_PROXIES` treats the balancer as the caller. Correct the actual trusted range
and restrict web to the balancer. Do not weaken the per-name protections or rotate passwords as a
substitute for fixing that network boundary.

## Prepare a concise support record

Record the actual failure, its scope and the recovery already attempted. For a migration include
the full safe diagnostic, current/target revisions, engine/PostgreSQL versions and exit status.
For a job include ID, state, counts, refusal code and lease/worker evidence. For a receiver include
delivery ID, attempt status, duration and suspension reason without signing keys or sensitive
payloads. For a request include `X-Request-Id` or `correlationId` and a bounded log excerpt.

Use the [log field reference](/docs/run/monitoring/#log-field-reference-and-examples) to connect
those records. Keep full debug traces under controlled access only when the ordinary message
cannot explain the failure. End temporary DEBUG logging by restoring the prior `LOG_LEVEL` and
recreating the engine. Capacity, custom-provider behavior and recovery duration that were not
exercised remain unverified; report them as such instead of saying the whole installation works.


## A certificate expires or disk space runs low

For automatic HTTPS, inspect Caddy's bounded logs with the same overlay files used to start it.
Check DNS and public TCP 443 for issuance and renewal; port 80 may remain closed. Preserve
`caddy-data` and follow [certificate recovery](/docs/run/https/#if-a-certificate-is-not-issued-or-renewed).
An expired public certificate can block callers even when internal health checks still pass.
For file mode, replace the matching certificate/key pair and validate/restart web.

For storage pressure, identify whether PostgreSQL, job files, assistant/session files, Docker logs
or backups occupy the affected filesystem. Use the [database size checks](/docs/run/database/#watch-database-growth)
and [file lifecycle](/docs/run/background-jobs/#keep-and-back-up-the-file-directory) before acting.
Pause new loads and extend capacity rather than deleting database files or active workbooks.
Lowering retention cannot immediately shrink the database or rewrite expiry times already stored
on jobs. Logs and metric archives have their own [retention policy](/docs/run/monitoring/#keep-monitoring-history-and-retire-a-scraper).
