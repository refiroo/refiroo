
- 2026-11-03T16:04:26+01:00 — OPERATIONS — Operations: run/overview.md; run/https.md; run/sign-in-and-mail-setup.md: service identity, signed-in API access and HTTPS. Already there; skipped branding cross-reference and compatibility history. Steering: no file present.

- 2026-11-03T16:04:26+01:00 — A developer instance: run/developer-instance.md — Prepare the dependencies. Expanded 1 fact: settings refresh also comments out retired settings. Steering: no file present.

- 2026-11-03T16:04:26+01:00 — From a phone on the same network: run/developer-instance.md — Browser and documentation addresses. Added 9 facts: certificate names, network addresses, forwarding paths and exclusions, Vite TLS variables, build-time API override, public guide build, instance guide behavior. Steering: no file present.

- 2026-11-03T16:04:26+01:00 — Settings: run/configure.md — See what is running; Apply a change; run/command-line.md. Already there: startup environment, read-only values/defaults/source, redaction, Compose and dev files; skipped catalogue implementation/test instructions. Steering: no file present.

- 2026-11-03T16:04:26+01:00 — Runtime: run/configure.md — Runtime catalogue and Runtime validation. Added 4 facts: exact key encoding, rejected retired key name, reference script choices, browser return origin rules; corrected documentation-reference path from Operations. Steering: no file present.

- 2026-11-03T16:04:26+01:00 — Several processes: run/several-processes.md — What happens at startup and activation; Jobs and process health. Expanded 3 facts: lease heartbeat interval, disabling idle protection, network timeout defaults. Steering: no file present.

- 2026-11-03T16:04:26+01:00 — Database connections: run/database.md — Budget connections before increasing workers. Expanded 2 facts: pool users and background connection failure recovery. Steering: no file present.

- 2026-11-03T16:04:26+01:00 — Capability groups: run/configure.md — Capability and limit behavior; Capability groups catalogue. Already there: all four defaults, absent routes versus job reads, independent change sets, read-only Settings and retired workspaces; skipped decision/history references. Steering: no file present.

- 2026-11-03T16:04:26+01:00 — Batch and job limits: run/configure.md — Batch and job limits catalogue; Limit application details. Added 5 facts: import disk streaming and combined item limits, preview legacy name, model-edit history cost, hourly consumer-event pruning. Steering: no file present.

- 2026-11-03T16:06:10+01:00 — Authentication: run/sign-in-and-mail-setup.md — API authentication; run/command-line.md; administer/clients.md; administer/signing-keys.md. Added 7 facts to operator setup: exact public exceptions, token refusal reasons, permission diagnostics, token scopes, credential grant, bootstrap privileges, monitoring role. Steering: no file present.

- 2026-11-03T16:06:10+01:00 — Changing SECRETS_ENCRYPTION_KEY: run/secrets-and-keys.md — Which key does what; Change the sealing key; If checking or resealing fails. Already there: all sealed kinds, stop-all procedure, both variables, check/all-or-none refusal, backup key pairing, recovery-code loss and recovery. Steering: no file present.

- 2026-11-03T16:06:10+01:00 — Roles and grants: administer/roles-and-grants.md; administer/clients.md; administer/signing-keys.md; administer/people-and-groups.md; administer/audit.md — Security history retention. Added 1 fact: security history has no expiry; skipped superseded upgrade transitions and deferred retention implementation. Steering: no file present.

- 2026-11-03T16:06:10+01:00 — Signing in from the browser: run/sign-in-and-mail-setup.md — Browser sessions and throttling; administer/sign-in.md — Help with the sign-in screen. Added 9 operator facts: PKCE, token memory, cookie attributes, refresh replay, same-site constraint, exact delay/lapse behavior, shared throttle sources, provider-start cap, reset-address fallback; code disagrees with Operations: own password change keeps current session (resets.change_password). Steering: no file present.

- 2026-11-03T16:06:10+01:00 — Signing in with the organisation's provider: administer/sign-in.md — Provider groups and sign-out limits; run/sign-in-and-mail-setup.md — Provider registration details. Added 8 administrator facts and 4 operator facts: named providers, group-claim behavior and limits, sign-out session exception, exact scopes/issuer examples and failure reasons; browser page omits protocol fields and paths. Steering: no file present.

- 2026-11-03T16:06:10+01:00 — A second factor for local accounts: administer/sign-in.md — Second factors and passkeys; guide/administer/help-someone-who-lost-a-device.md; run/secrets-and-keys.md. Expanded 3 facts: single-use app codes, clock tolerance and passkey-only recovery. Steering: no file present.

- 2026-11-03T16:06:10+01:00 — Sending mail: administer/mail.md — Notices and digests; run/sign-in-and-mail-setup.md — Inbox mail and digests. Expanded 2 administrator facts: digest recovery after downtime and no-mail scheduling; added 1 operator fact: mail leases across senders. Steering: no file present.

- 2026-11-03T16:06:10+01:00 — Database: run/database.md — Prepare an external database; run/developer-instance.md — Prepare the dependencies; run/backup-and-restore.md. Already there: PostgreSQL 17 only, ICU und, extension creation, URL, private Homebrew server, Compose image, backup/rehearsal wrappers; SQLite has no migration. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Startup checks and health: run/health-and-startup-checks.md — A process refuses startup or stays unready; A running database goes away; Distinguish the service states. Already there: bootstrap conflicts, all refusals, probes, workspace recovery and deferred workers, retry/log cadence; added 1 fact: unexpected thread failures retain ERROR tracebacks. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Monitoring: run/monitoring.md — Read the Operations page; Metrics reference; run/health-and-startup-checks.md. Already there: heartbeat freshness, row expiry, readiness reasons, thread states, pool/counter reporting, complete metrics/labels/buckets, alerts, scrape authentication; added 1 fact: Prometheus text version. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Logs: run/monitoring.md — Collect logs; Log field reference and examples. Already there: stderr, both formats, fields, access logger, probe level, ID validation and response/correlation reuse, expected failure diagnostics. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Background jobs: run/background-jobs.md — Restart and cancellation; Inspect results before retrying. Already there: capability/model prerequisite, hourly expiry, graceful/crash/outage/cancel behavior and chunk locking; skipped fixture timing as installation performance guarantee. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Exports: run/background-jobs.md — Keep and back up the file directory; Exports and previews. Already there: separate worker, files, snapshot/MVCC cost, restart/cancel, event stream/proxy/HTTP limits and formula safety. Code-versus-document: files.py uses {jobId}.{lease}.partial, not Operations {jobId}.partial; retained correct guide text. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Imports: run/background-jobs.md — Keep and back up the file directory; Exports and previews. Already there: shared batch worker, file lifecycle/refusal, transactional binding/restart, cancellation, XLSX/CSV/JSONL formats, preview rollback/locks/sample/expiry/rebind; skipped historical fixture timing. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Source files and dry runs: run/background-jobs.md — Keep and back up the file directory; Exports and previews. Expanded 2 facts: source size limit and staged cell cleanup/storage cost; skipped measured fixture duration as deployment promise. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Consumer events: run/background-jobs.md — Consumer-event derivation; run/webhook-delivery.md — Retries and suspensions. Added 5 facts: no switch, lock-free derivation, one workspace worker, rollback/replay safety, direct head comparison; retention/outage already there; skipped superseded initial-upgrade note and fixture throughput. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — AI proposals: Excluded by wave scope. Skipped: AI features after 0.16; existing AI pages left untouched. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Agent access: Excluded by wave scope. Skipped: AI/agent features after 0.16; existing sidebar entry left untouched. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Webhook subscriptions: run/webhook-delivery.md; administer/webhooks.md — State and delivery position; Signing keys; Deliveries. Already there: capability/defaults, retention/body/attempt storage, URL/security rules, key rotation and resealing, model/contract/retirement suspensions and reset-first recovery; added 1 browser fact: subscriptions are outside model releases. Steering: no file present.

- 2026-11-03T16:07:09+01:00 — Delivery: run/webhook-delivery.md — Network and receiver requirements; Retries and suspensions; Retain delivery evidence. Added 3 facts: HMAC input, dispatcher concurrency and logging levels; all retries/reasons/filter/DNS/TLS/lease/capability recovery already there; skipped fixture throughput claims. Steering: no file present.

- 2026-11-03T16:08:36+01:00 — Deploying: run/install-with-compose.md; run/https.md; run/overview.md. Already there: ordered installation, three services/volumes/users/paths, origin/keys, all HTTPS modes, trust/proxy rules, private metrics, body limits, backup/startup/admin/provider/mail; skipped internal deployment-test runner instructions. Steering: no file present.

- 2026-11-03T16:08:36+01:00 — Automatic HTTPS for a public installation: run/https.md — Get and renew public certificates automatically. Expanded 10 facts: Caddy 2, named authorities, ACME challenge, overlay configuration, fixed ports, email block, certificate/account persistence, renewal checks, detailed issuance recovery, non-public names. Steering: no file present.

- 2026-11-03T16:08:36+01:00 — Deployment topologies: run/several-processes.md — Share the installation identity; Increase workers in the reference container. Already there: one-process reference, multiple instances/nodes, capability differences and shared cursors/storage; source wording is narrower than its own Several processes section and WEB_CONCURRENCY support; guide distinguishes reference from supported multiprocess operation. Steering: no file present.

- 2026-11-03T16:08:36+01:00 — Model releases and rollback: run/model-releases-and-rollback.md — Roll back model content; Retire and remove releases; Check model selection before maintenance. Already there: bootstrap versus selection, validation/language refusal, lifecycle/concurrency, compatible rollback, retirement/reference rules, pruning flags/lock/transaction/output/draft links. Steering: no file present.

- 2026-11-03T16:08:36+01:00 — Upgrades: run/upgrades.md — Upgrade the Compose installation; Prepare and verify a cutover; Recover a failed cutover. Already there: quiesce, matching configuration/backup/rehearsal, explicit migration/startup, refusal diagnostics, per-migration transaction and restore-only rollback. Steering: no file present.

- 2026-11-03T16:08:36+01:00 — Backup and restore: run/backup-and-restore.md — all procedures. Already there: database/file/config inventory, custom pg_dump excluding process rows, scratch restore/check/cleanup, all checks/counts/results/refusals, recovery/whole-instance semantics and partial-recovery path; skipped historical timing, fixtures and acceptance-test narration. Steering: no file present.

- 2026-11-03T16:10:03+01:00 — Corrected guide/administer/add-a-sign-in-provider.md: used providers must be disabled, not deleted. Placed new explanations beside their existing topics on five pages. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — compose.yml — project, database, engine, web, volumes: run/install-with-compose.md; run/overview.md — Network and storage; run/several-processes.md. Already there: refiroo project identity, all images/services, required substitutions, collation, mounts, healthy dependencies, restart policy/private ports and constructed environment; exact retry timings are on Health and startup checks. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — compose.acme.yml — web, caddy, volumes: run/https.md — automatic HTTPS steps and Preserve certificates and renewal. Already there after Operations reconciliation: Caddy image, proxy mode/removed mounts and ports, fixed ports, Caddyfile mount, private-network trust and caddy-data persistence; skipped agent-specific features. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — caddy/Caddyfile — site and reverse proxy: run/https.md — automatic HTTPS steps and If a certificate is not issued or renewed. Already there after expansion: PUBLIC_URL substitution, email block, web:8080, immediate streaming flush, local authority versus public certificates; ACME details described without claiming which challenge won. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — .env.example — installation, Runtime, Capability groups, Batch and job limits, Webhook subscriptions: run/install-with-compose.md — Read the installation settings file; run/configure.md — Settings catalogue. Already there: all non-AI settings, defaults, secrets/generation and omitted image/Compose-controlled values; source comment wrongly names /docs for reference script, code catalogue says /docs/api; skipped AI proposals block by scope. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/Dockerfile — guide build, runtime, paths, user, environment, volume, probes and command: run/overview.md — Network and storage; run/health-and-startup-checks.md; run/several-processes.md. Already there: Python 3.14, Node 22 guide build, UID 10001/non-root, all non-AI paths, persistent job files, liveness timings, Uvicorn proxy/grace settings; source comment says no Node but runtime installs nodejs; skipped assistant-specific image setup by scope. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — frontend/Dockerfile — build and web runtime: run/overview.md — Network and storage; run/https.md; run/health-and-startup-checks.md. Already there: Node 22, nginx-unprivileged 1.28, same-origin build, dist/cert/config paths, nginx user, 8080/8443 and web defaults/probe; skipped build-copy implementation details. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — frontend/nginx/05-choose-mode.sh — mode selection and trusted proxies: run/https.md — Put an HTTPS load balancer in front; Correct a web startup refusal. Already there: files/proxy modes, certificate readability, PUBLIC_URL requirement, comma-separated IP/CIDR validation and exact messages; header trust default/recursive forwarding explained. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — frontend/nginx/tls.conf.template — TLS and redirect listeners: run/https.md — Certificate protocols and browser caching. Added 1 fact: TLS versions; redirect/ports/certificates/body limit already there. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — frontend/nginx/proxy.conf.template — private HTTP listener and forwarded scheme: run/https.md — Put an HTTPS load balancer in front. Already there: HTTP 8080, /web-health, X-Forwarded-Proto and trusted caller-address behavior, gzip/body limit; skipped internal nginx map/include structure. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — frontend/nginx/snippets/locations.inc.template — forwarding, streams, metrics, assets and fallback: run/https.md — Ports and uploads; Verify from the caller network; Certificate protocols and browser caching. Added 2 facts: immutable hashed-asset caching and uncached application shell; forwarding/private metrics/one-hour unbuffered streaming already there. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — frontend/nginx/snippets/headers.inc.template — response headers: run/https.md — Verify from the caller network. Already there: HSTS max-age 31536000, nosniff, same-origin referrer policy and both frame restrictions. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/config.py — constants and Settings: run/configure.md — all non-AI catalogues; Path defaults and container overrides. Already there: defaults/types/ranges/paths, URL validation, truthy parsing, cursor key and runtime sources. Code disagrees with Operations VITE_API_URL default: browser uses same origin; model default is backend-relative; guide already follows code. Skipped AI settings. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/config.py — from_env, prepare_job_file_dir, validate_secrets and validators: run/configure.md — Apply a change; Runtime validation; run/health-and-startup-checks.md — diagnostics. Already there: startup-only parsing, positive/zero limits, invalid-choice refusal, writable-directory probe and sealing-key requirement; skipped private helper mechanics. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/config.py — catalogue, describe_settings, without_password, cache/accessors: run/configure.md — See what is running; Runtime catalogue. Already there: source/default/value reporting, secret set-state only, password redaction; skipped implementation-only dataclasses, cache and accessors. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/create_admin.py — arguments, password and result: run/command-line.md — module table; Command examples and output; Respond to a refusal. Already there: all options, prompts/stdin, role scope/recovery flag, exact output and 0/1/2 exits. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/create_client.py — arguments, roles and credentials: run/command-line.md — module table; Command examples and output; Respond to a refusal. Already there: name, repeated role, one-time output and camel-case --json fields, default no rights and exits. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/generate_key.py — generation: run/command-line.md; run/secrets-and-keys.md. Already there: 32-byte URL-safe base64, random per call, no database access and exit 0. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/database_upgrade.py — database preparation and output: run/upgrades.md — Upgrade the Compose installation; Recover a failed cutover. Corrected 1 fact in three occurrences: upgrade migration run is one PostgreSQL transaction (migrations/env.py), not independently committed earlier revisions; exact command/output/exits already there. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/model_release_prune.py — eligibility, lock, flags and report: run/model-releases-and-rollback.md — Retire and remove releases; run/command-line.md. Already there: all references, retired/unused selection, dry-run, installation lock/transaction, retained drafts and 0/1 exits. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/model_release_raise.py — offline raising, plan, outcomes and report: run/upgrades.md — Stored models outside the language window; run/command-line.md. Already there: identity preservation, offline lock, old/inside/later windows, invalid/duplicate skips, dry-run and partial eligible success/exit behavior. Potential defect: per-release CLI report uses database release.id instead of public_id; reported, no code edited. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/reseal_secrets.py — key validation, check, transaction and report: run/secrets-and-keys.md — complete procedure and refusal table; run/command-line.md. Already there: both environment keys, equality/refusal, every sealed value or none, check-only, counts, recovery-code warning, output and exits. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/restore_check.py — target validation, rehearsal and report: run/backup-and-restore.md — Rehearse in a separate database; Rehearse the reference dump inside Compose; run/command-line.md. Already there: separate target, live reporting, preparation, counts/reasons, no HTTP operation and exit behavior. Potential defect: invalid/unsupported --restored URL refusal interpolates raw URL, potentially logging its password; reported without executing credential-bearing inputs. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/settings_template.py — target defaults, render, update and report: run/command-line.md — Print or update a settings template; run/developer-instance.md — Prepare the dependencies. Already there: --for choices, --update existing path, preserve existing/commented names, append defaults, retire setting lines and reports; skipped generator internals and excluded AI defaults. Steering: no file present.

- 2026-11-03T16:11:23+01:00 — backend/app/cli/__init__.py: No reader-facing behavior. Skipped: package marker only. Steering: no file present.

- 2026-11-03T16:12:53+01:00 — Editorial review finished across the 16 changed pages. The isolated build passed (225 pages), and terms/brand checks passed; link verification reports 225 shared header home-link errors plus an unrelated missing /docs/integrate/ link on model/workbook-onboarding. Those sources are outside this wave. Steering: no file present.

- 2026-11-03T16:14:13+01:00 — Finished guide/_waves/reconcile/R-OPS.md with 60 source/correction rows, per-page counts (62 added, 2 corrected, 23 expanded), source disagreements and static product observations. Final isolated build passed for 225 pages; terms/brand passed; verification links remain blocked by 225 shared header links and one unrelated model-page link. No new screenshots requested, no live operational procedures exercised. Steering: no file present.
