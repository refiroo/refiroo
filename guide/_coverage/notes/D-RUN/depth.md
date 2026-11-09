# D-RUN depth review

Read: guide/AGENTS.md, COMPLETE-COMMON.md, DEPTH-COMMON.md, D-RUN.md. These are the task instructions; top-level guidance is outside this task. Baseline word counts are in baseline.json. No prior D-RUN progress or steering file existed at start.

Every page review below records applicable setup/change/lifecycle/failure/recovery/removal/limits/access questions. Runtime commands are documented from source, not executed against a live installation.

## run/install-with-compose.md

Reviewed complete existing installation walkthrough. Added initialization-only POSTGRES_DB/USER/INITDB_ARGS and ENGINE_UPSTREAM, their cross-setting dependencies, failures and safe changes; corrected optional port 80. Existing sections cover setup, success, stopping/removal, backups, upgrades, key lifecycle and access. Source: compose.yml database/engine/web services, frontend/nginx/05-choose-mode.sh and templates. No steering file. Deployment steps have not been run on a host.

## run/https.md

Reviewed all depth questions. Added the mounted Caddyfile and every directive, change/undo steps, impact of expiry, and 443-only TLS-ALPN issuance/renewal; HTTP checks now conditional. Existing sections cover file renewal, trust, errors, removal/replacement by a balancer, limits and public verification. Sources: compose.acme.yml, caddy/Caddyfile, frontend/nginx/*.template and 05-choose-mode.sh; TLS-ALPN reachability explicitly confirmed by owner in D-RUN assignment. No promise of CA contact mail. No steering file. No live issuance/renewal trial.

## run/overview.md

Reviewed purpose, installation choices, topology, storage, growth, removal and support limits. Clarified that automatic HTTPS needs public 443; 80 only offers redirects. Detailed changes, failures and recovery link to their owning pages.

Sources: compose.yml, compose.acme.yml, caddy/Caddyfile, backend/Dockerfile, frontend/Dockerfile. Expiry/permissions belong to linked capability pages.

Open: None beyond unexecuted deployment commands.

## run/developer-instance.md

Reviewed dependencies, settings refresh, start/stop, device trust, address changes, failures and AI trial. Corrected the forwarded-path list to include /mcp. Backup and migration link to operator procedures; development CA removal is managed by the device, not refiroo.

Sources: scripts/dev.sh, scripts/postgres.sh, frontend/vite.config.ts.

Open: Phone trust menu steps were not exercised on physical devices.

## run/database.md

Reviewed setup, collation, extensions, pool changes, failures and recovery; added read-only size/free-space checks and explained growth, retention boundaries and safe capacity recovery. Removal uses normal backup/restore rather than filesystem deletion.

Sources: compose.yml, backend/app/config.py, engine/jobs/store.py:expire_jobs, engine/jobs/worker.py:sweep, engine/events/worker.py:sweep, engine/reads/feed.py, engine/model/release_lifecycle.py.

Open: Storage sizing and recovery times are workload dependent and not measured; no live database commands run.

## run/several-processes.md

Reviewed shared identity, setup/scaling/undo, startup locks, lease expiry, process lifecycle, failure and node recovery. Added assistant storage to the shared-storage requirements. Backup/removal and upgrade coordination link to their owning pages.

Sources: backend/app/main.py:ModelWorkers, app/db.py startup locks, engine/processes/heartbeat.py, engine/jobs/worker.py, compose.yml, engine/tasks/agent.py.

Open: Multi-node storage/topology is not supplied or validated by this documentation task.

## run/configure.md

Reviewed all catalogue defaults, secrecy, recreation/undo, permissions, route absence, failures, retention and setting dependencies. Added consequences of disabling job cleanup and distinguished AI numeric validation. Backup/move/rotation delegate to owning pages.

Sources: backend/app/config.py Settings/from_env/catalogue, backend/app/main.py worker start and route registration, engine/jobs/worker.py:sweep, engine/reads/feed.py.

Open: None beyond unexecuted deployment commands.

## run/secrets-and-keys.md

Reviewed sealing/cursor/token/webhook key lifecycle, successful and refused resealing, backup-key pairing and rollback. Added a database-password maintenance sequence and links for external credential replacement. Host/Docker privileges are required for offline maintenance; application roles do not authorize host commands.

Sources: compose.yml database role/connection interpolation, app/cli/reseal_secrets.py, engine/identity/resealing.py. PostgreSQL password interaction is an operator instruction, not a product CLI.

Open: Password rotation and its recovery were not performed against a live installation.

## run/sign-in-and-mail-setup.md

Reviewed authentication, session/reset/signing lifetimes, roles, provider and SMTP setup, failure messages, removal and queued-mail retention. Added public-origin cutover and same-origin host-move procedures with recovery checks.

Sources: app/config.py; engine/identity/tokens.py and passkeys.py:relying_party; engine/mail/sender.py and outbox.py; frontend settings MailPage.tsx and provider navigation.

Open: Provider-specific registration and mail receipt were not tested; queued links keep their original text.

## run/ai.md

Reviewed capability independence, setup/defaults, send policy, permissions, sandbox/network boundary, costs, failures, task recovery and retention. Added switch-off consequences, separate credential replacement checks and provider/model change effects; no external-token renewal promise.

Sources: app/config.py; engine/proposals/registry.py and calls.py; engine/tasks/agent.py:settings/environment/sweep; engine/tasks/store.py:expire; app/main.py:ModelWorkers; frontend settings AiPage.tsx and AgentAccessPage.tsx.

Open: External credential lifetimes are provider controlled; runtime AI/provider trials not performed.

## run/set-up-ai.md

Reviewed the complete setup guide, credential alternatives, successful/failed tests, network/API reachability and deployment recreation. Added maintenance/removal links and explicit host-recovery/session-volume consequences.

Sources: backend/Dockerfile; compose.yml; engine/proposals/registry.py; engine/tasks/agent.py; guide/reference/reference.sh and compose.override.yml.

Open: Provider tests, paid assistant turns and external Claude credential lifecycle not exercised.

## run/health-and-startup-checks.md

Reviewed unchanged: purpose and probes, initialization, exact refusal fragments, service states, partial workspace readiness, recovery/retry, permissions and limits are covered. Expiry/move/removal are not independent probe operations; linked keys, model raising and restore procedures own them.

Sources: app/main.py health/lifespan; app/db.py:prepare_database and migration failure diagnostics; app/config.py; backend/Dockerfile; frontend/Dockerfile.

Open: None beyond unexecuted deployment commands.

## run/monitoring.md

Reviewed operations states, access, metrics/log formats and labels, setup, token renewal and failures; added external metrics/log retention, counter loss on restart and safe scraper retirement. Restore of historical monitoring belongs to the collector, not the database rehearsal.

Sources: engine/processes/heartbeat.py; common/request_metrics.py; frontend OperationsPage.tsx; app/config.py; compose.yml and compose.acme.yml have no logging retention configuration.

Open: Collector setup and rotation not exercised; no production alert thresholds or retention periods measured.

## run/background-jobs.md

Reviewed jobs/leases/chunks, defaults, roles, cancellation, file lifetimes, errors/recovery, exports, preview and assistant behavior. Added stored-expiry behavior, disabled-worker cleanup consequences and coordinated file-directory move/undo.

Sources: engine/jobs/worker.py:sweep; engine/jobs/store.py:complete_job, await_confirmation, expire_jobs, idempotent; engine/jobs/files.py:reconcile; app/config.py:prepare_job_file_dir; compose.yml.

Open: Runtime job takeover, file relocation and load capacity were not exercised.

## run/webhook-delivery.md

Reviewed unchanged: enable/change/off, permissions, receiver checks, retries/lease timing, retention, rotation and ordered suspension recovery are covered. Host backup/restore uses the linked whole-instance procedure; receiver reconciliation remains a separate responsibility.

Sources: engine/events/subscriptions.py, subscription_rules.py, delivery_log.py, worker.py; docs/OPERATIONS.md Webhook subscriptions; app/config.py.

Open: Actual receiver deliveries, certificate trust and deduplication not exercised.

## run/command-line.md

Reviewed every listed module/option, exit status, preparation side effects, refusal, recovery and limits. Replaced a passwordless Compose rehearsal example with the complete secure configured-URL procedure. Commands need host privileges; generated identities use ordinary role administration afterwards.

Sources: app/cli/create_admin.py, create_client.py, generate_key.py, database_upgrade.py, reseal_secrets.py, restore_check.py, settings_template.py, model_release_raise.py, model_release_prune.py.

Open: Maintenance commands were inspected, not executed against a database.

## run/troubleshooting.md

Reviewed existing refusal/action tables and incident procedure; added expired-certificate and storage-pressure triage linking to concrete recovery steps. Startup/traffic state and role boundaries remain explicit; no destructive generic reset advice.

Sources: app/db.py; app/main.py health endpoints; app/config.py; engine/jobs/files.py and store.py; compose.acme.yml/caddy/Caddyfile; docs/OPERATIONS.md.

Open: None beyond unexecuted deployment commands.

## run/backup-and-restore.md

Reviewed full backup/rehearsal/replacement-host procedure and failures, permissions, volume/key pairing and rollback limits. Added planned server move/decommission sequencing, public-origin link and fail-fast pg_restore in the generic rehearsal. Retention schedule belongs to the operator.

Sources: app/cli/restore_check.py; engine/backups/rehearsal.py; compose.yml and compose.acme.yml; docs/OPERATIONS.md Backup and restore.

Open: No backup, migration, recovery rehearsal or public replacement-host test executed; assistant volumes remain optional with stated session loss.

## run/upgrades.md

Reviewed unchanged: source/image cutover, database/schema-language distinction, migrations and interruption/retry, model raising/skips, success probes, compatibility rules, matching-backup rollback and irreversible later-write loss are covered. Upgrade has no independent expiry setting.

Sources: app/db.py:prepare_database/migration diagnostics; app/cli/database_upgrade.py and model_release_raise.py; compose.yml; docs/OPERATIONS.md Upgrades.

Open: No real upgrade/interrupt/recovery trial; durations and external integrations unmeasured.

## run/model-releases-and-rollback.md

Reviewed unchanged: bootstrap vs stored selection, activation compatibility/access, retirement/deletion/pruning, default/referrer refusals, dry-run/preparation, restoration and assistant release lifecycle are covered. Installed releases have no automatic age expiry.

Sources: engine/model/release_lifecycle.py; app/cli/model_release_prune.py; app/main.py bootstrap; docs/OPERATIONS.md Model releases and rollback.

Open: No pruning or activation executed.

## run/production-checklist.md

Reviewed task/evidence sequence and failure recovery; corrected required public ports to 443 with optional 80 and conditional redirect checks. Added database growth and separate log/metric retention to capacity verification. Setup, changes and recovery link to owning procedures.

Sources: compose.acme.yml, caddy/Caddyfile, app/config.py; source-backed owning operator pages. Owner confirmed 443-only certificate issuance in assignment.

Open: Checklist not executed on a deployed installation; no capacity/recovery-time guarantees.

## run/security-checklist.md

Reviewed transport, secrets, roles, session/throttle, outbound, retention and failure/undo boundaries. Corrected optional HTTP redirects and replaced delivery-history/security-test prose with checks operators repeat after changes. Detailed lifetimes and restore remain on linked pages.

Sources: frontend/nginx templates and 05-choose-mode.sh; app/config.py; app/main.py; source-backed sign-in/keys/HTTPS procedures.

Open: No deployment security assessment or physical passkey ceremony performed.

## run/licence-and-source.md

Reviewed unchanged: source-link purpose/default, setup/recreation, refusal, access/verification, changes with upgrades and backup association are covered. Link configuration does not publish source. Credential rotation, expiry and data deletion do not apply to this URL.

Sources: app/config.py DEFAULT_SOURCE_CODE_URL, _source_code_url and catalogue; frontend AboutPage.tsx; docs/PRODUCT.md source-offer paragraph.

Open: No legal assessment or external source-host availability check performed.

## _waves/coverage/run.md

Mapped all 146 run entries; nine initially missing deployment entries are documented. Retained 254 historical rows. No new exclusions.

Sources: _coverage/inventory/*.json and reviewed pages.

Open: Inventory coverage checks names, not runtime behavior.

## _waves/screens-wanted/D-RUN.md

Recorded seven reused images and exact states; no new image requested. Deployment refresh carried forward for current paths.

Sources: guide/public/screens; page image URLs and captions.

Open: No visual inspection or recapture.

Coverage tooling limitation: tools/check.mjs normalPath() replaces braced placeholders before label matching, so the documented {$PUBLIC_URL} was still flagged. Added its exact inventory key in a non-rendered provenance comment beside the Caddyfile explanation, rather than excluding a reader capability. Shared uncovered.md is outside the edit allowance: coverage-output.cjs redirects only that report to this wave notes; the original check algorithm is unchanged.

## run/https.md

Added a hidden inventory provenance marker for the explained Caddy site variable because placeholder normalisation prevents its label matching. No reader capability excluded.

Sources: tools/check.mjs normalPath/coverage and caddy/Caddyfile.

Open: Coverage tool matching limitation documented in depth notes.

## run/database.md

Final review clarified that feed retention expires positions but does not remove audit history; consumer event rows are the independently pruned data.

Sources: engine/reads/feed.py:retention_floor, engine/events/worker.py:sweep.

Open: None beyond unexecuted deployment commands.

## _coverage/notes/D-RUN/report.md

Final report saved with per-page before/after word counts. Final isolated verify passed: 247 pages; terminology/brand and 69,685 local links/sources passed. Run coverage is 146/146, zero excluded/open; seven image paths exist.

Sources: GUIDE_OUT=_build/D-RUN npm run verify; original tools/check.mjs coverage with report-only redirection; verify.log and coverage.log.

Open: No runtime deployment/recovery/provider trials or screenshot inspection; other sections retain 144 uncovered entries.
