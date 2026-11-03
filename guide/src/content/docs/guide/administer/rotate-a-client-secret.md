---
title: Rotate a client secret
description: Make a replacement secret, switch the integration during an overlap and end the old secret.
reader: access-admin
---

You need **Security administration**. Arrange the handover with the integration owner
before a routine rotation. See [Clients](/docs/administer/clients/) for how secrets and grants differ.
Rotating the secret preserves the client ID, name and grants.

## Choose an overlap

1. Open **Settings › Security › Clients** and select the intended client. Check its name
   and **Client ID**. Inspect **Secrets**, including the last four characters, **Valid until**
   and **Last used**, so you can distinguish the current secret from a previous one.
2. Choose **Rotate secret…**. Select how long the current secret should keep working:
   **1 hour**, **24 hours** (the default), or **7 days**. Use enough time for the agreed handover.
3. If the secret may have leaked, choose **Stop it now**. The system is refused when it
   next tries to authenticate with the old secret until it has the replacement.
4. Choose **Make a new secret**. **Cancel** leaves the secrets unchanged. If creation fails,
   read **No new secret was made**, reload the client and check its current secrets before retrying.

![Rotate secret dialog with overlap choices and Make a new secret](/docs/screens/admin-client-rotate.png)

*Above: Stops reader (guide) is set for a 24-hour overlap in the reference dialog; no rotation has been submitted.*

## Save and switch

1. Copy the new secret from **New secret for …** into the agreed secure store. The dialog
   shows it once and says when the previous secret ends. Choose **I have copied it** after saving it.
2. Have the integration owner replace the configured secret while keeping the same client ID.
   During the overlap, both old and new secrets work for authentication.
3. Ask them to prove a fresh sign-in and the intended operation with the new secret.
   Check its **Last used** time in **Secrets**; a system still using existing access may
   not have tested the replacement yet.
4. Let the overlap expire, or use **End now** for the previous secret after checking the
   new one works. Match the last four characters carefully before ending an older secret.

If the new secret was not saved before the dialog closed, it cannot be displayed again.
Make another replacement and coordinate that handover. If access is refused after the overlap,
check that every running copy of the integration has switched and that the client remains active.
