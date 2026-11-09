---
title: A developer instance
description: Start local development servers and use HTTPS from a phone on the same network.
reader: operator
---

This setup is for development. For an installation, use [Docker Compose](/docs/run/install-with-compose/).
The commands below run from the repository root unless a directory change is shown.
You need Python 3.14, Node.js 22.23.4 or later and npm, and PostgreSQL 17. The database helper uses Homebrew's
PostgreSQL binaries on macOS; it runs its own server, without a login service.

## Prepare the dependencies

```bash
cd backend
python3.14 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cd ../frontend
npm ci
cd ../guide
npm ci
npm run build
cd ..
scripts/postgres.sh start
scripts/dev.sh settings
scripts/dev.sh admin operator "Development administrator"
```

The database helper prints its address. The settings command creates the ignored
`.dev/settings.env`, including the database URL and a new encryption key, unless your environment
already supplies one. Keep an existing database's key. Running the command again preserves your
lines and adds settings introduced by a newer version. An environment value takes precedence over
the file. The administrator command asks for a password.

When refreshing `.dev/settings.env`, `scripts/dev.sh settings` also comments out retired settings
that the engine would otherwise refuse. Run `scripts/dev.sh` without a command to list its tools.

Start each server in its own terminal:

```bash
scripts/dev.sh engine
```

```bash
scripts/dev.sh frontend
```

Open `http://localhost:5173`. The frontend forwards engine requests; its default engine target is
`http://localhost:8000`, changed with `ENGINE_URL`. The scripts keep the servers in the foreground:
Ctrl-C stops each. Stop the private database with `scripts/postgres.sh stop` when finished.
A port-in-use refusal names the process to stop; do that before starting another server.

## Open it from another device

Browser sign-in and passkeys require a secure page. A phone cannot use plain HTTP at the computer's
network address as if it were localhost.

1. Install `mkcert` (on macOS, `brew install mkcert`), then run `scripts/dev.sh cert`.
   This trusts its certificate authority on the computer and creates certificates in `.dev/certs/`.
2. Transfer and trust **only** the authority's `rootCA.pem`, found with `mkcert -CAROOT`, on the phone.
   Never transfer its private key. On iPhone, install the profile and enable it under
   Settings › General › About › Certificate Trust Settings. On Android, install it as a CA certificate.
3. Run `scripts/dev.sh engine --network` and `scripts/dev.sh frontend --network` in separate terminals.
4. Open the printed `https://<address>:5173` on both devices. Trust must succeed without a
   certificate warning. Allow the frontend port through the computer's firewall on this network.

The scripts discover the address from the default route. `RDM_DEV_ADDRESS` overrides it;
`scripts/dev.sh address` prints it. If the address changes, regenerate the certificate.
Network mode sets `PUBLIC_URL` to the frontend address and supplies matching browser origins.
Switching back to localhost changes the public address and requires signing in again.

The built guide is served through `/docs`; `/docs/api` is the API reference. Without a guide build,
`/docs` explains that the files are missing while the rest of the application remains available.

## Check the local services and finish cleanly

You need a shell, Homebrew PostgreSQL binaries on macOS, a browser and free development ports:
5173 for Vite, 8000 for the engine and 54320 for the private PostgreSQL server. The helper trusts
local database connections and binds PostgreSQL to localhost; do not use it as a production server
or expose its database port to the network. Local development CPU and memory minimums are
**not measured**. The development helper's log is `backend/.postgres/server.log`.

From a third terminal while the two servers run:

```bash
scripts/postgres.sh status
curl -i http://localhost:5173/health/live
curl -i http://localhost:5173/health
```

Expect `running: DATABASE_URL=...`, then HTTP 200 and `{"status":"ok"}` from both probes.
Sign in through `http://localhost:5173`, open a workspace and read its records. The engine's port
is useful for diagnostics; the browser should enter through the frontend origin so sign-in,
session cookies and passkeys all agree on the address.

`RDM_POSTGRES_PORT` selects the development database port and `RDM_POSTGRES_BIN` selects the
PostgreSQL binary directory. If either changes, check the generated `DATABASE_URL` and your
`.dev/settings.env` before starting the engine; an environment value takes precedence over that
file. Do not confuse `.dev/settings.env` with Compose's production `.env`.

| Exact message or fragment | Recovery |
| --- | --- |
| `PostgreSQL 17 binaries not found.` | Install `postgresql@17` or point `RDM_POSTGRES_BIN` at its binaries; do not start a second login service. |
| `No backend/.venv:` | Create the Python 3.14 virtual environment and install the backend dependencies using the displayed command. |
| `Port 8000 is already in use; stop that server first (Ctrl-C in its terminal, or kill <pid>):` | The helper lists the holder. Stop your prior engine before starting another. The port number can instead be the frontend port. |
| `No certificate yet: run 'scripts/dev.sh cert'.` | Create and trust the network certificate before using `--network`. |
| `run 'scripts/dev.sh cert' again.` | The stored certificate address differs from the computer's current address. Regenerate, then restart both network servers. |
| `Start the development server first: scripts/postgres.sh start` | Start PostgreSQL before backup or rehearsal. |
| `No dump to rehearse. Write one with 'scripts/postgres.sh backup', or name one.` | Take a dump first, or supply its actual path. |

For network HTTPS checks, use the address printed by `scripts/dev.sh address`, over port 5173,
on both computer and phone. The phone must trust the development CA; a warning means the secure
browser flow is not ready. Do not install that CA on unrelated production devices.

When finished, press Ctrl-C in each foreground server terminal, then run:

```bash
scripts/postgres.sh stop
scripts/postgres.sh status
```

Expect `Stopped the development server.` (or `The development server is not running.`), then
`stopped`. This preserves development data, settings and certificates. Start again with the same
key and `scripts/postgres.sh start`; deleting the data directory is not a safe fix for an unknown
startup problem. Use the [backup procedure](/docs/run/backup-and-restore/) if that data matters.

## Browser and documentation addresses

The development certificate covers the discovered address, `localhost` and `127.0.0.1`.
Network mode runs the engine at `https://<address>:8000` and the frontend at
`https://<address>:5173`. Vite enables HTTPS with `DEV_HTTPS_CERT` and `DEV_HTTPS_KEY` and
forwards requests to `https://localhost:8000`. The engine's browser-origin list includes the
frontend names and its own HTTPS names, so the API reference works through either port.
The engine command enables proxy headers for the locally forwarded caller address.

Vite forwards `/api`, `/oauth`, `/mcp`, `/.well-known`, `/docs`, `/openapi.json` and `/health`.
It does not forward `/metrics`; scrape the engine directly. `/brand` belongs to the frontend.
By default the browser calls the address where the page was opened. Only a build-time
`VITE_API_URL` selects a different engine; it is not a runtime environment override.

For a standalone documentation site without an engine, run `npm run build:public` in `guide/`.
That build includes a static, read-only API reference under `api/`, covering the management API
and the guide's example consumer API. An installation uses its engine's live reference instead.

## Try AI with a Claude subscription

Install Claude Code on the host and authenticate it with your development account. In
`.dev/settings.env`, set both switches to try all AI features:

```dotenv
AI_AGENT_COMMAND="claude --model sonnet"
AI_SEND_LEVEL=values
AI_PROVIDER=devtools.claude_code_provider:provider
AI_MODEL=sonnet
```

Leave `AI_AGENT_SANDBOX` unset on the host so the session uses the operating-system sandbox.
The provider in `backend/devtools` runs Claude Code with your sign-in and limits. It appends usage
to `backend/devtools/usage.jsonl`; dollar amounts report usage at API prices rather than money
charged to the subscription. It is for development and trying features, and is absent from the
production engine image. For a noninteractive subscription token, API-key credentials, compatible
endpoints and separate tests of both switches, follow [Set up AI](/docs/run/set-up-ai/).

Stop and restart the engine command to read changed settings. AI requests can send model details,
instructions and record data outside your machine. Review [the send policy, permissions and
retention](/docs/run/ai/) before trying it. Nothing is published by the assistant: review the proposal
and the resulting change set yourself. Actual subscription charges and limits belong to Claude Code.
