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

The `compose.acme.yml` overlay adds **Caddy 2** (`caddy:2`) in front of web. Caddy obtains and
renews certificates from **Let's Encrypt** or **ZeroSSL** using **ACME**, the protocol through which
a certificate authority checks control of a domain and issues a certificate. The authority must
be able to reach this public installation to complete its challenge. A local browser trusting the
site is not enough.

1. Choose a public DNS name and point it at this host. Check that its DNS addresses lead here,
   including any published IPv6 address. Make inbound ports **80 and 443** reachable from the
   internet. Another service must not already own those host ports.
2. Set `PUBLIC_URL` in the private environment to the HTTPS origin for that name. The
   overlay publishes Caddy on host ports 80 and 443 directly; `WEB_HTTP_PORT` and
   `WEB_HTTPS_PORT` do not change those overlay ports.
3. If you want to supply a certificate contact address, add this global block above the site
   block in your installation's `caddy/Caddyfile`, using your own address:

   ```caddyfile
   {
     email operator@example.org
   }
   ```

4. Start with both files from the repository root:

   ```bash
   docker compose -f compose.yml -f compose.acme.yml up -d --build
   docker compose -f compose.yml -f compose.acme.yml logs --tail=100 caddy
   ```

   No `./certs` directory or certificate files are needed. The overlay sets `WEB_TLS=proxy`,
   removes web's published ports and certificate mount, and makes Caddy the only public entry.
   It forwards to `web:8080`, which forwards engine paths privately. Streaming responses flush
   immediately through Caddy. Keep both `-f` arguments on subsequent commands.
5. Check HTTP redirection and HTTPS readiness from the caller's network:

   ```bash
   curl -I http://refiroo.example.org/
   curl -i https://refiroo.example.org/health
   ```

   Substitute your real name. Expect a redirect to HTTPS and readiness 200 with a trusted
   certificate. Follow the broader [public checks](#verify-from-the-callers-network) before
   opening traffic. Never bypass certificate validation to call issuance successful.

### Preserve certificates and renewal

Caddy's `/data` is the **`caddy-data` volume**. It holds both certificates and the certificate
authority account. Preserve it across container rebuilds and upgrades, and include it in protected
storage backups. Do not remove it to force a retry: losing it causes new issuance requests, which
the authorities rate limit. Caddy renews its managed certificates automatically; do not replace
its managed files by hand. Keep DNS, inbound reachability and Caddy running for renewals too.

Inspect the certificate actually served, rather than only a container's state:

```bash
openssl s_client -connect refiroo.example.org:443 -servername refiroo.example.org </dev/null \
  | openssl x509 -noout -subject -issuer -dates
```

Check the host, issuer and expiry, then verify the trusted HTTPS request with `curl` or a browser.
A contact address does not replace certificate-expiry monitoring.

### If a certificate is not issued or renewed

Read bounded Caddy logs using both Compose files. A name resolving elsewhere or a blocked public
port prevents the authority's challenge from reaching Caddy: correct DNS or the firewall, then
check the next attempt in the logs. If DNS publishes both IPv4 and IPv6, both advertised paths
must lead to the right entry. A host-port binding error requires freeing ports 80/443 or reviewing
the chosen topology. If the log reports an authority rate limit, preserve the account volume and
follow the retry time in that message instead of repeatedly recreating storage.

Check outbound connectivity from Caddy to the authority as well as inbound connectivity. A changed
Caddyfile must parse successfully; inspect its error before restarting repeatedly. For a running
container, validate the mounted file with:

```bash
docker compose -f compose.yml -f compose.acme.yml exec -T caddy \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile
```

After a valid change, restart Caddy with the same overlay arguments and repeat the public checks.
Keep the existing `caddy-data` volume. This public flow is unsuitable for a name only your network
knows: use your organisation's certificate files. Caddy can use its own local authority for
`localhost`, but that does not make its certificate publicly trusted or replace the
[development-device trust setup](/docs/run/developer-instance/).

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

## Certificate protocols and browser caching

The supplied certificate-file configuration accepts **TLS 1.2 and TLS 1.3** and enables HTTP/2.
For proxy mode, protocol policy belongs to Caddy or your organisation's HTTPS terminator.

Hashed files under `/assets/` are cached for one year with `immutable`; a changed build gives them
new names. The application page uses `Cache-Control: no-cache` so browsers check for an updated
page. Preserve these rules in a custom proxy to avoid serving an old page after an upgrade.
