---
title: Get a token
description: Sign in as an integration client and make an authenticated request.
reader: integrator
---

Use this sequence for an unattended system. Read [Signing in and tokens](/docs/integrate/signing-in-and-tokens/) for lifetimes and rotation.

1. Ask an administrator to [create a client](/docs/administer/clients/) with only the access your integration needs. Receive the instance address, client ID and one-time secret through your normal secure credential channel. A new client has no access until granted it.
2. Open the [OAuth token operation](/docs/api/?api=management#tag/oauth). Exchange the credentials using the client-credentials grant. Choose management for management operations or consumer for consumer reads. Use one supported credential method; sending both is refused.
3. Keep the returned bearer token in memory or your system's protected token store. Schedule renewal from the returned lifetime. Do not put the secret or token in source files, URLs or diagnostic logs.
4. For management access, call the [caller operation](/docs/api/?api=management#tag/security). For consumer access, read the [API index](/docs/api/?api=management#tag/consumer). Check that the intended workspace and API are available. A token can be valid while the necessary grant is absent.
5. Before expiry, exchange the credentials again. Clients do not receive refresh tokens. On an authentication refusal, check the reason before retrying; on a throttled token request, wait for the retry interval.

If the token works but a data call is forbidden, have the administrator review the client's grants for that workspace and API. Reissuing the same token does not add permissions. If the client was deactivated, agree the recovery with its administrator before resuming.
