# Example model set

`model/rdm-starter.json` is an **example** of what RDM Engine can do. It configures one reference-data
use case as three applications: RDM Master, RDM Systems and RDM Translations. They are showcases of
engine capabilities, not modules of the engine and not a template a new model has to follow. A model
may rename, reshape, replace or remove all three, and may add applications for entirely different
domains.

This page explains how applications, the model and the engine relate, lists what each example
application declares, and explains why the three differ.

## Engine, model and application

| Layer | What it is | What it knows |
| --- | --- | --- |
| **Engine** | Generic capabilities: object types, typed attributes, relation types and their patterns (containment, recursive hierarchy, cross-reference), view types (`table`, `mappingGrid`, `relationMatrix`, `tree`), detail composition, live editing, change sets, publications, model releases, paged APIs | Nothing about any application, object type or relation key. No backend or frontend code branches on a model key. |
| **Model** | A versioned JSON declaration of applications, object types, attribute types, relation types, allowed relationships and views | The structure of one use case |
| **Application** | A named selection of object types plus the views declared for it | Only what its declaration says |

Every application gets the **same feature set**. Any application may declare any view type, use any
relation pattern and have its own detail composition. Every application runs under the same live,
change-set and publication rules. An application's name, key and domain mean nothing to the engine.
"Master", "Systems" and "Translations" are labels in the example, nothing more.

Whether a view declaration is valid depends only on the structure it refers to, never on the
application that declares it. Model validation checks every view against its view-type contract
([APPLICATION_MODEL.md](APPLICATION_MODEL.md#applications-and-views)). For example, a `tree` needs
a containment path from its root types to its node types, and a `mappingGrid` needs a voluntary
association relation. If the model declares that structure, any application can have the view.

## What the example applications declare

| Application | Object types | `table` | `tree` | `mappingGrid` | `relationMatrix` |
| --- | --- | --- | --- | --- | --- |
| RDM Master | domain, codelist, master-value | domains, codelists, master-values | `domain-hierarchy` | `master-to-system-mapping` | – |
| RDM Systems | system, system-group, system-value, codelist, master-value | systems, system-values | `system-hierarchy` | `system-to-master-mapping` | `codelists-by-system`, `master-values-by-system` |
| RDM Translations | language, translation-group, translation, codelist, master-value | languages, translations | – | – | `codelist-translations`, `master-value-translations` |

Structure that the declarations rely on:

- **Master:** a containment chain domain → codelist → master-value, with master values nesting
  recursively (`master-value-has-child`).
- **Systems:** system → system-group (recursive) → system-value, with system values also directly
  under a system. There are two voluntary associations: `system-value-maps-to-master`
  (many-to-many) and `reference-has-system-representation` (a domain or codelist to system values).
- **Translations:** language → translation-group (recursive) → translation. There is also a
  required, uniquely scoped ownership binding `object-has-translation` from a domain, codelist or
  master value to a translation.

The example also declares one consumer API, `rdm` ("RDM API", contract version 1): domains,
codelists and master values under public names, the lists `domains`, `codelists` (by domain) and
`values` (by codelist, in sort order), and the event `values-changed` for master values created,
updated or deleted. It is there so a fresh installation has a consumer API to read, document and
subscribe to; a model may declare none, or many of a different shape.

## Why the example applications differ

**The applications differ only because the example model declares different views for them.** The
engine offers the same capabilities to all three. Each gap in the table above is example content that
nobody has declared yet. None of them is a limit of the application or a rule about how that kind
of application should look. The example spreads the view types over its applications so that each
contract appears at least once, and more than once where the contract serves different shapes. For
the tree, those shapes are a fixed chain and a recursive group level with mixed types.

What each gap would take:

| Gap | Possible with the existing structure? | What a model would declare |
| --- | --- | --- |
| Translations has no `tree` | Yes | A `tree` rooted at `language` over language, translation-group and translation. All three types carry the boolean `active`, so availability can be offered too. |
| Master has no `relationMatrix` | Yes, once the column and cell types belong to the application | For example, master values by language over `object-has-translation`, with `language` and `translation` added to Master's `objectTypeKeys` (a matrix's row, column and cell types must belong to the application). |
| Translations has no `mappingGrid` | Not over its own translation binding | A mapping grid accepts only voluntary associations. It rejects containment and required-ownership bindings such as `object-has-translation`. This is a property of that relation, not of the application. A mapping grid over a voluntary association would be valid in Translations just as in Master or Systems. |

The rule for every gap is the same: the structure decides what a view can express, and the model
decides whether to declare it.

## Using the example

- **Read it as a demonstration.** It shows one way to combine the capabilities. It does not
  prescribe how many applications a model has, how they are split, what they are called or which
  views each one should have.
- **Do not copy its shape to be "correct".** A catalogue, an MDM-lite model or a single-application
  model is as valid as this three-application RDM example
  ([COMPOSABLE_DOMAINS.md](COMPOSABLE_DOMAINS.md)).
- **A different view set for a different application is never a design reason.** When one example
  application shows a view type and another doesn't, the explanation is "the model doesn't declare
  it". Adding the declaration is a model change, with no engine change.
- **Tests do not rely on the example's keys.** The test suite validates the example with every type
  and relation key renamed, and runs generated models whose keys (`vol-*`) share nothing with it. A
  view type is accepted only when it works for configurations other than the one that motivated it
  ([ROADMAP.md](ROADMAP.md): at least two object or relation configurations per milestone).

Planning documents sometimes name a milestone or an acceptance scenario after an example domain,
such as translations by language or a system hierarchy. That name describes the demonstration used to
accept the work. The capability being delivered is still the generic one.
