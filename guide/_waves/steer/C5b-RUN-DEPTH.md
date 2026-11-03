# Steering for C5b (from the person who owns refiroo, 2026-11-03)

**Name the concrete things.** The pages describe mechanisms generically and leave out the names an operator
recognises and searches for. Example: automatic HTTPS is Caddy getting and renewing a **Let's Encrypt** (or
ZeroSSL) certificate (`compose.acme.yml`, `caddy/Caddyfile`, the `caddy-data` volume; OPERATIONS.md
"Automatic HTTPS"), yet `run/https.md` never says Let's Encrypt. Go through every Run page and name what is
actually used, with its version where refiroo fixes one: Docker and Docker Compose, the images and their
base images, PostgreSQL (supported versions, collation), nginx in the web image, Caddy, Let's Encrypt /
ZeroSSL and the ACME HTTP challenge (ports 80 and 443, DNS must point here), Uvicorn and the Python version,
Prometheus metrics format, JSON logs, SMTP for mail, OpenID Connect providers for sign-in, WebAuthn passkeys,
TOTP authenticator apps, signing algorithms of the keys, webhook signatures. Take each name from the files
(`compose*.yml`, Dockerfiles, `caddy/`, `frontend/nginx/`, `backend/pyproject.toml`, `config.py`,
`THIRD_PARTY_NOTICES.md`); never name something refiroo does not use. Apply this from your next unit on, and
go back over the pages you already finished.
