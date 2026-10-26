# The real sign-in provider try (0.12 I3, D369, E1)

**Status:** plan, awaiting the user's approval (2026-10-26). Nothing here is built.

I3 was tested against the harness's minimal OpenID Connect provider (`backend/tests/oidc_provider.py`),
which agrees with the engine because the same person wrote both. D369 promised one sign-in against a
real provider before E1. This plan makes that try automatic with **Keycloak in Docker**, so it is
repeatable at E1 and R instead of a one-off by hand.

## What it can and cannot prove

- **Can:** a provider the project did not write: its real discovery document, its signing keys, the
  shape of its ID tokens, its groups mapper, its login page and its end-session endpoint, with the
  engine and the application in the middle.
- **Cannot:** Microsoft Entra ID or Google. They need a tenant or an account and a public redirect
  address. Entra's group object IDs and its 200-group overage, and Google's missing groups claim, stay
  as what OPERATIONS says they are. If the user's organisation uses one of them, a one-time try by
  hand with that provider still follows E1; this plan does not replace it. Keycloak is the
  generic standard-compliant stand-in, and Okta behaves alike.

## The setup

1. **A Keycloak container** for the run: `quay.io/keycloak/keycloak:<a pinned version>`, started with
   `start-dev --import-realm`, on a free loopback port, admin credentials random per run. The engine
   accepts plain `http` for a provider on loopback only (`provider_client._checked_url`), so no
   certificate is needed. **Pull size and start time were not measured.**
2. **A realm file in the repository**, `backend/tests/keycloak/refiroo-realm.json`, imported at start:
   - realm `refiroo`; a confidential client `refiroo-engine` with a fixed secret for the run,
     standard flow only, PKCE `S256` required;
   - redirect URI `<PUBLIC_URL>/oauth/providers/keycloak/callback` (the address OPERATIONS tells an
     operator to register) and, as the *post logout redirect URI*, the second address the provider's
     page shows;
   - a **Group Membership** mapper on the client adding a `groups` claim with *full group path off*;
   - groups `finance` and `audit`;
   - people: `ada` (in `finance` and `audit`), `bo` (in `finance`), `cy` (no group), each with a
     password and an e-mail address; `ada` has a name with a non-ASCII letter.
3. **A runner**, `frontend/e2e/i3-real-provider.mjs` (`npm run test:browser:real-provider`): boots the
   harness at `localhost` (as `i4-sign-in.mjs` part c does), starts Keycloak, waits for its discovery
   document, runs the cases below in Chromium, and removes the container and its image at the end
   (`docker rm -f`; the pulled base image is left). One run, no other servers. It is **not** part of
   any default set: heavy and announced, run before E1 and at R.

## Cases (given / when / then)

Each runs on the starter model and on the starter under another product name.

1. **Register.** *Given* the administrator signed in, *when* they add a provider on Settings ›
   Security › Sign-in with Keycloak's realm address, client ID and secret, groups claim `groups`,
   *then* it is checked against the real discovery document and saved, and the page shows the
   redirect address registered in the realm file.
2. **First sign-in.** *Given* a signed-out browser, *when* the person presses Continue with Keycloak
   and signs in as `ada` on Keycloak's own page, *then* they land signed in in the application, their
   name (with the non-ASCII letter) and e-mail are those of the token, and Account names the provider.
3. **Groups.** *Given* `ada` signed in, *then* Settings › Security shows provider groups `finance` and
   `audit` with her as a member, as Keycloak sent them (no leading `/`).
4. **A person with no group.** *When* `cy` signs in, *then* they sign in and hold no provider group.
5. **A wrong password** at Keycloak returns nothing to the application: the browser stays on
   Keycloak's page and no person is created.
6. **Groups change at the provider.** *Given* `bo` signed in once, *when* `bo` is added to `audit`
   through Keycloak's admin API and signs in again, *then* the engine's `audit` group has `bo`.
7. **Second sign-in** of `ada` finds the same person (by `sub`), not a new one.
8. **Sign out of the provider too.** *Given* "Sign people out of the provider too" saved, *when* `ada`
   signs out of the application, *then* the browser goes through Keycloak's end-session endpoint and
   back to the sign-in page, and Continue with Keycloak asks for the password again.
9. **Local sign-in off.** *When* local sign-in is turned off through its confirmation, *then* the
   sign-in page offers only Continue with Keycloak and the local administrator's link.
10. **Keys rotate at the provider.** *When* Keycloak rotates its realm key and `ada` signs in again,
    *then* the sign-in works (the engine re-reads the key set).

Case 10 is a probe: if the engine fails there, report it as a finding for the user, do not change the
engine inside the plan.

## Who builds it, and how

A Sonnet agent can do it: the work is a realm file, a runner copied from `i3-sign-in-providers.mjs`
and `i4-sign-in.mjs` (part c shows the `localhost` host option), and one execution-guide row. The
brief it gets is this file plus these rules:

- Read `AGENTS.md`, this plan, `frontend/e2e/i3-sign-in-providers.mjs`, `frontend/e2e/helpers/harness.mjs`
  and OPERATIONS § Signing in with the organisation's provider. No other area.
- **Never edit the cases above.** A case the engine cannot pass is reported with its evidence, not
  worked around.
- Change no engine code. Add: the realm file, the runner, its `package.json` script, the execution
  guide row and a CHANGELOG line.
- Docker: announce the run with what it pulls; run it once (twice if a fix needs it); then stop and
  remove the container, confirm with `docker ps -a` and report what is left.
- Report per case: passed, failed with the observed result, or not reached; plus what was not tried.

## Cost and decisions for the user

- **Cost:** a pinned Keycloak image pulled once; a runner of its own in the heavy set; a realm file
  to keep current with Keycloak's export format.
- **Decide:** (a) approve the ten cases; (b) whether a one-time hand try with the organisation's own
  provider (Entra, Google, Okta) is still wanted after E1, and which one; (c) which Keycloak version
  to pin (the plan suggests the current stable release at the time of building).
