---
title: Model releases and rollback
description: Separate model selection from bootstrap files and application recovery.
reader: operator
---

A workspace runs an installed model release selected in the database. `RDM_MODEL_PATH` is only
bootstrap input: its default is `model/rdm-starter.json`, or `/opt/refiroo/rdm-engine/model/rdm-starter.json` in the image.
Startup validates the file and installs its release if missing, assigning it to a workspace without
one. Existing workspaces keep their selections. Editing that file never activates a new model.

For browser tasks, use [Releases](/docs/model/releases/). Model mutations require
`MODEL_ADMIN_MUTATIONS_ENABLED=true` (default false), plus the person's model permissions.
A draft is validated and compiled, installed as an inactive immutable release, then activated with
concurrency checks. Activation refuses a model incompatible with existing data.

## Roll back model content

Activate a previously installed compatible release through the model administration workflow.
The same data checks apply in either direction: if current data no longer fits the older model,
rollback is refused. Resolve the incompatibility in a reviewed model/data change instead of editing
release JSON or pointing the bootstrap file at an older version.

An unsupported model schema makes affected workspaces unavailable. Check Operations to distinguish
that from a database outage. Follow [Upgrades](/docs/run/upgrades/) to raise older stored models;
use an appropriate later engine for newer schemas.

## Retire and remove releases

Retiring a release removes it from pickers without stopping workspaces already using it. A release
used by the default workspace cannot be retired; first select a usable release for that workspace.
Retirement is not deletion. Deletion
requires that nothing refers to it: workspaces, records, change sets, publications, jobs, import
profiles and mappings can keep a release in use.

For many releases, inspect candidates first:

```bash
docker compose run --rm engine python -m app.cli.model_release_prune --dry-run
```

Then remove retired releases with no references:

```bash
docker compose run --rm engine python -m app.cli.model_release_prune
```

`--unused` also considers active releases with no references. Preview that wider selection before
using it:

```bash
docker compose run --rm engine python -m app.cli.model_release_prune --unused --dry-run
```

Pruning uses one transaction under the installation lock and can run while the service runs.
Drafts based on a removed release remain, without their link to it. Check the command's report;
exit 0 is success, 1 a database startup failure.

## Roll back the application

Restoring an older application requires its pre-upgrade database backup and matching configuration.
This restores all database state, unlike model activation. See [Back up and restore](/docs/run/backup-and-restore/).
Database downgrades and manual edits to release rows are unsupported.

## Check model selection before maintenance

You need Operations access to inspect readiness and model permissions for any browser activation.
Pruning on the server requires access to the private configured environment. Back up before any
irreversible deletion, and verify the engine version is intended for this database: even a prune
dry run first prepares its schema.

1. Open Operations and record each active workspace's release and schema. Check unavailable
   rows before pruning or changing bootstrap files.
2. For an intended model rollback, ask the model administrator to preview activation of the
   previously installed release in the workspace. Review incompatibilities and current runtime
   versions in the activation workflow; do not restart engines as a substitute for activation.
3. After successful activation, open the workspace, read a representative record and inspect its
   readiness in Operations. Other processes pick up the selection on their next request.
4. To reverse that selection, activate the prior release again, subject to the same current-data
   checks. If data changed meanwhile, that reverse operation can be refused too.

For pruning, a dry run prints each candidate as public release ID, `key@version`, lifecycle status
and schema, then a total. With no eligible candidates, the exact default message is:

```text
No retired and unused release; nothing to do.
```

A successful deletion reports `Deleted N retired and unused release(s).` With `--unused`, the
wording is `unused` and active unreferenced releases are included. Counts vary with your database.
Exit 1 means database preparation failed; use its diagnostic, then retry after correcting the
cause. A release still referenced is excluded rather than forcibly detached. Re-run the dry run
if references changed after your earlier inspection.

Pruning cannot be undone by restarting or changing `RDM_MODEL_PATH`. If a required release was
removed, review reinstalling its original source through model administration or restore the whole
matching backup in an isolated recovery process. Do not reconstruct immutable release rows using
SQL. Retire a release rather than delete it when you want it hidden from future choice while
preserving its identity and existing references.

## Releases prepared by the assistant

The assistant installs releases for review; a person activates or confirms a migration. A whole-type
move uses the migration preview and goes live on confirmation. A partial move can need a release
with both types, publication of the change set, then activation of the final release; if the old
type remains in the final model, the last activation step is unnecessary. The task shows the steps
for its result. Unused session-installed releases are retired when the task ends; the final release
needed by that result is kept. Do not mistake an installed release for an activated one.

An optional provider can explain a model change after **Explain this change** is pressed. It receives
model differences and record counts, not record values. Its statements cite the engine's facts and
never replace activation checks. See [AI policy and review](/docs/run/ai/) for who may ask, what is
sent, usage costs and retention, and [model changes with AI](/docs/model/ai-model-changes/) for the
browser task.
