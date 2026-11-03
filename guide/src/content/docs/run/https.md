---
title: Serve over HTTPS
description: Choose certificate files, automatic certificates, or a trusted HTTPS load balancer.
reader: operator
---

Serve the browser application and engine paths through one public HTTPS origin. Set `PUBLIC_URL`
to that origin before the first sign-in. The Compose reference installation keeps the engine and
database private; only the entry service publishes ports.

## Use your own certificates

The default `WEB_TLS=files` reads `fullchain.pem` and `privkey.pem` from `./certs`, mounted read
only. `WEB_CERTS_DIR` selects another host directory. Keep the private key secret and never commit it.

```bash
docker compose up -d --build
```

The web container redirects HTTP to `PUBLIC_URL`, serves HTTPS, and sends HSTS. Missing
certificate files refuse its start and name the files. Replace files before expiry and reload them:

```bash
docker compose restart web
```

Here a restart is sufficient because it reloads mounted files, rather than changed environment values.

## Get and renew public certificates automatically

Point the public name's DNS at the host and make ports 80 and 443 reachable from the internet.
Set `PUBLIC_URL`, then use the overlay:

```bash
docker compose -f compose.yml -f compose.acme.yml up -d --build
```

Caddy obtains and renews a certificate and redirects HTTP. No certificate directory is required.
The overlay makes `web` private and Caddy the only public service. Keep using both Compose files
for subsequent commands. Preserve `caddy-data`, which holds certificates and the authority account;
losing it forces fresh issuance, which certificate authorities rate limit.

If issuance fails:

```bash
docker compose -f compose.yml -f compose.acme.yml logs --tail=100 caddy
```

Check DNS and inbound ports first. A name known only inside your network cannot use this public
certificate flow. Use your organisation's certificate instead. An optional global email setting in
`caddy/Caddyfile` supplies an address for certificate-expiry notices.

## Put an HTTPS load balancer in front

Set `WEB_TLS=proxy`. The web container then serves HTTP on its internal port 8080 and uses the
balancer's `X-Forwarded-Proto`. Restrict its reachability to that balancer.
Set `WEB_TRUSTED_PROXIES` to the balancer's connecting addresses or ranges, comma separated.
Its default is empty: nobody's forwarded caller address is trusted. Then everyone appears to come
from the balancer and shares an address for sign-in throttling. A malformed range stops `web` at
startup with a message; correct the setting and recreate it.

The balancer must replace untrusted forwarded headers. Keep `PUBLIC_URL` as the external HTTPS
origin. Do not publish the engine directly: Compose sets `FORWARDED_ALLOW_IPS=*` because only the
private web service is supposed to reach it.

## Ports and uploads

| Setting | Default | When to change it |
| --- | --- | --- |
| `WEB_HTTP_PORT` | `80` | Host port for redirects, or HTTP behind your balancer. |
| `WEB_HTTPS_PORT` | `443` | Host port for TLS with certificate files. |
| `WEB_MAX_BODY` | `256m` | Maximum body accepted by web. Increase alongside `IMPORT_MAX_BYTES` for larger uploads. |

Custom proxies must forward the engine paths, including `/api`, `/oauth`, `/.well-known`, `/mcp`,
`/docs`, `/openapi.json` and `/health`. Job event streams must remain unbuffered and allow long-lived
responses. `/metrics` stays private. Check [readiness](/docs/run/health-and-startup-checks/) through
the public origin after any proxy change. Several instances also need [shared settings and storage](/docs/run/several-processes/).

## Check prerequisites and certificate files

You need the chosen public DNS name, access to its DNS and firewall rules, and either a certificate
and private key or a public name reachable by the certificate authority. Port 80 must reach the
HTTP entry and 443 the HTTPS entry unless an organisation's balancer owns those ports. The engine
and PostgreSQL do not need public ports. For certificate mode, place a certificate covering your
public host and its intermediate chain in `fullchain.pem`, and the matching private key in
`privkey.pem`. The web container runs unprivileged: both files must be readable by that container
user without exposing the private key to unrelated host users.

Before restarting a running web service, inspect the chain and expiry:

```bash
openssl x509 -in certs/fullchain.pem -noout -subject -issuer -dates
```

Expect your chosen host's certificate and a future expiry date. This command inspects only the
certificate file; it does not prove the private key matches or that browsers trust the chain.
After supplying both files, start web and inspect its configuration:

```bash
docker compose up -d web
docker compose exec -T web nginx -t
docker compose logs --tail=100 web
```

A valid configuration reports `syntax is ok` and `test is successful`. This is an nginx check;
complete the public tests below too. The entry script's success line starts `web: serving` and
names the public address, TLS mode and engine upstream.

## Verify from the caller's network

Replace the example name with your actual public host. Do not disable certificate validation:

```bash
curl -I http://refiroo.example.org/
curl -I https://refiroo.example.org/
curl -i https://refiroo.example.org/health
curl -i https://refiroo.example.org/metrics
```

With certificate files, expect HTTP 301 to the fixed HTTPS address, a successful HTTPS page, then
HTTP 200 with `{"status":"ok"}` for readiness. Public `/metrics` must return 404. Check
`Strict-Transport-Security: max-age=31536000`, `X-Content-Type-Options: nosniff`,
`Referrer-Policy: same-origin`, `Content-Security-Policy: frame-ancestors 'none'` and
`X-Frame-Options: DENY` on the application response. Header names are case-insensitive.
Automatic HTTPS also redirects HTTP; in proxy mode the external balancer owns redirection.

Open the application in a browser and sign in. Open a running job's page if jobs are used: updates
should arrive without waiting for the response to close. The supplied nginx disables proxy
buffering and sets read/send timeouts to one hour; custom balancers must preserve streaming and
allow long responses too. HTTP/2 avoids the small per-site stream limit of HTTP/1.1 browsers.

## Correct a web startup refusal

| Exact message or quoted message fragment | Cause and recovery |
| --- | --- |
| `web: WEB_TLS=files needs /opt/refiroo/rdm-engine/frontend/certs/fullchain.pem and /opt/refiroo/rdm-engine/frontend/certs/privkey.pem (the organisation's certificate and key).` | Files are missing or unreadable. Mount the right host folder with readable certificate and key; restart web. |
| `web: Mount them, or set WEB_TLS=proxy when a load balancer in front ends HTTPS.` | Use proxy mode only with an actual trusted HTTPS terminator, then recreate web. |
| `web: WEB_TLS must be 'files' or 'proxy', not` | An unsupported mode was supplied; correct `WEB_TLS` and recreate web. The message includes the rejected value. |
| `which is not an address or a range.` | A `WEB_TRUSTED_PROXIES` entry is malformed; the preceding text names it. Supply comma-separated IP addresses or CIDR ranges. |
| `web: Write addresses or ranges separated by commas, for example 10.0.0.0/8,192.168.1.5,fd00::/8.` | Correct the named entry and recreate web; do not replace it with unrestricted trust. |
| `web: PUBLIC_URL, the address people open (for example https://rdm.example.org), is not set.` | Supply the public origin. Compose normally catches this missing value before starting web. |

An nginx certificate/key parsing error needs the matching certificate files and correct permissions;
read the bounded web log for its exact path and reason. A browser trust failure needs a valid
chain trusted by the browser, not a retry with verification turned off.

## Renew or undo a proxy change

For renewed mounted files, replace both files in the existing directory, run
`docker compose exec -T web nginx -t`, then `docker compose restart web` and repeat the public
checks. Keep the previous still-valid pair until the replacement is confirmed. For changes to
`WEB_TLS`, ports, trust ranges or `WEB_CERTS_DIR`, use `docker compose up -d web` to recreate with
the new environment or mounts. Revert the private settings and recreate again if those checks fail.
Do not switch back to an expired certificate. For automatic certificates, preserve `caddy-data`
and inspect Caddy's logs rather than replacing its managed files manually.
