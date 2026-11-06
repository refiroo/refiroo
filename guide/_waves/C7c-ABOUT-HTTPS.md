# C7c: automatic HTTPS as a feature

Read `guide/AGENTS.md`. Reader: evaluators and operators deciding whether refiroo is easy to run safely.

The person who owns refiroo asked whether automatic certificate renewal is documented as a feature. It is
documented as a procedure (`run/https.md`) and in one sentence on `about/how-it-is-built.md`, but never
presented as what it is for the reader: a public installation gets HTTPS by itself. Set `PUBLIC_URL` to its
name and start with `compose.acme.yml`; Caddy obtains a Let's Encrypt (or ZeroSSL) certificate over ACME
and renews it before it expires, with nothing to install, buy or remember; an organisation with its own
certificates or HTTPS proxy uses those instead.

- `about/security-and-trust.md`: in the part on HTTPS (today "Production installations need HTTPS…"), say
  that refiroo provides it automatically for a public name, and what remains the operator's (DNS pointing
  here, ports 80 and 443 reachable, keeping the certificate volume).
- `about/how-it-is-built.md`: keep its sentence; make sure it links to `run/https.md`.
- `run/overview.md` and `run/production-checklist.md`: name automatic HTTPS where the reader decides how to
  serve refiroo, linking `run/https.md`.
- `run/https.md`: open with one or two sentences saying what the reader gets (a certificate obtained and
  renewed by itself) before the procedure.

Sources: `docs/OPERATIONS.md` "Automatic HTTPS", `compose.acme.yml`, `caddy/Caddyfile`. Only what they show.

## Files you may edit

- `src/content/docs/about/security-and-trust.md`
- `src/content/docs/about/how-it-is-built.md`
- `src/content/docs/run/overview.md`
- `src/content/docs/run/production-checklist.md`
- `src/content/docs/run/https.md`

## Report

The pages changed.
