# Use refiroo by capability, and the example applications

Read `guide/AGENTS.md` again: it now says to document refiroo's capabilities, with applications only as
examples in their own section, and where documentation pages and guides live.

The person who owns refiroo said: translation is not a refiroo capability. It is an application (RDM
Translations in the starter model, Names in the example data) built from generic capabilities. Applications
must be clearly examples and options, never features of refiroo.

Write these pages. Documentation pages explain the capability (what, why, how it works, rules, states,
limits, who may do what) and link to its guides; guides are generic steps with the example only in
screenshot captions, in the detail `guide/AGENTS.md` asks for. Use the existing pages (`use/records.md`,
`use/change-sets.md`, `guide/use/find-records.md`, `guide/use/correct-a-record.md`,
`guide/use/prepare-and-publish-a-change-set.md`) as the standard; do not edit them except to add links to
the new pages where a reader would want them.

| Capability | Documentation page | Guide |
| --- | --- | --- |
| Workspaces and applications | `use/workspaces-and-applications.md`: what a workspace is, that a model defines the applications and the views each offers, the four kinds of view (table, tree, mapping grid, relation matrix), switching workspace | `guide/use/open-an-application.md` |
| Relationships | `use/relationships.md`: kinds of relationship a model may define, which records a relationship may choose (candidates) and why a record is not offered, required and optional ones, what happens on removal | `guide/use/relate-records.md` |
| Hierarchies | `use/hierarchies.md`: trees, parents and children, moving, what a model allows | `guide/use/arrange-records-in-a-tree.md` |
| Mapping grids | `use/mapping-grids.md`: mapping codes of other systems to records, mapped, unmapped and ambiguous codes | `guide/use/map-codes-between-systems.md` |
| Relation matrices | `use/relation-matrices.md`: records against records (for example records against languages), cell states, filters, coverage | `guide/use/fill-in-a-relation-matrix.md`: replaces `guide/use/translate-names.md`; reuse what was right in it, made generic |

Example applications (`examples/`), short showcase pages:

- `examples/the-starter-model.md`: refiroo ships with a starter model as an option; its three applications
  (RDM Master, RDM Systems, RDM Translations), what each shows and which capabilities it uses (links); a
  model may rename, reshape, replace or remove them. Source: `docs/EXAMPLE_MODEL.md`, `model/rdm-starter.json`.
- `examples/translations.md`: how the RDM Translations application keeps names in several languages from
  records, an owning relationship and relation matrices; that it is configuration, not a feature; links to
  those capabilities.
- `examples/the-example-data.md`: the Graubünden public transport data used in this documentation's
  screenshots (Network, Systems, Names), its sources and attribution (`samples/SOURCES.md`), and that Names
  is the same idea as RDM Translations.

## Screenshots

Screens file: `CAPABILITIES.screens.json`

The screenshots named in that file are attached and are the real screens; reference them as
`/docs/screens/<name>.png` with captions saying what the example shows. The pilot's screenshots in
`PILOT.screens.json` may also be referenced. List any screenshot you still need.

## Files you may edit

- `src/content/docs/use/workspaces-and-applications.md`
- `src/content/docs/use/relationships.md`
- `src/content/docs/use/hierarchies.md`
- `src/content/docs/use/mapping-grids.md`
- `src/content/docs/use/relation-matrices.md`
- `src/content/docs/use/records.md`
- `src/content/docs/use/change-sets.md`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/examples/*.md`

## Report

The pages written or changed, the screenshots used and still needed, anything you were unsure of, and
anything in refiroo that looked wrong. Say whether `guide/use/translate-names.md` can be deleted (its
content now in the relation-matrix guide); do not delete it yourself.
