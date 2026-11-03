---
title: How refiroo is built
description: A web application and API service backed by PostgreSQL, with persistent background work.
reader: evaluator
---

One engine serves many model-defined applications through a web front end and an API service backed by PostgreSQL. The browser and integrations use the service; they do not write database tables directly. See [What refiroo is](/docs/about/what-is-refiroo/) for what this lets a team do.

## One service, shared rules

The service validates the model and uses it to interpret records, fields, relationships and views. It supplies the same data rules to ordinary edits, bulk jobs, imports and publication. The browser renders the views defined by the model rather than implementing a separate application for each domain.

The backend uses Python 3.14 and FastAPI, served by Uvicorn, with Pydantic 2 for typed inputs, SQLAlchemy 2 for database access and Alembic for database migrations. PostgreSQL holds model releases, reference data, history and operational state; the reference installation uses PostgreSQL 17 with ICU text collation. The web front end uses React and TypeScript, built with Vite.

Docker Compose runs the reference installation. Its nginx 1.28 web server serves the interface and forwards API requests to the engine. For automatic HTTPS, an optional Caddy 2 service obtains and renews certificates through ACME, using Let's Encrypt or ZeroSSL. An organisation can instead supply its own certificates or use its existing HTTPS proxy. The [operator overview](/docs/run/overview/) explains what to deploy.

## Standards and formats

People can sign in through an organisation's OpenID Connect provider or local accounts. Local accounts support WebAuthn passkeys and time-based one-time passwords (TOTP) from authenticator apps. External systems authenticate with OAuth 2.0 client credentials. See [Who can do what](/docs/about/people-and-access/).

The APIs exchange JSON and publish OpenAPI 3.1 contract documents. Consumer webhooks use HMAC-SHA256 signatures and offer RDM JSON or CloudEvents 1.0 messages. File exchange supports Excel .xlsx workbooks and CSV; notifications use SMTP mail. Operators can collect Prometheus metrics. These connections are configured by the organisation; reading the interface does not require a hosted analytics service.

## Open-source components

refiroo uses the AGPL-3.0-or-later licence. Its dependencies have their own licences. FastAPI, Pydantic, SQLAlchemy, Alembic, React, Vite, Astro, Starlight and the Scalar API-reference viewer use the MIT licence. Uvicorn and the WebAuthn verification library use BSD-3-Clause; the psycopg PostgreSQL driver uses LGPL-3.0-only. The repository's third-party notices list the bundled components and their licence texts, including libraries bundled with the driver.

See [Licence and compatibility](/docs/about/compatibility-and-licence/) for the running installation's source offer, and [Licence and source](/docs/run/licence-and-source/) for configuring it.

## Background work survives a restart

Larger imports, exports and data changes can run as background jobs. Job parameters, progress and outcomes are stored in the database. Workers in the service claim jobs and checkpoint their work. If a process stops, another worker can resume work whose claim has expired.

A completed part of an independent load remains applied; an all-or-nothing operation has different transaction rules. Jobs report what happened rather than treating cancellation as an undo. See [Background jobs](/docs/run/background-jobs/).

## Several processes can share the database

The standard container starts one API process. Several processes or servers can use the same PostgreSQL database. Database coordination protects startup, writes and job claims. Each request resolves the workspace's model release, so a release changed through one process is picked up by the others on their next request.

An operator must configure shared signing material and shared job-file storage where requests can reach different processes. Monitoring reports the processes and workspaces they serve. See [Several processes](/docs/run/several-processes/) and [Monitoring](/docs/run/monitoring/).

## Documentation stays with the installation

The guide is built with Astro and Starlight, with local Pagefind search, and bundled with the installation. Its pages, fonts and scripts are served locally, so reading it needs no outside service. The [API reference](/docs/api) also bundles its Scalar viewer by default and disables hosted extras. An operator can deliberately choose an externally hosted viewer script instead; that option needs internet access.

This local delivery concerns viewing documentation and the interface. Configured sign-in providers, mail servers and webhook receivers are separate connections chosen by the organisation.

## Operation includes recovery

Startup checks refuse unsafe database and model states with a reason and a recovery instruction. Health checks distinguish a process that answers from one ready to serve data. Operators can rehearse restoring a backup into a separate database and inspect the result.

Activating an older model release does not restore older data. See [Health and startup checks](/docs/run/health-and-startup-checks/) and [Backup and restore](/docs/run/backup-and-restore/).
