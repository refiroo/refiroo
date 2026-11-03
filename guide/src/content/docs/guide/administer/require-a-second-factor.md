---
title: Require a second factor
description: Require a second step for password sign-in and check the result.
reader: access-admin
---

Use this policy when a password alone should not sign people in. You need **Security administration**.
It applies to local password sign-in, including recovery administrators. Provider sign-ins
use their provider's own checks. Read [Sign-in and second factors](/docs/administer/sign-in/)
for passkeys, sessions and recovery.

## Prepare people

1. Tell people that password sign-in needs an authenticator app or passkey. They can prepare
   on their own **Settings › Account** page using **Set up an authenticator app** or
   **Add a passkey**. See [Your account](/docs/use/account/).
2. Ask people using an app to save the recovery codes shown at setup somewhere they can
   reach without that device. Each code works once. Someone with another registered passkey
   has another way in if a device is lost.
3. Check that an administrator can help with lost devices. If nobody can sign in, recovery
   requires an operator on the server; turning this policy on includes the recovery administrators too.

## Turn the requirement on

1. Open **Settings › Security › Sign-in** and select **Local accounts**.
   Under **Second factor**, find **Require a second factor with a password**.
2. Tick it. The **Require a second factor?** confirmation explains that people without a
   factor must set up an app on the sign-in page before a session starts.
3. Choose **Require it** to apply the policy. **Cancel** leaves it unchanged.
   Wait for the setting to show as checked. There is no separate Save button.
4. At the next password sign-in, check that someone with a factor is asked for the second
   step. Someone with neither an app nor a passkey must complete setup and save the recovery
   codes before continuing. A registered passkey also meets the requirement.

![Local accounts settings showing the second-factor requirement checkbox](/docs/screens/admin-signin-local.png)

*Above: the reference instance shows the requirement before it is enabled. No policy was changed for this capture.*

## Correct a problem or turn it off

If the change is refused, read **Not changed**, reload the settings and check the saved
state before trying again. Someone whose app codes fail should check their phone's time
and use a recovery code or another registered passkey if available. Follow
[Help someone who lost a device](/docs/guide/administer/help-someone-who-lost-a-device/)
when they have no remaining method.

To stop requiring the second step, clear **Require a second factor with a password**.
This saves immediately. It does not remove anyone's configured app or passkeys; an account
with an authenticator app continues to use it until that factor is removed.
People cannot remove their own required factor while the requirement is on.
