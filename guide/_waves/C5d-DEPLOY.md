# C5d: "Deploy to production with Docker", step by step

Read `guide/AGENTS.md`. Reader: an operator deploying refiroo on a server of their own organisation and
maintaining it themselves, from the page alone.

The person who owns refiroo asked for one page, not two: `run/install-with-compose.md` becomes the
step-by-step production deployment, titled "Deploy to production with Docker" (keep its slug; change its
sidebar label in `sidebar/run.mjs`). Keep everything right on it today; `run/https.md`,
`run/backup-and-restore.md`, `run/upgrades.md` and `run/configure.md` stay the detail it links to. General
for any operator: the example host is `refiroo.example.org`; name no version ("the tag of the version you
run"); no troubleshooting section (link `run/troubleshooting.md`).

Steps, in this order, each with the exact commands and what they print when they work:

1. **Before you start:** a Linux server with Docker and Docker Compose 2.24 or newer (`docker compose
   version`; `compose.acme.yml` uses `!reset`), a DNS name pointing at it, inbound ports 80 and 443 (keep
   today's wording on ports), `git` and `openssl`.
2. **Get the source at a tag, never a moving branch:**
   `git clone https://github.com/refiroo/refiroo.git /opt/refiroo/refiroo && cd /opt/refiroo/refiroo &&
   git checkout v<version>`. Why the tag: About, `GET /system` and the default `SOURCE_CODE_URL`
   (`backend/app/config.py`: `https://github.com/refiroo/refiroo/tree/v{ENGINE_VERSION}`) name the version
   you run; an upgrade checks out the next tag.
3. **When the repository is private: a GitHub App with a short-lived token** (a public repository is simply
   cloned; present this step as optional, for that case). Create the App in the organisation's settings,
   `https://github.com/organizations/<org>/settings/apps/new` (personal account:
   `https://github.com/settings/apps/new`): Webhook "Active" unticked; Repository permissions: Contents
   Read-only, nothing else; "Only on this account". Note the Client ID, generate a private key (.pem),
   Install App › Only select repositories › the repository; the installation ID is the number at the end of
   the address after installing; the repository's Settings › GitHub Apps then lists it. On the server:
   `sudo mkdir -p /opt/refiroo && sudo chown "$USER" /opt/refiroo`; the key at `/opt/refiroo/github-app.pem`,
   `chmod 600`. The token script `/opt/refiroo/github-app-token`, `chmod 700`, exactly:

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

   Check: `/opt/refiroo/github-app-token | cut -c1-8` prints `ghs_` and the start of the token; a token
   lasts an hour. Have git ask for a fresh one on every fetch, nothing stored in the remote address:
   `git config --global credential.https://github.com.helper '!f() { echo username=x-access-token; echo "password=$(/opt/refiroo/github-app-token)"; }; f'`.
   Keep the .pem with the .env backups; if the key leaks, delete it on the App's page and generate a new one.
4. **Fill `.env` without editing it by hand:**

   ```bash
   cp .env.example .env && chmod 600 .env
   sed -i "s|^PUBLIC_URL=.*|PUBLIC_URL=https://refiroo.example.org|" .env
   sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$(openssl rand -base64 24 | tr -d '/+=\n')|" .env
   sed -i "s|^SECRETS_ENCRYPTION_KEY=.*|SECRETS_ENCRYPTION_KEY=$(openssl rand -base64 32 | tr '+/' '-_')|" .env
   sed -i "s|^RDM_CURSOR_SIGNING_KEY=.*|RDM_CURSOR_SIGNING_KEY=$(openssl rand -base64 32)|" .env
   grep -E '^(PUBLIC_URL|POSTGRES_PASSWORD|SECRETS_ENCRYPTION_KEY|RDM_CURSOR_SIGNING_KEY)=' .env
   ```

   Then copy `.env` off the server; say which values are secrets and why losing `SECRETS_ENCRYPTION_KEY`
   matters (link `run/secrets-and-keys.md`).
5. **Start with automatic HTTPS (Let's Encrypt):** set the overlay once so later commands need no `-f`:
   `echo 'export COMPOSE_FILE=compose.yml:compose.acme.yml' >> ~/.bashrc && source ~/.bashrc`; then
   `docker compose up -d --build`, `docker compose ps`, `docker compose logs -f caddy` (wait for
   "certificate obtained successfully"), `curl -sS https://refiroo.example.org/health/live`. `COMPOSE_FILE`
   is a shell setting, not an `.env` value: `compose.yml` passes every `.env` value to the engine.
6. **The first administrator** (as the page says today), then people under Settings › Security › People with
   one-time password links (check the exact labels in `frontend/src/`); the documentation is at `/docs`
   (not `/guide`); AI and agent access stay off until switched on (link `run/set-up-ai.md`).
7. **The first backup, and one before every upgrade:**

   ```bash
   mkdir -p ~/refiroo-backups && cd /opt/refiroo/refiroo
   docker compose exec -T database pg_dump -U rdm -Fc --exclude-table-data=engine_processes rdm > ~/refiroo-backups/rdm-$(date +%Y%m%d-%H%M).dump
   docker run --rm -v refiroo_job-files:/files -v ~/refiroo-backups:/out alpine tar czf /out/job-files-$(date +%Y%m%d-%H%M).tgz -C /files .
   ```

   Off the server: both files and `.env`. The volume is `refiroo_job-files` because `compose.yml` says
   `name: refiroo`. Restoring: link `run/backup-and-restore.md`.
8. **Upgrade:** the backup of step 7, then `git fetch --tags && git checkout v<next> && docker compose up -d
   --build`; the engine migrates the database at start. There is no downgrade: to go back, restore the
   backup with the old tag. Link `run/upgrades.md`.

Check every command, path, setting and label against the repository (`compose.yml`, `compose.acme.yml`,
`caddy/Caddyfile`, `.env.example`, `backend/app/cli/`, `docs/OPERATIONS.md`); report anything that does not
hold instead of writing it. Do not state that port 443 alone is enough for the certificate: that is not yet
confirmed.

## Files you may edit

- `src/content/docs/run/install-with-compose.md`
- `sidebar/run.mjs`

## Report

The page's steps, and anything in the repository that disagreed with the brief.
