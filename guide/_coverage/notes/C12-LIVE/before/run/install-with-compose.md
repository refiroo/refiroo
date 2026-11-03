---
title: Install with Compose
description: Build the reference installation, create its first administrator, and check readiness.
reader: operator
---

Use a host with Docker Engine and Docker Compose, the repository for the version you intend to
run, a DNS name reaching that host, and an HTTPS arrangement. Run these commands from the
repository root. The reference installation builds the engine and web images locally; its database
image is `postgres:17-alpine`.

## Prepare the address and secrets

1. Choose the permanent address people open, such as `https://refiroo.example.org`. It is the token
   issuer and the host passkeys belong to. A later host change signs people out and makes their
   existing passkeys unusable there.
2. Create the private settings file:

   ```bash
   cp .env.example .env
   chmod 600 .env
   ```

3. Set `PUBLIC_URL` in `.env` to that address, without a path or trailing slash. Generate each secret
   separately and copy its output into the corresponding setting in that private file:

   ```bash
   openssl rand -base64 24 | tr -d '/+=\n'
   openssl rand -base64 32 | tr '+/' '-_'
   openssl rand -base64 32
   ```

   These are, in order, `POSTGRES_PASSWORD`, `SECRETS_ENCRYPTION_KEY` and
   `RDM_CURSOR_SIGNING_KEY`. All three are secrets: never commit them or put them in an image.
   Keep the encryption key outside the database, securely alongside the configuration for its backups.
   The database password initializes a new database; editing it later does not change an existing
   PostgreSQL role's password.
4. [Provide HTTPS](/docs/run/https/). By default, put `fullchain.pem` and `privkey.pem` in `certs/`
   beside `compose.yml`. The private key is also a secret. Missing files stop the web container
   with a message naming them.

## Start and sign in

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 engine
```

The database initializes with the required collation. The engine creates or migrates its schema
and loads its bootstrap model. The web container waits for the engine's liveness check; a healthy
container can still be in maintenance mode. Check readiness separately:

```bash
curl --fail https://refiroo.example.org/health
```

Replace the example host with your own. Expect HTTP 200. For 503, read the bounded engine log and
follow [startup checks](/docs/run/health-and-startup-checks/) before opening traffic.

Create the first administrator; replace the example name:

```bash
docker compose run --rm engine python -m app.cli.create_admin \
  --username operator --name "Installation administrator"
```

Enter the password twice when prompted. It needs at least 15 characters by default, at most 128,
and must satisfy the password rules. A refusal explains why nothing was created. Open `PUBLIC_URL`
and sign in. This administrator starts with the roles needed to set up the instance and keeps
local sign-in available for recovery. Hand out narrower access as people take over:
[People and groups](/docs/administer/people-and-groups/) and [Roles and grants](/docs/administer/roles-and-grants/).

## Preserve the installation

Keep the `database` and `job-files` volumes. The latter holds imports, exports and model-authoring
source files. Set up [backups](/docs/run/backup-and-restore/) before loading important data.
Only `web` should be public; the engine trusts the caller address it forwards.

For another settings file, set `RDM_ENV_FILE` to its path and use Compose's `--env-file` with the
same file on every invocation. This supplies both Compose's substitutions and the engine's environment.
When using the automatic HTTPS overlay, keep both `-f` arguments on later commands too.
The overlay uses Compose's `!reset` syntax; use a Compose version that supports it.

The images keep application files under `/opt/refiroo/rdm-engine`. The engine runs from
`backend/`; its bootstrap model is `model/rdm-starter.json`, its built documentation is `guide/dist`,
and the persistent job volume is mounted at `data/job-files` beneath that directory.
The web image mounts certificates at `frontend/certs`. Use these paths for custom mounts;
mounting a volume at an old path leaves the actual job files unprotected.

## Check the host before starting

You need access to the version's complete source tree, a shell allowed to use Docker, and a
private place for settings and backups. Docker must be able to download base images and build
dependencies. PostgreSQL 17, Python 3.14 and Node 22 are supplied by the images; you do not install
them on the production host. A minimum host CPU, memory and disk size has **not been measured**.
Allow storage for the database, retained uploads and downloads, image builds and backup copies.

```bash
docker version
docker compose version
docker compose config --quiet
```

The first two commands must report installed client/server and Compose versions. The last command
is run **after** filling `.env`; success has no output and exit status 0. It checks Compose input,
not database readiness. The automatic-certificate overlay requires Compose support for `!reset`;
this guide does not establish a tested minimum Docker or Compose version. If the parser rejects
that tag, update Compose before using the overlay.

Allow inbound TCP 80 and 443 to the entry service. Keep 5432 (PostgreSQL) and 8000 (engine)
unpublished. DNS must resolve the public name to the installation or its HTTPS balancer.
See the [network and storage inventory](/docs/run/overview/#network-and-storage).

## Read the installation settings file

These are the installation-specific lines above the generated engine catalogue in `.env.example`.
A commented line uses its default; an empty required secret must be filled before Compose starts.

| Line | Default; secret? | What to supply or change |
| --- | --- | --- |
| `PUBLIC_URL` | Example address only; no | Your permanent HTTPS origin, without path or trailing slash. |
| `POSTGRES_PASSWORD` | Required; yes | Generated password used when PostgreSQL first initializes its volume. |
| `SECRETS_ENCRYPTION_KEY` | Required; yes | The sealing key retained for the life of the stored secrets. |
| `RDM_CURSOR_SIGNING_KEY` | Required by Compose; yes | A stable cursor key, shared by every engine process. |
| `WEB_TLS` | `files`; no | `files` for mounted certificates; `proxy` behind an HTTPS terminator. |
| `WEB_TRUSTED_PROXIES` | Empty; no | In proxy mode, addresses or ranges the web service trusts for caller addresses. |
| `WEB_CERTS_DIR` | `./certs`; private key inside | Host directory containing the certificate chain and private key. |
| `WEB_HTTP_PORT` | `80`; no | Host port forwarded to web port 8080. |
| `WEB_HTTPS_PORT` | `443`; no | Host port forwarded to web port 8443 in certificate mode. |
| `WEB_MAX_BODY` | `256m`; no | nginx request-body ceiling; the engine applies its limits afterwards. |

The generated portion groups the other engine settings into Runtime, Capability groups, Batch and
job limits, Webhook subscriptions and AI proposals. Comments explain each line; uncommenting it
sets an override. The [settings reference](/docs/run/configure/) gives the defaults and when to
change them. AI and agent settings have their own [operator pages](/docs/run/ai/).

`RDM_ENV_FILE` is a Compose input rather than an engine setting. For an existing alternate private
file, use the same selection on **every** command:

```bash
RDM_ENV_FILE=./production.env docker compose --env-file ./production.env config --quiet
RDM_ENV_FILE=./production.env docker compose --env-file ./production.env up -d --build
```

Do not print expanded `docker compose config` into a support report: it can contain secrets.
Compose's required-variable messages include `Set POSTGRES_PASSWORD in .env (see .env.example)`,
`Set SECRETS_ENCRYPTION_KEY in .env (see .env.example)`,
`Set RDM_CURSOR_SIGNING_KEY in .env (see .env.example)` and
`Set PUBLIC_URL in .env (see .env.example)`. Fill the named value in the selected file and repeat
`config --quiet` before starting containers.

## Check the first browser session and stop safely

After readiness succeeds, open the public origin and sign in with the new administrator. The home
page lists workspaces this person may browse; open one and confirm its applications load. A missing
workspace can be an access or model-readiness problem; inspect Operations and grants before
changing the bootstrap file. This checks a real session as well as the unauthenticated health probe.

If the administrator command says `The passwords differ; nothing was created.`, repeat it and enter
the same password twice. `Created administrator 'operator' (...)` confirms creation; the value in
parentheses is that person's ID. Keep the initial setup account available until another authorised
administrator has successfully signed in.

To pause a newly installed instance without removing its stored state:

```bash
docker compose stop
```

To resume, use `docker compose up -d`. Do not remove the named volumes to repair a startup failure:
that discards the database and job files. Correct the named setting, certificate or database problem,
then start again and repeat readiness and sign-in checks. Deleting production data is not an
installation rollback; recovery uses the [matching backup](/docs/run/backup-and-restore/).
