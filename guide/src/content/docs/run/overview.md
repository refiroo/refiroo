---
title: What you run
description: Understand the reference installation and choose your next operator task.
reader: operator
---

Run refiroo with the repository's Docker Compose installation. It builds the application from
source and runs three containers:

| Container | Responsibility | Persistent storage |
| --- | --- | --- |
| `web` | Serves the browser application and forwards requests to the engine. Ends HTTPS when using your certificates. | Certificate files supplied by you. |
| `engine` | Serves the API and documentation, checks the database at startup, and runs background work. | `job-files` volume. |
| `database` | PostgreSQL 17, the only supported database. | `database` volume. |

Only the web service publishes host ports. The engine runs as an unprivileged user. Jobs run in
threads inside the engine process; there is no separate worker service to install. The optional
automatic HTTPS overlay adds Caddy and makes it the only public container.

## Start here

1. [Install with Compose](/docs/run/install-with-compose/) and [choose HTTPS](/docs/run/https/).
2. [Configure the installation](/docs/run/configure/), preserving its [secrets and keys](/docs/run/secrets-and-keys/).
3. [Set up sign-in and mail](/docs/run/sign-in-and-mail-setup/), if needed.
4. Check [readiness](/docs/run/health-and-startup-checks/), set up [monitoring](/docs/run/monitoring/), and [rehearse a restore](/docs/run/backup-and-restore/).
5. Complete the [production checklist](/docs/run/production-checklist/).

For local code work, use the [developer instance](/docs/run/developer-instance/). It is a development
setup, separate from the tested Compose reference installation. Several processes can share a
database, but arranging several nodes and their shared storage is outside that reference installation.

AI is optional. Read [About AI](/docs/run/ai/) before [setting it up](/docs/run/set-up-ai/).
Production CPU, memory and disk sizing for your workload is **not measured**. Set capacity from
observations of your own records, files, traffic and retention; defaults are limits, not sizing guarantees.

For supplier-file synchronisation, the operator keeps workers, shared file storage and database
connectivity available; a restarted independent job resumes after its last committed chunk.
The integrator reviews rejected rows and maintains its change-feed position. Use
[File exchange](/docs/integrate/files-imports-and-exports/), [Following changes](/docs/integrate/following-changes/)
and [Background jobs](/docs/run/background-jobs/) together when recovering an interrupted load.

## Network and storage

The reference Compose file builds two local images and downloads the database image. The engine
image uses Python 3.14 slim and builds the guide using Node 22 Alpine. The web image builds the
browser client with Node 22 Alpine and serves it with
`nginxinc/nginx-unprivileged:1.28-alpine`. PostgreSQL uses `postgres:17-alpine`; the optional
certificate overlay uses `caddy:2`. Building needs access to image and package registries. These are
source builds, so keep the exact source version with your deployment record.

| Connection | Port and direction | Exposure |
| --- | --- | --- |
| Browser → web | Host TCP 443 → container 8443 with certificate files | Public HTTPS entry. TCP 80 → 8080 redirects to the fixed public address. |
| Browser → Caddy, with the overlay | Host TCP 80 and 443 | Caddy is public and forwards to private `web:8080`. |
| HTTPS balancer → web, in proxy mode | Container 8080, through your selected host port | Restrict to the balancer. This hop is HTTP on a trusted network. |
| web → engine | `engine:8000`, HTTP on the Compose network | Private. Never publish engine port 8000 with the reference trust settings. |
| engine → database | `database:5432`, PostgreSQL | Private. No host port is published. |
| Monitoring → engine | Internal 8000, authenticated `/metrics` | Private; public web returns 404 for this path. |
| engine → sign-in provider / webhook receiver | HTTPS to the configured host and port | Outbound only, when configured. |
| engine → SMTP | Configured port; commonly 587 STARTTLS or 465 TLS | Outbound only, when configured. |

The public proxy forwards `/api/`, `/oauth/`, `/mcp`, `/.well-known/`, `/docs`, `/openapi.json` and
`/health` paths. Other paths serve the browser application. `/mcp` is available only when agent
access is enabled; see [AI and agent settings](/docs/run/ai/).

| Storage or file | Location | Protect or recreate? |
| --- | --- | --- |
| Database volume | `database` service, `/var/lib/postgresql/data` | Back up as PostgreSQL state. It holds records, models, identities, jobs, feeds and delivery logs. |
| Job-file volume | Engine, `/opt/refiroo/rdm-engine/data/job-files` | Back up with the database. Some files are temporary; draft/profile source workbooks are long lived. |
| Private environment | Host `.env`, or your selected file | Keep securely outside database backups, associated with each backup. Losing its sealing key loses access to stored secrets. |
| Certificate directory | Host `./certs`, mounted read only at `/opt/refiroo/rdm-engine/frontend/certs` | Protect private keys; preserve or replace through your certificate issuer. Not needed with automatic HTTPS. |
| Certificate account and certificates | Overlay `caddy-data`, mounted at `/data` | Preserve and back up to avoid unnecessary reissuance and authority limits. |
| Built application and guide | Images, under `/opt/refiroo/rdm-engine` | Rebuild from the matching source and dependencies; not mutable business data. |
| Container logs | Docker's configured logging storage | Export/rotate according to your retention policy; replacing a container is not log archiving. |

The reference file does not persist optional assistant folders separately. Before enabling that
feature, review its [storage and security requirements](/docs/run/ai/). Temporary exports may be
regenerated, but deleting the entire job-file volume also loses input files. A database backup alone
cannot reconstruct those workbooks. See [Background jobs](/docs/run/background-jobs/) for each
file's lifetime and [Back up and restore](/docs/run/backup-and-restore/) for a consistent pair.

## Know the boundary of support

The installation procedure covers the checked-in Compose services and HTTPS overlay. It supplies
no Kubernetes, managed-database, high-availability or automatic failover procedure. Multiple engine
processes have shared-database coordination, but assembling a multi-node deployment and its shared
storage requires your own operational validation. Hardware minimums, production service targets
and recovery times are **not measured** for your workload.
