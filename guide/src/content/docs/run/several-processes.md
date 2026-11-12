---
title: Several processes
description: Share a database safely and understand startup, leases and process readiness.
reader: operator
---

Several engine processes may share one PostgreSQL database. They can be workers on one host or
instances on different nodes. The tested Compose reference starts one engine process; a deployment
across nodes also needs shared file storage and a load balancer that you arrange.

## Share the installation's identity

Use the same `PUBLIC_URL`, `SECRETS_ENCRYPTION_KEY` and `RDM_CURSOR_SIGNING_KEY` everywhere.
The two keys are secrets; never commit them. Mount the same `JOB_FILE_DIR` on shared storage:
a job can be accepted by one process and handled by another. If the built-in assistant is enabled,
also preserve its task folders and Claude Code session files across every process that can take
over its work; the reference mounts are listed in [What you run](/docs/run/overview/#network-and-storage).
Separate local directories on different nodes do not form shared storage. Budget all their
[database connections](/docs/run/database/) together. Capability groups may differ by instance,
for example an internal administration instance and a more restricted public instance.

`WEB_CONCURRENCY` defaults to `1`. Uvicorn reads this environment variable even without a
`--workers` argument, so increasing it starts more worker processes in the engine container.
Recreate the container after changing it and verify the process list on Operations.

## What happens at startup and activation

Processes starting together take the database installation lock in turn to check, migrate and
install bootstrap content. The others wait, then see the prepared database. Avoid treating this wait
as a failed start.

A model activation or workspace migration becomes visible to every process on its next request.
No coordinated restart is needed. A read crossing a workspace's model change can return
`409 MODEL_RELEASE_CHANGED`; the client reads again.

Writes take database locks for the workspace or change set. Uniqueness, versions and relationship
rules therefore apply across processes. A stalled idle transaction releases its locks when
`DATABASE_IDLE_TRANSACTION_TIMEOUT` expires, by default 300 seconds. Its next database operation
fails; restart a frozen process after addressing the cause rather than disabling this protection.

If a node loses connectivity during a SQL statement, the idle-transaction timeout does not apply:
the database must first detect the lost connection. Review PostgreSQL's `tcp_keepalives_idle`,
`tcp_keepalives_interval`, `tcp_keepalives_count` and `tcp_user_timeout` for several-node deployments.
Operating-system defaults can otherwise leave locks held long after a node disappears.

A process that resumes after PostgreSQL ended its idle transaction saves none of that transaction.
Its request can report `transactionEnded`, or `unreachable` if it meets the closed connection first.
Its job is left for lease recovery. It can serve again after reconnecting; investigate repeated
freezes or starvation before changing the timeout.

## Jobs and process health

Each process runs its own workers. Database notifications wake idle workers, and job leases keep
them from applying the same work. A worker renews its lease while running; another takes over only
when renewal stops and `JOB_LEASE_SECONDS` expires, by default 120 seconds.

Open **Settings › This instance › Operations** with Operations access. It lists live and silent
processes, their readiness, threads, connections and workspace failures. Reports arrive every
`PROCESS_HEARTBEAT_SECONDS` (default 15); three missed intervals mark a process silent.
A clean stop removes the row; a dead process's row ages out after a day.

Use `/health/live` for liveness and `/health` for readiness. An instance can be ready while one
workspace is unavailable: inspect workspace readiness on Operations as well.
[Monitoring](/docs/run/monitoring/) explains the screen and instance-wide metrics.

A newer job for the same subject can supersede an older one, such as a replacement dry run for the
same draft. A running one-step job checks cancellation before committing, so its late result cannot
overwrite the newer result. This rule concerns work about the same draft or operation; ordinary
independent batches are not deduplicated merely because they name the same workspace.

## Increase workers in the reference container

Use this only after calculating the server-wide connection budget and measuring whether CPU,
memory or requests actually need more workers. No production worker count or memory requirement
has been measured. The existing reference named file volume is shared among workers in the same
container; multiple hosts require shared storage you arrange yourself.

1. Record the current process count on Operations and preserve the current private settings.
   Set one value in `.env`, for example:

   ```dotenv
   WEB_CONCURRENCY=2
   ```

2. Recreate the engine and check startup:

   ```bash
   docker compose up -d engine
   docker compose logs --tail=100 engine
   curl -i https://refiroo.example.org/health
   ```

3. On Operations, wait for heartbeats and check that two worker processes are live and ready,
   with the intended engine version and workspace releases. Recheck database use and the
   `rdm_database_unavailable_total` reasons under your representative load. At defaults, two
   workers can open 32 steady-state database connections, plus startup and maintenance overhead.
4. If resource pressure or connection failures increase, restore `WEB_CONCURRENCY=1`, recreate
   and repeat those checks. This changes process count; it does not remove database records.

A clean stop releases job leases after the current work can finish. The reference Uvicorn command
allows ten seconds for graceful shutdown; work that cannot finish before termination follows
crash/lease recovery instead. Do not promise that a very long atomic operation completes within
a routine container stop. Allow the lease to expire and inspect the job before resubmitting it.

## Diagnose a silent or stalled process

First compare Operations' last heartbeat with the configured interval and inspect bounded engine
logs. A missing row after a clean stop is expected; a silent row can indicate a crash, database
partition or freeze. Verify that the process is still present before removing it from service.
Do not delete process rows by hand to make the alert disappear.

For `transactionEnded`, the timed-out transaction saved nothing. A request may retry; job work is
left for lease recovery. For persistent `unreachable`, restore network/database access first.
For `poolExhausted`, inspect all pool users before increasing workers: adding workers can exhaust
the PostgreSQL server faster. The [database procedure](/docs/run/database/#inspect-connection-pressure)
provides read-only commands. Changing idle-transaction limits needs recreation on every instance.

Multi-node load balancing must use readiness for routing, preserve the shared public issuer and
allow long event streams. Every node must use the same sealing/cursor keys and see the same files.
Do not place different engine versions behind one address without first checking both against
the stored schema and model-language window; this page supplies no rolling-upgrade guarantee.

A running worker renews its lease every third of `JOB_LEASE_SECONDS`, including during a long
step. Job notifications use PostgreSQL `LISTEN`. Setting the idle-transaction timeout to `0`
lets a stalled transaction hold locks until the process resumes or its connection closes.
Raise the timeout only if its warning occurs during legitimate work. Lost-connection detection
with default TCP keep-alives can take about two hours on Linux and macOS; review the database
server's keep-alive settings before using multiple nodes.
