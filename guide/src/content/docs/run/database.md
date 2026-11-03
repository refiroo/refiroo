---
title: The database
description: Prepare PostgreSQL with the required collation and budget its connections.
reader: operator
---

Use PostgreSQL 17. SQLite and other database engines are unsupported, and there is no SQLite
migration tool. The reference Compose installation creates the correct database for you.

## Prepare an external database

Use the ICU root collation `und` so ordering is consistent. As a database administrator:

```sql
CREATE DATABASE rdm TEMPLATE template0 LOCALE_PROVIDER icu ICU_LOCALE 'und' LOCALE 'C';
```

The database role needs `pg_trgm`, `btree_gin` and `pgcrypto`. Startup creates these extensions when
it has permission; otherwise ask the database administrator to install them in the target database.
The runtime role should not have permission to create databases merely to rehearse restores.

Set `DATABASE_URL` to `postgresql+psycopg://user:password@host:5432/rdm` in the engine's private
environment. It has no default. Treat the password and credential-bearing URL as secrets; never
commit them. URL-encode special characters in credentials. Compose builds this URL itself.

A missing URL, another database or driver, wrong collation, or unavailable extensions puts the
service out of readiness. Read the startup message before retrying. A populated database with the
wrong collation needs a properly created database and a [restore](/docs/run/backup-and-restore/),
not a settings change pretending its ordering is correct.

## Budget connections before increasing workers

| Setting | Default | Effect |
| --- | --- | --- |
| `DATABASE_POOL_SIZE` | `5` | Connections kept by each process. |
| `DATABASE_POOL_MAX_OVERFLOW` | `10` | Extra busy-period connections, closed when returned; `0` permits none. |
| `DATABASE_POOL_TIMEOUT` | `30` seconds | How long a request waits for a free connection. |
| `DATABASE_IDLE_TRANSACTION_TIMEOUT` | `300` seconds | Ends an idle transaction and releases locks; `0` disables it. |

Requests and background workers share each process's pool. The job listener has another connection;
startup also uses a connection while checking and migrating. The documented steady-state maximum
per process is `DATABASE_POOL_SIZE + DATABASE_POOL_MAX_OVERFLOW + 1`, or 16 with defaults.
Multiply by all worker processes on all instances, and leave headroom for startup, backups and
administrator sessions below PostgreSQL's usable `max_connections` after reserved slots.
The startup warning sees only its own instance's configured total, not the other instances.

The shared pool also serves worker lease heartbeats, the consumer-event deriver and the webhook
dispatcher. A background thread that cannot obtain a connection logs an ERROR and retries as it
would for an unreachable database; adding request capacity alone does not reserve worker capacity.

A pool wait that expires returns `503 DATABASE_UNAVAILABLE`, reason `poolExhausted`, with
`Retry-After: 5`; nothing is saved. PostgreSQL refusing another connection gives
`tooManyConnections`; ending an idle transaction gives `transactionEnded`. Occasional peaks may
clear with a retry. Persistent failures require checking active work and the server-wide budget
before raising the pool or reducing worker count. See [Monitoring](/docs/run/monitoring/).

For the repository's private development server, use `scripts/postgres.sh start`, `status` and
`stop`; [A developer instance](/docs/run/developer-instance/) explains the setup.

After correcting database configuration or completing a restore, recreate the engine if its
connection settings changed and require `/health` to return 200 again. Inspect every workspace
on Operations before reopening traffic. A configuration fix does not require discarding a working
database or starting a fresh volume.

## Inspect the reference database

You need a shell allowed to run Compose, the installation's private settings and a running database
container. Run these read-only checks from the repository root:

```bash
docker compose exec -T database psql -U rdm -d rdm -c 'SHOW server_version;'
docker compose exec -T database psql -U rdm -d rdm -c \
  "SELECT datname, datlocprovider, datlocale FROM pg_database WHERE datname = current_database();"
docker compose exec -T database psql -U rdm -d rdm -c \
  "SELECT extname FROM pg_extension WHERE extname IN ('pg_trgm','btree_gin','pgcrypto') ORDER BY extname;"
docker compose exec -T database psql -U rdm -d rdm -c 'SELECT version_num FROM alembic_version;'
```

Expect server version 17, database `rdm`, provider `i` (ICU) and locale `und` or `root`. After the
first successful engine start, all three extension names and one migration revision should be
present. Before initialization there is no `alembic_version` table; do not create or stamp it by
hand. Run the engine's database preparation instead. To check that PostgreSQL is accepting local
connections, use `docker compose exec -T database pg_isready -U rdm -d rdm`; this does not test
whether the engine's credentials work over the container network.

For a database prepared by an administrator outside Compose, install missing extensions in that
database as its owner or a suitably privileged role:

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

These statements should report `CREATE EXTENSION` (or a notice that one already exists). If the
extension is unavailable, install PostgreSQL's contrib modules on that server first. This is the
engine's database requirement, not an additional managed-database installation recipe; Compose
remains the reference installation.

## Inspect connection pressure

```bash
docker compose exec -T database psql -U rdm -d rdm -c 'SHOW max_connections;'
docker compose exec -T database psql -U rdm -d rdm -c 'SHOW superuser_reserved_connections;'
docker compose exec -T database psql -U rdm -d rdm -c \
  'SELECT state, count(*) FROM pg_stat_activity GROUP BY state ORDER BY state;'
```

Record the actual limits and current use. Four workers at default settings can open 64 steady-state
connections, before other installations and maintenance connections. A startup warning does not
reserve those slots; every installation on the server must fit within the same budget. Check the
Operations pool figures alongside PostgreSQL activity. `idle in transaction` differs from `idle`:
only the former retains a transaction and can hold write locks.

Every pool setting in the table above is non-secret and needs engine recreation. Preserve the old
values, change only the needed values in `.env`, run `docker compose up -d engine`, then check
readiness and watch the failure counter under representative traffic. To undo a pool adjustment,
restore the earlier values and recreate again. Do not cancel arbitrary sessions or raise the server
limit without checking their workload and memory cost; production connection capacity is **not measured**.

The reference database stores its files at `/var/lib/postgresql/data`. Do not copy that live
filesystem directory as though it were a consistent database backup; use
[the PostgreSQL dump and restore procedure](/docs/run/backup-and-restore/).
