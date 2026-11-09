---
title: Run the service
description: Start refiroo, recover safely and inspect the deployment and its configuration.
reader: operator
---

These journeys are for operators keeping refiroo available and understanding what the deployment
actually runs. Operators need the appropriate server or platform access for installation work;
the application's Operations permission opens deployment diagnostics. It does not grant reference
data editing or security administration.

## Run the service, and recover from an expected refusal

An operator begins with [Install with Compose](/docs/run/install-with-compose/),
[The database](/docs/run/database/) and [Configure refiroo](/docs/run/configure/) to prepare
persistent storage, PostgreSQL and the instance's settings. Start the service, then use
[Health and startup checks](/docs/run/health-and-startup-checks/) to decide whether it is ready
for traffic. Liveness means that the process answers; readiness also needs the database and at
least one workspace it can serve. Readiness alone does not prove every workspace is available.

If startup refuses or enters maintenance mode, read the stated cause, resulting service state
and recovery action. [Troubleshooting](/docs/run/troubleshooting/) connects database connectivity,
collation, missing extensions, migration revisions and model problems to their safe remedies.
Correct the named setting or dependency, then restart where instructed and check readiness again.
Do not edit migration revision rows or stored model documents to suppress a refusal.
[Upgrades](/docs/run/upgrades/) covers migration and unsupported stored-release recovery.

Once serving, use [Monitoring](/docs/run/monitoring/) to inspect workspace and process readiness,
background threads, connection pools and request diagnostics. During a database outage, a process
can remain live while unready. Restore connectivity and allow workers to recover; repeatedly
restarting healthy processes does not restore PostgreSQL. With several processes, follow
[Several processes](/docs/run/several-processes/) for their shared database and file storage.

Complete the recovery preparation with [Back up and restore](/docs/run/backup-and-restore/).
Restore a backup into a separate database and run the documented restore check there, then inspect
the recorded rehearsal outcome. The check must not target the live database. A failed rehearsal
is evidence to resolve before depending on that backup, rather than proof of a working restore.
Preserve the concise error and correlation references when escalating a failure.

## Check what a deployment runs and how it is configured

An operator identifies the running application version, supported model languages, model release
and source information before diagnosing a mismatch or planning maintenance.
[Monitoring](/docs/run/monitoring/) connects the deployment pages with process and workspace
information. [Configure refiroo](/docs/run/configure/) explains the settings catalogue, current
values, defaults, and whether a value came from the environment.

The pages inspect configuration; they do not edit environment settings. Change those in the
server or platform configuration and restart as documented. Secret settings show whether they
are present rather than revealing their values; the database address masks its password.
After a model activation, check the selected workspace's running release rather than assuming
all workspaces run the same one.

Use [Licence and source](/docs/run/licence-and-source/) to verify the running version's source
link, especially for a modified installation. If behaviour still disagrees with configuration,
return to [Troubleshooting](/docs/run/troubleshooting/) with the version, time, failing action,
workspace and diagnostic reference, excluding credentials and full environment files.

## Open a production installation over HTTPS

Start with [What you run](/docs/run/overview/) and
[Install with Compose](/docs/run/install-with-compose/), then choose automatic public
certificates, your organisation's certificate files or an existing HTTPS balancer in
[Serve over HTTPS](/docs/run/https/). Automatic issuance and renewal needs a public DNS name
and reachable port 443; port 80 is optional for redirects. Preserve certificate storage and
check renewal through the public address. Private names need a different certificate route.

[Set up sign-in and mail](/docs/run/sign-in-and-mail-setup/), test a complete sign-in and
recovery path, then complete the [production checklist](/docs/run/production-checklist/)
and [security checklist](/docs/run/security-checklist/). A healthy container does not establish
that every workspace, public sign-in, notification or receiver works. Keep the outcomes for
your installation and correct failed checks before admitting traffic.

## Upgrade and recover a failed cutover

Follow [Upgrades](/docs/run/upgrades/) to record the running source, supported model languages,
private configuration, backup and file archive before maintenance. Check the new deployment's
readiness, workspaces, sign-in and retained files before reopening writes. An unsupported stored
model needs the documented raising review; a database migration refusal needs its stated remedy.

[Model releases and rollback](/docs/run/model-releases-and-rollback/) distinguishes a compatible
model activation from application rollback. Restoring an older application requires its matching
pre-upgrade database and configuration; changing the bootstrap model file does not switch
existing workspaces. Do not repair a cutover by editing migration revision rows.

## Back up, rehearse and move to another host

[Back up and restore](/docs/run/backup-and-restore/) connects a consistent PostgreSQL and
job-file backup to its source version and protected keys. Rehearse the restore in an isolated
database and inspect the recorded result before relying on it. Include the public sign-in path
and file downloads when testing a replacement host; a database-only check does not establish those.

Use the same runbook's host-move sequence to stop writers, take the final consistent copy,
restore, verify and cut over the public address. Preserve the recovery material until the
replacement is proven. Retire the old host after cutover so it cannot resume competing work.
A missing sealing key prevents recovering stored secrets from their encrypted values alone.

## Replace secrets and watch growing storage

[Secrets and keys](/docs/run/secrets-and-keys/) identifies client credentials, signing material,
cursor keys and the sealing key before choosing the replacement procedure. Check which processes
share them and coordinate with the administrator and receivers. Retain the key matching a backup;
replacing a value blindly can make stored credentials unreadable or invalidate saved positions.

[The database](/docs/run/database/) covers connection budgets and growth. Combine it with
[Background jobs](/docs/run/background-jobs/), [Webhook delivery](/docs/run/webhook-delivery/)
and [Monitoring](/docs/run/monitoring/) to watch files, queues, delivery results and retained logs.
Change retention deliberately; it can remove diagnostic detail without removing reference data.
[Several processes](/docs/run/several-processes/) requires shared identity and file storage.
Measure the actual workload before making capacity or recovery-time promises.

## Enable optional AI or prepare a developer instance

Read [AI operation](/docs/run/ai/) before [Set up AI](/docs/run/set-up-ai/). Choose the provider,
built-in assistant and external-agent connection separately, set a send policy and credentials,
apply the configuration, then verify each enabled path. Inspect calls and task retention as well
as service readiness. Disabling a feature stops future use; it does not erase published records,
history or all retained task material. Follow the same page for replacement credentials or cleanup.

For local source work instead, follow [Developer instance](/docs/run/developer-instance/).
It has a different support boundary from the reference installation. Use
[Command-line tools](/docs/run/command-line/) for the documented maintenance commands, and
[Troubleshooting](/docs/run/troubleshooting/) to prepare concise diagnostics when a recovery fails.
