---
title: Translations as an example
description: See how records, ownership and relation matrices can hold names in several languages.
reader: evaluator
---

Names in several languages are one use of refiroo's generic capabilities. The optional
[starter model](/docs/examples/the-starter-model/) configures this as RDM Translations;
the [guide's example data](/docs/examples/the-example-data/) configures it as Names.
Neither application is built into refiroo's behaviour. A different model can change the types,
fields, relationships, rules and views, or omit this use entirely.

## How the pieces fit together

A language is a [record](/docs/use/records/). A translation is another record with its own name,
content fields, version and history. It sits beneath a language, directly or through groups.
A required [owning relationship](/docs/use/relationships/#associations-ownership-and-containment)
connects it to the record being translated. That owner can be in another application in the same
workspace.

In the starter model, a translation can hold a translated name, description and value, plus
Active. Its ownership rule permits only one active translation for the same owner and language.
Keeping an inactive translation differs from deleting it. Deleting its owner can also delete
the translation, so the deletion impact must be reviewed first.

A [relation matrix](/docs/use/relation-matrices/) brings these connections together: owners
are rows, languages are columns and translations appear in their cells. The starter model offers
matrices for codelists and master values. The guide's model offers them for municipalities and
operators. Each view chooses its displayed fields and permitted actions.

![A municipality's existing Romansh name open in a matrix cell editor](/docs/screens/matrix-cell-editor.png)

*Above: in Names, Chur · rm shows Cuira as Translated name, with Active selected. Open Chur (rm)
opens the translation record itself. The editor was cancelled without changing it.*

A One cell means one translation counts under the model's condition, not that its wording has
been checked. A None cell lacks a related record; it is different from a translation record
whose text is blank. Inactive means records exist but none counts; History only means an earlier
publication held a related record that is absent now. The matrix can filter missing or inactive cells across selected languages.
For those tasks, follow [Fill in a relation matrix](/docs/guide/use/fill-in-a-relation-matrix/).
For creation from an owner's page, follow
[Create an owned related record](/docs/guide/use/relate-records/#create-an-owned-related-record).

## The same view beyond languages

![A matrix with systems as columns and system-code records in its cells](/docs/screens/matrix-municipalities-by-system.png)

*Above: Municipalities by system in Systems compares municipalities with their codes in different
systems. The columns are systems rather than languages, using the same relation-matrix capability.*

refiroo stores the values people supply; a relation matrix does not generate translated text.
The data can be corrected in Live or prepared in a [change set](/docs/use/change-sets/), with
the same validation, [permissions](/docs/use/records/#who-may-read-and-change-records)
and conflict protection as other records. [History](/docs/use/history/) records the changes;
[publications](/docs/use/publications/) preserve agreed snapshots.

If an active translation already exists for the owner and language, open and correct it instead
of adding another. An owned translation must be created with its required owner connection;
removing that connection by itself is refused. Inspect an inactive translation before adding
a replacement, since changing its Active field can make it count again.

*Screenshot data: Source: opentransportdata.swiss, Service Points (Didok), Federal Office of
Transport / SBB, snapshot 2026-11-02. Wikidata, CC0. See [The example data](/docs/examples/the-example-data/)
for sources and fictional additions.*
