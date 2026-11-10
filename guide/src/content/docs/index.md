---
title: refiroo documentation
description: Learn what refiroo does, look after shared data, shape a model, manage access, run the service or connect another system.
reader: evaluator
head:
  - tag: title
    content: refiroo documentation
---

refiroo is where a team keeps the shared lists, codes, names and connections that other systems depend on. A model shapes the applications and rules; people maintain the data in the browser, and other systems read or change it through APIs.

## A few ideas to begin with

- A **model** defines record types, fields, relationships and views. An **application** groups them into a working area.
- A **workspace** holds data under one model release. Different workspaces can use different models.
- **Live** is the current data. A **change set** prepares changes separately; publishing applies them and creates a read-only **publication**.
- **Roles and grants** decide what each person or integration may read and change.

Read [How refiroo works](/docs/about/how-it-works/) for these ideas and [Three kinds of change](/docs/about/three-kinds-of-change/) to distinguish editing records, publishing data and releasing a model.

## Evaluate refiroo

Begin with [What refiroo is](/docs/about/what-is-refiroo/) to decide whether it fits your shared reference data. Then explore:

- [How refiroo works](/docs/about/how-it-works/) — models, records, connections and workspaces.
- [The example data](/docs/examples/the-example-data/) — public transport stops showing the capabilities together.
- [Sharing data with other systems](/docs/about/sharing-data-with-other-systems/) — how integrations read, supply and follow data.
- [How refiroo protects data](/docs/about/data-quality-rules/) — model rules, concurrent saves and reviewed changes.
- [Who can do what](/docs/about/people-and-access/) — responsibilities, grants and sign-in.
- [Security and trust](/docs/about/security-and-trust/) — access, protection and operational responsibilities.
- [How refiroo is built](/docs/about/how-it-is-built/) — technology, deployment and recovery.
- [Versions, compatibility and licence](/docs/about/compatibility-and-licence/) — stable contracts and the running source offer.
- [Accessibility and devices](/docs/about/accessibility/) — keyboard and phone use, display choices and evidence limits.

## Look after data

As a data steward, begin with [Home](/docs/use/home/) to find the workspaces and work available to you. Then use:

- [Workspaces](/docs/use/workspaces/) — choose where you are working.
- [Find records](/docs/guide/use/find-records/) — search, filter and open the records you need.
- [Records](/docs/use/records/) — read and correct fields and understand refused saves.
- [Change sets](/docs/use/change-sets/) — prepare, review and publish coordinated changes.
- [Importing and exporting](/docs/use/importing-and-exporting/) — exchange files and repeat a checked load.
- [Copying and moving](/docs/use/copying-and-moving/) — prepare records in another workspace.
- [AI and your data](/docs/use/ai-and-your-data/) — decide whether to use optional proposals or an assistant.
- [Notification settings](/docs/use/notifications-settings/) — follow publications and choose immediate email or digests.

## Shape a model

As a model administrator, begin with [Models](/docs/model/models/) to understand drafts, releases and activation. Then read:

- [The model editor](/docs/model/the-model-editor/) — find and change the model's definitions.
- [Types, attributes and relations](/docs/model/types-attributes-relations/) — define records, reusable fields and connections.
- [Applications and views](/docs/model/applications-and-views/) — arrange navigation and the screens people use.
- [Record pages and tables](/docs/model/record-pages-and-tables/) — choose panels, columns and filters.
- [Workbook onboarding](/docs/model/workbook-onboarding/) — turn an existing file into a reviewed model and loading profile.
- [Releases](/docs/model/releases/) — check, install and activate a model release.

## Administer access

As an access administrator, begin with [Roles and grants](/docs/administer/roles-and-grants/) to understand what access allows and where it applies. Then use:

- [People and groups](/docs/administer/people-and-groups/) — manage accounts and shared membership.
- [Sign-in](/docs/administer/sign-in/) — manage how people authenticate.
- [Clients](/docs/administer/clients/) — give another system its own identity and access.
- [Audit](/docs/administer/audit/) — inspect administrative changes.

## Run the service

As an operator, begin with [What you run](/docs/run/overview/) to understand the services and storage. Then follow:

- [Install with Compose](/docs/run/install-with-compose/) — install and start refiroo.
- [Configure the installation](/docs/run/configure/) — choose the settings for your deployment.
- [Back up and restore](/docs/run/backup-and-restore/) — protect data and rehearse recovery.
- [Production checklist](/docs/run/production-checklist/) — check the deployment before use.

## Connect another system

As an integrator, begin with [Integrating with refiroo](/docs/integrate/overview/) to choose an interface and sequence. Then read:

- [Signing in and tokens](/docs/integrate/signing-in-and-tokens/) — authenticate the integration's client.
- [Identifiers, paging and errors](/docs/integrate/identifiers-paging-and-errors/) — traverse data and handle refusals.
- [Consumer APIs](/docs/integrate/consumer-apis/) — read the business contract declared by the model.
- [Load, then follow changes](/docs/guide/integrate/load-then-follow-changes/) — keep another system in step.

## Tasks and reference

Choose a task in [User journeys](/docs/journeys/) for a path through the relevant explanations and guides. Open the [API reference](/docs/api/) for the operations, request fields and response schemas served by your instance.

To find a particular topic, choose **Search** at the top of the documentation, or press **Ctrl+K** (**Command+K** on a Mac).
