---
title: The starter model
description: See how an optional starter model combines refiroo's capabilities into three applications.
reader: evaluator
---

refiroo ships with a starter model as an option for reference-data work. It defines three
applications: RDM Master, RDM Systems and RDM Translations. A model may rename, reshape, replace
or remove them, or organise entirely different data. Their names do not give them special
capabilities; every application can declare any supported view when its structure allows it.

For selecting a workspace and application, see
[Workspaces](/docs/use/workspaces/) and [Applications](/docs/use/applications/) and
[Open an application](/docs/guide/use/open-an-application/).

## RDM Master

This application groups reference data into domains, codelists and master values. Its tables
support finding and maintaining records. Domain hierarchy arranges their containment; master
values can themselves contain master values. A mapping view connects master values to their
representations in other systems.

It demonstrates [records](/docs/use/records/), [lists and filters](/docs/use/lists-and-filters/),
[relationships](/docs/use/relationships/), [hierarchies](/docs/use/hierarchies/) and
[mapping grids](/docs/use/mapping-grids/).

![The starter model's RDM Master application with an empty Domains table](/docs/screens/example-rdm-master.png)

*Above: RDM Master in the Default workspace has Domains, Codelists and Master values collections.
Domains and Domain hierarchy are two views of the selected collection. This workspace has no data yet.*

## RDM Systems

This application holds systems, nested system groups and system values. A system value can
connect to a master value or represent a domain or codelist. It offers a hierarchy, a mapping
grid and matrices comparing codelists or master values against systems.

It demonstrates [relationships](/docs/use/relationships/), [hierarchies](/docs/use/hierarchies/),
[mapping grids](/docs/use/mapping-grids/) and [relation matrices](/docs/use/relation-matrices/).

![The starter model's RDM Systems application with an empty Systems table](/docs/screens/example-rdm-systems.png)

*Above: RDM Systems in Default offers Systems, System values, Codelists and Master values.
Systems and System hierarchy are visible tabs. The table is empty because this workspace has no records.*

## RDM Translations

This application holds languages, nested translation groups and translation records. A required
owning relationship connects each translation to what it translates. Matrices compare codelists
or master values against languages and allow creation and correction of related translations.
The model allows only one active translation per owner and language.

It demonstrates [records](/docs/use/records/), [relationships](/docs/use/relationships/) and
[relation matrices](/docs/use/relation-matrices/). See [Translations as an example](/docs/examples/translations/)
for how those pieces fit together.

![The starter model's RDM Translations application with an empty Languages table](/docs/screens/example-rdm-translations.png)

*Above: RDM Translations in Default offers Languages, Translations, Codelists and Master values.
No languages have been added to this workspace.*

All three applications share [Live editing](/docs/use/records/),
[change sets](/docs/use/change-sets/), [publications](/docs/use/publications/) and
[record history](/docs/use/history/). Access depends on
[roles and grants](/docs/administer/roles-and-grants/), rather than the application name.
Differences in their collections and views come from this model's declarations. For a populated
example using the same capabilities, see [The example data](/docs/examples/the-example-data/).

## A contract for other systems

The starter model also declares **RDM API**, contract version 1. It exposes domains, codelists
and master values under public names, with lists of domains, codelists by domain and values by
codelist in sort order. Its **values-changed** event reports master values created, updated or
deleted, watching changes to the public code, name, active flag and validity dates. Its object
reads include related system representations and translations, and its lookups and batch resolution
find records through their own or related identifiers. See
[The consumer API example](/docs/examples/the-consumer-api/) for the declaration and a populated
example of the same capability. This is an example contract a model can replace or omit. A security administrator grants
a client access to it in the intended workspace; see [Clients](/docs/administer/clients/).
The [model editor](/docs/model/the-model-editor/#consumer-contracts-and-the-structured-document-view)
holds its definition.

*Screenshot data: Source: opentransportdata.swiss, Service Points (Didok), Federal Office of
Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. See [The example data](/docs/examples/the-example-data/)
for sources and fictional additions.*
