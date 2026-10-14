# Product overview

RDM Engine lets a team define and run its own reference-data applications without building separate
software for each one. A model describes the kinds of records, their fields, how they connect and how
they are shown; the engine supplies the screens, the API, validation, history and search.

For example, a company may call the same delivery method "Collection" in its central list, "PICKUP"
in its webshop and "Store collection" in its warehouse system. A data steward keeps the shared meaning,
connects each system's value to it and supplies the translated labels. Other systems then read the
agreed data instead of keeping lists of their own.

This page is the product overview. The [product functionality guide](product-functionality/README.md)
holds the detailed capability catalogue, user stories, journeys and acceptance scenarios; how the
engine is built is in [ARCHITECTURE.md](ARCHITECTURE.md).

## Who it is for

| Who | Typical job | What they get |
| --- | --- | --- |
| Data owner or steward | Correct a code, add a value, organise a list | Colleagues use accurate shared data at once |
| Mapping steward | Connect a system's value to its shared meaning | Systems exchange the intended equivalent |
| Localisation steward | Supply and correct translations | People see the right label in their language |
| Integration team | Read, load and synchronise reference data | Systems agree without manual reconciliation |
| Workspace administrator | Set up working areas and retire old ones | People know where to work and what is read only |
| Model administrator | Define a new domain or change its rules | The application evolves without custom code |
| Service operator | Run, upgrade and recover the service | People can rely on the service and its data |

These are responsibilities, not permission roles: sign-in and permissions arrive in 0.12.

## What makes it different

- **One engine, many applications.** Another reference-data domain is another model, not another
  application. Every application gets every capability; the bundled Master, Systems and Translations
  applications are [examples](EXAMPLE_MODEL.md), not built-in modules.
- **Connections that keep their meaning.** A record's place in a hierarchy, its equivalent in another
  system and its translation are different kinds of connection, each with its own rules.
- **Simple daily work.** A correction is live when saved. Coordinated changes are prepared separately,
  without blocking daily work.
- **One set of rules on every path.** The browser, the API and bulk loads go through the same
  validation; no channel is a way around it.
- **API first.** Everything the browser does is available through the API, which is the product's
  main contract; the browser is one client of it.

## What you can do today

Status as of Base 0.8 (released 2026-09-29) and the 0.9 work delivered since. "Browser" means a person
can complete the task in the application; "API" means another system can.

### Find and understand data — browser and API

- Choose a workspace, then an application, and browse its collections; where the model groups them,
  fold and unfold the groups in the sidebar and open a group's page to find a collection by name.
- Search, filter by typed fields and sort lists of any size. Lists scroll continuously in both
  directions, show their totals and jump to a page, a value, the start or the end.
- Switch between the views a collection offers: a table, a mapping grid, a relation matrix or a tree.
- See in a list which records each row is related to, where the model shows a relationship as a
  column, and sort by it where each row holds at most one; filter a list to the records related to
  chosen records, or to none.
- Open a record to see its fields, its place in the hierarchy, its children, its relationships and its
  change history, and return to the list where you left it. Where a record may hold only one
  relationship of a kind, you set it or change it rather than adding another.
- Browse a hierarchy of any depth in the sidebar tree, and search it to find a record with its path;
  select several records there and drag them to a new parent together.
- Export what a collection page shows, with its filters, as an Excel workbook, CSV or JSON Lines; a
  notification says when the file is ready, with Download and the job's page.
- Export a collection as a workbook for people: the table's columns, its relationship columns as
  lists of names, a sheet per chosen relationship, coloured as the app is; edit it in Excel and
  import it back without a profile, changing exactly what was edited, refused where someone else
  changed a record meanwhile. Records that belong to the exported ones, such as translations, can be
  laid out as a column per parent (a language's group): fill a new language's column to add every
  translation at once. Cells naming another record choose from a list of the records allowed.

### Keep data accurate — browser and API

- Add, edit and delete records, edit a field in place (the name and subtitle in the record's header
  too), connect and disconnect related records. Where the model limits which records a relationship
  may choose, only those are offered, everywhere it can be chosen.
- A save is live immediately and recorded in the record's history. If someone else changed the record
  meanwhile, nothing is overwritten: your input is kept and the newer version is shown.
- Deleting a record first shows what else it would remove or disconnect, and asks for confirmation.
- Mark a value unavailable through its availability field, as an ordinary edit.
- Select records in a collection (by hand, a range, or every record the search and filters match)
  and, after a preview of what will change and what will be refused, set or clear fields on all of
  them at once, add, remove, replace or clear their relationships of one kind, or delete them with
  what depends on them; records someone else changed meanwhile are refused, not overwritten.

### Prepare changes together — browser and API

- Open a change set to prepare several related changes away from live data, while others keep
  correcting live data.
- Start it from current live data or from an earlier publication, and prepare it against a newer
  model version than the one in use.
- **Review changes** lists every record and relationship the change set adds, changes or removes, with
  each changed field before and after.
- Validate it, then publish it: its changes apply together over current live data, unrelated live
  edits survive, and a conflict publishes nothing and loses no one's work.
- Every publication is kept as a read-only snapshot you can browse; withdrawing a publication keeps
  its history.

### Map values between systems — browser and API

- A mapping grid shows each source value as mapped, unmapped or ambiguous, across the whole list.
- Choose, replace or clear a value's target in one action, with search over the candidates.

### Fill translation and coverage gaps — browser and API

- A relation matrix shows records against the values of another list, for example values by language,
  with each cell current, missing, inactive or kept only in history.
- Filter to the gaps across the whole list, and create, correct, link or unlink from a cell.
- A second active translation for the same target and language is refused.

### Organise hierarchies — browser and API

- In a tree, add a child, rename, set availability and move a record by menu, keyboard or drag and
  drop, including to the top level. Invalid destinations are shown with the reason.
- In a change set, reshape the hierarchy: move a record where another type belongs, change a record's
  type, insert or remove a level. A preview shows every affected record before anything changes;
  records keep their identity, and what a new type has no place for is kept in history and offered
  back later.

### Check and set up the deployment — browser and API

- In **Settings** (the gear in the top bar), see what the deployment runs (engine version, schema
  languages, active model release, database revision) and how it is configured: every setting with
  its value, its default and where it came from, and the capability groups on or off. Settings are
  read here, never edited; secrets show only whether they are set.
- Choose the theme and the default table density for this browser.
- In Settings › **Integration**, read each consumer API the active release declares (its version,
  base URL, exposed types, lists and events), follow and cancel jobs beside the batch, job and feed
  limits, and open each job's page with its state, progress and, for an export, what the file
  holds and Download; start an export of any types of a workspace; and open each API's reference.
  On **Webhooks**, subscribe a receiver to a consumer API's
  events, one per request or batched, with the object or as a notification only, in RDM JSON or
  CloudEvents 1.0; keep the signing key shown once, and see whether delivery is going, why a subscription
  stopped and what fixes it; edit, suspend, resume and delete subscriptions. Each webhook's
  **Deliveries** list what was sent, with each attempt, the request and the receiver's answer.

### Manage workspaces — browser and API

- In Settings › **Workspaces**, create, rename, retire, reactivate and delete workspaces, and choose the default. A retired
  workspace stays readable; a workspace that was ever published can only be retired.

### Manage the application model — browser and API

- In Settings › **Model**, inspect installed model releases, compare them and export them.
- Edit a model draft as JSON, validate it, install it as a new release and activate it. Activation is
  refused when existing data would not fit; the previous release stays available to roll back to.
- Through the API, change a draft by typed operations with a readable history, undo and redo; a
  change that would need a migration of released structure is refused with its impact.
- In the model editor, change a draft without writing JSON: applications, types in their containment
  tree, attributes, relation types, the relationship matrix and navigation groups, each marked new,
  changed or released; move attributes and types by drag or Move to…; read the issues and the history,
  undo and redo; install and activate in one confirmed step.
- Preview a type's record page and table from the draft over real records before installing it, and
  lay out its panels, fields, columns, filters and sort in place, each change a step with undo.
- Define the draft's consumer APIs in the same editor: what each exposes, its fields, related
  records, operations, lists, match rules, events and filters, each change a step with undo; read the
  schema of its message and a message example before installing; see at once when a change needs a
  higher contract version, and raise it in a step.

### Integrate other systems — API

- Look up records of every type at once, or list every relationship in a workspace, in live data, a
  change set or a publication.
- Query one record type by field values, by ancestor (by its ID, or by its name or a field) and by a
  related record, choosing the fields returned and including related records.
- Ask which records a relationship may choose, as the model limits them, and have a relationship
  outside those refused.
- Declare a business validity period on a record type and read the records valid on a date (`asOf`).
- Load up to a million records in one bulk request, run inline or in the background: create, update,
  upsert by a unique key, and delete records; create, ensure, change and remove relationships (by
  their ID, or by their two records, so a removal sent again changes nothing), and replace a
  record's whole set of related records; each item with its own outcome. Choose all-or-nothing or
  item-by-item, preview a background load without writing anything before applying it, retry safely
  with an idempotency key, follow progress and cancel.
- Follow a workspace's changes in order: every change to live data has the next number in the
  workspace's change feed, with no gaps, so an integration reads on from the last number it
  processed, resumes after an interruption and recognises repeats. A publish lists each record and
  relationship it changed, then itself. Entries name what changed and why, never values. After the
  retention period an integration is told which publication to re-read, or to export, before it
  reads on.
- Follow any job as it changes: the engine pushes the job at once and after each change, until it
  ends.
- Export a stated scope of a workspace (live data, a change set or a publication; chosen types with
  their own criteria, a subtree, a business date, with or without relationships) as JSON Lines, CSV
  or an Excel workbook, read at one instant and described by its job: counts, context, the change
  feed position it equals, size and checksum. The JSON Lines file sent back as a bulk request changes
  nothing; edited, it updates only the records nobody changed since.
- Import a file into a workspace, live or into a change set, as a job: an Excel workbook or a CSV
  file through an import profile kept in the engine (which sheets and columns load which records,
  values, parents, relationships and related records such as translations), a JSON Lines file of
  bulk items, or an export sent back. Each row's outcome names its sheet and row; a row that cannot
  load is refused with every failing cell, and the rest load or, all-or-nothing, none. A preview
  tries the file against the data without changing anything and says what loading it would do, row
  by row and column by column, before it is confirmed. In the browser, Import on a collection page or
  on Jobs previews a file, shows its refused rows and how its columns were read, and loads it
  on confirmation. Another workspace's export loads as the workspace's own records, whole, and sent
  again changes nothing.
- Keep a workbook with a model draft and read its profile: its sheets' lists and header rows, and per
  column what its values are, whether it identifies a row, how its values are split, the values that
  stand for nothing and where else the same values occur; then dry-run the whole file through an
  import profile against the draft's model, as if it were installed, and read what the import would
  do, how that differs from the last dry run, and the rows behind each figure, with nothing written.
  Map the workbook step by step in the draft's own import profile, undone like any model change,
  kept valid as the model is renamed and reorganized, and dry-run again after each step; installing
  the draft saves the profile for the load. A lookup may create the list values it names.
- Start a draft from a workbook and map it in the model editor: the sheets and columns beside the
  model, a column's mapping in the centre, Map to… by keyboard or by dragging a column onto a type,
  value maps, the dry run after each step with the rows behind each figure; then load the workbook
  into a new change set in one confirmed dialog and review and publish it.
- Have the engine propose the model and its mapping from a workbook, as a new application or as
  additions to the model: each shape it recognises (keys, parents, code lists, lookups, flag sets,
  multi-valued cells, translations, external IDs, placeholders, drifting names) becomes one step in
  the editor, marked as proposed with why and its alternatives, changed like anything else; propose
  again after a newer workbook, keeping what you decided and reporting where the workbook disagrees.
- Load the next version of a workbook through its saved profile: see what differs before anything
  is written (columns new, missing or renamed, new list values, names that drifted, records the file
  no longer names, the profile against the current model, what the load would do), accept a rename
  or ignore a new column, then load it into a new change set whose review holds only the
  differences. Records missing from the file are kept, or deleted in the change set when the
  profile says so.
- Declare consumer APIs in the model: the read-only contracts other systems will use, written as
  what each one exposes, offers, looks like and filters by, with defaults for what is left out, and
  checked so that a breaking change needs a new contract version. Another system reads one business object through
  such an API by its record ID, in the declared shape, or reads its declared lists page by page,
  narrowed by the API's parameters, or looks business objects up by a code, ID or name, its own or a
  related record's, scored and ordered by the API's declared weights.
- Read the API reference at `/docs`, which works without internet access.

### Use it comfortably — browser

- Keyboard operation throughout, narrow-screen layouts, light and dark mode, resizable panels and
  display preferences. Accessibility and visual regression checks run on every release.

## What is planned

| Release | What it adds |
| --- | --- |
| 0.9.0-alpha.1 | PostgreSQL as the only database, with real concurrency: workspaces write in parallel (in progress) |
| 0.9 | Bulk relationship and mapping loads; the consumer APIs (lookup by code across systems, lists, crosswalks) with change events that carry the changed data, and signed webhooks; import and export of files with a preview |
| 0.10 | Turn a spreadsheet into a working application; one structured editor for the model and the import mapping ([design](MODEL_AUTHORING.md)) |
| 0.11 | Production readiness: performance at scale, several servers, monitoring, rehearsed backup and restore, moving workspaces between model versions in stages |
| 0.12 | Sign-in for people and systems, permissions per application, record type and operation, rotating webhook signing keys |
| 1.0 | Change released structure through the editor (renames, splits, merges) with a migration preview; reusable model modules |

The [roadmap](ROADMAP.md) has each release's scope and exit criteria.

## Change rules

- **Daily reference data:** adding or correcting a record, field, translation, parent or ordinary
  relationship is a direct live operation. A save validates the data, prevents silent overwrites and
  records the change. It needs no change set and creates no publication.
- **Coordinated data changes:** a user may choose to work in a change set. Its changes stay separate
  until publishing applies them together over current live data. Unrelated live changes survive;
  conflicting or invalid changes publish nothing and keep both the change set and live data.
- **Application definitions:** a model draft changes the allowed structures and rules. Installing it
  creates an immutable release; activating it is a separate step after a compatibility check. A data
  change set is not a model editor, and replacing the bootstrap model file does not activate anything.

These rules apply equally to mapping, translation, hierarchy and bulk work. Touching many records is
not a reason to require a change set, and any additional mandatory review step needs a stated user
benefit and an explicit product decision.

## Boundaries

The product is focused on reference data. It is not intended to become a general data catalogue,
business glossary, lineage scanner or enterprise governance suite. Other applications are supported
where the same record, field, relationship and view model is genuinely useful, but reference data and
its integration remain the design centre.

Neighbouring domains such as MDM-lite and small, specific product catalogues are modelled on the engine,
not built into it. A capability they motivate must be generic, have a second real use and work with
live data, change sets, publications and model releases (ADR-032). The
[composable domains](COMPOSABLE_DOMAINS.md) direction records the admission tests and the design doors
current work keeps open.

## How success is judged

An administrator can define and release another reference-data application without changing Python
or TypeScript. A steward can then select its workspace, find a record, create or correct it with its
required fields and connections, and see the live result through the same generic controls, in one
edit and save. The same journeys work for differently configured record types.

Acceptance is judged by [user journeys](product-functionality/USER_JOURNEYS.md),
[user stories](product-functionality/USER_STORIES.md) and
[realistic scenarios](product-functionality/ACCEPTANCE_SCENARIOS.md), not by whether a route,
component or model declaration exists. A passing component test or a documentation update cannot mark
an unexercised journey complete.
