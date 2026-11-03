# Documentation pilot: Records and Change sets

Read `guide/AGENTS.md` for the readers, the rules and the example world. This assignment adds one thing it
does not yet say: the guide is one part of the documentation. Documentation pages explain a capability;
guide pages (the four already in `src/content/docs/guide/use/`) take the reader through a task step by step.

Write two **documentation pages** for people who work in the browser (stewards first, and anyone who wants
to understand the capability):

1. **Records** (`src/content/docs/use/records.md`): what a record is, how records belong to applications,
   types and workspaces, what a record holds (fields, typed values, relationships, a place in a hierarchy,
   translations), validity periods, versions and why a save can be refused when someone else changed the
   record first, history (who changed what and when), deleting and what happens to dependent records, and
   who may read, create, change and delete records (the roles and permissions as refiroo defines them).
2. **Change sets** (`src/content/docs/use/change-sets.md`): what a change set is for and when to use one
   instead of a direct correction, how it works (it starts from live data or a publication, its changes stay
   apart from live data, other people keep correcting live data meanwhile), reviewing and validating,
   publishing and what happens to live edits made in the meantime, publications as read-only snapshots,
   withdrawing or discarding a change set, a change set prepared for a newer model release, approvals where
   they are required, and who may open, edit, review, approve and publish (roles and permissions).

How to write them:

- **Generic first.** Describe refiroo in general terms: "an application", "a workspace", "a record type".
  Never "open Network in the Graubünden workspace" in the text. The Graubünden stops are only the
  illustration: put the example in screenshot captions ("Above: the Network application in the Graubünden
  workspace, showing the stops of the canton") or in a clearly marked example after the general
  explanation.
- **Detailed.** Each section explains the rules, the states and the limits the reader meets, what the
  screen shows, and what happens on each outcome. Take the facts from the code and the documents named in
  `guide/AGENTS.md`; the roles and permissions from the permission catalogue in the code.
- **Link to the guide** for every task: where the page says the reader can do something, link to the guide
  page that shows the steps (`./find-records/`, `./correct-a-record/`,
  `./prepare-and-publish-a-change-set/`, `./translate-names/`). Do not repeat the steps.
- No JSON, no API paths, no internal names.

## Screenshots

Screens file: `PILOT.screens.json`

The screenshots named in that file are attached. Reference those that help as `/docs/screens/<name>.png`,
with a caption that says what the example shows. List any further screenshot you would want.

## Files you may edit

- `src/content/docs/use/records.md`
- `src/content/docs/use/change-sets.md`

## Report

The two pages, the screenshots used and wanted, anything you were unsure of, and anything in refiroo that
looked wrong.
