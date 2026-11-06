---
title: Propose again with a newer workbook
description: Replace the draft source and review renewed proposals without losing manual decisions.
reader: model-admin
---

Use a saved workbook draft when a corrected file needs the same modelling work. You need
**Model authoring**. See [Workbook onboarding](/docs/model/workbook-onboarding/) for proposal ownership.

1. Open the draft and read **History** before replacing its source. In **More actions**, choose
   **Upload a newer workbook…**. A draft without a source offers **Add a workbook…** instead.
2. Choose **Workbook**, an XLSX workbook or CSV file, and review **Compare with the records of**.
   Upload and wait for the new source to be profiled. If it fails, read the file error and retry
   with a corrected file; do not rely on the previous source's counts.
3. Inspect every sheet, changed header and list range. Existing reading instructions may no
   longer fit the columns. Check your row keys and reference matching before accepting proposals.
4. Choose **Propose again…**. Review **A new application**, **A new model**, **Additions to the
   model** or **Nothing: I will map it by hand**, with **Application name** where offered.
   Apply the intended choice. **Proposing from the workbook** pauses editing until it finishes.
5. Only elements still as proposed follow the new proposal. Manual edits remain yours and
   undone proposals stay undone. Review conflicting column choices in **Issues**, rather
   than assuming the engine replaced your decision.
6. Inspect **Proposed because**, **Evidence** and **History**, then obtain a
   [new dry run](/docs/guide/model/check-a-workbook-with-a-dry-run/) before loading.

![Draft menu with upload-newer-workbook and propose-again actions](/docs/screens/use-wb-draft-menu.png)

For routine uploads through an already installed profile, use **Settings › Import profiles**,
**Upload the next version…** and its comparison instead. Review changed or missing columns,
unknown values and missing-record choices before accepting the next file.

## Get the example update

If you started with the [example workbook](/docs/guide/model/start-a-draft-from-a-workbook/#get-the-example-workbook),
<a download="Haltestellen_Busbetrieb_Nord_next.xlsx" href="/docs/downloads/Haltestellen_Busbetrieb_Nord_next.xlsx">download Haltestellen_Busbetrieb_Nord_next.xlsx</a>
and select it in **Workbook** in step 2. This fictional update renames **UIC-Nr** to
**UIC number** on **Haltestellen** and adds **Capture note**, filled with **Preview only**
on the first five data rows. The other two sheets are unchanged.

Use it to practise reviewing a renamed column and an extra column. It does not correct
the workbook's unresolved references. Check the key and mappings again, decide whether
to ignore **Capture note**, and run a new dry run before loading anything.
