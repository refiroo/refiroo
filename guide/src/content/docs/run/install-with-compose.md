---
title: Deploy to production with Docker
description: Deploy from a source tag, get automatic HTTPS, create your administrator, back up and upgrade.
reader: operator
---

Deploy refiroo on your organisation's Linux server with Docker Compose. This walkthrough builds
the application from the tag of the version you run and uses Caddy 2 to obtain and renew public
HTTPS certificates. Replace `refiroo.example.org` with your own host name throughout.

## 1. Before you start

You need a Linux server, Docker Engine, **Docker Compose 2.24 or newer**, `git`, `openssl` and
`curl`. Use Bash for the commands below, with an account allowed to run Docker and `sudo`.
Check the installed tools:

```bash
docker version
docker compose version
git --version
openssl version
curl --version
```

Expect Docker's **Client** and **Server** details, `Docker Compose version` followed by its
version, `git version`, `OpenSSL` and curl's version information. The automatic HTTPS overlay uses
Compose's `!reset` syntax to remove the web container's published ports and certificate mounts.
Docker must be able to download base images and build dependencies.

Point a public DNS name at this host, including any published IPv6 address. Allow inbound TCP 443 to the entry service. Port 80 is optional: open it only if you want
HTTP requests redirected to HTTPS. Certificate issuance and renewal can use TLS-ALPN on 443 alone. Keep 5432 (PostgreSQL) and 8000 (engine) unpublished. DNS must resolve
the public name to the installation or its HTTPS balancer. For this walkthrough Caddy is the entry
service, and nothing else may occupy ports 80 and 443. See the
[network and storage inventory](/docs/run/overview/#network-and-storage).

The images supply PostgreSQL 17, Python 3.14 and Node 22; you do not install them on the host.
A minimum host CPU, memory and disk size has **not been measured**. Allow storage for the database,
retained uploads and downloads, image builds and backup copies.

## 2. Get the source at a tag

Prepare a directory owned by your deployment account:

```bash
sudo mkdir -p /opt/refiroo && sudo chown "$USER" /opt/refiroo
```

Success produces no output. For a public repository, clone directly. **If the repository is
private, complete step 3 before running the clone.** Replace `v<version>` below with the tag of the
version you intend to deploy; do not type the angle brackets.

```bash
git clone https://github.com/refiroo/refiroo.git /opt/refiroo/refiroo && cd /opt/refiroo/refiroo && git checkout v<version>
```

Expect `Cloning into '/opt/refiroo/refiroo'...`, download progress and a checkout message such as
`HEAD is now at` followed by a commit. Git may explain that you are in a detached HEAD state;
that is expected when running a tag.

Changes listed as Unreleased in the source changelog need a version that contains them.

Use a tag rather than a moving branch. **About**, the system API's `GET /api/v1/system` response
and the default `SOURCE_CODE_URL` point to the source for the running engine version:
`https://github.com/refiroo/refiroo/tree/v<version>`. An upgrade checks out the next tag. If you run
modified source, set `SOURCE_CODE_URL` to your corresponding source, including those changes;
see [Licence and source](/docs/run/licence-and-source/).

Run later Compose commands from `/opt/refiroo/refiroo`.

## 3. For a private repository: use a GitHub App

Skip this step for a public repository. A GitHub App gives this server read access to the selected
repository using a short-lived token. You need permission to create and install the App in the
account that owns that repository.

1. Open `https://github.com/organizations/<org>/settings/apps/new`, replacing `<org>` with the
   organisation. For a personal account, use `https://github.com/settings/apps/new`.
2. Choose a unique **GitHub App name** and a **Homepage URL**, such as your organisation's site.
   Under **Webhook**, untick **Active**. Under **Repository permissions**, set **Contents** to
   **Read-only**. Request no other permissions; GitHub includes its required read-only metadata
   permission. Under **Where can this GitHub App be installed?**, choose **Only on this account**,
   then **Create GitHub App**.
3. Note the **Client ID**. Under **Private keys**, choose **Generate a private key** and keep the
   downloaded `.pem` file private.
4. Open **Install App**, install it on the repository's account and choose **Only select
   repositories**. Select the repository and install. The installation ID is the number at the
   end of the address after installing. The repository's **Settings › GitHub Apps** then lists it.
5. On the server, prepare the directory if you have not already done so:

   ```bash
   sudo mkdir -p /opt/refiroo && sudo chown "$USER" /opt/refiroo
   ```

   Securely transfer the private key to `/opt/refiroo/github-app.pem`, then restrict it:

   ```bash
   chmod 600 /opt/refiroo/github-app.pem
   ```

   Both commands are silent on success. Only your deployment account should read the key.
6. Save the following script as `/opt/refiroo/github-app-token`, replacing the two placeholders.
   If the private repository has a different name, replace `refiroo` in `repositories` too.

   ```bash
   #!/usr/bin/env bash
   set -euo pipefail
   CLIENT_ID="<Client ID>"
   INSTALLATION_ID="<installation ID>"
   KEY=/opt/refiroo/github-app.pem
   b64() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
   now=$(date +%s)
   header=$(printf '{"alg":"RS256","typ":"JWT"}' | b64)
   payload=$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' $((now-60)) $((now+540)) "$CLIENT_ID" | b64)
   sig=$(printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -sign "$KEY" | b64)
   curl -fsS -X POST \
     -H "Authorization: Bearer $header.$payload.$sig" \
     -H "Accept: application/vnd.github+json" \
     -d '{"repositories":["refiroo"],"permissions":{"contents":"read"}}' \
     "https://api.github.com/app/installations/$INSTALLATION_ID/access_tokens" \
     | grep -o '"token": *"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/'
   ```

7. Make it executable and check only the token's first eight characters:

   ```bash
   chmod 700 /opt/refiroo/github-app-token
   /opt/refiroo/github-app-token | cut -c1-8
   ```

   Expect `ghs_` followed by the start of the token. A token lasts one hour. The script signs a
   short-lived request with the private key; the server's clock must be accurate.
   See GitHub's [installation token documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app).
8. Have Git request a fresh token when it needs credentials, without storing a token in the remote
   address:

   ```bash
   git config --global credential.https://github.com.helper '!f() { echo username=x-access-token; echo "password=$(/opt/refiroo/github-app-token)"; }; f'
   ```

   Success is silent. This changes the deployment account's GitHub credential helper; use a
   dedicated deployment account so it does not affect unrelated checkouts. Existing credential
   helpers or cached credentials can satisfy a request first. Return to step 2 and clone using
   the repository's HTTPS address, replacing the owner if your private repository uses another one.

Keep the `.pem` securely with the `.env` backups described below. If it leaks, delete that key on
the App's page, generate a new one and replace the server copy.

## 4. Fill the settings file

Choose the permanent HTTPS origin, without a path or trailing slash. It is the token issuer,
where sign-in returns to and the host passkeys belong to. Changing its host later signs people
out and makes their existing passkeys unusable there.

From `/opt/refiroo/refiroo`, create `.env` and fill the four required values without editing it by
hand. **Run this only for a new installation**: repeating it replaces existing settings and keys.

```bash
cp .env.example .env && chmod 600 .env
sed -i "s|^PUBLIC_URL=.*|PUBLIC_URL=https://refiroo.example.org|" .env
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=\n')|" .env
sed -i "s|^SECRETS_ENCRYPTION_KEY=.*|SECRETS_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')|" .env
sed -i "s|^RDM_CURSOR_SIGNING_KEY=.*|RDM_CURSOR_SIGNING_KEY=$(openssl rand -base64 32)|" .env
grep -E '^(PUBLIC_URL|POSTGRES_PASSWORD|SECRETS_ENCRYPTION_KEY|RDM_CURSOR_SIGNING_KEY)=' .env
```

These substitutions use GNU `sed` on Linux. On macOS, use `sed -i ''` in place of
`sed -i` on each of the four lines.

The copy and substitutions are silent. The final command prints four lines: `PUBLIC_URL` with
your address, then three different non-empty secret values. Inspect them privately; do not paste
the output into logs or a support report.

`POSTGRES_PASSWORD`, `SECRETS_ENCRYPTION_KEY` and `RDM_CURSOR_SIGNING_KEY` are secrets. Never commit
`.env` or bake it into an image. The database password initializes a new database; editing it
later does not change an existing PostgreSQL role's password. Losing `SECRETS_ENCRYPTION_KEY`
makes stored signing keys, webhook keys and second-factor secrets unreadable. Keep the cursor key
stable across restarts and shared by all engine processes.

Copy `.env` off the server into protected backup storage now. Keep the encryption key outside the
database backup, with access controlled separately. See [Secrets and keys](/docs/run/secrets-and-keys/).

To enable the assistant, follow [Set up AI](/docs/run/set-up-ai/); Compose sets its API address
to `http://127.0.0.1:8000` inside the engine container unless you override `AI_AGENT_API_URL`.

## 5. Start with automatic HTTPS

The `compose.acme.yml` overlay adds **Caddy 2**, which obtains and renews public certificates using
**ACME**, normally from **Let's Encrypt**, with **ZeroSSL** also available through Caddy's default
issuer configuration. It needs no `certs/` directory. Keep Caddy's `caddy-data` volume: it holds
certificates and the certificate-authority account. Repeatedly discarding it can lead to issuance
limits. For your own certificates or an HTTPS load balancer, follow [Serve over HTTPS](/docs/run/https/)
instead of this step.

Set the overlay selection once in your deployment account's Bash configuration, then load it:

```bash
echo 'export COMPOSE_FILE=compose.yml:compose.acme.yml' >> ~/.bashrc && source ~/.bashrc
docker compose config --quiet
```

These commands normally print nothing and exit 0. `config --quiet` validates the merged Compose
input after `.env` is filled. If it rejects `!reset`, update Compose before continuing. If it names
an empty required value, fill that value in `.env`. Do not print expanded `docker compose config`
into a support report: it can expose secrets.

`COMPOSE_FILE` is a **shell setting**, not an `.env` value: `compose.yml` passes every `.env` value
to the engine. Keep it in your shell, and run commands from the repository root. New interactive
Bash shells read `~/.bashrc`; for a scheduled job or another shell, explicitly export
`COMPOSE_FILE=compose.yml:compose.acme.yml` there too.

:::caution[Every later command needs both Compose files]
From now on, every `docker compose` command must use both `compose.yml` and `compose.acme.yml`:
upgrades, restores, configuration changes, backups and scheduled jobs included. A command such as
`docker compose up -d` run without `compose.acme.yml` recreates web in its own-certificate mode.
It then competes with the still-running Caddy for ports 80 and 443, or refuses to start without
`./certs`, and the site stops answering until you run the command again with both files.
Certificates also renew only while Caddy runs. The certificates in `caddy-data` are not lost.
:::

In a scheduled job, give Compose an open input stream: append `</dev/null` to the startup
command if the runner closes standard input. Some Compose/buildx versions fail the build
with `read |0: file already closed` otherwise. This is separate from supplying the settings file.

Start the installation:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f caddy
```

The build prints download and build progress, followed by container creation and startup. The
database initializes with the required collation. The engine creates or migrates its schema and
loads its bootstrap model. The web container waits for the engine's liveness check, and Caddy waits
for web.

`ps` lists `database`, `engine`, `web` and `caddy` as running. After their checks finish, the first
three show `healthy`; Caddy has no container health check. Only Caddy publishes ports 80 and 443;
web, the engine and PostgreSQL stay private. Keep it this way: the engine trusts the caller
address forwarded by web.

In Caddy's log, wait for **`certificate obtained successfully`** for your host. Press **Ctrl+C**
to leave the log view; this does not stop the containers. Then check the HTTPS address:

```bash
curl -sS https://refiroo.example.org/health/live
curl --fail -sS https://refiroo.example.org/health
```

Both successful responses contain `{"status":"ok"}`. Liveness means only that the process
answers; a healthy container can still be in maintenance mode. The second command checks
readiness and must succeed before you continue. For a readiness failure, follow
[Health and startup checks](/docs/run/health-and-startup-checks/). For other failures, use
[Troubleshooting](/docs/run/troubleshooting/).

## 6. Create the first administrator and sign in

Replace the e-mail address and display name as needed:

```bash
docker compose run --rm engine python -m app.cli.create_admin \
  --email operator@example.org --name "Installation administrator"
```

The command asks `Password:` and `Password again:`. Enter the same password twice. It needs at
least 15 characters by default, at most 128, and must satisfy the password rules. Without
a terminal, the command refuses with `No terminal to ask for the password: pipe it with
--password-stdin.` and exits 2. Use `docker compose run --rm -T engine` with
`--password-stdin` and pipe one password line from your protected secret source; see
[Command-line tools](/docs/run/command-line/). On success,
expect:

```text
Created administrator 'operator' (<person ID>).
```

The value in parentheses is the new person's ID. A refusal explains why nothing was created.
If it says `The passwords differ; nothing was created.`, repeat the command and enter the same
password twice.

Open `https://refiroo.example.org` and sign in. This administrator starts with the roles needed
to set up the instance and keeps local password sign-in available for recovery. Keep the account
available until another authorised administrator has successfully signed in.

Check that the home page lists the workspaces this person may browse. Open one and confirm its
applications load. A missing workspace can be an access or model-readiness problem: inspect
Operations and grants before changing the bootstrap file. This checks a real session as well as
the unauthenticated health probe.

Add other people through **Settings › People and access › People**:

1. Select **New person**. Fill **Name** and **E-mail**, the address they sign in with.
2. Select **Create and make a password link**. The **Pass on the password link** dialog shows a
   **Password link** once. Copy it, pass it privately to that person and select **I have copied it**.
   The person uses it to set their own password; the link works once, until the displayed expiry.
3. Grant the person the roles they need on their page. A new person has no roles yet. Prefer
   narrower access to sharing the setup administrator's account.

For the full access workflow, see [People and groups](/docs/administer/people-and-groups/) and
[Roles and grants](/docs/administer/roles-and-grants/). To mail password links or use your
organisation's sign-in provider, follow [Set up sign-in and mail](/docs/run/sign-in-and-mail-setup/).

The documentation is at `https://refiroo.example.org/docs/`; its API reference is at `/docs/api`.
AI proposals and agent access stay off until you enable them. See [Set up AI](/docs/run/set-up-ai/).

## 7. Take the first backup

Take a backup before loading important data and before every upgrade. Protect both PostgreSQL
and `job-files`: the latter holds imports, exports and model-authoring source files. A database
dump alone does not protect those files. The `assistant` volume holds each task's working files,
Claude Code configuration, transcripts and turn logs in its own randomly named folder. A backup
may omit this volume: losing it loses open tasks’ folders and session logs, not records. The
backup commands below omit it.

Pause traffic and integrations that write. Stop the engine so its workers cannot change or clean
up files between the two copies; leave PostgreSQL running:

```bash
mkdir -p ~/refiroo-backups && cd /opt/refiroo/refiroo
chmod 700 ~/refiroo-backups
umask 077
docker compose stop engine
```

The directory and permission commands are silent. Compose reports the engine stopped. Then take
the matching pair:

```bash
docker compose exec -T database pg_dump -U rdm -Fc --exclude-table-data=engine_processes rdm > ~/refiroo-backups/rdm-$(date +%Y%m%d-%H%M).dump
docker compose run --rm --no-deps -T engine python -c \
  'import sys,tarfile; t=tarfile.open(fileobj=sys.stdout.buffer,mode="w|"); t.add("/opt/refiroo/rdm-engine/data/job-files",arcname="."); t.close()' > ~/refiroo-backups/job-files-$(date +%Y%m%d-%H%M).tar
```

`pg_dump` normally prints nothing; it must exit 0. The archive command uses the engine
service’s configured job-file mount and finishes silently with exit 0. Stop on either failure; a file left by
a failed command is not a completed backup. The minute in each filename is the time that command
ran, so record which two files belong together. Do not repeat a backup in the same minute: its
filename would be reused.

Keep the same Compose project name and files as the running installation: the commands
then use its mounts even when the project is not named `refiroo`. Inspect the archive before
copying it away, replacing `YYYYMMDD-HHMM` with the timestamp of the file just created:

```bash
tar -tf ~/refiroo-backups/job-files-YYYYMMDD-HHMM.tar
```

Expect `.` and relative paths for stored job files; a new installation can have only `.`.
If files should exist but the archive is empty, check the project and mounts before relying
on it. Keep the database volume too; do not remove named volumes to repair a startup problem.

Copy **both files and `.env` off the server** into protected backup storage. Record the source tag
with the pair and retain any GitHub App private key, custom model files and TLS materials needed
to recover the installation. With automatic HTTPS, also preserve `refiroo_caddy-data` through
your storage backup process. Keep encryption keys separately controlled outside the database dump.
Rehearse restoration before relying on the backup; follow [Back up and restore](/docs/run/backup-and-restore/).

If this is the first backup rather than an upgrade, resume the engine:

```bash
docker compose up -d engine
curl --fail -sS https://refiroo.example.org/health
```

Compose reports the engine started; wait for readiness to return `{"status":"ok"}` and check
sign-in before reopening writers. For an upgrade, keep writers paused and continue below.

The image versions and dependencies are pinned. To change those pins rather than take them from
a release, follow [Maintain build versions](/docs/run/upgrades/#maintain-build-versions).

## 8. Upgrade to the next tag

An upgrade keeps the named volumes: `database`, `job-files` and `assistant`, plus `caddy-data`
with automatic HTTPS. Keep the same Compose project name and mounts so open assistant tasks
retain their folders and session logs. When upgrading from the earlier shared-transcript layout,
existing files are kept but the next turn starts a new session. Follow
[Upgrades](/docs/run/upgrades/#volumes-and-open-assistant-tasks) for the obsolete transcript volume
and the private webhook receivers that need an operator setting before delivery resumes.

Read the target version's compatibility notes and rehearse it on a copy of your data. Take the
backup in step 7 first, keeping the old tag and matching configuration for recovery. Keep writers
paused and the old engine stopped. From `/opt/refiroo/refiroo`, replace `v<next>` with the next tag:

```bash
git fetch --tags && git checkout v<next> && docker compose up -d --build
```

Git reports any fetched tags and the checked-out commit; Compose prints build progress and the
containers it starts or recreates. A fetch with no new tags can be silent. The engine migrates
the database at startup. With private-repository access from step 3, Git can request a fresh App
token without changing the remote address.

Check the new deployment before reopening writers:

```bash
docker compose ps
docker compose logs --tail=100 engine
curl -sS https://refiroo.example.org/health/live
curl --fail -sS https://refiroo.example.org/health
```

Expect the same running services and `{"status":"ok"}` from both probes. Check sign-in, the
version in **About**, every active workspace and any integrations you rely on. A startup migration
failure leaves the engine in maintenance mode with readiness 503; use
[Health and startup checks](/docs/run/health-and-startup-checks/).

There is no supported database downgrade. To go back, stop the new deployment and restore the
pre-upgrade backup with the old tag and matching configuration. This restores the data as it was
at backup time. See [Upgrade refiroo](/docs/run/upgrades/) for explicit migration checks and
[Back up and restore](/docs/run/backup-and-restore/) for recovery.

## Database and upstream values in Compose

The following values are set directly in `compose.yml`, rather than selected from `.env`. To use
an external database or another engine address, adapt your deployment file deliberately; adding
these names to `.env` alone does not change the checked-in values.

| Value | Checked-in value | What it controls |
| --- | --- | --- |
| `POSTGRES_DB` | `rdm` | Database created when the PostgreSQL volume is first initialized. |
| `POSTGRES_USER` | `rdm` | PostgreSQL initialization account. The engine connection and database health check also use this name. |
| `POSTGRES_INITDB_ARGS` | `--locale-provider=icu --icu-locale=und --locale=C` | Creates a new database cluster with the ICU root collation required by the engine. |
| `ENGINE_UPSTREAM` | `http://engine:8000` | Private engine address nginx forwards API, documentation and health requests to. |

The PostgreSQL initialization values apply only to an empty database volume. Changing them does
not rename an existing database or role, change its password, or convert its collation. Preserve
the volume and use [database administration](/docs/run/database/) and a checked restore when
needed. If you customize names, update `DATABASE_URL` and the database health check together.
An incorrect upstream can leave web running while API requests fail; inspect web and engine logs
and check public readiness after recreating web. Keep the engine address private.

## Settings and paths for other installations

The walkthrough uses the automatic HTTPS overlay. These installation-specific lines in
`.env.example` also support other arrangements:

| Setting | Default; secret? | What to supply or change |
| --- | --- | --- |
| `PUBLIC_URL` | Example address only; no | Your permanent HTTPS origin, without path or trailing slash. |
| `POSTGRES_PASSWORD` | Required; yes | Password used when PostgreSQL first initializes its volume. |
| `SECRETS_ENCRYPTION_KEY` | Required; yes | The sealing key retained for the life of the stored secrets. |
| `RDM_CURSOR_SIGNING_KEY` | Required by Compose; yes | A stable cursor key, shared by every engine process. |
| `WEB_TLS` | `files`; no | `files` for mounted certificates; `proxy` behind an HTTPS terminator. The overlay selects `proxy`. |
| `WEB_TRUSTED_PROXIES` | Empty; no | In proxy mode, addresses or ranges web trusts for caller addresses. The overlay sets these for Caddy. |
| `WEB_CERTS_DIR` | `./certs`; private key inside | Directory with `fullchain.pem` and `privkey.pem` in file mode. The overlay removes this mount. |
| `WEB_HTTP_PORT` | `80`; no | Host port forwarded to web port 8080 without the overlay. |
| `WEB_HTTPS_PORT` | `443`; no | Host port forwarded to web port 8443 in certificate mode without the overlay. |
| `WEB_MAX_BODY` | `256m`; no | nginx request-body ceiling; the engine applies its limits afterwards. |

The automatic HTTPS overlay publishes Caddy on 80 and 443 directly; the two `WEB_*_PORT` settings
do not change its ports. For the generated engine settings below these lines, use
[Configure refiroo](/docs/run/configure/); AI settings also have their [operator pages](/docs/run/ai/).
A commented line uses its default; uncommenting it sets an override.

`RDM_ENV_FILE` is a Compose input, used to select an alternate private settings file. If you use
one, pass that same file to Compose for substitutions and to the engine on **every** invocation:

```bash
RDM_ENV_FILE=./production.env docker compose --env-file ./production.env config --quiet
RDM_ENV_FILE=./production.env docker compose --env-file ./production.env up -d --build
```

The validation command is silent on success; startup prints build and container progress.
Use this only with an existing, filled private file. Required-variable errors name the missing
setting: `POSTGRES_PASSWORD`, `SECRETS_ENCRYPTION_KEY`, `RDM_CURSOR_SIGNING_KEY` or `PUBLIC_URL`.
Fill it in the selected file and validate again.

The images keep application files under `/opt/refiroo/rdm-engine`, separate from the host checkout.
The engine runs from `backend/`; its bootstrap model is `model/rdm-starter.json`, its built
documentation is `guide/dist`. The engine’s named volumes mount at `data/job-files` (`job-files`),
`data/assistant` (`assistant`, task folders including Claude Code configuration and session logs)
under that image root. The web image mounts file-mode
certificates at `frontend/certs`. Use these paths for custom mounts; mounting a volume elsewhere
leaves the actual files unprotected.

To pause the installation without removing its stored state:

```bash
docker compose stop
```

Compose reports the containers stopped. Resume with `docker compose up -d`, which reports them
started, then repeat readiness and sign-in checks. Keep the named volumes; recovery uses the
[matching backup](/docs/run/backup-and-restore/).

`docker compose down` also keeps named volumes. Adding `-v` removes `database`, `job-files`,
`assistant`, plus `caddy-data` with the HTTPS overlay. That deletes records,
job files, assistant task folders and session logs, and Caddy’s certificates and account. Do not
use `docker compose down -v` to repair the installation.
