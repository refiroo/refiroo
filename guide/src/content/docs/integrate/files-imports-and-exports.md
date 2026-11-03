---
title: Files, imports and exports
description: Exchange files with checked profiles, authoritative execution and a usable synchronization baseline.
reader: integrator
---

Use an export to hand a defined dataset to another system, and an import to bind a supplied file to the model. Both run as [jobs](/docs/integrate/jobs/). Follow [Exchange a supplier file](/docs/guide/integrate/exchange-a-supplier-file/) or [Load, then follow changes](/docs/guide/integrate/load-then-follow-changes/).

## Export a defined scope

The [export operation](/docs/api/?api=management#tag/exports) selects one workspace and context: live, a change set or a publication. Choose types and their criteria, optionally a subtree and business date, and whether to include relationships. JSON Lines, CSV and Excel workbook formats serve different recipients; choose the layout before requesting the file.

An export reads one database snapshot. Its job output records counts, context, model release, format, size and checksum. A live export also records the feed position matching that snapshot. **Keep that position from the job metadata**, not by looking for a position inside the file. It is the checkpoint for following changes after loading the baseline. If its worker crashes, an export restarts its whole snapshot read rather than appending to an incomplete file. Only a completed job serves output; failed, cancelled and expired work cannot be used as a partial baseline.

JSON Lines exports contain repeatable upserts and relationship ensure operations. Sending an untouched export back to its workspace changes nothing. Edited records carry version claims, protecting changes made since export. CSV and the normal workbook layout use the export's table contract. History is not transferred, and importing is not a database restore.

## Import with a profile

Use the [import and import-profile operations](/docs/api/?api=management#tag/imports) for supplier CSV and workbooks. A profile maps sheets and columns to model types, names, typed attributes, parents, relationships and related owned records. It can use value maps for placeholders, split relationship lists, flags and selected reference values. The binding handles generic model structures, including records owned through relationships. Bind a parent once, as a fixed value or a column (`PARENT_BOUND_TWICE` otherwise). Creating missing named parents or related records needs name matching (`CREATE_NEEDS_NAME_MATCH` otherwise).

Profiles are versioned instance resources associated with a model. Saving and using a profile checks its references against the chosen workspace's model. Check it again after changing releases. A profile belonging to another model is refused as `IMPORT_PROFILE_MODEL_MISMATCH`; do not repurpose its key silently.

Choose a repeatable key: public ID, an attribute key, an allowed stored-unique or compound key, or a name key. A name key with a parent identifies children under that parent. Ambiguous existing names are `AMBIGUOUS_NAME_KEY`; ambiguous compound or stored keys need correction rather than a guessed match. A compound key must have every component bound and filled, and must identify at most one existing record. `KEY_NOT_BOUND`, `MISSING_RECORD_KEY` and `KEY_AMBIGUOUS` require fixing the profile, filling the key or disambiguating existing combinations; a configured skip rule can omit rows without keys. Without a key, each row creates a record again on the next load.

Matching reads existing records and records loaded by the same file. Parents load before children, and relationships follow their records. Profiles can explicitly create missing named references where configured. Repeated keys merge compatible filled values; conflicting non-empty values reject the contributing rows as `DUPLICATE_KEY_IN_FILE`.

Imports without a profile accept JSON Lines batch items or refiroo's exported table and workbook layouts. A profile normally permits updating found records; without a profile the default protects changed records unless versions or explicit overwrite permit the update. Choose this deliberately rather than relying on a supplier's intent.

## Preview before applying

A preview binds the file and tries changes without committing them. Read the proposed counts, every refused row and its failing cells, and the per-column report: empty, converted, value-mapped, resolved, not found, ambiguous or refused. The preview tries items independently to expose problems even for atomic policy; its result explains what that chosen policy would allow.

Large previews can be samples, by default up to 10,000 items. Read their coverage before treating the preview as complete. Confirmation binds the stored file again against current data and executes the chosen policy. Preview success does not guarantee execution success. Confirmation is idempotent; cancelling a waiting preview ends it immediately. An expired preview cannot be confirmed.

Correct refused rows in the source and send the file again; correctly keyed rows already applied become unchanged. Row outcomes are paged, not supplied as a downloadable refused-row file. A profile configured to delete records missing from the file requires a change set (`MISSING_DELETE_NEEDS_CHANGE_SET`), so the removed records can be reviewed. Missing-record deletion removes their relationships but refuses to silently remove surviving descendants or required dependants; resolve those dependencies before confirming another preview.

## Workbooks for people

A people workbook follows a collection table's columns, labels and order, with hidden record IDs, versions and its import profile. Relationship summaries can be marked as not imported. Separate relationship sheets add or change relationships without removing omitted ones. Main-sheet columns configured as relationship lists replace those sets.

Blank attribute cells leave stored values alone. A blank **replacing relationship-set cell clears the set**, if the model allows it; do not assume every blank is ignored. An owned-record column left empty makes no change. Columns grouped by parent can create or update those owned records when filled. Single-record choices can use dropdowns from a reference sheet; invalid choices still face the model's rules on import. Keep hidden identity and version columns intact when editing a round trip.

For browser controls, see [Importing and exporting](/docs/use/importing-and-exporting/) and [Jobs](/docs/use/jobs/). An integration can request the same layout through the export API without reproducing the browser workflow.

## Load into another workspace

Record IDs are unique across the instance. An export's IDs still identify the original workspace's records. Explicitly choose counterparts to load them as the target workspace's own records. Derived IDs depend on the source ID and target workspace; repeating the load finds the same counterparts. Parent and endpoint references translate too, and outcomes retain the source ID.

Counterparts work only between workspaces running the same model. `COUNTERPARTS_ACROSS_MODELS` requires a [model-to-model move](/docs/guide/integrate/move-records-between-models/). No continuing synchronization relationship is created by the counterpart load. Relationship IDs are not translated. Source version claims are ignored for counterpart upsert, update and ensure-relationship operations; deletes still claim the target counterpart's version. A missing counterpart reference requires loading its owning file first.

## Recover from file refusals

`IMPORT_FILE_MISSING`, `IMPORT_FILE_UNREADABLE`, `IMPORT_FILE_MISMATCH` and `UNSUPPORTED_FILE_FORMAT` require the expected readable file and layout. CSV is UTF-8 with supported quoting; workbook formulas use their cached values rather than being calculated. `IMPORT_TOO_LARGE` and `IMPORT_TOO_MANY_ITEMS` require splitting below the configured upload and job limits (defaults 200 MB and 1,000,000 items).

`INVALID_IMPORT_PROFILE` requires fixing the reported binding paths; `IMPORT_PROFILE_NOT_FOUND` or `IMPORT_PROFILE_EXISTS` requires the intended profile key; `IMPORT_PROFILE_VERSION_CONFLICT` requires reading its latest version. `PROFILE_CHECK_NOT_FOUND` requires a current check, while `SOURCE_FILE_PROFILE_NOT_READY` means finish preparing its profile. `SOURCE_FILE_MISSING`, `SOURCE_FILE_NOT_FOUND` and `SOURCE_SHEET_NOT_FOUND` require the intended stored file and sheet. `MISSING_RECORD_KEY`, `REFERENCE_NOT_FOUND`, `PARENT_NOT_FOUND` and `INVALID_ATTRIBUTE_VALUE` require correcting the named source cells. `INVALID_EXPORT_LAYOUT` requires a supported layout and consistent column choices. Refusals name paths or cells so a client can present the cause beside the source data.
