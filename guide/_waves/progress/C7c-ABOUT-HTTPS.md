
- 2026-11-04T02:40:31+01:00 — Finished `guide/src/content/docs/about/security-and-trust.md`. Explains automatic certificate issuance and renewal, the operator’s DNS, port and storage responsibilities, and the alternatives. No steering file present; no uncertainties.

- 2026-11-04T02:40:38+01:00 — Finished `guide/src/content/docs/about/how-it-is-built.md`. Kept the existing Caddy, ACME and certificate-authority explanation and linked automatic HTTPS directly to the operator page. No steering file present; no uncertainties.

- 2026-11-04T02:40:47+01:00 — Finished `guide/src/content/docs/run/overview.md`. Names automatic HTTPS as a deployment choice, explains issuance and renewal, and points to the overlay procedure and certificate/proxy alternatives. No steering file present; no uncertainties.

- 2026-11-04T02:40:58+01:00 — Finished `guide/src/content/docs/run/production-checklist.md`. Adds automatic HTTPS to the serving decision, with DNS, public ports and certificate-volume checks, while retaining supplied-certificate and balancer choices. No steering file present; no uncertainties.

- 2026-11-04T02:41:09+01:00 — Finished `guide/src/content/docs/run/https.md`. Opens with automatic issuance and renewal for a public name, the public-origin setting and overlay, before the existing procedures. No steering file present; no uncertainties.

- 2026-11-04T02:41:39+01:00 — Finished final review and validation of all five pages. `GUIDE_OUT=_build/C7c-ABOUT-HTTPS npm run build` passed (247 pages); checked that the changed pages were generated and the automatic-HTTPS section anchor exists. No steering file present; no screenshots needed, uncertainties or product defects found; live certificate issuance and renewal were not exercised. Build output is in `guide/_coverage/notes/C7c-ABOUT-HTTPS/build.log`.
