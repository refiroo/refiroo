---
title: Command-line tools
description: Choose the supported maintenance command and run it in the correct configured environment.
reader: operator
---

Database commands use the configured `DATABASE_URL` and engine settings. They prepare the database
as startup does, so they may apply pending schema migrations before their own operation. A release
`--dry-run` previews that release operation; it does not suppress database preparation. Use the
application version intended for that database and back up before running a newer one.
`generate_key` only prints random key material and does not connect to the database. Run them in the intended
installation, not against an accidental default database. The reference installation supplies its
environment through Compose. From the repository root, for example:

```bash
docker compose run --rm engine python -m app.cli.create_admin \
  --username operator --name "Installation administrator"
```

In a configured host backend environment, use `cd backend` then
`.venv/bin/python -m app.cli.<command>`. These host commands do not load Compose's `.env`
automatically. Never pass secret values as literal shell arguments.

| Module after `app.cli.` | Arguments | Purpose and result |
| --- | --- | --- |
| `create_admin` | `--username NAME --name "Display name"`, optional `--email ADDRESS`, `--password-stdin` | Creates an instance administrator, including local recovery sign-in. Prompts twice for the password, or reads one stdin line. Exit 0 created, 1 database failure, 2 invalid/refused input. |
| `create_client` | `--name "Client name"`, repeatable `--role KEY`, optional `--json` | Creates a client and prints its credentials once; without roles it can do nothing until granted access. Exit 0 created, 1 database failure, 2 invalid/refused input. Store its secret securely. |
| `generate_key` | None | Prints a new 32-byte URL-safe-base64 sealing key; exit 0. Secret output: never commit or log it. |
| `database_upgrade` | None | Migrates the configured database. Exit 0 success, 1 startup/migration failure. Back up before upgrading. |
| `reseal_secrets` | Optional `--check` | Checks sealed values or reseals them under `NEW_SECRETS_ENCRYPTION_KEY`. Stop all engines first. Exit 0 success, 1 database/unreadable-value failure, 2 key configuration refusal. |
| `restore_check` | `--restored URL`, optional `--backup NAME` | Prepares a restored copy and records its workspace checks in the live database. Exit 0 passed, 1 failed, 2 nothing checked. The restored URL must be a separate PostgreSQL database. |
| `model_release_raise` | Optional `--dry-run` | Raises eligible older stored models in place. Stop every engine first. Exit 1 if any model was skipped or database preparation failed, otherwise 0; later schemas remain reported and unchanged. |
| `model_release_prune` | Optional `--dry-run`, `--unused` | Removes unreferenced retired releases, or also unreferenced active releases with `--unused`. Exit 0 success, 1 database failure. Preview first. |
| `settings_template` | `--for dev` or `--for compose`, optional `--update PATH` | Prints catalogue defaults, or updates a settings file while preserving existing lines and marking retired settings. A successful run exits 0. It does not apply settings to a running process. |

Argument parsing can also exit 2 for missing or invalid command options. Use `--help` on tools that
accept arguments to inspect their syntax without performing maintenance.

Use the full procedures for [key changes](/docs/run/secrets-and-keys/),
[upgrades and model raising](/docs/run/upgrades/), [restore checks](/docs/run/backup-and-restore/)
and [release pruning](/docs/run/model-releases-and-rollback/). Their downtime and backup steps are
part of the operation, not optional precautions.

The development wrappers `scripts/dev.sh` and `scripts/postgres.sh` configure the private developer
instance. They are described in [A developer instance](/docs/run/developer-instance/) and do not
manage the Compose installation.

## Print or update a settings template

From the configured host backend directory, print a template without changing a file:

```bash
.venv/bin/python -m app.cli.settings_template --for dev
```

To bring an existing developer settings file up to date:

```bash
.venv/bin/python -m app.cli.settings_template --for dev --update ../.dev/settings.env
```

`--update` requires an existing file. It preserves its existing lines, appends missing settings as
comments and comments out retired settings. Review its report before starting the engine: a
commented-out retired secret still needs to be transferred to its replacement setting with the
same value. It does not invent database credentials or apply new values to a running process.
The Compose template leaves out settings supplied by Compose or the image; use `.env.example`
for a complete new installation.

## Command examples and output

These examples run from the reference installation's repository root with its existing private
configuration. Keep the HTTPS overlay arguments or alternate environment-file selection used by
that installation. Tools that take arguments support `--help`; Python modules without argument
parsing (`generate_key` and `database_upgrade`) perform their work when invoked.

| Command | Example | Successful output |
| --- | --- | --- |
| Create administrator | `docker compose run --rm engine python -m app.cli.create_admin --username operator --name "Installation administrator" --email operator@example.org` | `Created administrator 'operator' (...)`. Parentheses contain the new person's ID. |
| Create monitoring client | `docker compose run --rm engine python -m app.cli.create_client --name Monitoring --role operator --json` | One JSON object with `clientId` and `clientSecret`; store the secret immediately. |
| Generate sealing key | `docker compose run --rm --no-deps engine python -m app.cli.generate_key` | One base64 line; a new random key every time. It does not install the key. |
| Upgrade database | `docker compose run --rm engine python -m app.cli.database_upgrade` | `Database migration completed successfully.` |
| Check stored secrets | `docker compose run --rm engine python -m app.cli.reseal_secrets --check` | `Every sealed value opens with the current key (...)` and a recovery-code report. |
| Reseal stored secrets | `docker compose run --rm -e NEW_SECRETS_ENCRYPTION_KEY engine python -m app.cli.reseal_secrets` | `Re-sealed N value(s): ...` and `Set SECRETS_ENCRYPTION_KEY to the new key before starting the engine.` Follow the [complete procedure](/docs/run/secrets-and-keys/). |
| Check restored copy | `docker compose run --rm engine python -m app.cli.restore_check --restored postgresql+psycopg://rdm@database:5432/rdm_restore_check --backup refiroo-backup.dump` | `Backup rehearsal passed.`, workspace counts and `Recorded in the instance (Settings › Operations). Delete the copy when done.` Create and restore the copy first. |
| Preview raising models | `docker compose run --rm engine python -m app.cli.model_release_raise --dry-run` | Per-release schema changes, skips and a dry-run total, or a nothing-to-do message. |
| Raise models offline | `docker compose run --rm engine python -m app.cli.model_release_raise` | `Raised N release(s) to schema ...; N skipped.` Later schemas are separately reported and left alone. |
| Preview release pruning | `docker compose run --rm engine python -m app.cli.model_release_prune --unused --dry-run` | Release ID, key/version, status, schema and count; `Nothing changed.` refers to release deletion. |
| Prune retired unused releases | `docker compose run --rm engine python -m app.cli.model_release_prune` | `Deleted N retired and unused release(s).` or `No retired and unused release; nothing to do.` |
| Print Compose settings | `docker compose run --rm --no-deps engine python -m app.cli.settings_template --for compose` | Commented settings in catalogue groups; no file is changed. |

`N`, `...` and parenthesised identities in this table stand for values printed for your database;
they are not literal fixed output. `--role` may be repeated for a client. `--password-stdin` reads
one line for an administrator and skips the second prompt; pipe from a protected secret source,
not a password typed into the shell command. Neither creation tool is a password-reset tool:
for an existing person use the access administration workflow.

## Respond to a refusal

Read the exit status immediately (`echo $?` in the same shell). Exit 0 means the command completed,
not that every workspace is ready: model raising can leave later schemas unchanged. Database
preparation failures exit 1 and print the same actionable diagnostics as startup. Correct those
using [Health and startup checks](/docs/run/health-and-startup-checks/).

`The passwords differ; nothing was created.` exits 2; repeat creation with matching passwords.
`Not created: name is not valid.` exits 2 for a client name refused by validation. Other creation
refusals begin `Not created:` and give their specific reason. Correct that input rather than
repeating it unchanged. A missing option prints argparse usage and exits 2 before the task runs.

For resealing, `Not re-sealed: SECRETS_ENCRYPTION_KEY is not set.` means supply the **original**
key, not a new one. `Not re-sealed: NEW_SECRETS_ENCRYPTION_KEY is the current key.` means the two
keys are equal. A missing new key prints
`Not re-sealed: NEW_SECRETS_ENCRYPTION_KEY is not set; generate one with \`python -m app.cli.generate_key\`.`
These configuration refusals exit 2. An unreadable sealed value exits 1 and changes none of them.

There is no CLI undo for account creation or pruning. Manage created accounts and their grants
through access administration; restore deleted release content only through a supported installation
or whole-instance recovery workflow. Rehearse a backup before maintenance that changes stored
content. A settings template's `--update` edits only the path you name and does not create missing
parent directories or a new settings file: preserve your old file first and review the result.
