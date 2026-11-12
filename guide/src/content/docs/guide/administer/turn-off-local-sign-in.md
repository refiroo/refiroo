---
title: Turn off local sign-in
description: Move ordinary browser sign-in to a working provider while preserving an administrator’s recovery route.
reader: access-admin
---

You need **Security administration** and an enabled provider that has already signed someone in successfully. Keep a tested local recovery account. This change affects local password sign-in, not clients’ authentication. See [Sign-in and second factors](/docs/administer/sign-in/#local-accounts).

## Prepare a way back

1. Follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/) and prove a complete sign-in through **Continue with …**. Check that the right person and roles are reached.
2. Open **Settings › People and access › People** and open the recovery administrator’s row. Under **Sign-in**, check that their password is set and **Keeps local sign-in** is on. This is separate from their Security administrator role.
3. If needed, turn **Keeps local sign-in** on. It saves immediately and offers **Undo**; turning it off asks for confirmation. Test the retained account before proceeding. It still needs any required second factor; keep that device or recovery route available.
4. Tell affected people to use the organisation’s provider. Arrange links for existing accounts so they keep their roles and history rather than acquiring duplicate identities.

## Turn off ordinary password sign-in

1. Open **Settings › People and access › Sign-in** and select **Local accounts**. **Turn off…** appears only after an enabled provider has successfully signed someone in. If absent, complete that proof first.
2. Choose **Turn off…**. Read **Turn local sign-in off?**, including which providers are offered and how many people keep password sign-in.
3. Choose **Turn off**, or **Cancel** to leave it enabled. Wait until Local accounts shows **Off**. If **Not changed** appears or details changed meanwhile, review the saved state before trying again.
4. In a separate browser session, check provider sign-in. Check the recovery account through **Sign in with a local administrator account**. Ordinary local accounts no longer sign in with a password.

While local sign-in is off, refiroo refuses to deactivate the last active person keeping it or remove their retained route. Keep more than one prepared recovery person if your organisation requires that resilience. Turning local sign-in off does not remove people, passwords, roles or the second-factor requirement.

## Restore local sign-in

Open **Local accounts** and choose **Turn on**. This acts immediately, without a confirmation. Check **People sign in with a password again.** If no administrator can reach refiroo, the operator must use the server recovery procedure; see [Configure sign-in](/docs/run/sign-in-and-mail-setup/).
