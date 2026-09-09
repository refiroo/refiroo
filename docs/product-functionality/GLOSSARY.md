# Product glossary

Use these terms consistently in user interfaces, user stories and validation reports.

| Term                           | User-facing meaning                                                                            | Avoid confusing it with                                                    |
| ------------------------------ | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| Application                    | A configured area of the product that groups relevant record types and views                   | A hardcoded software module                                                |
| Application model              | The versioned definition of applications, record types, fields, relationships and views        | The live reference data stored using that definition                       |
| Attribute / field              | A typed value attached to a record, such as a code, date or availability flag                  | An untyped text property                                                   |
| Binding                        | A rule that says where a reusable field or relationship may be used                            | A particular stored value or relationship                                  |
| Candidate                      | The complete proposed content seen inside a workspace design draft                             | Live content or an immutable historical snapshot                           |
| Catalogue retirement           | Makes a workspace read-only while retaining discovery and reads                                | Publication retirement                                                     |
| Conflict                       | A safe refusal because the content or expected version changed since the user read it          | A generic server failure                                                   |
| Containment                    | A parent/child relationship that also determines navigation and ownership                      | An ordinary cross-reference                                                |
| Cursor / continuation          | An opaque value used to load the next bounded page of the same query                           | A public record ID or client-readable offset                               |
| Design draft / workspace draft | An optional workspace-level area for preparing a coordinated set of changes                    | A mandatory step for a routine live edit; an individual record draft       |
| Direct live edit               | An ordinary data change that becomes visible immediately after a conflict-protected save       | Editing the application model in place                                     |
| Immutable                      | Read-only after creation; a new release or revision is required for a different snapshot       | Merely hidden from the current interface                                   |
| Live data                      | The reference records and relationships returned by normal active workspace reads              | The active application-model release                                       |
| Mapping                        | A business association between a source value and its representation/target                    | Any generic relationship screen; containment                               |
| Model draft                    | Editable JSON proposing a change to the application model                                      | A workspace design draft containing reference data                         |
| Model release                  | An immutable installed application-model snapshot                                              | A workspace content revision                                               |
| Publication                    | The result of activating a coordinated workspace design draft as a revision                    | Every direct live record save                                              |
| Publication retirement         | Removes the current-publication designation; live records and history remain available       | Retiring the workspace catalogue entry or each record                      |
| Record                         | A governed reference-data item such as a Domain, Codelist, Master Value, System or Translation | A model definition of the record type                                      |
| Record type / object type      | The configured definition of one kind of record                                                | A starter-application-specific code branch                                 |
| Record version                 | The concurrency number used to protect one live or draft record from silent overwrite          | A model release or workspace revision number                               |
| Relation / relationship        | A typed, directed connection between two records                                               | A parent relationship that users may freely edit through relation controls |
| Stable ID                      | A public identity that survives labels, internal storage changes and workspace revisions       | An internal database sequence number                                       |
| Translation                    | A governed, language-specific representation connected to one target and a translation group   | Free text stored directly on every target type                             |
| Workspace                      | A named governed scope containing reference data                                               | An application, user account or application-model release                  |
| Workspace revision             | An immutable snapshot created by activating a workspace design draft                           | The continuously editable live data store or a record version              |

## Preferred lifecycle language

- Say **edit live data** for routine record maintenance.
- Say **prepare a design draft** for coordinated changes away from live data.
- Say **validate the draft** when checking the complete candidate without publishing.
- Say **activate the draft** or **publish a workspace revision** for the atomic workspace-level action.
- Say **retire publication** when clearing the current published revision.
- Say **retire workspace** only for the catalogue administration action that makes the scope read-only.
- Say **install a model release** and **activate a model release** as separate model-administration
  actions.

Do not describe individual records as draft, published or retired lifecycle entities. A record may
exist in a draft candidate or an immutable revision, but publication lifecycle belongs to the workspace.
A model-defined `active` field represents business availability, not engine publication state.
