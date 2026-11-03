# refiroo documentation: the full outline

Capabilities only. Applications (RDM Master, Systems, Translations; Network, Systems, Names) appear only in
`examples`. Each group is one documentation page ("About ...") plus its guides (tasks). Status per page:
**exists** (already written), **partly** (exists, see NOT-YET-COVERED.md), **new** (to write). Items marked *(after 0.16)* are
collected in the last list and are not written now.

Source abbreviations: CF = docs/product-functionality/CURRENT_FUNCTIONALITY.md (F01-F30); UJ = USER_JOURNEYS.md
(J01-J57); US = USER_STORIES.md; GL = GLOSSARY.md; PG = PRODUCT_GUIDE.md; PR = docs/PRODUCT.md; CL = CHANGELOG.md
(release or package); OPS = docs/OPERATIONS.md; MA = MODEL_AUTHORING.md; AM = APPLICATION_MODEL.md; UI = UI_MODEL.md;
INT = INTEGRATION_API.md; CAPI = CONSUMER_API.md; API = API.md (concepts only); COMPAT = COMPATIBILITY.md;
INV = guide/_waves/MODEL-EDITOR-INVENTORY.md; BASE 0.n = docs/BASE_0_n_IMPLEMENTATION_PLAN.md.
Release names used in CL: 0.5, 0.6, 0.7, 0.8, 0.9(-alpha.1), 0.10(-alpha.1), 0.11(-alpha.1), 0.12, 0.16 (0.13-0.15
are skipped in CL; the Unreleased block is the guide's own tooling and has no product capability).

Page counts (E = exists, N = new): about 0E/9N; use 14E/~24N pages, 13E/~22N guides; model 5E/~12N pages, 7E/~24N guides;
administer 0E (being written)/12N pages, ~25N guides; run 0E/~18N; integrate 0E/~19N pages, ~10N guides; examples 3E/1N.
Exact counts at the end.

---

## 1. About refiroo (`about/`, reader: evaluator). All new. No guides; short pages, plain words.

| Path | Title | Must cover | Sources |
| --- | --- | --- | --- |
| about/what-is-refiroo | What refiroo is | One engine, many applications defined by a model; what it is for (reference data: codes, lists, mappings, names) and what it is not for (no transactional data, no workflow engine, no own domain applications); who it serves (data steward, mapping/localisation steward, integration team, workspace/model admin, operator); the browser is one client of the API; what "starter model" is (an option, not part of refiroo) | PR "What makes it different", "Who it is for"; PG; CF F01, F16; AGENTS (capabilities not applications) |
| about/how-it-works | How refiroo works in one page | Model, application, record type, record, relationship, hierarchy; workspace with Live, change sets, publications; model release and activation; the lifecycle words (edit live, prepare, validate, publish, withdraw, retire, install, activate) | GL (all of it, esp. "One workspace" and "Preferred lifecycle language"); CF F01, F02, F12-F15; PG "Three different kinds of change" |
| about/three-kinds-of-change | Three kinds of change | Correct today's data (live) / prepare related changes (change set) / change what the application allows (model draft, release, activation); why each is separate; history answers different questions (record history, publication, release, asOf) | PG whole page; UJ J02, J05, J08; CF F05, F12, F15 |
| about/data-quality-rules | How refiroo protects data | Typed values, required/unique/range rules; same rules on browser, API, import; versions and refused saves (nothing silently overwritten); previews before destructive or bulk changes; publish all-or-nothing; history names who | CF F06, F10, F13, F17, F22; PR "One set of rules on every path" |
| about/sharing-data-with-other-systems | How other systems get the data | The API for everything the browser does; consumer APIs as stable read contracts; change feed and webhooks; bulk loads and files; business-date reads; pointer to Integrate | CF F16, F20-F25; PR; CAPI "Why a second API tier" |
| about/people-and-access | Who can do what | Roles (nine predefined), groups, grants by workspace, narrowed grants, clients; the interface shows only what you may do; sign-in with local accounts, the organisation's provider, second factors, passkeys | CF F26, F27; PR "Who it is for"; UJ J39-J41 |
| about/security-and-trust | Security, audit and privacy | Every route authenticated, every change names who, security events, sealed secrets, signed webhooks, sessions, rate limits, no password in records; what AI may see and send (send levels) is an *(after 0.16)* section | CF F26, F27, F29; CL 0.12 E1, Z4; OPS "Authentication"; docs/SECURITY_REVIEW_0_12.md |
| about/how-it-is-built | How refiroo is built | One service plus PostgreSQL, the web front end, background jobs, several processes on one database; offline guide and API reference; no outside calls at view time | CF F19, F24; OPS "Deployment topologies"; docs/ARCHITECTURE.md (not read in this audit; confirm) |
| about/compatibility-and-licence | Versions, compatibility and licence | What is committed from 0.12 (API, consumer APIs, model language window); additive vs breaking; the licence and source offer a running instance gives (AGPL s13); open source policy | COMPAT; CF F15 (language versions), F19 (About page); CL 0.12 L1, L2; docs/OPEN_SOURCE.md |
| about/accessibility | Accessibility and devices | Keyboard use, labelled regions, light and dark, phone layout, resizable panels; no screen-reader testing recorded (say so) | CF F18; UI |

---

## 2. Use refiroo (`use/`, `guide/use/`, reader: steward)

### 2.0 Screens without a group (null group)
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/home | exists, partly | Greeting and roles; Continue where you left off; workspace cards (default first, model/version, role, applications), open change set buttons (own; all where one publishes), your change sets with size, Your recent changes (5), Follow toggle, none-yet message | CF F02 "Home", F11, F28 (AO3); UJ J45, J57; CL 0.12 HM1, 0.16 AO3 |
| use/account | exists, partly | Account menu; password; sessions (sign out one/all); second factor and recovery codes; passkeys; What you can do table; Notifications link | CF F26, F27; UJ J39; CL 0.12 I4b, I4c, 0.12 "Settings › Account" |

### 2.1 Applications and workspaces
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/applications | exists, partly | Application shell, collections, four lenses, collection groups (fold/unfold, group page with search), detail composed of panels, default when model declares none; no forms/dashboards | CF F01; AM "Applications and views", "Navigation groups"; UI |
| guide/use/open-an-application | exists | | CF F01, F02 |
| use/workspaces | exists, partly | Selector (label/search, key in address, default, single workspace = label), model/release shown and marks, "Not in this model" page, workspace that cannot be served and why, retired workspace read only, links to model pages for administration | CF F02, F15 "In the browser"; CL 0.12 UW1 |
| guide/use/switch-workspace | exists | | CF F02 |
| guide/use/open-a-retired-or-unavailable-workspace | new | Open a retired workspace from Settings; what the "cannot be served" page says | CF F02, F19; CL 0.12 UW1 |

### 2.2 Finding records (lists, search, filters)
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/lists-and-filters | **new** | Search, typed filter pills and + Filter editor, relationship filters (any of / none / any), none under / any under, Created/Updated (live), one sort, continuous scroll, total, Go to, address keeps state, one-line rows with ellipsis, related-record columns (+N more, sort only for single), table fits the window, density and column display settings, same in change sets and publications; limits (one sort, no date filter for asOf) | CF F03, F21 (browser limit), F18; UJ J01; US-D03, D04; CL 0.8 Track S, 0.12 LS1, TV1 |
| guide/use/find-records | exists, partly | add: relationship filters, + Filter groups, phone filter sheet, Go to, expand related column | CF F03 |
| guide/use/continue-a-long-list | new | Jump to a page/value/end, Show earlier records, return to the list where you were | CF F03, F04, F07; UJ J01 |

### 2.3 Records
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/records | exists, partly | add: inline edit (click, Enter, pencil, trash, Save/Escape), header title/subtitle, ID with copy, Edit record, cell editing in lists, relationship row icons and lock, field kinds list (text, long text, integer, decimal, boolean, date, date-time, JSON), rules (range, at-least-one-of, unique within ancestor), missing vs false/zero, add a record with parent and required relations in one save, deleting impact | CF F04-F06, F10; UJ J02-J04; US-D05..D08 |
| guide/use/correct-a-record | exists | | CF F05, F06 |
| guide/use/add-a-record | new | New record with fields, parent, required relationships; refusal reasons | CF F05, F07, F08; UJ J03 |
| guide/use/delete-a-record | new | Impact preview (children, owned dependants, unlinked relations), confirm, live vs change set, never erases history | CF F10; UJ J04; US-D11 |
| guide/use/stop-offering-a-value | new | Set availability false / end a validity period instead of deleting | US-D14; CF F21; PG |
| guide/use/propose-a-change | new | Contributor: "Propose a change" / "Propose a new ...", name a change set, band wording for Reader/Contributor/narrowed grants | CF F27 (interface follows permissions); UJ J40; CL 0.12 Z5 |

### 2.4 Changing many records
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/changing-many-records | **new** | Selection (checkbox, Shift range, shown rows, all matching Cmd+A, leave out), the bar, Change values / Change relationships / Delete, preview before apply, refused records with reason, concurrent change refusal, selection limit, who sees it (Bulk and import) | CF F03; UJ J32 |
| guide/use/change-values-of-many-records | new | Keep/set/clear per field, preview, Apply, Preview again, View job | CF F03 |
| guide/use/change-relationships-of-many-records | new | Add/remove/replace/set/clear, candidates, required | CF F03 |
| guide/use/delete-many-records | new | Preview counts by type, relationships removed, "Delete 352 records" | CF F03, F10 |

### 2.5 Relationships
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/relationships | exists, partly | add: set/change/delete for single, parent shown not edited, Connected on tree side pane, candidates "every place that offers records", criteria and why a record is not offered, edit relationship fields, lock rows, record found by search | CF F08, F03 (candidates); UJ J13, J10; AM "Which records a relationship may choose" |
| guide/use/relate-records | exists | | CF F08 |
| guide/use/replace-a-records-related-records | new | Review and replace the set in one write (whole set, version) | UJ J10; CF F08, F22 |

### 2.6 Hierarchies
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/hierarchies | exists, partly | add: sidebar tree at any size, search with path, multi-select and drag/Move to…, touch press-and-hold, group folding, model-declared tree view editing (add child, rename, availability), invalid destinations disabled with reason, publications read only; **restructuring in a change set** (Becomes, Change type…, Insert level above…, Remove this level…, Change type of all…, preview, kept in history) | CF F07; UJ J14, J15; US-H01..H03; CL 0.8 Milestone C, 0.11 U1 |
| guide/use/arrange-records-in-a-tree | exists | | CF F07 |
| guide/use/reshape-a-hierarchy | new | Change type / insert or remove a level in a change set; read the preview | CF F07; UJ J15 |
| guide/use/move-several-records-together | new | Multi-select, drag, Move to…, touch | CF F07 |

### 2.7 Mapping grids
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/mapping-grids | exists, partly | add: counts and state filter incl. Proposed *(after 0.16)*, target previews, atomic replace keeping identity/fields, create missing target in context, publishing refuses diverged mappings | CF F08; UJ J09 retired note; US-M01..M04; CL 0.6, 0.7 |
| guide/use/map-codes-between-systems | exists | | CF F08 |

### 2.8 Relation matrices
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/relation-matrices | exists, partly | add: cell field choice (first text/number field), filter to missing cells across the whole list, restore an inactive/history cell, link/unlink values, records stay in their own application, matrix only in applications whose model declares it | CF F09; UJ J16; US-L01..L04 |
| guide/use/fill-in-a-relation-matrix | exists | | CF F09 |

### 2.9 Change sets
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/change-sets | exists | review for the F12/F13/J17/J18 items (amber strip, More change set actions menu, Move this change set to release, Move workspace and publish) | CF F12, F13, F15 (migration paragraphs); UJ J05, J06, J17, J18 |
| guide/use/prepare-and-publish-a-change-set | exists | | CF F12, F13 |
| guide/use/review-what-a-change-set-changes | new | Review changes list, before/after, moved record names both parents | CF F13; UJ J17 |
| guide/use/continue-live-work-while-a-change-set-is-open | new | Live edits survive publishing; conflict stops publishing | UJ J06; US-W04 |
| guide/use/start-from-an-earlier-publication | new | Start a change set from a publication, not a rollback | CF F12, F14; UJ J07 |
| guide/use/prepare-under-the-next-model-version | new | Change set on another release; Move this change set to; Move workspace to release and publish… (needs model rights) | CF F12, F15; UJ J18 |

### 2.10 Publications
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/publications | exists | | CF F14; UJ J07 |
| guide/use/browse-a-publication | exists | | CF F14 |
| guide/use/withdraw-a-publication | new | Withdraw current designation; effect | CF F14; UJ J07; GL |

### 2.11 History
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/history | exists, partly | add: day headings, Show fewer, Changes page limits (no values, no export), "Before sign-in", client marked, job/publication as cause | CF F11; UJ J44; CL 0.12 RH1, Z6 |
| guide/use/see-who-changed-what | exists | | CF F11 |

### 2.12 Importing and exporting data (moves out of "Loading a workbook")
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/importing-and-exporting | **new** | Import on a collection and New import on Jobs; file kinds; profile or none; all-or-nothing vs rows that load; update found records; always previewed; per-column report; refused rows with failing cells; "Read as exported"; Export of what the page shows (types, date, relationships, format); workbook for people (columns, Advanced, hidden ID/version columns, "(not imported)"); columns per parent for filling in; dropdown sheets; clearing a cell clears nothing; file from another workspace gets derived IDs; limits | CF F22; UJ J27 (browser parts), J11; US-I04, I07, I08; CL 0.9 J1-J4, 0.10 |
| guide/use/export-records | new | Export from a collection, formats, notification, Download, job page | CF F22 |
| guide/use/edit-in-excel-and-import-back | new | People's workbook round trip, exact-change rule, someone-else-changed refusal | CF F22 |
| guide/use/add-a-language-with-a-workbook | new | Columns per parent; fill an empty column; translations created (example only, generic text) | CF F22 |
| guide/use/import-a-file | new | Import, preview, Load the file, Cancel import, retry refused rows | CF F22 |
| guide/use/load-the-next-version-of-a-workbook | new | Settings › Data operations › Import profiles, Upload the next version…, Accept rename, Ignore new column, Load into a change set | CF F15 (next version); UJ J35 |
| use/jobs | **new** | Jobs list (all workspaces you may see), states, results, Cancel, job page (progress, error, file, checksum, what it did: copy/move counts, migration counts), notifications, retention, limits; jobs run with the requester's rights | CF F22, F27 (jobs), F11 (job as cause); UJ J24; CL 0.16 (job page says what it did) |
| guide/use/follow-and-cancel-a-job | new | | CF F22 |

### 2.13 Loading a workbook as a new model (see section 3; moved) 
The existing use/loading-a-workbook and guide/use/load-a-workbook describe building a model from a workbook (draft, source pane, proposals) and loading into a change set. Home in the outline: `model/workbook-onboarding` (section 3.7). `use/` keeps only 2.12.

### 2.14 Inbox, notifications and approvals
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/inbox-and-approvals | exists, partly | add: kinds of notice, bell (20 unread, how many more), Notifications page filters, notices open in their workspace, job notices; approval flow; policy is set under Administer (link) | CF F27 (approval items under J42), F28; UJ J42, J46; CL 0.12 A1-A3, NT1 |
| guide/use/approve-a-change-set | exists | | UJ J42 |
| use/notifications-settings | **new** | Email me when something arrives; kinds (approval waiting, approved, sent back, job); At once / Digest / Off; digest time; follow a workspace and Stop following; when the switch is not shown (no mail, no address, client) | CF F28 (inbox notices, digests and following); UJ J46.10, J57; CL 0.12 M2, 0.16 AO3 |
| guide/use/set-up-email-notices | new | | CF F28 |
| guide/use/follow-a-workspace | new | | CF F28; UJ J57 |

### 2.15 Appearance, keyboard and devices
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| use/appearance-and-devices | **new** | Settings › Appearance: theme, table density, record-type palette, pencil visibility; display preferences, resizable panels; keyboard (menus, Shift+F10, tree keys, selection keys); phone navigation (band, drawer, tabs); touch drag | CF F18, F07 (touch); UI; CL 0.11 U1 |
| guide/use/change-how-refiroo-looks | new | | CF F18 |

### 2.16 Reading by business date *(browser has no date filter: say so)*
Covered in use/records "Validity periods" (exists); asOf itself is Integrate. No separate page.

### 2.17 Asking, suggesting, explaining with AI *(after 0.16, see last list)*

---

## 3. Model your data (`model/`, `guide/model/`, reader: model-admin)
Merged with guide/_waves/MODEL-EDITOR-INVENTORY.md (INV). Every INV row has a home below. **Must-not notes** (INV §15 and
scattered "not found" lines; no model page may promise these): editing icons or colours of applications, types or groups;
default values on attributes; valid-from/valid-to (effective period) settings on attributes (the engine has effective
periods in the model language, the editor has no control: only the JSON view); formats or lengths; choice lists as a value
type (a list is a relation to a "list type"); creating tree or mapping-grid views, or editing them (only table
columns/filters/sort in the layout editor, and relation-matrix create/change/remove); table density per view; translations
or labels beyond the single name, plural and label per element; rebase or merge of a draft onto a newer release; a standing
compare of the draft with the active release in the editor (compare exists only inside Install/Apply and on the release
page); mapping scores shown in the move editor; a `uniquePer` rule editor; a separate hierarchy-level editor (hierarchy is
containment relation types plus Move to…); dragging a list's outline on the grid; choosing a field's editor; what a load does
with missing records (set in Import profiles / API); drags on a phone (menus do everything); who sees which button beyond
the three rights (Model authoring, Model release, Browse) is not established.

### 3.1 Models (Settings › Model)
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/models | exists, partly | List of models (default workspace's first, in use, rest, drafts without a model), pills (Runs the default workspace, Retired, Draft), a model's tabs Overview/Releases/Drafts/Structure with counts, Structure = read-only attributes and relations of a chosen release, Overview lists workspaces running it with Change model…, "Model mutations are disabled" banner and the deployment setting, rights needed | CF F15; INV §1 (1.1-1.10), §0; CL 0.12 M2 follow-up, UW1 |
| guide/model/create-a-model-draft | exists, partly | Dialog fields: Draft name, Starting document (Installed release / Empty model / Import JSON), Base release, JSON document or file; New draft from <version>; Start from a workspace (Edit model) | INV 1.3, 1.4, 11.3, 3.5 |
| guide/model/delete-a-draft | new | Delete draft… ("only the editable draft") | INV 4.11 |

### 3.2 The model editor (frame)
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/the-model-editor | exists, partly | Frame (header, Source pane, Model pane, centre, drawer with Issues/History/Dry run), About this draft facts (base release, version +1 per step, "Saved as you go"), rename draft, Undo/Redo, Close, More actions, Add menu, empty draft message, one dialog per operation with "Not applied", every operation is a history step, keyboard (arrows, Home/End, Enter/Space, Right/Left fold, Shift+F10), phone tabs and no drags | CF F15 "model editor"; INV §4 (4.1-4.16), §10; MA "The editor" |
| guide/model/find-your-way-around-the-editor | new | Selecting, search/fold, element panel, keyboard walk | INV 4.15, §5 |
| guide/model/undo-and-review-the-draft-history | new | History tab (Applied/Undone/JSON edit), per-step Undo, Earlier steps, "Undo the steps that depend on it too?" | INV 10.2, 10.3, 9.4; CF F15 |
| guide/model/work-on-a-draft-with-others | new | "Another change came first": see their steps, Apply mine again; JSON "A newer draft version exists" Reload/Copy local JSON | INV 9.1, 9.2 |

### 3.3 Types, attributes and relations
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/types-attributes-relations | **new** | Object type (key rules: editable until released, fixed after), attribute type vs attribute on a type (Required, Read-only, Unique, Shared with), value types (Text, Long text, Integer, Decimal, Boolean, Date, Date-time, JSON), features (Searchable, Filterable, Sortable, Unique), relation type with reverse names, relation pair with cardinality (many-to-one ... many-to-many) and Required, "Which records may be chosen" criteria (names, attributes, ancestor), containment as hierarchy, list types, relationship matrix grid; draftOnly operations after release (refused with counts when data uses it); no default values / effective period control (must-not) | CF F15; AM "Attribute types", "Object types", "Relation types", "Which records a relationship may choose"; MA "Operation catalogue", "Lists as object types"; INV §5 (5.1-5.9) |
| guide/model/add-a-record-type-and-fields | exists, partly | Stands (top / under type), containment relation (new/existing), plural name, inline cell edits, features | INV 5.1, 5.4, 5.6 |
| guide/model/add-a-relationship | exists, partly | add: "Which records may be chosen..." criteria editor, relation type keys and reverse names, relationship matrix | INV 5.7-5.9; AM K7 |
| guide/model/reuse-and-change-attributes | new | Attach existing, Rename, Change key, Make required/optional, read-only, unique, Value type, Move to…, Features… | INV 5.5, 5.6 |
| guide/model/split-merge-and-move-types | new | Split…, Merge into…, Move to… (also by drag to a type, an application or the top level), "Take it out of", Stop listing in this application, Remove type; drag with keyboard alternative | INV 5.4, §8 (8.1-8.8), Move to dialog; CF F15 |
| guide/model/turn-an-attribute-into-a-list | new | Turn into a list type…, relation name | INV 5.5; MA "Lists as object types" |
| guide/model/rename-or-re-key-an-element | new | Rename vs Change key; key fixed once released | INV 5.2-5.6 |
| guide/model/remove-an-element | new | Confirmations; refused when data uses it (counts) | CF F15 |

### 3.4 Applications, navigation groups and views
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/applications-and-views | **new** (page; guide arrange exists) | Application panel (object types, Views table with kind and shows, navigation groups), navigation groups (Open/Folded start, order, group page), listing a type in more than one application, relation-matrix view as the one view the editor creates, table views get created with a type, kinds of view the model language knows but the editor does not edit | CF F01, F09; AM "Applications and views", "Navigation groups"; INV 5.2, 5.3, 6.3, 6.4 |
| guide/model/arrange-applications-and-views | exists, partly | Check against INV 5.2-5.3, 6.2-6.4 (list an existing type; navigation group menu items; Move to group…; Move up/down) | INV |
| guide/model/add-a-relation-matrix | new | Rows, Cells show, Columns, Column heading, Fields in a cell, Row columns, What people can do; Change… / Remove relation matrix | INV 6.4; CF F09 |
| guide/model/group-collections-in-navigation | new | Add group, Rename, Start folded/unfolded, Move up/down, Move to group…, Remove group | INV 5.3 |

### 3.5 Record pages and tables (preview and layout editor)
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/record-pages-and-tables | **new** | Preview (Record page and Table tabs over a real record of a chosen workspace or an empty record, disabled buttons, not shown while the draft has errors), Edit layout (regions Main/Side, panels up/down/region/hide/rename/columns/sort, field groups, missing fields, table columns/filters/default sort incl. the record's parent first), every change a step, menus by keyboard and drag by mouse, a type without a detail page gets one in a step, what active release shows | CF F15 "Preview", "Edit layout"; INV 6.1, 6.2, 8.7; UI "Detail composition" |
| guide/model/preview-a-type | new | | INV 6.1 |
| guide/model/edit-a-record-page | new | | INV 6.2 |
| guide/model/choose-table-columns-filters-and-sort | new (part of arrange guide today) | | INV 6.2 |

### 3.6 Consumer APIs in the editor
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/consumer-apis | **new** | What a consumer API contract is for a model admin (exposed types and public names, operations, fields with sources/role/default, lists, XREF match rules, custom events, filters), contract version, "Needs v2", compatibility status, Schema and Message example with Copy/Download, activation refused for a breaking change, read-only page Settings › Integration › Consumer APIs, grants are for clients only; link to Integrate for reading | CF F23; INV §7; CAPI; AM "Consumer API definitions"; UJ J25; CL 0.9 C1-C6, 0.10 A4c |
| guide/model/define-a-consumer-api | new | Add Consumer API… (Key, Types to expose), tabs Types and related / Fields / Operations / Filters / Schema / Message example; Expose a type, Add field, Add related, Add list, Add XREF rule, Add custom event, Add filter, Sources…, Matches on…, Describe…, Edit as JSON… | INV §7 |
| guide/model/raise-a-contract-version | new | Raise contract version to N+1; install dialog result | INV §7, 9.8; CF F15, F23 |
| guide/model/see-a-consumer-apis-documents | new | Schema and message example; the read-only Settings page | CF F23, F24 |

### 3.7 Drafts from a workbook (moves here from use/)
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/workbook-onboarding | **new** (absorbs use/loading-a-workbook) | Source pane (sheets, lists, columns with status), column facts, Map to… choices (name, attribute, parent, related record, flag of a relation, ignore), value maps, split, key, lookups that create missing values, proposals marked **Proposed** with Proposed because, Propose again, inferred shapes (key and name, repeated parent, code with name, text lists, Y/N sets, several values per cell, translations per row/column, GUIDs, placeholders), workbook describing a model, sheets of lists (Adjust list…, Don't load, Load as a list…, read N lists as one), dry run tab, import profile follows the model, Load into a change set | CF F15 (workbook paragraphs); INV §12; MA "Pattern catalogue", "Import profile"; UJ J33, J34; CL 0.10-alpha.1, 0.10 |
| guide/model/start-a-draft-from-a-workbook | new (exists in part: guide/use/load-a-workbook) | | INV 1.2, 12.1, 12.2 |
| guide/model/map-a-column | new | | INV 12.4-12.6 |
| guide/model/read-lists-in-a-sheet | new | | INV 12.7; CF F15 |
| guide/model/propose-again-with-a-newer-workbook | new | | INV 4.8, 4.9; CF F15 |
| guide/model/load-a-workbook-into-a-change-set | new | | INV 12.9, 4.7; UJ J34 |
| guide/model/check-a-workbook-with-a-dry-run | new | | INV 10.4; CF F15 |

### 3.8 Checking a model
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/issues-and-dry-run | exists | Issues drawer tab with fix actions ("Use as the profile's key"), "No issues", compare via install dialog | INV 10.1, 10.5 |
| guide/model/fix-issues-before-installing | exists | | |

### 3.9 The JSON view
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/json-view | **new** | JSON workbench (Draft name, JSON model, syntax, authoritative validation with go-to-path, summary, Save draft, Compile and compare, Export JSON, Canonical model), edits recorded as one "JSON edit" step, Import JSON on create, what only JSON can set (effective period, other model-language fields) | CF F15; INV §11; AM |
| guide/model/edit-a-draft-as-json | new | | INV 11.1-11.6 |

### 3.10 Releases and activation
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/releases | exists, partly | add: Retire…, Bring back, Delete… (only if never used), Retired list, technical details (Release ID, content hash), Release history compare, Activation check per workspace, model pickers offer only usable releases, raising old schema releases (operator), release ID | CF F15; INV §2 (2.1-2.9); CL 0.12 MR1, L2 |
| guide/model/install-and-activate-a-release | exists | add: Release key/Version/Name fields, Activate into existing or new workspace, "Comparing with the base release", Apply to this workspace | INV §13, 3.6 |
| guide/model/compare-releases | new | Compare with picker, semantic changes table | INV 2.7 |
| guide/model/retire-or-delete-a-release | new | | INV 2.4; CF F15 |
| guide/model/export-a-release | new | Export JSON | INV 2.1 |
| model/migrations | **new** | When data does not fit: Preview the migration…, per missing type/field choice (Became / Not kept), counts (converted, type changed, removed, to fix), accept removal with checkbox, Migrate; stale review (Close / Preview again); Migrate and publish; Move this change set; activation checks consumer API contracts; other workspaces untouched | CF F15 (migration paragraphs); INV 3.1-3.4, 9.3; UJ J37; BASE 0.11 |
| guide/model/change-a-workspaces-model | new | Activate dialog result classes (Compatible / A migration is needed / A different model / needs higher contract version / Could not be checked) and the migration page | INV 3.1, 3.2; UJ J36, J37 |
| guide/model/migrate-a-workspace | new | | UJ J37 |
| guide/model/model-language-versions | (page) model/model-language-versions **new** | Window of supported versions, raising a release (operator command), refused outside window | CF F15 last paragraph; COMPAT "The schema language"; CL 0.12 UW1, L2 |

### 3.11 Workspaces (Settings › Workspaces)
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/managing-workspaces | **new** | List (active first, then retired, search), workspace page tabs Overview/Access/Approval/Activity, create (default's model or chosen release), rename, retire, reactivate, make default, delete (empty and never published only), workspace administration is a deployment setting, each workspace's applications, Edit model, Apply to this workspace, "Copy or move data…" | CF F02; INV 3.5-3.7; UJ J19, J36; CL 0.12 M2 follow-up |
| guide/model/create-a-workspace | new | | UJ J19, J36 |
| guide/model/retire-or-delete-a-workspace | new | | CF F02; GL (Retire vs Withdraw) |
| guide/model/make-a-workspace-the-default | new | | CF F02 |
| guide/model/edit-a-workspaces-model | new | Edit model → draft → Apply to this workspace; what the dialog lists | CF F02; INV 3.5, 3.6 |

### 3.12 Moving data between models
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| model/model-mappings | exists, partly | add: Settings › Data operations › Copy and move page (Mappings list, Recent copies and moves), New copy or move dialog, tabs Mapping/Source/Target/Not copied, Copy vs Move, Proposed marks, Why this step, undo/redo, dry-run figures, "mapping names other releases", Selection dialog, Start dialog, "reads only" notices, job page counts | CF F15 (Copy and move); INV §14; UJ J38 |
| guide/model/move-records-to-another-model | exists | | |
| guide/model/edit-a-mapping-row | new | | INV 14.3, 14.4 |
| guide/model/choose-what-moves | new | | INV 14.6 |

---

## 4. Administer access (`administer/`, `guide/administer/`, reader: access-admin)
Codex is writing this section now; the folders were empty when audited. This outline is the reference to check its
result against (slugs are those already in astro.config.mjs GROUPS, kept). Screens: guide/_waves/ADMIN.screens.json.
Needs the Security administration rights; Security pages are shown only to security administrators.

| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| administer/people-and-groups | new | People list (roles held, search, active/deactivated), a person's page (name, e-mail, one-time password link shown once and mailed when mail is set, sign out everywhere, deactivate/restore, roles direct or via group, groups, recent activity, See changes, Link to an existing person…, Keeps local sign-in), Groups (create/rename/delete, roles, add members several at once searched/ticked/pasted usernames and e-mails with a check, remove several), provider groups listed under the provider, last security administrator cannot be removed | CF F27; UJ J40; CL 0.12 SP1, SP1b, I3, I4a |
| guide/administer/add-a-person | new | Create, one-time link, mail it | UJ J40; CL 0.12 SP3 |
| guide/administer/manage-a-group | new | | CF F27 |
| guide/administer/link-a-provider-person | new | Link to an existing person… | CF F26 limits; CL 0.12 I4a |
| administer/roles-and-grants | new | Action groups and nine predefined roles; custom role (empty or copied); grants to person/group/client, instance or workspace; narrowing to applications and record types (what it allows, what refuses; stale grant); roles instance-only; grant dialog with cards and consumer API grid; workspace Access tab; changes apply on next request; account page "What you can do" | CF F27; UJ J40, J47; CL 0.12 Z1, Z2, K1 |
| guide/administer/grant-a-role | new | | CF F27 |
| guide/administer/create-a-custom-role | new | | CF F27 |
| guide/administer/narrow-a-grant-to-record-types | new | | CF F27 |
| administer/sign-in | new | Sign-in screen; local accounts (wrong-password slowdown, never locked), session limits (12 h idle, 14 days), the organisation's provider (OpenID Connect, address to register, Continue with, first sign-in creates person, groups, local sign-in off with administrators as way back, sign out of provider setting), authenticator app, recovery codes, require second factor, passkeys, forgotten password link where mail is set up | CF F26; UJ J39; OPS "Signing in from the browser", "Signing in with the organisation's provider", "A second factor"; CL 0.12 I2-I6, I4a-c |
| guide/administer/add-a-sign-in-provider | new | | CF F26; CL 0.12 I3 |
| guide/administer/require-a-second-factor | new | | CL 0.12 I4b |
| guide/administer/help-someone-who-lost-a-device | new | | CF F26 |
| guide/administer/turn-off-local-sign-in | new | | CF F26 |
| administer/clients | new | Systems that call the API: ID and secret shown once, access (roles, consumer APIs per workspace), rotate secret with overlap (hour, day, week, none), last four characters, end previous early, deactivate, last token time, recent activity, webhooks it made; consumer API grants for clients only | CF F27; UJ J41; CL 0.12 SP2, Z3 |
| guide/administer/create-a-client | new | | |
| guide/administer/rotate-a-client-secret | new | | |
| guide/administer/grant-a-consumer-api-to-a-client | new | | CF F27 |
| administer/signing-keys | new | Token signing keys, rotate every 30 days on their own, start new, retire at once after leak | CF F27; UJ J43 |
| guide/administer/rotate-signing-keys | new | | |
| administer/approval-policies | new | Workspace Approval tab: require approval, second person rule; Approve publications (Data owner), submit/withdraw/send back wording; who sees what | CF F27 area; UJ J42; CL 0.12 A1, A3 |
| guide/administer/set-an-approval-policy | new | | |
| administer/audit | new | Security events per person/client/instance (signing in with address, failed sign-in, roles, groups, links, deactivation; kinds filter; day headings; no secrets), the Changes page for data changes | CF F11, F27; UJ J44; CL 0.12 Z4, RA1 |
| guide/administer/find-who-changed-something | new | | |
| administer/mail | new | Settings › Integration › Mail: server, port, security (STARTTLS/TLS/unencrypted relay), login, from address, public address, sealed password, Send test message and what failures say, outbox and Messages list (retry schedule, Stop sending), nothing sent without it | CF F28; UJ J46; OPS "Sending mail"; CL 0.12 M1 |
| guide/administer/set-up-mail | new | | |
| administer/webhooks | new (page screens; concepts in integrate) | Settings › Integration › Webhooks: name, consumer API, workspace, events, filters, request form; Configuration/Deliveries tabs; pause/resume (from first change not taken or from now), rotate key with overlap, Stop it now, redeliver, deliveries kept a week; why paused | CF F23 (Webhooks paragraph); UJ J30; CL 0.12 K1, A2 |
| guide/administer/create-a-webhook | new | | |
| guide/administer/rotate-a-webhook-key | new | | |
| guide/administer/find-out-why-a-webhook-paused | new | | |
| administer/api-reference-and-consumer-api-pages | new | Settings › Integration › API reference and Consumer APIs (read-only pages), copy buttons | CF F23, F24 |
| administer/jobs-and-limits | new | Settings › Data operations › Jobs, batch/job limits and retention shown (operators set them); see also use/jobs | CF F22 |
| administer/deployment-pages | new | Settings › About, Deployment (settings with source and meaning; secrets read as set/not set; changes need restart), Operations | CF F19 |
| administer/agent-access *(after 0.16)* | new | Settings › Security › Agent access | CF F30; ADMIN.screens.json admin-agent-access |

## 5. Run refiroo (`run/`, reader: operator). All new, guides in the page (commands). No `guide/run`.

| Path | Must cover | Sources |
| --- | --- | --- |
| run/overview | What you run: one service, PostgreSQL only, web front end, jobs in the background; the order to read | OPS "Settings", "Deploying"; PR |
| run/install-with-compose | Images, reference installation, first administrator, first start | OPS "Deploying"; CL 0.12 DP2, DP3 |
| run/developer-instance | A developer instance, from a phone on the same network | OPS "A developer instance"; CL 0.12 DP1a |
| run/configure | Settings catalogue and how to read it (runtime, source, default), capability groups (model administration, workspace administration, jobs), batch and job limits, change feed retention, Settings changes need a restart, the Deployment page | OPS "Settings"; CF F19 (Settings › About, Deployment) |
| run/https | Automatic HTTPS for a public installation; WEB_TLS=proxy behind a load balancer; deployment topologies | OPS "Automatic HTTPS", "Deployment topologies"; CL 0.12 DP4, C3 |
| run/database | PostgreSQL requirement, collation, database connections and pools, wrong-database refusals | OPS "Database", "Database connections"; CF F19 |
| run/several-processes | Several processes on one database, startup one at a time, model activation visible to all, Operations page and probes | OPS "Several processes"; CF F19; CL 0.11 N1, N3 |
| run/secrets-and-keys | SECRETS_ENCRYPTION_KEY, what changing it voids, reseal command, signing keys | OPS "Changing SECRETS_ENCRYPTION_KEY"; CL 0.12 K1, C7 |
| run/sign-in-and-mail-setup | Operator side of providers and mail (settings, public address, SPF/DKIM, secrets not carried to another server) | OPS "Authentication", "Sending mail"; CL 0.12 C6 |
| run/health-and-startup-checks | Live and ready probes, startup refusals and what to do (unknown revision, collation, schema outside window) | OPS "Startup checks and health"; CF F19 |
| run/monitoring | Prometheus metrics, JSON logs, request ID, Operations page (workspaces served, processes live/silent, jobs, failing webhooks, refresh 15 s) | OPS "Monitoring", "Logs"; CF F19; CL 0.11 O1, O2 |
| run/background-jobs | Jobs survive restarts, retention, exports and imports limits, source files and dry runs | OPS "Background jobs" and subsections; CF F22 |
| run/webhook-delivery | Consumer events, delivery, retries up to a day, retention of deliveries, host rules | OPS "Consumer events", "Webhook subscriptions", "Delivery"; CF F23 |
| run/upgrades | Upgrade command, migrations at startup, model language window, raising stored releases, compatibility commitment | OPS "Upgrades"; COMPAT; CL 0.12 L2, 0.16 header |
| run/backup-and-restore | Backup, restore into a separate database, rehearsal command and the Operations page result; restore is the only way to restore data | OPS "Backup and restore"; CF F19; UJ J12; CL 0.11 O2 |
| run/model-releases-and-rollback | Application rollback vs activating an older release; retiring releases; release prune command | OPS "Model releases and rollback"; CF F15 |
| run/security-checklist | Hardening: CSP, framing, cookies, rate limits, TLS, secrets; the sweep | OPS; CL 0.12 E1, C1-C10; docs/SECURITY_REVIEW_0_12.md |
| run/production-checklist | One list from all the above | OPS whole; CF F19 |
| run/troubleshooting | Messages and what each means (DATABASE_UNAVAILABLE, ENGINE_UNREACHABLE, 503 states, workspace cannot be served, stuck jobs, failed webhooks, failed mail) | OPS; CL 0.12 UW1; UJ J12 |
| run/command-line | The `python -m app.cli...` commands in one table | OPS; CL 0.12 (reseal_secrets, model_release_raise), 0.11 (model_release_prune) |
| run/licence-and-source | AGPL s13 offer, `GET /system` | CL 0.12 L1 |
| run/ai-and-agent-settings *(after 0.16)* | | OPS "AI proposals", "Agent access" |

## 6. Integrate (`integrate/`, `guide/integrate/`, reader: integrator)
Concept and sequence pages. Operations link to /docs/api; never repeat fields.

| Path | Must cover | Sources |
| --- | --- | --- |
| integrate/overview | The tiers: management API, consumer APIs, feed and webhooks, files and jobs; where /docs/api is; choosing | CF F16, F24; CAPI "Why a second API tier"; API principles |
| integrate/signing-in-and-tokens | Client credentials, token issuing, lifetimes, scopes by role and consumer API grant, secret rotation overlap, no unauthenticated routes, refusals name action and workspace, assistant refresh token not a browser session | CF F16, F26, F27; API "Security"; CL 0.12 I1, Z1, Z3 |
| integrate/identifiers-paging-and-errors | Stable UUIDs and keys, signed cursors, position paging, totals, structured errors, bounded pages, open objects | CF F16; API "Entity identifiers", "Collection paging"; COMPAT "What clients must tolerate" |
| integrate/versions-and-conflicts | Expected versions, VERSION_CONFLICT, publish conflicts, racing writers, workspace release moved meanwhile | CF F17, F19; API |
| integrate/workspaces-contexts-and-models | Live, change set, publication contexts on reads, each workspace's own model, reads across workspaces, "Not in this model" in the API | CF F02, F15; UJ J36, J20 |
| integrate/reading-records | Cross-type lookup, edge list, model-aware query, expand, fields, asOf | CF F20, F21; INT Q1-Q4; UJ J20-J23 |
| integrate/business-dates | Effective period, asOf on lists/queries/consumer reads, refusal for undated types | CF F21; INT Q4; US-I06; UJ J23 |
| integrate/discovering-the-model | Reading model, releases, OpenAPI, consumer API index | CF F15, F23, F24; UJ J20 |
| integrate/writing-in-bulk | Batches as jobs, items and outcomes, failure policies, per-item concurrency, idempotency key, preview, limits 1,000 inline / 1,000,000 background, deletes with impact, relation items and set replacement | CF F22; INT P1-P7, B1-B8; UJ J11, J24; US-I03 |
| integrate/files-imports-and-exports | Export scope and formats, change feed position in the file, import profiles (versions, checks), previews and per-column reports, workbook for people, round trip, ID derivation across workspaces | CF F22; INT J1-J6; UJ J27, J35; US-I04, I07, I08 |
| integrate/jobs | States, progress, cancel, follow via events, retention, run with requester's rights | CF F22, F27; INT P6 |
| integrate/following-changes | Change feed: numbers, kinds and filters, no missing numbers, no values, expiry and re-read from a publication, retention 30 days | CF F25; INT F1-F5; UJ J26; US-I05 |
| integrate/consumer-apis | Concept: declared contract, version, defaults, index and OpenAPI per API, grants, publications read, caching, representations (target) | CF F23; CAPI "Engine design"; UJ J25, J28 |
| integrate/reading-business-objects | By ID, lists paged, parameters, publication reads, ETag/unchanged | CF F23; UJ J28 |
| integrate/looking-up-and-resolving | Lookup scoring, parameters narrowing, exactly-one result, batch resolve up to 1,000, translate between systems/languages, limits (3 characters, 10,000, 100 terms) | CF F23; UJ J29 |
| integrate/consumer-events-and-webhooks | Events declared in the contract, following events, webhook subscriptions (batching, form, CloudEvents), signing and key rotation, ordering, retry up to a day, pausing reasons, redelivery, workspace events | CF F23; UJ J30; CAPI "Change events and webhooks"; CL 0.12 A2, K1 |
| integrate/model-and-release-operations | Typed model-draft operations over API, install/activate, migrations (preview, confirm), mappings between models and moves (dry run, then change set), per-workspace activation | CF F15 ("Through the API"); UJ J36-J38; API "Model authoring", "Workspace models" |
| integrate/changes-approvals-and-publication | Change sets via API, submit/approve/send back, errors (CHANGE_SET_SUBMITTED, APPROVAL_REQUIRED), notifications as events | CF F12, F13; UJ J05, J42; API |
| integrate/security-model-for-integrators | Roles/narrowed grants as refusals, jobs and clients, security events, audit identity (actor, cause, channel) | CF F27, F11; UJ J40, J44, J47 |
| integrate/compatibility | What is committed, additive vs breaking, extensions reserved, model language window | COMPAT |
| integrate/api-reference | Where /docs and /docs/api live, try-it signed-in, offline script | CF F24; CL 0.12 C1, C10 |
| integrate/assistants-and-agents *(after 0.16)* | MCP, tools, change sets prepared by an assistant, `channel: mcp` | CF F30; UJ J51-J53; API "Agent access" |

Guides (sequences):
| Path | Must cover | Sources |
| --- | --- | --- |
| guide/integrate/get-a-token | | CF F26; UJ J41 |
| guide/integrate/read-a-collection-completely-and-resume | | UJ J21; US-I02 |
| guide/integrate/load-then-follow-changes | Export as starting point, then feed from its position; expired number re-read | UJ J26, J24; CF F22, F25 |
| guide/integrate/submit-a-bulk-change | | UJ J11 |
| guide/integrate/exchange-a-supplier-file | | UJ J27 |
| guide/integrate/read-as-of-a-date | | UJ J23 |
| guide/integrate/read-through-a-consumer-api | | UJ J28 |
| guide/integrate/resolve-a-file-of-codes | | UJ J29 |
| guide/integrate/subscribe-a-webhook-and-verify-it | | UJ J30 |
| guide/integrate/move-records-between-models | | UJ J38 |

## 7. Example applications (`examples/`, reader: evaluator)
| Path | Status | Must cover | Sources |
| --- | --- | --- | --- |
| examples/the-starter-model | exists | RDM Master / Systems / Translations: each app, which capabilities and where they link; a model may rename or remove them | docs/EXAMPLE_MODEL.md; CF F01 |
| examples/translations | exists | Records + ownership + relation matrices (not a feature) | CF F09 |
| examples/the-example-data | exists | Network, Systems, Names (Graubünden) and sources | guide/samples/README.md, SOURCES.md |
| examples/the-consumer-api | new | The one small consumer API of the starter model (master data, event for changed codelist values), as an example of the contract | CF F23 last paragraph |

## 8. After 0.16 (AI features; not written now)
| Item | Future home | Sources |
| --- | --- | --- |
| Ask a list in words: Search / Ask switch, filters from words, send levels, limits | use/ask-in-words + guide/use/ask-a-list-in-words | CF F29; UJ J54; CL 0.16 "asking a list in words" |
| Propose targets in mapping grids (Proposed by the AI, Proposed filter, history says AI) | use/mapping-grids + guide/use/propose-targets | CF F29; UJ J49; CL 0.16 AP2 |
| Loading a workbook or changing records with the assistant (task page, proposal, Checks, Accept the model, saved profile, a way on at every state) | use/loading-with-the-assistant + guides; model/workbook-onboarding cross-link | CF F29; UJ J50; CL 0.16 AP6, AP6a, AP10, AP13 |
| Change this model… from words (whole type moves, partial split in three steps) | model/change-a-model-from-words | CF F29; UJ J50; CL 0.16 AP12 |
| Account of a model change (What this change does, Explain this change) | model/releases, model/migrations | CF F29; UJ J55; CL 0.16 AO1 |
| What changed in a period (Explain this period) | use/history (a section exists already) | CF F29; UJ J56; CL 0.16 AO2 |
| Digests and following | NOT AI, **in scope now** (use/notifications-settings) | CF F28; UJ J57 |
| AI settings page, provider, send levels, call list, test request | administer/ai or run/ai-and-agent-settings | CF F29; OPS "AI proposals" |
| Agent access (/mcp, agent clients, tools, sessions) | administer/agent-access, integrate/assistants-and-agents | CF F30; UJ J51-J53; OPS "Agent access" |
| History marks "prepared by an assistant"; `channel` mcp | use/history | CF F30 |

## 9. Counts
Computed in NOT-YET-COVERED.md (end).
