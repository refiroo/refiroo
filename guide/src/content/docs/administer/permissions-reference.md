---
title: Permissions reference
description: Compare every action group, the work it permits and the predefined roles that include it.
reader: access-admin
---

Use this reference when choosing a role or checking why someone cannot complete a task.
Open **Settings › People and access › Roles** with **Security administration** to compare the
matrix or create a custom role. Roles select whole action groups, not individual actions.
[Roles and grants](/docs/administer/roles-and-grants/) explains where grants apply and
how direct and group access combine. Follow [Create a custom role](/docs/guide/administer/create-a-custom-role/)
to put the groups together.

## Action groups and actions

The action names below are the words used when a permission refusal explains what is
missing. A role can allow an action while another rule still prevents it: for example,
a second-person approval rule, a submitted change set or a write restriction.

| Action group | Actions it allows | Predefined roles holding the group | Where it applies |
| --- | --- | --- | --- |
| Browse | Reading the model; Reading the workspace; Reading records; Reading change sets; Reading publications; Exporting records; Using this job. | Reader; Contributor; Data steward; Data owner; Agent | Selected workspaces or the whole instance |
| Edit live | Changing records. | Data steward; Data owner | Selected workspaces or the whole instance |
| Work in change sets | Changing records; Changing change sets; Submitting a change set; Withdrawing a submission; Using this job. | Contributor; Data steward; Data owner; Agent | Selected workspaces or the whole instance |
| Publish | Publishing a change set; Withdrawing a publication. | Data steward; Data owner | Selected workspaces or the whole instance |
| Approve publications | Withdrawing a submission; Deciding on a change set. | Data owner | Selected workspaces or the whole instance |
| Bulk and import | Sending a batch or an import; Using import profiles; Using source files; Using this job. | Data steward; Data owner | Selected workspaces or the whole instance |
| Copy and move | Using model mappings; Moving records; Using this job. | Data owner | Selected workspaces or the whole instance |
| Model authoring | Authoring models; Reading model releases; Using this job. | Model administrator | The whole instance only |
| Install a model | Installing a model release. | Model administrator | The whole instance only |
| Model release | Reading model releases; Installing a model release; Changing the workspace's model; Using this job. | Model administrator | Selected workspaces or the whole instance |
| Workspace administration | Changing the approval policy; Administering workspaces; Creating a workspace from a workbook. | Workspace administrator | The whole instance only |
| Integration administration | Managing consumer subscriptions. | Integration administrator | Selected workspaces or the whole instance |
| Feed | Reading the change feed. | Data owner; Integration administrator | Selected workspaces or the whole instance |
| Operations | Reading the service's operations; Testing the AI provider. | Operator | The whole instance only |
| Security administration | Security administration; Reading agent access; Changing agent access. | Security administrator | The whole instance only |
| Use AI proposals | Ask for AI proposals and summaries; keeping changes also needs their write permissions. | Data steward; Data owner; Model administrator; Workspace administrator; Integration administrator | Selected workspaces or the whole instance |

**Changing records** uses **Edit live** for Live and **Work in change sets** inside a
change set. One does not grant the other. **Withdrawing a submission** additionally
checks that the caller submitted it or can approve it. **Deciding on a change set** means
**Approve and publish** or **Send back**; approval publishes in the same step.
**Changing the approval policy** belongs to **Workspace administration**, not
**Security administration**.

**Creating a workspace from a workbook** also needs either **Install a model** or
**Model release**, together with **Bulk and import**, all granted for the whole instance.

**Reading model releases** is shared by **Model authoring** and **Model release**.
**Installing a model release** is shared by **Install a model** and **Model release**.
Installation alone does not change a workspace. **Changing the workspace's model**
activates a release or migrates that workspace.

**Security administration** includes people, groups, roles, grants, clients, sign-in
providers, second-factor policy, mail and signing keys. **Reading agent access** opens
its settings, assistants, agent clients and calls. **Changing agent access** registers,
blocks and restores the assistants people sign in with. Neither gives workspace data
access by itself.

**Operations**, held by the predefined **Operator** role, also includes **Editing the e-mail template**: changing the template and its logo, and sending a test message.
It includes **Reading the service's operations** and **Testing the AI provider**.
The test sends a real request and can incur a provider charge. **Integration administration**
manages consumer subscriptions and their deliveries; reading data through a consumer API
still requires an explicit client grant. See [Clients](/docs/administer/clients/).

## Using this job

**Using this job** means reading, following, cancelling or confirming a job. The required
group follows the kind of work; it is not a group to tick in a role.

| Kind of work | Group used |
| --- | --- |
| Batch, import, import profile and profile check | Bulk and import |
| Export | Browse |
| Move and inferred model mapping | Copy and move |
| AI record proposals | Work in change sets |
| Assistant task | Bulk and import |
| Workspace migration | Model release |
| Model dry run and model inference | Model authoring |

The requester can still see and cancel their own job after losing the group. Continuing
the work uses current permissions and can fail at the next step. See
[Jobs and limits](/docs/administer/jobs-and-limits/) for visibility and retention.

## What every signed-in person can open

Signing in allows people to inspect their own account and permissions and read general
information about refiroo. Listing workspaces returns only those where they hold a role;
it does not grant Browse. The browser's workspace selector offers readable workspaces.
The Changes page combines only the data and model changes the viewer is allowed to see.
An empty list does not prove that no work took place.

<!-- Inventory actions with no screen label: action:signed-in; action:workspaces.list; action:changes.read. -->
<!-- Predefined role identifiers, not browser labels: role:workspace-admin; role:integration-admin; role:security-admin. -->

## What someone without a group sees

Settings hides pages that need a group the person does not hold anywhere. Without
**Security administration**, for example, People, Groups, Roles, Clients, Agent access,
Sign-in, Signing keys and Mail are absent. Without **Operations**, Deployment, Operations
and AI are absent. Without **Integration administration**, Webhooks is absent. Consumer
APIs needs **Browse** somewhere; its entries still depend on the selected workspace.

In a workspace, the interface hides actions the person cannot perform. A Reader sees
**You can read this workspace** without edit actions. Someone who can propose changes
works through **Propose a change**; that does not give them Live editing or publication.
Narrowed writers see controls on the permitted record types. Other restrictions, such
as a frozen submission or a retired workspace, can also make an action unavailable.

If permissions change while a page is open, a previously visible action can be refused.
Read the action, required group and workspace in the message. Check direct grants,
group memberships and whole-instance grants, then reload after correcting access.
[Account › What you can do](/docs/use/account/#what-you-can-do) shows the person's
combined grants. A hidden control is not a reason to create another identity.

## The assistant ceiling

The predefined **Agent** role contains **Browse** and **Work in change sets**. These
same two groups are the maximum for every external assistant connection, even when its
person holds more. Actual access is the intersection with the person's or client's grants.
An assistant cannot use **Publish**, **Approve publications**, **Edit live**, access
administration or model administration through that connection. It prepares changes in
change sets created by its own person or client. See [Agent access](/docs/administer/agent-access/)
for registration, blocking and ending a connection.
