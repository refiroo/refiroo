---
title: Get a token
description: Sign in as an integration client and make an authenticated request.
reader: integrator
---

Use this sequence for an unattended system. Read [Signing in and tokens](/docs/integrate/signing-in-and-tokens/) for lifetimes and rotation.

1. Ask an administrator to [create a client](/docs/administer/clients/) with only the access your integration needs. Receive the instance address, client ID and one-time secret through your normal secure credential channel. A new client has no access until granted it.
2. Open the [OAuth token operation](/docs/api/?api=management#tag/oauth). Exchange the credentials using the client-credentials grant. Choose management for management operations or consumer for consumer reads. Use one supported credential method; sending both is refused.
3. Keep the returned bearer token in memory or your system's protected token store. Schedule renewal from the returned lifetime. Do not put the secret or token in source files, URLs or diagnostic logs.
4. For management access, call the [caller operation](/docs/api/?api=management#tag/security). For consumer access, read the [API index](/docs/api/?api=management). Check that the intended workspace and API are available. A token can be valid while the necessary grant is absent.
5. Before expiry, exchange the credentials again. Clients do not receive refresh tokens. On an authentication refusal, check the reason before retrying; on a throttled token request, wait for the retry interval.

If the token works but a data call is forbidden, have the administrator review the client's grants for that workspace and API. Reissuing the same token does not add permissions. If the client was deactivated, agree the recovery with its administrator before resuming.

## Make the exchange

This short example is a consumer connection. Set `INSTANCE_URL` to the HTTPS instance address without a trailing slash. Supply `CLIENT_ID` and `CLIENT_SECRET` from your protected credential store; the placeholders are not credentials. The [token operation](/docs/api/?api=management#tag/oauth) describes the complete request contract.

```sh
curl --silent --show-error --fail-with-body \
  --user "$CLIENT_ID:$CLIENT_SECRET" \
  --data-urlencode 'grant_type=client_credentials' \
  --data-urlencode 'scope=consumer' \
  "$INSTANCE_URL/oauth/token"
```

On success, HTTP 200 contains `access_token`, `token_type` equal to `Bearer`, `expires_in` in seconds and `scope` equal to `consumer`. Store the token without printing it in a production log. With `ACCESS_TOKEN` set from that answer, check discovery:

```sh
curl --silent --show-error --fail-with-body \
  --header "Authorization: Bearer $ACCESS_TOKEN" \
  "$INSTANCE_URL/api/consumer?workspace=graubuenden"
```

The workspace in this request is a **reference-data example**. Replace it with the workspace you were granted. The answer lists only APIs this consumer client may read there; an empty `items` list can mean the grant is missing. Follow `nextCursor` when present. For a management connection, exchange with `scope=management` and check the caller operation linked in step 4 instead. Keep separate tokens when one process needs both interfaces.

## Recover or stop

A failed exchange has an OAuth `error` and `error_description`, rather than a data route's `error.code`. For `invalid_client`, check which secret is current, whether its overlap ended and whether the client is active. For `invalid_scope`, check both the requested audience and client kind. A 429 includes `Retry-After`; wait that interval. Do not repeatedly exchange a secret known to have expired.

When retiring an integration, stop scheduled calls and remove its stored token and secret. Ask its administrator to deactivate the client or remove its grants. Deactivation is checked on the next request; deleting a local token alone does not revoke another copy. [Client administration](/docs/administer/clients/) covers rotation and deactivation.
