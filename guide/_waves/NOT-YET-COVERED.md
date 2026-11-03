# What the existing pages do not yet cover

Audited 2026-11-02 against OUTLINE.md and its sources (CF = CURRENT_FUNCTIONALITY.md, UJ = USER_JOURNEYS.md,
INV = MODEL-EDITOR-INVENTORY.md, CL = CHANGELOG.md). Method: each page's headings and text read, then keyword checks
across all existing pages. "Absent" means the term does not occur anywhere in the pages of that section. The code wins
over the docs; items marked *(verify)* are doc statements not re-checked against the screens. Pages under `administer/`
did not exist yet (Codex is writing them); see the end.

## A. Missing across several pages (the largest)

1. **No page covers importing, exporting, or jobs.** Absent from use/, guide/use/, model/, examples/: Export, workbook for
   people, columns per parent, Import profiles, Jobs, Download (CF F22; UJ J27, J24; CL 0.9 J1-J4). Home: OUTLINE 2.12.
2. **No page covers changing many records** (selection, Change values, Change relationships, Delete N records; CF F03; UJ J32).
3. **Lists, search and filters have no documentation page** (filter pills, + Filter, relationship filters, continuous scroll,
   Go to, columns of related records; CF F03). Only a guide (find-records) exists.
4. **Appearance, keyboard, phone and accessibility are absent** (Settings › Appearance, density, palette, pencil, shortcuts,
   phone band; CF F18, F07 touch).
5. **Notification settings are absent**: Email me when something arrives, kinds, At once / Digest / Off, digest time (CF F28;
   UJ J46.10, J57). Follow a workspace is covered only as one sentence on home.md.
6. **Consumer APIs in the model editor are absent** (INV §7; CF F23). Only mentioned as a check in install and issues pages.
7. **The JSON view, model language versions, migrations (page), workspace administration (page), drafts from a workbook (as a
   model topic) are not in model/** (INV §11, §3, §12; CF F15).
8. **Applications, workspaces, and capabilities that the contributor uses**: "Propose a change" absent everywhere (CF F27
   "interface follows permissions"; UJ J40).
9. **Whole sections do not exist**: about, run, integrate (administer is being written).
10. **AI features** (Ask in words, Propose targets, assistant, Change this model…, account of a change): only "Explain this
    period" appears (history.md); the rest is *(after 0.16)*, so absent is expected.

## B. Page by page

### use/home.md
- Covers cards, Continue where you left off, work waiting, Follow button, recent changes. Does not state: cards list "default
  first"; someone who may browse no workspace reads that there is none under the instance's name; an address naming a
  workspace/application/record opens it directly (CF F02 "Home"; UJ J45).
- States Follow as a toggle but says nothing of followed-workspace notices (a notice when a change set is published there, not
  your own) or Stop following in Settings › Notifications (CF F28 "Digests and following"). Add after use/notifications-settings.

### use/account.md
- Absent: where the account menu names the roles held in the workspace open (CF F27 end); roles listed once with the groups
  they come through, limited permission as a count that opens application by application (CF F27, "Settings › Account shows").
  *(verify: the page has a "What you can do" section; check that depth.)*
- Second factor and passkeys are on this page. Administer/sign-in will cover the administrator side. Keep the user task here, link both ways.
- Absent: the Notifications link target (use/notifications-settings), Appearance link.

### use/applications.md
- Absent: navigation groups of collections (fold/unfold, remembered per reader, folded group marked when it holds the open
  collection, group page with search by name; CF F01). Absent: the detail page is composed of panels with a default when the
  model declares none; no forms/dashboard views exist (CF F01 limits).
- Says "four kinds of view"; correct per CF F01.

### guide/use/open-an-application.md, switch-workspace.md
- Absent: "Not in this model" page for an address naming something the workspace's model lacks, listing the workspaces whose
  model has it; a toast says when the model or release differs; the workspace that cannot be served and its reason
  (CF F15 "In the browser"; CL 0.12 UW1). Open a retired workspace from Settings › Workspaces (CF F02): only workspaces.md says it.

### use/workspaces.md
- Covers model per workspace, selector marks, manage list. Absent: workspace page tab Activity details, Edit model/Apply to this
  workspace, make default, reactivate, delete rules ("Delete…" only for an empty never-published workspace), "workspace
  administration is a deployment setting" and what the screen says when off (CF F02). These belong in model/managing-workspaces;
  the "Manage workspaces" section of this page should shrink to a pointer. States "default workspace cannot be retired or
  deleted" *(verify against CF F02, which says a workspace ever published can only be retired and the default is a separate
  setting)*.
- Page says Reader/Contributor roles can/cannot write; consistent with CF F27.

### use/records.md (1,695 words, the broadest page)
- Absent: field types list (long text, decimal, date-time, JSON), rules (numeric ranges, at-least-one-of, unique within an
  ancestor) beyond a general line; inline editing mechanics (click, Enter, pencil, trash, Save/Escape, selecting text to copy
  does not edit), header title and subtitle editing, Add for an empty subtitle, Edit record in the ⋯ menu, ID with copy button,
  editing in cells of a list and a toast saying Live or change set (CF F06). Absent: a new record carries fields, parent
  and required relationships in one save (CF F05). Absent: Delete dialog counts (children by type, relationships removed,
  those that reach records that stay) and Delete from many (CF F10, F03). Absent: bulk (see A2). Absent: Show earlier/Show
  fewer of history (CF F04, F11). The history section here is one paragraph: move kinds/By/day headings to use/history.
- Also misplaced: "Validity periods" is fine here, but note the browser has no date filter (CF F21).

### use/relationships.md and guide/use/relate-records.md
- Absent: Set/Change/Delete wording for single relationships; "Connected" chips beside a tree; lock icon for rows managed
  through the parent; edit the relationship's own fields; the candidate rule offered "in every place that offers records" and
  the refusal text through the API; relation form for a new record's required relationship (CF F03, F06, F08). Replace a set in
  one write (UJ J10) is not a guide.

### use/hierarchies.md and guide/use/arrange-records-in-a-tree.md
- Absent: restructuring in a change set (Becomes <type>, Change type…, Insert level above…, Remove this level…, Change type of
  all <type> in here…, preview with what has no place; kept in history; CF F07, UJ J15). The page mentions "Change type",
  "Insert level", "Remove this level" once only; no guide. Absent: multi-select moves, Move to…, right click/Shift+F10,
  Show earlier records, touch press-and-hold (CF F07; CL 0.11 U1), sidebar tree search listing all types with their path.

### use/mapping-grids.md, guide/use/map-codes-between-systems.md
- Absent: counts and the state filter by name; target chips in the target type's colour; "create a missing target in context"
  is in the guide (US-M04) but not the page; publishing refuses a change set whose mappings diverged from live data (CF F08).
  AI-proposed targets *(after 0.16)*.

### use/relation-matrices.md, guide/use/fill-in-a-relation-matrix.md
- Absent: which cell field shows (first text/number field of the view, else the name), that the matrix is added per application
  in the model editor, that records stay in their own application (CF F09; CL 0.16 relation matrix fixes). Mostly complete.

### use/change-sets.md (2,047 words)
- Largest page. Verify against CF F12/F13/J05-J18. Absent: the amber strip and **More change set actions** menu (changing the
  model version, discarding); **Move ‹workspace› to ‹release› and publish…** and **Move this change set to ‹release›…** buttons
  (CF F15 migration paragraphs; UJ J18); Contributor's **Propose a change** (absent everywhere); "withdrawing a request is by
  its submitter or an approver" (CL 0.12 MR1) *(verify)*. Split candidates: move "Preparing for another model release" to a
  guide; move "When approval is required" into use/inbox-and-approvals (already duplicated there).

### use/publications.md, guide/use/browse-a-publication.md
- Close to complete. Absent: "created from" vs "superseded by" wording kept apart (the page uses Started from / Replaced as
  current, which matches the screen *(verify)*); no guide for Withdraw (UJ J07).

### use/history.md, guide/use/see-who-changed-what.md
- Absent: day headings, "show 10 newest, then 20 more", Show fewer; entries by a bulk job name the job as cause; changes by a
  publish name the publication; "client" mark; limits (Changes page shows no values, cannot be exported, leaves out
  model-to-model operations; changes before 0.12 read "Before sign-in") (CF F11). The sentence "Earlier events recorded before
  sign-in may have no named author" is right but the on-screen words are "Before sign-in".
- "Explaining a period" is an AI section: keep, mark *(after 0.16)* in the list; it is written in present tense.

### use/inbox-and-approvals.md, guide/use/approve-a-change-set.md
- Covers bell, Notifications page, approval flow. Absent: email notices and kinds, digests, Stop sending (see A5); notices read
  automatically when the job's confirmation is done; bell lists at most 20 unread (CL 0.12 NT1). The approval policy setup is
  an administrator task (administer/approval-policies): this page should link there. Duplicate of change-sets.md "When approval
  is required".

### use/loading-a-workbook.md and guide/use/load-a-workbook.md  (misplaced)
- They explain building a model from a workbook (model draft, source pane, proposals, issues, dry run, Load into a change set).
  That is model-administrator work (needs Model authoring and Model release; the page itself says "Ask a model administrator").
  Move both to model/workbook-onboarding and the model guides of OUTLINE 3.7. Missing from them: the three inference shapes
  (workbook that describes a model, sheets of lists laid out for reading, repeated parents), Adjust list…, Don't load this
  list, Load as a list…, read N lists as one, "Propose again…", "Upload a newer workbook…", value maps, lookups creating
  values, the dry run tab per source and "what changed since the last dry run" (CF F15; INV §12). Replace in use/ by
  use/importing-and-exporting.

### model/models.md
- Absent: model list ordering and pills, Retired section, "Model mutations are disabled" banner, Structure tab detail, "Change
  model…" from the Overview tab (INV §1). Rights named (Model authoring, Model release, Browse) *(verify)*.

### model/the-model-editor.md and guide/model/*
- Strong coverage of frame, history, layout. Absent: keyboard operation of the model pane (arrow keys, Home/End, Right/Left,
  Shift+F10), phone tabs and "drags are off on a phone", About this draft facts, rename the draft in the header, **Open as
  JSON**, Delete draft…, Add menu items fully (Navigation group…, Attribute type…, Relation type…), the whole relationship
  matrix grid (INV 5.9, 4.15, 4.16, 4.12, 4.11, 4.4).
- Wording conflict: page says "refresh the draft and reconsider your change" after a refused edit; the screen offers
  "Another change came first" with the other administrator's steps and **Apply mine again** (INV 9.1). Fix.
- Page title "Compare before releasing" is accurate (compare is only in Install/Apply and on the release page, INV 10.5, but
  is not a standing editor view): keep the wording that says so.
- Absent: consumer API tab (A6), JSON view, Export JSON.

### guide/model/add-a-record-type-and-fields.md, add-a-relationship.md
- Absent: **Which records may be chosen** criteria (names, attributes, ancestor; CF F03 "candidates", INV 5.8; AM K7). The word
  "criteria" does not occur in model pages. Absent: Stands (top level / under a type), plural name default, new containment
  relation vs existing, attribute features (Searchable, Filterable, Sortable, Unique) and Value types by name *(verify)*, cardinality
  choices by name, Required toggle (INV 5.1, 5.4, 5.6, 5.8). Not to say: default values, validity on attributes.

### guide/model/arrange-applications-and-views.md
- Check against: navigation group menu (Rename, Start unfolded/folded, Change key, Move up/down, Remove), List an existing
  type…, Stop listing in this application, Move to group… (INV 5.2, 5.3). Absent: table view columns that include the record's
  parent first; relation matrix creation fields (INV 6.2, 6.4). Must not imply tree, mapping-grid or density editing.

### model/releases.md, guide/model/install-and-activate-a-release.md
- Covers retire, bring back, compare. Absent: **Delete…** of a release nothing was made under; "Run by no workspace"/"Runs this
  release" pills; Release ID and content hash with Copy; Export JSON; model pickers offering only usable releases; the
  per-workspace Activation check (INV 2.1-2.8; CF F15; CL 0.12 MR1). Install dialog fields (Release key, Version, Name,
  Activate into an existing or new workspace) and the five result classes of the Activate dialog (INV §13, 3.1).

### model/issues-and-dry-run.md, guide/model/fix-issues-before-installing.md
- Add the fix actions on issues ("Use as the profile's key", remove a panel naming a removed field) and the Dry run tab
  figures per source (INV 10.1, 10.4).

### model/model-mappings.md, guide/model/move-records-to-another-model.md
- Absent: Copy and move page as a whole (Mappings list, Recent copies and moves), the mapping editor's tabs, "mapping names
  other releases" fix, read-only notices, the job page of a copy/move (CF F15, F22 "A job's own page"; INV §14).
  Probably correct on proposals and dry run.

### model/ (absent pages)
- model/consumer-apis, model/json-view, model/migrations, model/model-language-versions, model/managing-workspaces,
  model/applications-and-views, model/record-pages-and-tables, model/types-attributes-relations, model/workbook-onboarding.

### examples/the-starter-model.md, translations.md, the-example-data.md
- Correctly placed (applications only in examples). Check that the starter model page matches EXAMPLE_MODEL.md and names the
  consumer API of the starter model (CF F23 last paragraph) -> examples/the-consumer-api.
- `use/records.md`, `use/relationships.md` and `use/applications.md` link to "Translations as an example" and name
  Network/Systems/Names in captions only: acceptable per guide/AGENTS.md rule 5.

### index.md
- 5 words only. Needs a reader-oriented start page (who reads what), using the AGENTS table.

## C. Misplaced pages (summary)
| Page | Now in | Belongs in | Why |
| --- | --- | --- | --- |
| use/loading-a-workbook, guide/use/load-a-workbook | use | model (workbook-onboarding and guides) | needs Model authoring/release; builds a model |
| use/workspaces "Manage workspaces" section | use | model/managing-workspaces | create, retire, Edit model are administrator actions |
| use/change-sets "Preparing for another model release" | use | guide in use + link to model/migrations | needs Model rights for the move buttons |
| use/change-sets "When approval is required", use/inbox-and-approvals "policy" | use | policy part to administer/approval-policies | policy is an administrator setting |
| use/account second factor and passkeys | use | stays; add administer/sign-in for the administrator side | both readers |
| use/history "Explaining a period" | use | keep, mark after 0.16 | AI feature |

## D. administer/ (Codex writing; empty at audit)
Check the result against OUTLINE section 4. The easiest omissions: Link to an existing person…, Keeps local sign-in, the
instance-only roles rule, consumer API grants for clients only, stale narrowed grants, mail (Settings › Integration › Mail),
webhooks page, API reference/Consumer APIs pages, Jobs/limits page, About/Deployment/Operations pages, recent-activity
filters (RA1). Slugs already in astro.config.mjs GROUPS are kept.

## E. Counts (pages = documentation pages, guides separately; approximate, from OUTLINE.md)
| Section | Pages exist/new | Guides exist/new |
| --- | --- | --- |
| about | 0 / 10 | 0 / 0 |
| use | 14 / 8 | 13 / 26 |
| model | 5 / 9 | 7 / 36 |
| administer | 0 / 12 (+1 after 0.16) | 0 / 20 |
| run | 0 / 21 (+1 after 0.16) | 0 / 0 |
| integrate | 0 / 21 (+1 after 0.16) | 0 / 10 |
| examples | 3 / 1 | 0 / 0 |
| total | 22 / 82 | 20 / 92 |
