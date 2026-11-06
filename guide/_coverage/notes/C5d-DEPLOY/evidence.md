# C5d deployment evidence

Read guide/AGENTS.md and guide/_waves/C5d-DEPLOY.md in full. No earlier progress or wave steering file existed.

Checked compose.yml, compose.acme.yml, caddy/Caddyfile, .env.example, backend/app/cli/create_admin.py, backend/app/config.py (source URL), backend/app/main.py (health handlers), backend/Dockerfile, frontend/Dockerfile, frontend/src/features/security/PeoplePage.tsx (creation and password-link UI), targeted Deploying and backup sections of docs/OPERATIONS.md, and existing HTTPS, backup and upgrade guide pages.

- Project name refiroo gives refiroo_job-files. Overlay publishes only Caddy, on TCP 80 and 443; database and engine remain private. Caddy image has no healthcheck; do not claim all four containers healthy.
- Caddy config uses default certificate issuers: Let's Encrypt or ZeroSSL, not exclusively Let's Encrypt. Keep both inbound ports; no claim about 443 alone.
- Health live returns {"status":"ok"} even in maintenance. Also check /health readiness before sign-in and after upgrade.
- create_admin prompts Password: / Password again:, success Created administrator '<username>' (<public ID>). Password default minimum 15, maximum 128. Initial roles include setup roles and kept local sign-in.
- People: New person; Username, Name, E-mail (optional); Create and make a password link; Pass on the password link; I have copied it. New person has no roles until granted.
- Backup pair needs quiesced writers and engine stopped during database dump and file archive. Preserve caddy-data separately. Automatic startup migrations exist; no supported downgrade.
- Existing page's minimum Compose version was unspecified; brief requires 2.24+. Check overlay parsing using config --quiet, without printing secrets.
- Paths in images remain /opt/refiroo/rdm-engine, distinct from host checkout /opt/refiroo/refiroo. Preserve alternate environment selection and settings inventory.

External primary references checked for the new GitHub App instructions:
- https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app (Client ID recommended, RS256, iat -60, exp within ten minutes)
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app (one-hour lifetime; repository and permission restriction)
- https://docs.docker.com/reference/compose-file/merge/ (!reset clears ports/volumes)

Limits: no production deployment, real GitHub App installation or live certificate issuance performed. Validate shell syntax and local generation safely; do not run deployment commands or change Git configuration.

## Completed validation

- `GUIDE_OUT=_build/C5d-DEPLOY npm run build` in guide/: passed, 247 pages, 3.99 seconds. Build output retained in this notes folder. Two warnings concern files outside this wave: unsupported caddyfile highlighting in run/https.md (plain-text fallback) and a conflicting /404 route. Neither blocked the build; neither was changed.
- `node --check guide/sidebar/run.mjs`: passed.
- `git diff --check -- guide/src/content/docs/run/install-with-compose.md guide/sidebar/run.mjs`: passed.
- `python3 guide/_coverage/notes/C5d-DEPLOY/verify.py`: passed. Shell syntax for 20 Bash blocks after substituting the documented tag placeholders; prescribed App script exact match; in-memory openssl generation (database-safe password and two decoded 32-byte keys); 17 internal page links; sidebar and eight step headings; built HTML title and headings.
- Initial verifier regex incorrectly captured indented Markdown code fences; fixed the working-note checker and reran successfully. No page defect was involved.
- No screenshots needed for this command-led operator page. People UI details are checked against source; no browser visual claim.
- No live deployment, Git configuration mutation, real GitHub credentials, certificate issuance, backup, restore or upgrade exercised. No services or background processes started; the isolated build completed.

Brief/repository differences reported: `/system` is the router-relative shorthand for the actual `/api/v1/system`; Caddy supports ZeroSSL as well as Let's Encrypt and has no container healthcheck; backup consistency needs writers paused and engine stopped. The earlier page said minimum Compose version was unestablished; this wave uses the required 2.24+ prerequisite plus merged-input validation. Private authentication must precede the clone even though it is presented as step 3 after source selection. Existing page details retained in the walkthrough and final settings/path reference.
