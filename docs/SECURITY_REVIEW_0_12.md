# Security review of 0.12 (E1)

**Status:** open — C2 awaiting the user's decision; everything else fixed or accepted. Phases A–C of
[the E1 plan](testing/E1_SECURITY_CHECKPOINT_PLAN.md) are done (2026-10-26); Phase D (fixes) is done
but for C2. E1 is delivered only when every finding below is fixed or accepted by the user, and a
high-severity finding stops E1 until then (the user, 2026-10-26).

What was examined: the generated sweep (`backend/tests/journeys/test_j47_*`), the composed cases, the
deployment runner (`npm run test:deployment`), the real-provider try
(`npm run test:browser:real-provider`, Keycloak 26.8.1, ten cases passed after the `iss` fix `8e7126e`)
and a read-only review of the 0.12 changes (`a68466b..HEAD`) by an agent that did not write the code,
code reading only, no dynamic testing. Findings from the review are the agent's report; C1 was
re-checked in the code by the lead before filing (below).

## What the sweep proved

233 operations with an action and 6 open ones, as 10 principals (the 9 predefined roles and a caller
with no grants) and with no token: about 6,100 requests per run, none a 5xx, every allow/refuse equal
to the catalogue. The consumer routes (18 operations on 2 APIs), 34 routes outside the OpenAPI document
(each classified, 470 junk requests, 15 state tables unchanged), person tokens (equal to a client with
the same role) and reset by mail with a second factor (not skipped). Not covered: person and group
consumer grants, junk on the consumer routes, timing on reset, passkey ceremonies with real credentials,
behaviour behind nginx in a real browser.

## Findings

| ID | Severity | State | Finding |
| --- | --- | --- | --- |
| C1 | **High** | fixed (`test_a_narrowed_live_delete`, `test_a_narrowed_cascade_delete_reaches_only_permitted_types`, `test_a_narrowed_batch_and_import_delete`, `test_a_narrowed_delete_in_a_change_set`) | Deletions skip the narrowing check (below) |
| C2 | Medium | open | Source files: Bulk anywhere reaches every model-draft file and can supersede files of other workspaces |
| C3 | Medium | fixed (`npm run test:deployment`, step 6 and 9b–9d: a forged `X-Forwarded-For` is not counted unless the connecting address is in `WEB_TRUSTED_PROXIES`; a bad entry stops `web`) | `WEB_TLS=proxy`: the caller chooses the address the engine sees |
| F1 | Low | fixed (`test_authorization_refuses_before_an_unknown_parameter_is_refused`, `test_authentication_refuses_before_an_unknown_parameter_is_refused`, `test_an_open_route_still_refuses_an_unknown_parameter`) | The unknown-parameter check runs before authentication and authorization (`main.py:262`); two unit-probe cases pin it |
| F3 | Medium | fixed (`test_a_binary_body_is_refused_with_422_never_500`) | A non-UTF-8 request body gives `500 INTERNAL_ERROR`, reachable without a token on the `/oauth` routes (`management/errors.py`, `jsonable_encoder(exc.errors())`); strict xfail |
| F4 | Medium | fixed (`test_a_nul_byte_in_an_address_is_refused_with_4xx_never_503`, `test_a_value_the_driver_refused_is_not_an_outage`) | A NUL byte in an address gives `503 DATABASE_UNAVAILABLE` and counts as a database outage in `/metrics` (`common/outage.py::_unreachable_state`: no SQLSTATE counts as unreachable); strict xfail |
| C4 | Low | accepted by the user (the per-account wait is D271's design against password spraying; API.md and OPERATIONS now say a known username can be slowed by anyone) | Anyone who knows a username can keep it slowed (up to 15 minutes per attempt) for password sign-in; "never locked" (D271) holds only for the owner's patience |
| C5 | Low | fixed (`npm run test:deployment`, steps 4 and 9: `Content-Security-Policy: frame-ancestors 'none'` and `X-Frame-Options: DENY` on the application page, both modes) | The application page can be framed (no `frame-ancestors`/`X-Frame-Options` in `frontend/nginx/snippets/headers.inc.template`) |
| C6 | Low | fixed (`test_a_new_host_or_port_needs_the_password_sent_again`, `test_a_new_issuer_needs_the_secret_sent_again`, `test_an_issuer_is_not_changed_while_people_are_linked_through_the_provider`) | Write-only secrets follow an endpoint change: the SMTP password stays when host/port change; a provider's client secret stays when the issuer changes (and linked identities stay keyed on provider and `sub`) |
| C7 | Low | fixed (`test_resealing_says_whose_recovery_codes_the_new_key_voids`; the cryptography is unchanged: the command and OPERATIONS say how many people must make new codes) | Changing `SECRETS_ENCRYPTION_KEY` silently voids every recovery code (they are HMACed with the key itself; `reseal_secrets` and the OPERATIONS procedure do not mention it) |
| C8 | Info | accepted by the user (informational) | Reset by mail: response time can reveal whether an account exists; each ask replaces the person's pending link (3 per name before the slowing) |
| C9 | Info | fixed (docs only: API.md and OPERATIONS now state the code's cookie path `/oauth`, the consumer OpenAPI document needing no token, and the throttle's free failures per name and per address) | Docs out of line with code: the refresh cookie path is `/oauth`, not `/oauth/token` and `/oauth/revoke` (API.md ~5949); API.md ~5960 says a consumer OpenAPI document needs a token, but D412 serves it without one; throttle wording ("3 free" for the address; the code allows 20) |
| C10 | Suspicion | fixed (`test_the_page_runs_only_the_scripts_it_ships_and_cannot_be_framed`, `test_the_cdn_setting_names_the_pinned_host_in_its_policy`; `npm run test:browser:v1` once: the page renders, the console is signed in, "Try it" works) | `/docs` has no CSP and can mint a management token from the cookie (`oauth_console.py`); if Scalar renders model-authored descriptions unsanitised, a model author could take a Security administrator's token. Scalar's sanitising not checked |
| F2 | Info | accepted by the user (informational) | `GET /objects/{type}/{id}/history` reads `workspaceKey` and `publicationId` to find its workspace but does not declare them (naming them gives 422) |
| R1 | Decision | accepted by the user: a rotated secret does not end an access token already issued, which stays valid for up to its hour (the lifetime bound; API.md says a token proves who, never what the caller may do) | A rotated client secret does not end an access token already issued (valid up to an hour; API.md: a token proves who, never what the caller may do). The plan's B3 expected 401; the test asserts the documented behaviour |

### C1 (high) — deletions skip the narrowing check

A caller holding Data steward or Contributor in workspace W, **narrowed** to one record type or
application, can delete records of types it may not write: `DELETE /objects/{id}` (with `cascade=true`
and a preview token too), a `delete` item in `POST /batches` and an import's deletions of rows missing
from a file, and a delete inside a change set (published later by an unnarrowed publisher).
Cause: `engine/records/deletion.py` (`delete_records`, `LiveScope.write` :467–489,
`ChangeSetScope.write` :541–563) removes rows with raw SQL and never calls `refuse_types`; the callers
`deletion.py:1091`, `change_sets/records.py:435` and `jobs/batches.py:503` add no check. The only
narrowing checks are in `engine/records/writes.py` (`permit`, used by `remove_records` :404, which these
paths do not use) and `batch_lookup._permit` (creates and updates). *Checked by the lead:* `refuse_types`
is called only from `writes.py` and `batch_lookup.py`; the three delete callers go through
`delete_records`. Not reproduced dynamically.
Why the tests missed it: the B2 table maps `delete /objects/...` to `test_a_narrowed_live_write`, which
never deletes. Suggested fix: in `delete_records`, after `_decide` and before `scope.write`, read the
distinct (application, type) pairs of the objects to delete and the end types of the relations, and call
`refuse_types` for the scope's workspace; add J40 cases for a narrowed single, cascade, batch and
change-set delete; correct the B2 table. This touches the write unit's invariants, so it waits for the
user's go-ahead.

### The fixes, in short (Phase D2)

- **C3.** In `WEB_TLS=proxy`, `web` takes the caller's address from `X-Forwarded-For` only when the
  connection comes from an address in the new `WEB_TRUSTED_PROXIES` (default empty: trust nobody), by
  nginx's `real_ip` module (`real_ip_recursive on`), and sends the engine that one address, replacing
  what the request carried. `compose.acme.yml` lists the private ranges (only Caddy reaches `web`).
  Whether Caddy replaces a client's `X-Forwarded-For` was not verified in Caddy's code; the setting is
  safe with Caddy as long as Caddy appends the address it saw. Not tested against a real balancer
  other than the runner's own connection.
- **C6.** Mail: a new host or port needs the password in the same save (`422 MAIL_PASSWORD_REQUIRED`,
  `details.field` `password`). Providers: a new issuer needs `clientSecret` in the same save (`422
  SIGN_IN_PROVIDER_SECRET_REQUIRED`, new code), and the issuer of a provider anyone has signed in with
  cannot change (`409 SIGN_IN_PROVIDER_IN_USE`). The settings screens were not changed: they show the
  engine's message.
- **C7.** `reseal_secrets` and `--check` print how many people hold unused recovery codes; they
  become void under a new key.
- **C10.** `/docs` sends a `Content-Security-Policy` allowing scripts from the engine and the page's
  own two inline scripts **by hash** (not `'self'` alone: the page's configuration and sign-in code
  are inline, and moving them to a file would have added a route; a hash allows exactly those bytes and
  no other inline script). Scalar needs inline styles (`style-src 'unsafe-inline'`), `data:` and
  `blob:` images and `data:` fonts; it needed no `unsafe-eval` and no inline-script allowance.

### Reviewed and found sound

Access tokens (ES256 only, `alg`/`kid` before lookup, all claims required, key/principal/session/
generation read in one statement, rotation under an advisory lock); refresh tokens (hashed, rotated under
lock, reuse ends the session); the authorization code (one-time, PKCE S256, `redirect_uri` exact match,
unknown never redirected to); cookies and Origin checks; redirects compared by origin; OIDC (state hashed
and bound to the browser, nonce, PKCE, RFC 9207 `iss`, ID token allowlist and claims, people matched by
provider and `sub`, SSRF protection: one DNS resolution, connection to the checked IP, no redirects,
link-local refused); passkeys; TOTP and recovery codes (single use); reset links (256-bit, hashed,
single use, the base from settings, never the Host header); sealing (AES-256-GCM, random 96-bit nonces,
per-value AAD); the permissions cache and its generation triggers; jobs re-checking their requester; no
SQL from input; the engine's HTML pages escape values and send a strict CSP; `/metrics` 404 at nginx and
a token at the engine; images run non-root with no secrets in layers; the access token held in memory
only; no `dangerouslySetInnerHTML`.

### Not examined

Moves, restructuring and type-change internals beyond their write-unit calls; `administration.py` grant
and role logic beyond route actions; workbook and CSV parsing (zip bombs, XML entities), formula
injection in exports; webhook payload signing and the dispatcher; feed and consumer reads; mail
templates and header injection; `passkey.js` and the sign-in screens in detail; cursor signing;
migrations other than the authorization triggers; Caddy's `X-Forwarded-For` handling in code;
`scripts/dev.sh` beyond what it binds; any dynamic testing by the reviewer.

## Hand try with the organisation's own provider

Open (E1 plan decision 3): wanted after E1 or not, and which provider.
