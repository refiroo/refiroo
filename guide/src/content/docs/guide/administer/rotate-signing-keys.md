---
title: Rotate signing keys
description: Start a normal signing key replacement or retire the current key after suspected disclosure.
reader: access-admin
---

You need **Security administration**. Choose the normal or emergency procedure below
according to the reason for replacement. See [Signing keys](/docs/administer/signing-keys/)
for the automatic schedule and how these keys differ from client secrets.

## Start a normal replacement

1. Open **Settings › People and access › Signing keys**. Note the key marked **Signing** and its
   **Created** time. A previously replaced key may still show **Verifying until**.
2. Choose **Start a new key** when ready. **This acts immediately, without a dialog.**
   It is not a preview or the start of a confirmation sequence.
3. Check that a new row is **Signing** and the previous key has a replacement time and a
   verification deadline. Existing access continues until it expires. People and clients
   move to the replacement through normal renewal; no secret handover is needed.

![Signing keys list with one current key marked Signing](/docs/screens/admin-signing-keys.png)

*Above: The reference instance has one current key, marked Signing.*

## Retire the current key after suspected disclosure

1. On the same page, check which key is **Signing**. Choose **Retire the current key now**.
2. Read **Retire the current key now?**. Access signed with that key is refused from the
   next request. People's sessions renew without a fresh sign-in; clients must retry with
   fresh access obtained using their unchanged client secret.
3. Choose **Retire it now** to proceed, or **Cancel** to leave the key in place.
4. Check the list for the retired key's **Retired** time and a new **Signing** key.
   Have affected integration owners check renewal if their systems report a refusal.

![Confirmation for immediate retirement of the current signing key](/docs/screens/admin-signing-keys-retire.png)

*Above: the reference retirement confirmation is open but has not been confirmed.*

If the action reports a failure, read the message and reload the key list to establish the
current state before trying again. A signing-key retirement does not replace a leaked
client secret; use [Rotate a client secret](/docs/guide/administer/rotate-a-client-secret/)
for that separate credential.
