---
title: What refiroo is
description: One engine for shared reference data, shaped to your organisation and available to its systems.
reader: evaluator
---

refiroo is an engine for reference data: the fairly stable lists other systems depend on, such as codes, categories, names and the connections between them. A team defines its own reference-data applications with a **model**, without building separate software for each. refiroo supplies the screens, the API, validation, history, search, access control, approvals and publication.

## Bring scattered lists together

Reference data can be scattered across thousands of small spreadsheets, each team and system keeping its own copy, columns and version of the truth. People spend time reconciling those lists before they can use them together.

refiroo brings that work into one place. You can upload an existing workbook without first rebuilding its layout: an import profile says how its sheets and columns become records, fields and connections. A workbook can even be the starting point for a model. A model administrator reviews the proposed structure and mapping, checks issues and runs a dry run to see which rows can load and which need attention. Loading into a change set keeps the proposed data separate until it is reviewed and published. See [Workbook onboarding](/docs/model/workbook-onboarding/).

The agreed list then has a history, people responsible for it and connections to other lists. People edit it in the browser, export a workbook for colleagues and load their changes back; other systems read it through the API. Saved import profiles can read later versions of the original workbook. File loads meet the same rules as other changes. See [Importing and exporting](/docs/use/importing-and-exporting/).

## Give different codes a shared meaning

Consider the guide's example world: public transport stops in Graubünden, Switzerland. The same stop has a stop number, a SLOID identifier and a code in a ticketing system. Names are maintained in five languages. Without a shared place to connect them, each system keeps its own list, and people reconcile codes and names by hand.

With refiroo, a steward keeps the agreed meaning once, connects each system's code to it and supplies the names. Other systems read that agreed data. A code can change in one system without losing the connection to the stop it represents.

The guide uses public stop data and names, with a fictional ticketing system to show mappings. Source: opentransportdata.swiss, Service Points (Didok), Federal Office of Transport / SBB, snapshot 2026-11-02; Wikidata, CC0. These are examples of records and relationships a model defines.

## What makes it different

**One engine, many applications.** A model defines record types, fields, relationships and views. A new reference-data domain can use another model. Every application has the same capabilities; its model chooses the views it offers. The shipped applications are optional examples you can replace or remove. See [How refiroo works](/docs/about/how-it-works/).

**Connections that keep their meaning.** A place in a hierarchy, an equivalent code in another system and a translation are different connections, each with its own rules. The model defines which records may connect and how. See [Connections carry meaning](/docs/about/how-it-works/#connections-carry-meaning).

**Three kinds of change.** A live edit corrects today's data when saved. A change set prepares related changes separately, with approval where required, then publishes them together as one consistent publication. A model release changes the structure and rules. Daily work continues while changes are prepared. See [Three kinds of change](/docs/about/three-kinds-of-change/).

**One set of rules on every path.** Browser edits, API calls and bulk loads meet the same validation and permission checks. Values keep their types, connections follow their rules and a stale save cannot silently overwrite newer work. See [How refiroo protects data](/docs/about/data-quality-rules/).

**API first.** Everything the browser does is available through the API. Model-defined consumer APIs give other systems a common way to read agreed data, with a consistent shape within each contract. See [Sharing data with other systems](/docs/about/sharing-data-with-other-systems/).

**Governed changes.** Roles and narrowed grants control who may change which data. Approval policies govern publication, and history records who changed what and when; review comments can explain why. See [Who can do what](/docs/about/people-and-access/) and [Security, audit and privacy](/docs/about/security-and-trust/).

**Workspaces with their own models.** An organisation can keep several working areas in one installation. Each workspace uses its own selected model release, so workspaces can share a model or use different ones. See [How refiroo works](/docs/about/how-it-works/).

## Who it helps

| Responsibility | What refiroo helps you do |
| --- | --- |
| Data steward | Correct shared values and organise lists. |
| Mapping or localisation steward | Connect equivalent codes and maintain names in different languages. |
| Integration team | Load, read and synchronise agreed data. |
| Workspace administrator | Provide working areas and keep old ones readable. |
| Model administrator | Change the structure and rules of the data. |
| Operator | Run, monitor, upgrade and recover the service. |

These are responsibilities. [Roles and grants](/docs/about/people-and-access/) decide what each person may actually do.

## Where it fits

refiroo serves reference data: relatively stable information used to describe, classify or connect other data. It is not intended to store transactions such as purchases or journeys, or to replace the systems that process them. Its approval controls govern reference-data publication; it is not a general workflow engine.


It is not a general data catalogue, business glossary, lineage scanner or enterprise governance
suite. A small product catalogue or a lightweight master-data use can fit when its needs can
be expressed through the same records, fields, relationships and views. These are uses you
model; they do not add fixed domain modules to refiroo.
