---
title: The API reference and Consumer APIs pages
description: Find the documentation and handover details for integrations without changing the active model.
reader: access-admin
---

Use **Settings › Connections › API reference** to find the interactive reference for refiroo’s interfaces. Use **Consumer APIs** to inspect the read interfaces declared by the active model. These pages are read-only: neither changes a definition nor grants access.

## API reference

**Sources** lists **Management API**, its version and the engine version, followed by the available consumer APIs at their contract versions. Select a source name to open its interactive reference. The **OpenAPI document** column opens or downloads the corresponding document for an integration developer.

The Management API supports the browser and integrations. A consumer API exposes a model-defined selection of data for consuming systems. Its contract version is separate from the engine version and model release version. Use the displayed versions when discussing an integration with its owner.

![API reference Sources table with the management interface and a consumer interface](/docs/screens/admin-api-reference.png)

## Consumer APIs

This Settings page is offered to people with **Browse**. It identifies the active model release and offers **Open the release**. For each available consumer API it shows its name, description, contract version, **Base URL**, **OpenAPI document** and a table of operations. Use the copy controls beside the addresses to hand them to the integration owner; select an operation’s description to open its reference.

These are connection details for the integration team. You do not need to type them into another Settings page. For their meaning and use, see [Consumer APIs](/docs/integrate/consumer-apis/).

Definitions change through a model release, not on this page. When **The active release declares no consumer API** appears, **Open model** takes a model administrator to the model. Ask them to declare the required interface if one is needed.

The **Change feed** section states how long change entries are kept. Once an integration falls behind that retention, it needs recovery rather than continuing from an expired position. The operator sets retention; the integration owner handles synchronisation.

![Consumer APIs with an interface’s version, copy controls and operation descriptions](/docs/screens/admin-consumer-apis.png)

## Documentation is separate from access

Being able to open a reference does not authorise reading its data. Consumer API descriptions are publicly readable; data needs an explicit grant to a **client**, for the chosen API in one workspace. A management role never substitutes for that grant, and people do not receive consumer API grants. The list of APIs available to a client is limited to its grants. Follow [Grant a consumer API to a client](/docs/guide/administer/grant-a-consumer-api-to-a-client/).

If a page fails to load, use its retry control. A failure to read the definitions does not mean the model declares none. Check the selected workspace and the active release before sending connection details.
