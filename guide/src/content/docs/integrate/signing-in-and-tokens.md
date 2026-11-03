---
title: Signing in and tokens
description: Authenticate a client and keep its access working during token and secret rotation.
reader: integrator
---

Give an unattended integration a client identity. An administrator [creates the client and grants access](/docs/administer/clients/); your integration exchanges its credentials for a bearer token through the [OAuth token operation](/docs/api/?api=management#tag/oauth). Follow [Get a token](/docs/guide/integrate/get-a-token/) for the sequence.

## Choose the audience

Request the management audience for management operations or the consumer audience for consumer data. The audience selects which interface accepts the token; it does not grant permissions. Management access comes from roles. Consumer access requires a separate grant for the API in the workspace, and is available to clients only. A person's browser role does not make their token a consumer credential.

The default access-token lifetime is one hour. Use the lifetime returned when the token is issued; the operator can change it. Clients have no refresh token. Obtain another access token using the client credentials before the current token expires. Send tokens in the authorization header, never in URLs.

Tokens identify the caller. Permissions and whether the caller is active are checked on requests, so removing access or deactivating a client takes effect on the next request. Do not store a permission decision for the lifetime of a token.

## Rotate without interrupting work

The administrator can rotate a client secret with an overlap. Store the new secret securely, switch the integration to it and obtain a token to check it works before the old secret ends. The administrator can see last-use times and end the overlap early. See [Client secrets](/docs/administer/clients/#secrets-and-rotation) and the [security operations](/docs/api/?api=management#tag/security). A missing client or secret is reported as `CLIENT_NOT_FOUND` or `CLIENT_SECRET_NOT_FOUND`; `CLIENT_HAS_NO_SECRETS` requires an administrator to supply a usable secret.

Token signing keys rotate independently of client secrets. A token refused after a signing-key change needs a new token, not a new client secret.

## When sign-in or a request fails

OAuth failures use the OAuth error format. `invalid_client` means the credentials cannot authenticate the client; check the ID, secret, expiry and active state. Repeated failures are slowed, including failures with an unknown client ID. Respect the retry interval. `invalid_scope` needs a supported audience; `invalid_request` needs a corrected token request.

Protected API calls use the engine's error format. `AUTHENTICATION_REQUIRED` means no token was supplied. `TOKEN_INVALID` identifies an expired, revoked, wrong-audience or unverifiable token: obtain the correct token, and investigate revocation rather than retrying indefinitely. `CONSUMER_API_CLIENTS_ONLY` requires a client identity. `FORBIDDEN` requires a suitable grant; its explanation names the action and workspace. See [Security for integrators](/docs/integrate/security-model-for-integrators/).

Health probes, public OpenAPI documents, the API reference and sign-in endpoints have open routes. Data routes require authentication; there is no setting to turn it off.

## Browser sessions

People sign in through the authorization-code flow with PKCE. Their refresh tokens rotate and belong to sessions; clients do not reuse this mechanism. Browser sessions default to 12 idle hours and 14 days overall. A used refresh token has a 30-second recovery grace only while its successor is unused. Older reuse or reuse after that successor was consumed ends the session. A transient server failure during renewal does not itself sign the browser out. Browser applications should preserve that distinction between a refused session and a temporarily unavailable server.
