---
title: Exchange a supplier file
description: Preview a keyed supplier file, review row and column reports and reconcile its load.
reader: integrator
---

Prepare a repeatable exchange so resending a corrected file does not create duplicates. [Files, imports and exports](/docs/integrate/files-imports-and-exports/) explains formats and profiles.

1. Agree the target workspace, types and stable source keys. Read its [model](/docs/api/?api=management#tag/model). For CSV or workbook input, save or select a checked [import profile](/docs/api/?api=management#tag/imports) that maps the supplier's sheets, columns and relationships. A normal refiroo export can be read without a separate profile.
2. Check what the profile does with matching records and records absent from the file. If absent records are to be deleted, target a change set. Choose atomic policy if no row may load unless all are valid; choose independent if good rows may load separately.
3. Upload the file through the [import operation](/docs/api/?api=management#tag/imports), requesting a preview and keeping its idempotency key. Follow the returned job to awaiting confirmation.
4. Read the preview coverage and policy result. Page row outcomes and examine each failing cell. Use the column report to detect incorrect matching, unexpected empties or conversions. A sample preview leaves untried items; it is not assurance for the whole file.
5. Correct the file and start a new preview if its interpretation is wrong. If the intended changes are acceptable, use the [job confirmation operation](/docs/api/?api=management#tag/jobs). Confirmation rebinds against data as it stands then. Cancel the waiting preview to abandon it without applying changes.
6. Read final results and retain a reconciliation record before retention expires. Correct refused rows and resend the keyed file. Previously applied rows should be unchanged; check this rather than suppressing duplicate errors.

To return data to a supplier, start an [export](/docs/api/?api=management#tag/exports) with the agreed scope and format, wait for completion and download its output. Keep its metadata and checksum with the file. A cancelled or failed export is not a partial deliverable.

For an export loaded into another workspace of the same model, explicitly choose counterparts. For different models use a model mapping and move. Do not reuse source IDs as though they belonged to the destination.

## Check the first exchange before scheduling it

Use a small file whose intended results you know. Include a new row, an unchanged keyed row and an update to an existing row. In the **reference-data example**, these might be stop identifiers and names; the profile still uses ordinary types, attributes and relationships. Check the preview's interpreted values and cells, not just its total row count. A row can produce several items.

Keep the exact uploaded bytes, request and key together. Import idempotency includes the file's SHA-256: a corrected cell changes the request fingerprint. Use a new key and a new preview after correcting a file. Replaying the original key with changed bytes gives `IDEMPOTENCY_KEY_REUSED`.

When testing blanks, distinguish attributes from replacing relationship lists. An empty attribute cell leaves its value alone; an empty replacing relationship cell requests an empty set. Check formula results are stored as cached values in XLSX before upload. Convert legacy `.xls` files to XLSX. If the file lacks a recognised extension, name its supported format in the request.

After execution, compare final row and item reports with the preview. Save them before `expiresAt`, together with the profile definition, source checksum, job ID, resulting IDs and any remaining refusals. If data or access changed between preview and confirmation, reread the job and current context. A confirmation refusal does not prove execution started; the job can still be awaiting confirmation.

For the return file, check the downloaded file's SHA-256 against the completed job's manifest before handing it over. Keep the manifest's workspace, release and context beside the file so the recipient knows what it contains. Changing or deleting a saved profile does not reverse a prior load; deliberate data corrections use a new reviewed load or change set.
