---
title: Manage access
description: Connect sign-in, people, roles, system clients, key rotation and security review.
reader: access-admin
---

These journeys connect getting into refiroo with granting and reviewing access. People and
systems need permission for the work they do, in the workspace where they do it. An administrative
role does not automatically grant access to reference data. Start with
[People and access](/docs/about/people-and-access/) for the distinction between roles and grants.

## Sign in and work

A person opens refiroo, signs in by an offered method and returns to the page they wanted.
[Sign-in](/docs/administer/sign-in/) explains local passwords, an organisation's provider, passkeys
and second factors. [Account](/docs/use/account/) connects personal security settings, password
changes and sessions. Use the account menu to sign out when finished, or end other sessions from
your account when needed.

Repeated failed sign-ins are slowed. If a required second factor is unavailable, use a saved
recovery code or ask an administrator to
[help after a lost device](/docs/guide/administer/help-someone-who-lost-a-device/).
Where mail is configured, a forgotten-password request can provide a fresh one-use link; a reset
does not remove the second factor. If sign-in succeeds but no workspace opens, ask for Browse
access rather than resetting the password again.

## Manage who can do what

A security administrator [adds a person](/docs/guide/administer/add-a-person/), who sets their
password through the one-use link, or arranges the organisation's provider sign-in.
Next read [Roles and grants](/docs/administer/roles-and-grants/) and
[grant a role](/docs/guide/administer/grant-a-role/) directly or through a
[group](/docs/guide/administer/manage-a-group/). Choose the workspace and, when appropriate,
[narrow writes to record types](/docs/guide/administer/narrow-a-grant-to-record-types/).
Browse covers the workspace; narrowing writes does not hide other records there.

Review effective access, including grants inherited through groups and from the installation.
A Reader reads but cannot write; a Contributor proposes changes in change sets. Grants and
activation state take effect on the next request, and jobs recheck their requester's permissions.
The last security administrator cannot be removed. Use [Audit](/docs/administer/audit/) to check
who changed access and investigate a refusal against the action and workspace it names.

## A system calls with a client

An integration team asks a security administrator to create a separate identity for its system.
Read [Clients](/docs/administer/clients/), then
[create a client](/docs/guide/administer/create-a-client/) and save its secret when it is shown
once. Give it management roles for the work it must perform, or
[grant a consumer API](/docs/guide/administer/grant-a-consumer-api-to-a-client/) in the intended
workspace. One kind of grant does not imply the other.

The integrator then follows [system sign-in](/docs/integrate/signing-in-and-tokens/) and
[obtain system access](/docs/guide/integrate/get-a-token/) to connect the system under those grants.
Check allowed work and refused work before relying on it. Later,
[rotate the client secret](/docs/guide/administer/rotate-a-client-secret/) with an overlap when
needed, or deactivate the client to end its access. A deactivated client cannot keep working
with previously issued access. Keep a client separate from a person's browser account so its
activity and grants remain identifiable.

## Rotate a key

A security or integration administrator first identifies which credential needs replacement.
[Signing keys](/docs/administer/signing-keys/) explains ordinary replacement and emergency
retirement; [Rotate signing keys](/docs/guide/administer/rotate-signing-keys/) carries the chosen
action through verification. Normal replacement preserves existing access until expiry.
Emergency retirement ends access signed with the retired key immediately; browser sessions renew
and integrations must obtain fresh access.

For a delivery-signing key, [rotate a webhook key](/docs/guide/administer/rotate-a-webhook-key/)
from that webhook instead. Share the new key securely with its receiver and use the chosen overlap
to maintain verification during handover. These actions do not replace a client's secret.
Changing the encryption key used to store secrets is a separate operator procedure in
[Secrets and keys](/docs/run/secrets-and-keys/); coordinate that work with the operator.

## Check the security model

A security reviewer, administrator or integrator needs to understand where access is enforced
and how to assess the deployment. Begin with [Security, audit and privacy](/docs/about/security-and-trust/),
then compare the intended access with [Roles and grants](/docs/administer/roles-and-grants/) and
[Audit](/docs/administer/audit/). Include direct, group and installation-wide grants, writes
narrowed to types, background work and the separate grants for consumer APIs.

The service enforces permissions across browser and integration operations. Hiding a button is
not the security boundary. Deactivation and revoked permissions affect later requests and job
steps. Use the [Security checklist](/docs/run/security-checklist/) with the operator for HTTPS,
credential storage and deployment controls. Integrators can continue with
[the security model for integrations](/docs/integrate/security-model-for-integrators/).
This review connects the documented rules and evidence; it is not a separate security-checking
screen in refiroo.
