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
