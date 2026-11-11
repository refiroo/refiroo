# oauth

These are the engine's OAuth 2.0 endpoints, at the root of the instance and not under `/api/v1`. A program signs in with `POST /oauth/token`, sends the token as `Authorization: Bearer`, and asks again before it expires; a browser or an assistant gets its tokens from the same endpoint after a person signs in on the engine's page. Refusals use OAuth's own answer, `{"error": "invalid_client", "error_description": "..."}`, not the error envelope the other operations use.

1. Sign in a program: `POST /oauth/token` with `grant_type=client_credentials`; `expires_in` says how long the token lasts.
2. Verify a token yourself: read the keys from `GET /oauth/jwks` and fetch them again when a token names an unknown `kid`.

## GET /.well-known/oauth-authorization-server

Title: Read the authorization server's metadata

Describes the engine as an authorization server (RFC 8414): its issuer, endpoints, grant types and scopes. Use it to configure a client from one address. `registration_endpoint` appears only while agent access and open registration are on, and the `agent` scope only while agent access is on.

## GET /.well-known/oauth-protected-resource

Title: Read the MCP resource's metadata

Describes `/mcp` as an OAuth protected resource (RFC 9728) and names the authorization server that signs an assistant in. Assistants find it from the `401` that `/mcp` answers. It answers `404 not_found` while agent access is off.

## GET /.well-known/oauth-protected-resource/mcp

Title: Read the MCP resource's metadata at its derived address

Answers the same document as `GET /.well-known/oauth-protected-resource`, at the address RFC 9728 derives from `/mcp`, which some assistants ask for first.

## GET /oauth/jwks

Title: Read the keys that verify tokens

Publishes the public keys that verify access tokens now, by `kid`, as a JSON Web Key Set (RFC 7517). Cache it. After `POST /api/v1/token-signing-keys/rotation` new tokens carry a new `kid`, so refetch when a token names one you do not hold.

## POST /oauth/register

Title: Register an assistant

An assistant registers itself (RFC 7591) as a public client: it holds no secret, proves each sign-in with PKCE and returns only to this computer or to a host in `MCP_REDIRECT_HOSTS`. It needs agent access and `MCP_OPEN_REGISTRATION`: otherwise `404 not_found` or `403 access_denied`. Refusals are `400 invalid_redirect_uri` or `invalid_client_metadata`, and `429 temporarily_unavailable`. An administrator registers one with `POST /api/v1/agent-access/applications`.

## POST /oauth/revoke

Title: Sign out a session

Ends the session a refresh token belongs to (RFC 7009), taking the token from `token` or the browser's cookie, and clears the cookie; the session's access tokens are refused from then on. An unknown token answers the same `200`, so it does not say which tokens exist. A client's token is not revoked here: deactivate the client.

## POST /oauth/token

Title: Get an access token

Gets an access token. A program sends `grant_type=client_credentials`, its client ID and secret as HTTP Basic credentials or as `client_id` and `client_secret` (not both), and `scope`: `management` (the default) or `consumer`; an agent client asks for `agent`. A browser or assistant redeems a sign-in `code` or a `refresh_token`. Refusals are OAuth's: `400` `invalid_request`, `invalid_scope` or `invalid_grant`, and `401` `invalid_client` (`429` with `Retry-After` while slowed).

### Parameters

- Authorization: `Basic` and the base64 of `client_id:client_secret`, for `client_credentials`.

## Schemas

### Body_token_oauth_token_post

- grant_type: `client_credentials` for a program; `authorization_code` or `refresh_token` for a browser or an assistant.
- scope: `management` (the default), `consumer` or, with agent access on, `agent`.
- client_id: The client's ID, when the credentials are not in the `Authorization` header; `browser` for the browser's grants, an assistant's own ID for its.
- client_secret: The client's secret, when it is not in the `Authorization` header. A browser or an assistant has none.
- code: The one-time code the sign-in page returned, for `authorization_code`.
- code_verifier: The PKCE verifier whose challenge started the sign-in, for `authorization_code`.
- redirect_uri: The address the sign-in returned to, for `authorization_code`; it must be the one the sign-in used.
- refresh_token: The session's refresh token, for `refresh_token`; the browser's cookie is used when it is left out. Each is used once.
- resource: An assistant's request for `/mcp`; it must name this instance's `/mcp` address.

### Body_revoke_oauth_revoke_post

- token: The refresh token of the session to end; the browser's cookie is used when it is left out.
- token_type_hint: Accepted and ignored; only refresh tokens are revoked here.
