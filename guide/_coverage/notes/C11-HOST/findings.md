# C11-HOST: the run pages' commands on a clean host (DOC11, 2026-11-08)

A fresh copy of the checkout and a clone from the page's own URL, Compose project `refiroo-rehearsal`
(own volumes, ports 8580/8543), own-certificate HTTPS for `localhost` (the Caddy path needs a public DNS
name). Old version for the upgrade: `v0.16.1-alpha.1`, because `v0.16.0` does not build (finding 1); new
version: the working tree. Everything was removed afterwards.

| Page | Run | Worked | Differ | Not run |
| --- | --- | --- | --- | --- |
| install-with-compose | 33 | 25 | 8 | 10 |
| configure | 1 | 1 | 0 | 0 |
| secrets-and-keys | 6 | 6 | 0 | 1 |
| https | 11 | 10 | 1 | 5 |
| sign-in-and-mail-setup | 4 | 2 | 2 | 0 |
| health-and-startup-checks | 5 | 5 | 0 | 0 |
| command-line | 13 | 13 | 0 | 2 |
| backup-and-restore | 16 | 16 | 0 | 4 |
| upgrades | 11 | 11 | 0 | 0 |
| model-releases-and-rollback | 3 | 3 | 0 | 0 |
| database | 11 | 11 | 0 | 2 |
| monitoring | 4 | 4 | 0 | 0 |
| troubleshooting | 11 | 11 | 0 | 0 |
| production-checklist | 7 | 7 | 0 | 0 |
| several-processes | 3 | 3 | 0 | 0 |
| **Total** | **139** | **128** | **11** | **24** |

## Findings

1. **Blocks (product, release).** `/docs/run/install-with-compose/`: `git checkout v0.16.0` then
   `docker compose up -d --build` fails: `dockerfile parse error on line 61: unknown instruction:
   AI_AGENT_FOLDERS=/data/assistant`. The tag's `backend/Dockerfile` ends with two stray lines of an `ENV`
   instruction after `CMD`. `v0.16.1-alpha.1` and the current code build. A tag cannot be changed: pages
   must not name `v0.16.0` as the version to check out.
2. **Costs time.** install-with-compose step 7, the job-file backup (`docker run ... -v
   refiroo_job-files:/files ... alpine tar czf ...`): with another project name the volume is
   `<project>_job-files`; Docker silently creates an empty `refiroo_job-files`, `tar` exits 0 and writes an
   87-byte archive. The page states the assumption but gives no check (the `tar -tf` listing is only on
   backup-and-restore). The install page's `.tgz` through Alpine also differs from backup-and-restore's
   plain `.tar` through the engine image (restore accepts both): one way would be clearer.
3. **Costs time.** No page shows the own-certificate path for a test install: making a self-signed
   certificate (`openssl req -x509 ... -addext subjectAltName=DNS:localhost`), uncommenting the port lines
   in `.env`, that `PUBLIC_URL` carries the port (`https://localhost:8543`, works), and a check that key and
   certificate match.
4. **Costs time.** `create_client --role data-owner` → `Not created: Role 'data-owner' not found.` The pages
   name roles as the screens do ("Data owner"); the keys (`reader`, `contributor`, `steward`, `owner`,
   `model-admin`, `workspace-admin`, `integration-admin`, `operator`, `security-admin`, `agent`) appear
   nowhere but `operator`. Found via `GET /api/v1/roles` with a `security-admin` client.
5. **Costs time.** sign-in-and-mail-setup's client-credentials example uses `http://localhost:8000`, which
   a Compose install does not publish (the public origin works; one sentence says so). Getting
   `ACCESS_TOKEN` is left to the reader. No operator page shows a first write without a browser.
6. **Small.** The four `sed -i` lines of install step 4 fail with BSD sed (macOS): `sed -i ''` needed. The
   page says Linux.
7. **Small (product).** `create_admin` without a terminal ends in an `EOFError` traceback from `getpass`;
   `--password-stdin` (only on command-line) works. A second run prints `Not created: Another person has
   this username.`, exit 2, as the page says.
8. **Small.** `docker compose up -d --build` with closed standard input fails: `failed to execute bake:
   read |0: file already closed` (Compose 2.39.2, buildx 0.28); builds with `</dev/null`. A scheduled job may
   hit it; the page mentions scheduled jobs.
9. **Small.** backup-and-restore, replacement host step 4 (`run --rm --no-deps -T engine python -c ...`)
   starts an image build in a fresh project; the page does not say so.
10. **Small.** https: the Caddy validation command uses `exec -T caddy ...`, which needs a running Caddy;
    `run --rm --no-deps -T caddy caddy validate ...` works (`Valid configuration`).
11. **Small.** upgrades: the upgrade created an `assistant-claude` volume the older checkout lacked; the
    kept-volumes list does not mention it.
12. **Small.** monitoring gives no command for a first scrape test. Inside the engine container,
    `GET http://engine:8000/metrics` with a token gave `rdm_process_ready{...} 1`; the public `/metrics` is
    404 (also with a token), as the https page's check expects. JSON log fields have a space after each
    comma, unlike the page's sample.
13. **Small (product).** `generate_key --help` prints a key and `database_upgrade --help` migrates: both
    ignore their arguments. The command-line page recommends `--help`.

## Not run

`sudo mkdir /opt/refiroo`; the GitHub App commands (private repository); `echo ... >> ~/.bashrc`; `logs -f
caddy` and the Caddy HTTP/HTTPS checks and `openssl s_client` (no public name); the `RDM_ENV_FILE`
commands; `psql \password` (needs a terminal); the host-side backup block and `settings_template --for dev`
(developer path); external-database `CREATE DATABASE`/`CREATE EXTENSION`; browser steps (sign-in, Settings
pages, passkeys, real mail).

## Worked (summary)

Tool checks, clone, `.env`, `config --quiet`, health probes; configure (`LOG_FORMAT=json` shown with source
`environment`); secrets `--check`, export, reseal; own-certificate HTTPS (301 to HTTPS, 200s, HSTS,
`nosniff`, `Referrer-Policy: same-origin`, `frame-ancestors 'none'`, `X-Frame-Options: DENY`); every
command-line tool; backup and replacement-host restore (`restore_check`: `Backup rehearsal passed.`;
refuses the live database, exit 2); upgrade (`Database migration completed successfully.`); all database
checks; `WEB_CONCURRENCY=2`; the production checklist's public checks.
