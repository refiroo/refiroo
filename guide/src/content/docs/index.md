---
title: refiroo documentation
description: Learn what refiroo does, look after shared data, shape a model, manage access, run the service or connect another system.
reader: evaluator
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
- [Security and trust](/docs/about/security-and-trust/) — access, protection and operational responsibilities.

## Look after data

As a data steward, begin with [Home](/docs/use/home/) to find the workspaces and work available to you. Then use:

- [Workspaces](/docs/use/workspaces/) — choose where you are working.
- [Find records](/docs/guide/use/find-records/) — search, filter and open the records you need.
- [Records](/docs/use/records/) — read and correct fields and understand refused saves.
- [Change sets](/docs/use/change-sets/) — prepare, review and publish coordinated changes.

## Shape a model

As a model administrator, begin with [Models](/docs/model/models/) to understand drafts, releases and activation. Then read:

- [The model editor](/docs/model/the-model-editor/) — find and change the model's definitions.
- [Types, attributes and relations](/docs/model/types-attributes-relations/) — define records, reusable fields and connections.
- [Applications and views](/docs/model/applications-and-views/) — arrange the screens people use.
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
