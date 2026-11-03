---
title: Who can do what
description: Roles, workspace grants and sign-in keep responsibility separate from access.
reader: evaluator
---

Governed changes start with roles and grants: they control who may do what, while approval policies govern publication. Access can differ between workspaces, and a grant can narrow writes to particular applications or record types. Jobs and other systems face permission checks too. See [What refiroo is](/docs/about/what-is-refiroo/) for the overview.

## Roles describe work

refiroo includes nine general predefined roles. People can hold several, and an administrator can create custom roles from groups of actions.

| Role | Main responsibility |
| --- | --- |
| Reader | Browse data without changing it. |
| Contributor | Prepare changes in change sets, without editing Live or publishing. |
| Data steward | Maintain Live data, prepare and publish change sets, and run bulk work. |
| Data owner | Stewardship plus publication approval, following changes, and copying or moving data. |
| Model administrator | Author, install and select model releases. |
| Workspace administrator | Manage workspaces and their default. |
| Integration administrator | Manage webhook subscriptions and follow changes. |
| Operator | Monitor the service and inspect deployment settings. |
| Security administrator | Manage people, groups, clients, roles and grants. |

The role's scope still matters. Model, workspace, integration, operations and security administration do not automatically include permission to browse or edit reference data. See [Roles and grants](/docs/administer/roles-and-grants/) for the full rules.

## Grants say where a role applies

A **grant** gives a role to a person, group or client, either across the instance or in one workspace where the role supports it. Group members inherit the group's grants. Several grants combine their permissions.

A workspace grant can narrow writes to selected applications or record types. This limits what the holder may change; it does not hide other types they may browse. A grant naming a type removed from the model grants nothing for that missing type.

The interface offers the actions the person can complete in the current workspace. A Reader has no editing controls. A Contributor can propose a change in a change set. **Settings → Account** shows **What you can do**, with roles and permissions by workspace. If an expected action is missing, check the workspace and this account summary, then ask a security administrator. Permission changes apply on the next request, so an action already open can still be refused.

## Approvals govern publication

A workspace can require publication approval and a different person to decide it. A submitted change set is frozen for review; an authorised person must withdraw the request before it is edited. Approval publishes the submitted content, while sending it back requires a comment.

Holding Publish alone does not bypass a required approval. The exact policy also determines whether someone holding both Publish and Approve may publish directly. See [Approval policies](/docs/administer/approval-policies/) and [Inbox and approvals](/docs/use/inbox-and-approvals/).

## People and systems sign in differently

People can use a local account or the organisation's configured sign-in provider. Local accounts support an authenticator app, recovery codes and passkeys. Administrators can require a second factor. Provider-only accounts use the provider's security and cannot add local second factors or passkeys.

People can review and end their browser sessions on Account. A system uses its own **client**, with its own credentials and grants. Reading a consumer API requires a separate grant for that API in a workspace; no general role opens it, and these grants belong to clients, not people or groups.

See [Sign-in](/docs/administer/sign-in/), [Your account](/docs/use/account/) and [Clients](/docs/administer/clients/).
