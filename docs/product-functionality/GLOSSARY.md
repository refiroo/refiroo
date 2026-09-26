# Product glossary

Use these terms consistently in user interfaces, user stories and validation reports. The workspace,
change set, publication and lifecycle terms follow
[ADR-031](../DECISIONS.md#adr-031--workspace-terminology-and-deployment-capability-boundaries): one
meaning per word, one verb per action.

| Term                      | User-facing meaning                                                                                                                                            | Avoid confusing it with                                                       |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Activate (model release)  | Makes an installed model release serve the installation                                                                                                        | Publishing a change set; installing a model draft                             |
| Application               | A configured area of the product that groups relevant record types and views                                                                                   | A hardcoded software module                                                   |
| Application model         | The versioned definition of applications, record types, fields, relationships and views                                                                        | The live reference data stored using that definition                          |
| Attribute / field         | A typed value attached to a record, such as a code, date or availability flag                                                                                  | An untyped text property                                                      |
| Binding                   | A rule that says where a reusable field or relationship may be used                                                                                            | A particular stored value or relationship                                     |
| Candidate                 | The complete proposed content seen inside a change set: live data with the change set's changes applied                                                        | Live content or an immutable publication                                      |
| Change set                | An optional group of data changes in one workspace, prepared away from live data and published together                                                        | A mandatory step for a routine live edit; a model draft; a separate workspace |
| Conflict                  | A safe refusal because the content or expected version changed since the user read it                                                                          | A generic server failure                                                      |
| Containment               | A parent/child relationship that also determines navigation and ownership                                                                                      | An ordinary cross-reference                                                   |
| Cursor / continuation     | An opaque value used to load the next bounded page of the same query                                                                                           | A public record ID or client-readable offset                                  |
| Direct live edit          | An ordinary data change that becomes visible immediately after a conflict-protected save                                                                       | Editing the application model in place                                        |
| Hierarchy editor          | The 0.8 steward screen for browsing and maintaining a deep model-defined hierarchy as a tree                                                                   | A workspace; the sidebar navigation tree                                      |
| Immutable                 | Read-only after creation; a new model release or publication is required for a different snapshot                                                              | Merely hidden from the current interface                                      |
| Install (model draft)     | Turns a validated model draft into an immutable model release                                                                                                  | Activating a model release; publishing a change set                           |
| Live                      | The current, directly editable data of a workspace, returned by normal reads                                                                                   | The active model release; a separate workspace                                |
| Mapping                   | A business association between a source value and its representation/target                                                                                    | Any generic relationship screen; containment                                  |
| Model draft               | Editable JSON proposing a change to the application model; the only kind of "draft"                                                                            | A change set containing reference data                                        |
| Model release             | An immutable installed application-model snapshot                                                                                                              | A publication of workspace data                                               |
| Publication               | The immutable snapshot of a workspace created by publishing a change set, referred to as "Publication N"                                                       | Every direct live record save; a model release                                |
| Publication number        | The per-workspace counter N in "Publication N": the highest number in the workspace plus one. It continues across model releases and is never called a version | A record version or a model-release version                                   |
| Publish (change set)      | Applies a change set's changes to live data atomically and creates the next publication                                                                        | Activating a model release; a direct live edit                                |
| Record                    | A governed reference-data item such as a Domain, Codelist, Master Value, System or Translation                                                                 | A model definition of the record type                                         |
| Record type / object type | The configured definition of one kind of record                                                                                                                | A starter-application-specific code branch                                    |
| Record version            | The concurrency number used to protect one live or change-set record from silent overwrite                                                                     | A model-release version or publication number                                 |
| Relation / relationship   | A typed, directed connection between two records                                                                                                               | A parent relationship that users may freely edit through relation controls    |
| Retire (workspace)        | The workspace administration action that makes a workspace read-only while retaining discovery and reads                                                       | Withdrawing a publication; a record's availability                            |
| Stable ID                 | A public identity that survives labels, internal storage changes and publications                                                                              | An internal database sequence number                                          |
| Translation               | A governed, language-specific representation connected to one target and a translation group                                                                   | Free text stored directly on every target type                                |
| Translation editor        | The 0.8 steward screen showing translation coverage as a target-by-language matrix                                                                             | A workspace; the generic relations panel                                      |
| Withdraw (publication)    | Removes a publication's current designation (status `withdrawn`); live data and history are unchanged                                                          | Retiring a workspace; deleting records                                        |
| Workspace                 | A named governed scope containing reference data                                                                                                               | An application, user account, model release, change set or publication        |

## One workspace: live, change sets and publications

A workspace has live data, any number of change sets and a sequence of publications, and runs on one
model release. Live, a change set and a publication are ways of viewing one workspace, not workspaces
themselves; the workspace selector chooses the workspace, and the context badge says which of its
views is shown.

```text
Workspace "default" (model release 0.8.0)
├── Live                  current data; routine edits save here directly
├── Change set "Q3 codes" candidate = live + its changes; validate, then publish
│        └── publish ──▶ changes become live, and Publication 13 is recorded
└── Publications          Publication 1 … Publication 13, immutable, read-only
```

Publishing a change set changes live data and records the next publication in the same operation.
Withdrawing a publication removes only its current designation. Retiring the workspace makes live
data, change sets and publications read-only together.

## Preferred lifecycle language

- Say **edit live data** for routine record maintenance.
- Say **prepare a change set** for coordinated changes away from live data.
- Say **validate the change set** when checking the complete candidate without publishing.
- Say **publish the change set** for the atomic workspace-level action; it creates **Publication N**.
- Say **withdraw the publication** when clearing the current publication.
- Say **retire the workspace** only for the workspace administration action that makes it read-only.
- Say **install a model draft** and **activate a model release** as separate model-administration
  actions. Never say "activate" for a change set.

Do not describe individual records as draft, published or retired lifecycle entities. A record may
exist in a change set's candidate or an immutable publication, but the publication lifecycle belongs
to the workspace. A model-defined `active` field represents business availability, not engine
publication state.

Until [W2](../BASE_0_8_IMPLEMENTATION_PLAN.md#w2-rename-change-sets-and-publications) lands, the
API, database and browser still use the earlier names: a change set is a workspace draft
(`workspaceDraftId`, "Draft · name", "Activate draft"), a publication is a workspace revision
(`workspaceRevisionId`, `revisionNumber`, "Revision N", "Historical snapshot"), and withdrawing a
publication is `POST /workspaces/{key}/retirement`.
