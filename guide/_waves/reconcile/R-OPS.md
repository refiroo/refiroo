# R-OPS reconciliation

Counts describe discrete facts added, corrected or expanded during this wave; already-covered facts are listed by topic. Source headings are processed in order. Screenshots already referenced by pages are retained; no new screen is requested at this stage.

| Source heading | Facts checked and destination | Result |
| --- | --- | --- |
| OPERATIONS — Operations | run/overview.md; run/https.md; run/sign-in-and-mail-setup.md: service identity, signed-in API access and HTTPS | Already there; skipped branding cross-reference and compatibility history |
| A developer instance | run/developer-instance.md — Prepare the dependencies | Expanded 1 fact: settings refresh also comments out retired settings |
| From a phone on the same network | run/developer-instance.md — Browser and documentation addresses | Added 9 facts: certificate names, network addresses, forwarding paths and exclusions, Vite TLS variables, build-time API override, public guide build, instance guide behavior |
| Settings | run/configure.md — See what is running; Apply a change; run/command-line.md | Already there: startup environment, read-only values/defaults/source, redaction, Compose and dev files; skipped catalogue implementation/test instructions |
| Runtime | run/configure.md — Runtime catalogue and Runtime validation | Added 4 facts: exact key encoding, rejected retired key name, reference script choices, browser return origin rules; recorded source discrepancy: documentation-reference path in Operations should be /docs/api |
| Several processes | run/several-processes.md — What happens at startup and activation; Jobs and process health | Expanded 3 facts: lease heartbeat interval, disabling idle protection, network timeout defaults |
| Database connections | run/database.md — Budget connections before increasing workers | Expanded 2 facts: pool users and background connection failure recovery |
| Capability groups | run/configure.md — Capability and limit behavior; Capability groups catalogue | Already there: all four defaults, absent routes versus job reads, independent change sets, read-only Settings and retired workspaces; skipped decision/history references |
| Batch and job limits | run/configure.md — Batch and job limits catalogue; Limit application details | Added 5 facts: import disk streaming and combined item limits, preview legacy name, model-edit history cost, hourly consumer-event pruning |
| Authentication | run/sign-in-and-mail-setup.md — API authentication; run/command-line.md; administer/clients.md; administer/signing-keys.md | Added 7 facts to operator setup: exact public exceptions, token refusal reasons, permission diagnostics, token scopes, credential grant, bootstrap privileges, monitoring role |
| Changing SECRETS_ENCRYPTION_KEY | run/secrets-and-keys.md — Which key does what; Change the sealing key; If checking or resealing fails | Already there: all sealed kinds, stop-all procedure, both variables, check/all-or-none refusal, backup key pairing, recovery-code loss and recovery |
| Roles and grants | administer/roles-and-grants.md; administer/clients.md; administer/signing-keys.md; administer/people-and-groups.md; administer/audit.md — Security history retention | Added 1 fact: security history has no expiry; skipped superseded upgrade transitions and deferred retention implementation |
| Signing in from the browser | run/sign-in-and-mail-setup.md — Browser sessions and throttling; administer/sign-in.md — Help with the sign-in screen | Added 9 operator facts: PKCE, token memory, cookie attributes, refresh replay, same-site constraint, exact delay/lapse behavior, shared throttle sources, provider-start cap, reset-address fallback; code disagrees with Operations: own password change keeps current session (resets.change_password) |
| Signing in with the organisation's provider | administer/sign-in.md — Provider groups and sign-out limits; run/sign-in-and-mail-setup.md — Provider registration details | Added 8 administrator facts and 4 operator facts: named providers, group-claim behavior and limits, sign-out session exception, exact scopes/issuer examples and failure reasons; browser page omits protocol fields and paths |
| A second factor for local accounts | administer/sign-in.md — Second factors and passkeys; guide/administer/help-someone-who-lost-a-device.md; run/secrets-and-keys.md | Expanded 3 facts: single-use app codes, clock tolerance and passkey-only recovery |
| Sending mail | administer/mail.md — Notices and digests; run/sign-in-and-mail-setup.md — Inbox mail and digests | Expanded 2 administrator facts: digest recovery after downtime and no-mail scheduling; added 1 operator fact: mail leases across senders |
| Database | run/database.md — Prepare an external database; run/developer-instance.md — Prepare the dependencies; run/backup-and-restore.md | Already there: PostgreSQL 17 only, ICU und, extension creation, URL, private Homebrew server, Compose image, backup/rehearsal wrappers; SQLite has no migration |
| Startup checks and health | run/health-and-startup-checks.md — A process refuses startup or stays unready; A running database goes away; Distinguish the service states | Already there: bootstrap conflicts, all refusals, probes, workspace recovery and deferred workers, retry/log cadence; added 1 fact: unexpected thread failures retain ERROR tracebacks |
| Monitoring | run/monitoring.md — Read the Operations page; Metrics reference; run/health-and-startup-checks.md | Already there: heartbeat freshness, row expiry, readiness reasons, thread states, pool/counter reporting, complete metrics/labels/buckets, alerts, scrape authentication; added 1 fact: Prometheus text version |
| Logs | run/monitoring.md — Collect logs; Log field reference and examples | Already there: stderr, both formats, fields, access logger, probe level, ID validation and response/correlation reuse, expected failure diagnostics |
| Background jobs | run/background-jobs.md — Restart and cancellation; Inspect results before retrying | Already there: capability/model prerequisite, hourly expiry, graceful/crash/outage/cancel behavior and chunk locking; skipped fixture timing as installation performance guarantee |
| Exports | run/background-jobs.md — Keep and back up the file directory; Exports and previews | Already there: separate worker, files, snapshot/MVCC cost, restart/cancel, event stream/proxy/HTTP limits and formula safety. Code-versus-document: files.py uses {jobId}.{lease}.partial, not Operations {jobId}.partial; retained correct guide text |
| Imports | run/background-jobs.md — Keep and back up the file directory; Exports and previews | Already there: shared batch worker, file lifecycle/refusal, transactional binding/restart, cancellation, XLSX/CSV/JSONL formats, preview rollback/locks/sample/expiry/rebind; skipped historical fixture timing |
| Source files and dry runs | run/background-jobs.md — Keep and back up the file directory; Exports and previews | Expanded 2 facts: source size limit and staged cell cleanup/storage cost; skipped measured fixture duration as deployment promise |
| Consumer events | run/background-jobs.md — Consumer-event derivation; run/webhook-delivery.md — Retries and suspensions | Added 5 facts: no switch, lock-free derivation, one workspace worker, rollback/replay safety, direct head comparison; retention/outage already there; skipped superseded initial-upgrade note and fixture throughput |
| AI proposals | Excluded by wave scope | Skipped: AI features after 0.16; existing AI pages left untouched |
| Agent access | Excluded by wave scope | Skipped: AI/agent features after 0.16; existing sidebar entry left untouched |
| Webhook subscriptions | run/webhook-delivery.md; administer/webhooks.md — State and delivery position; Signing keys; Deliveries | Already there: capability/defaults, retention/body/attempt storage, URL/security rules, key rotation and resealing, model/contract/retirement suspensions and reset-first recovery; added 1 browser fact: subscriptions are outside model releases |
| Delivery | run/webhook-delivery.md — Network and receiver requirements; Retries and suspensions; Retain delivery evidence | Added 3 facts: HMAC input, dispatcher concurrency and logging levels; all retries/reasons/filter/DNS/TLS/lease/capability recovery already there; skipped fixture throughput claims |
| Deploying | run/install-with-compose.md; run/https.md; run/overview.md | Already there: ordered installation, three services/volumes/users/paths, origin/keys, all HTTPS modes, trust/proxy rules, private metrics, body limits, backup/startup/admin/provider/mail; skipped internal deployment-test runner instructions |
| Automatic HTTPS for a public installation | run/https.md — Get and renew public certificates automatically | Expanded 10 facts: Caddy 2, named authorities, ACME challenge, overlay configuration, fixed ports, email block, certificate/account persistence, renewal checks, detailed issuance recovery, non-public names |
| Deployment topologies | run/several-processes.md — Share the installation identity; Increase workers in the reference container | Already there: one-process reference, multiple instances/nodes, capability differences and shared cursors/storage; source wording is narrower than its own Several processes section and WEB_CONCURRENCY support; guide distinguishes reference from supported multiprocess operation |
| Model releases and rollback | run/model-releases-and-rollback.md — Roll back model content; Retire and remove releases; Check model selection before maintenance | Already there: bootstrap versus selection, validation/language refusal, lifecycle/concurrency, compatible rollback, retirement/reference rules, pruning flags/lock/transaction/output/draft links |
| Upgrades | run/upgrades.md — Upgrade the Compose installation; Prepare and verify a cutover; Recover a failed cutover | Already there: quiesce, matching configuration/backup/rehearsal, explicit migration/startup, refusal diagnostics, per-migration transaction and restore-only rollback |
| Backup and restore | run/backup-and-restore.md — all procedures | Already there: database/file/config inventory, custom pg_dump excluding process rows, scratch restore/check/cleanup, all checks/counts/results/refusals, recovery/whole-instance semantics and partial-recovery path; skipped historical timing, fixtures and acceptance-test narration |
| Provider maintenance follow-through | guide/administer/add-a-sign-in-provider.md — Maintain the provider | Corrected 1 fact: a provider with identities is disabled rather than deleted, as providers.delete_provider enforces; relocated additions beneath their relevant existing headings |
| compose.yml — project, database, engine, web, volumes | run/install-with-compose.md; run/overview.md — Network and storage; run/several-processes.md | Already there: refiroo project identity, all images/services, required substitutions, collation, mounts, healthy dependencies, restart policy/private ports and constructed environment; exact retry timings are on Health and startup checks |
| compose.acme.yml — web, caddy, volumes | run/https.md — automatic HTTPS steps and Preserve certificates and renewal | Already there after Operations reconciliation: Caddy image, proxy mode/removed mounts and ports, fixed ports, Caddyfile mount, private-network trust and caddy-data persistence; skipped agent-specific features |
| caddy/Caddyfile — site and reverse proxy | run/https.md — automatic HTTPS steps and If a certificate is not issued or renewed | Already there after expansion: PUBLIC_URL substitution, email block, web:8080, immediate streaming flush, local authority versus public certificates; ACME details described without claiming which challenge won |
| .env.example — installation, Runtime, Capability groups, Batch and job limits, Webhook subscriptions | run/install-with-compose.md — Read the installation settings file; run/configure.md — Settings catalogue | Already there: all non-AI settings, defaults, secrets/generation and omitted image/Compose-controlled values; source comment wrongly names /docs for reference script, code catalogue says /docs/api; skipped AI proposals block by scope |
| backend/Dockerfile — guide build, runtime, paths, user, environment, volume, probes and command | run/overview.md — Network and storage; run/health-and-startup-checks.md; run/several-processes.md | Already there: Python 3.14, Node 22 guide build, UID 10001/non-root, all non-AI paths, persistent job files, liveness timings, Uvicorn proxy/grace settings; source comment says no Node but runtime installs nodejs; skipped assistant-specific image setup by scope |
| frontend/Dockerfile — build and web runtime | run/overview.md — Network and storage; run/https.md; run/health-and-startup-checks.md | Already there: Node 22, nginx-unprivileged 1.28, same-origin build, dist/cert/config paths, nginx user, 8080/8443 and web defaults/probe; skipped build-copy implementation details |
| frontend/nginx/05-choose-mode.sh — mode selection and trusted proxies | run/https.md — Put an HTTPS load balancer in front; Correct a web startup refusal | Already there: files/proxy modes, certificate readability, PUBLIC_URL requirement, comma-separated IP/CIDR validation and exact messages; header trust default/recursive forwarding explained |
| frontend/nginx/tls.conf.template — TLS and redirect listeners | run/https.md — Certificate protocols and browser caching | Added 1 fact: TLS versions; redirect/ports/certificates/body limit already there |
| frontend/nginx/proxy.conf.template — private HTTP listener and forwarded scheme | run/https.md — Put an HTTPS load balancer in front | Already there: HTTP 8080, /web-health, X-Forwarded-Proto and trusted caller-address behavior, gzip/body limit; skipped internal nginx map/include structure |
| frontend/nginx/snippets/locations.inc.template — forwarding, streams, metrics, assets and fallback | run/https.md — Ports and uploads; Verify from the caller network; Certificate protocols and browser caching | Added 2 facts: immutable hashed-asset caching and uncached application shell; forwarding/private metrics/one-hour unbuffered streaming already there |
| frontend/nginx/snippets/headers.inc.template — response headers | run/https.md — Verify from the caller network | Already there: HSTS max-age 31536000, nosniff, same-origin referrer policy and both frame restrictions |
| backend/app/config.py — constants and Settings | run/configure.md — all non-AI catalogues; Path defaults and container overrides | Already there: defaults/types/ranges/paths, URL validation, truthy parsing, cursor key and runtime sources. Code disagrees with Operations VITE_API_URL default: browser uses same origin; model default is backend-relative; guide already follows code. Skipped AI settings |
| backend/app/config.py — from_env, prepare_job_file_dir, validate_secrets and validators | run/configure.md — Apply a change; Runtime validation; run/health-and-startup-checks.md — diagnostics | Already there: startup-only parsing, positive/zero limits, invalid-choice refusal, writable-directory probe and sealing-key requirement; skipped private helper mechanics |
| backend/app/config.py — catalogue, describe_settings, without_password, cache/accessors | run/configure.md — See what is running; Runtime catalogue | Already there: source/default/value reporting, secret set-state only, password redaction; skipped implementation-only dataclasses, cache and accessors |
| backend/app/cli/create_admin.py — arguments, password and result | run/command-line.md — module table; Command examples and output; Respond to a refusal | Already there: all options, prompts/stdin, role scope/recovery flag, exact output and 0/1/2 exits |
| backend/app/cli/create_client.py — arguments, roles and credentials | run/command-line.md — module table; Command examples and output; Respond to a refusal | Already there: name, repeated role, one-time output and camel-case --json fields, default no rights and exits |
| backend/app/cli/generate_key.py — generation | run/command-line.md; run/secrets-and-keys.md | Already there: 32-byte URL-safe base64, random per call, no database access and exit 0 |
| backend/app/cli/database_upgrade.py — database preparation and output | run/upgrades.md — Upgrade the Compose installation; Recover a failed cutover | Corrected 1 fact in three occurrences: upgrade migration run is one PostgreSQL transaction (migrations/env.py), not independently committed earlier revisions; exact command/output/exits already there |
| backend/app/cli/model_release_prune.py — eligibility, lock, flags and report | run/model-releases-and-rollback.md — Retire and remove releases; run/command-line.md | Already there: all references, retired/unused selection, dry-run, installation lock/transaction, retained drafts and 0/1 exits |
| backend/app/cli/model_release_raise.py — offline raising, plan, outcomes and report | run/upgrades.md — Stored models outside the language window; run/command-line.md | Already there: identity preservation, offline lock, old/inside/later windows, invalid/duplicate skips, dry-run and partial eligible success/exit behavior. Potential defect: per-release CLI report uses database release.id instead of public_id; reported, no code edited |
| backend/app/cli/reseal_secrets.py — key validation, check, transaction and report | run/secrets-and-keys.md — complete procedure and refusal table; run/command-line.md | Already there: both environment keys, equality/refusal, every sealed value or none, check-only, counts, recovery-code warning, output and exits |
| backend/app/cli/restore_check.py — target validation, rehearsal and report | run/backup-and-restore.md — Rehearse in a separate database; Rehearse the reference dump inside Compose; run/command-line.md | Already there: separate target, live reporting, preparation, counts/reasons, no HTTP operation and exit behavior. Potential defect: invalid/unsupported --restored URL refusal interpolates raw URL, potentially logging its password; reported without executing credential-bearing inputs |
| backend/app/cli/settings_template.py — target defaults, render, update and report | run/command-line.md — Print or update a settings template; run/developer-instance.md — Prepare the dependencies | Already there: --for choices, --update existing path, preserve existing/commented names, append defaults, retire setting lines and reports; skipped generator internals and excluded AI defaults |
| backend/app/cli/__init__.py | No reader-facing behavior | Skipped: package marker only |

## Per-page counts

Counts are the factual points identified in the rows above, counted once per changed page. Repeated corrections of the same rule count once. Already-covered facts and editorial relocation are excluded. Paths below are relative to `guide/src/content/docs/`.

| Page | Added | Corrected | Expanded |
| --- | ---: | ---: | ---: |
| run/developer-instance.md | 9 | 0 | 1 |
| run/configure.md | 9 | 0 | 0 |
| run/several-processes.md | 0 | 0 | 3 |
| run/database.md | 0 | 0 | 2 |
| run/sign-in-and-mail-setup.md | 21 | 0 | 0 |
| administer/audit.md | 1 | 0 | 0 |
| administer/sign-in.md | 8 | 0 | 3 |
| administer/mail.md | 0 | 0 | 2 |
| run/health-and-startup-checks.md | 1 | 0 | 0 |
| run/monitoring.md | 1 | 0 | 0 |
| run/background-jobs.md | 5 | 0 | 2 |
| administer/webhooks.md | 1 | 0 | 0 |
| run/webhook-delivery.md | 3 | 0 | 0 |
| run/https.md | 3 | 0 | 10 |
| run/upgrades.md | 0 | 1 | 0 |
| guide/administer/add-a-sign-in-provider.md | 0 | 1 | 0 |
| **Total** | **62** | **2** | **23** |

No new page or sidebar entry was needed. All 35 Operations headings have a row; AI proposals and Agent access are explicitly skipped as instructed. The remaining 25 rows cover the listed deployment/configuration/CLI sources and the provider-guide correction. No in-scope source heading remains open. Shared coverage and screenshot-request files were not edited because they are outside the explicit allowlist.

## Code versus document disagreements

- Operations' browser-session summary says a password change ends sessions. `engine/identity/resets.py:change_password` keeps the current browser session and ends the others. Existing administrator text was correct; the operator explanation now follows it.
- Operations calls an export partial file `{jobId}.partial`; `engine/jobs/files.py` and `exports.py` use `{jobId}.{lease}.partial`. The existing guide was correct and is retained.
- Operations lists a frontend API default of localhost:8000. `frontend/src/api/address.ts` uses the page origin in a browser unless a build-time override is present. The guide follows the code.
- Operations and the .env example comment call `/docs` the API-reference location in some places. The code and current deployment serve the guide there and the API reference at `/docs/api`. The guide distinguishes them.
- Operations abbreviates the bootstrap path as `model/rdm-starter.json`. `config.py` resolves the implicit path beneath the backend package root; the image overrides it to the repository-shaped model path. Existing guide detail correctly distinguishes these.
- Operations' topology paragraph calls one process the supported topology, while its Several processes section and `WEB_CONCURRENCY` support multiple workers/instances. The guide describes one process as the reference default and explains shared-database operation separately.
- The backend Dockerfile's guide-stage comment says the engine contains no Node. Its runtime stage installs `nodejs`. The guide does not repeat the stale comment; assistant-specific setup remains excluded.
- Operations describes migration transactions per migration; `migrations/env.py` wraps `context.run_migrations()` in one transaction without per-migration transactions or explicit autocommit blocks. Corrected the guide's stronger and incorrect claim that earlier revisions could remain committed after a failed run.
- The existing provider guide implied deletion was always an option. `engine/identity/providers.py:delete_provider` refuses a provider with identities; the task now tells the administrator to disable a used provider.

## Things that looked wrong in refiroo

These are static code observations; no product code was changed and no credential-bearing inputs were executed.

- `backend/app/cli/restore_check.py:_restored` includes the raw rejected URL in malformed/unsupported-target diagnostics. If that URL includes a password, the refusal can expose it to terminal or collected stderr logs.
- `backend/app/cli/model_release_raise.py:main` prints the internal numeric `release.id` in per-release output, unlike pruning's public ID. This makes the maintenance tools inconsistent and gives operators an identifier the public API does not use.
- Guide link verification rejects the shared header's `/` link on every built page, although the application lives there. Its other failure is `/docs/integrate/` from `model/workbook-onboarding`, which has no target. Header, checker and model page are outside this wave's edit scope.

## Verification and limits

- `GUIDE_OUT=_build/R-OPS npm run build`: passed, 225 pages.
- Final `GUIDE_OUT=_build/R-OPS npm run verify`: its build passed; terms and brand passed; links failed with 226 findings (225 shared header `/` links and one unrelated model-page link). No additional link or image failure was reported for this wave.
- `git diff --check` scoped to the owned content: passed.
- Build and verification logs are under `_coverage/notes/R-OPS/`; no working notes were written elsewhere.
- No new screenshot placeholder was added; existing screen references were retained. No new screenshot is requested for these additions. Screens were not recaptured or inspected in a running instance.
- Commands and procedures were checked against repository sources. No Docker deployment, public ACME issuance/renewal, provider/SMTP service, database migration, restore or webhook receiver was exercised. Authority behavior and provider-specific configuration were not tested live.
- No application source, unrelated page, shared guide configuration or sidebar was edited. No commits or Git state changes were made.
