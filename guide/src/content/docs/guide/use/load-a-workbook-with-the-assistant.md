---
title: Load a workbook with the assistant
description: Send a workbook, review the model and every-row check, then load a change set for publication.
reader: steward
---

Use this when a file needs interpretation before it can load. You need the assistant enabled,
permission to send values, **Use AI proposals**, **Bulk and import**, **Work in change sets**
and available background jobs. A model change needs a model administrator's access too.
The whole workbook, your words and the workspace model go to Claude Code; it can read records
as needed. Turns can incur costs and the task and session files are retained. Read
[AI and your data](/docs/use/ai-and-your-data/) and
[Loading with the assistant](/docs/use/loading-with-the-assistant/) before starting.

1. Open an application in the current workspace and check that it is writable. Open the
   workspace's **⋯** menu and choose **Import…**. When the assistant is offered, **Load a
   workbook** opens first. To use a known manual import instead, choose **Import without the
   assistant…** and follow [Import a file](/docs/guide/use/import-a-file/).
2. In **Workbook**, choose one XLSX or CSV file. Check **Into** names the intended workspace.
   In **Tell the assistant about this file (optional)**, explain the result you need: for an
   update, say how rows correspond to the records already held and what must stay unchanged.
   Read the sending note, then choose **Read the workbook**. If the file exceeds the instance's
   size limit, reduce it or ask the operator about that limit; nothing has been loaded.
3. The task page shows **Working on it** and the steps actually completed. You can leave and
   return from **Settings › Jobs**, or choose **Stop**. A fitting saved profile can prepare
   the file without starting AI; the page then follows that saved layout.
4. Read **The assistant’s proposal**, its types and counts, and **The check of every row**.
   Expand **Show the model change**. Check **Checks**, **Needs attention** and **Columns left
   out**. New records beside records already held can mean the update key is wrong. A type
   omitted despite holding records, filled cells left out, refused rows and skipped empty
   keys all need a decision before you accept.
5. Under **Questions**, inspect the assumed choices. Change wrong ones and choose **Answer and
   design again**. For other corrections, use **Tell the assistant what to change** and **Send
   to the assistant**. **Open in the model editor** opens the draft if you need to edit it.
   Close the editor to return. If the check predates your edit, ask the assistant to check again.
6. When the proposal matches your intent and its check is current, choose **Accept the model**.
   The session installs any necessary release without activating it, then loads into a new
   change set. If the engine refuses it, read the reason and correct the proposal on this page.
   A saved-layout task instead shows **What the load would do** and a load button: inspect the
   per-sheet figures, expand changed records, read refused row examples and
   **What confirming does, in this order** before loading. Its button explicitly says when it
   also activates a model; that activation is not undone if the subsequent load fails.
7. On **Loaded into the change set**, read the created and changed counts and any **Not loaded**
   detail. Check whether a profile was saved; **Open the profile** leads to it. If none was
   saved, read why before assuming next month's file can repeat the load.
8. Choose **Review the change set**. Check the actual record and relationship changes, validate,
   obtain any required approval and publish through
   [Prepare and publish a change set](/docs/guide/use/prepare-and-publish-a-change-set/).
   If its release is not active yet, have a model administrator activate the compatible release
   first. Loaded records reach Live only when published.

![The workbook dialog with Workbook, Into, instructions and the sending note](/docs/screens/use-assistant-workbook.png)

![A loaded assistant task naming the change set and saved profile](/docs/screens/use-assistant-loaded.png)

If the proposal or load is wrong, use [Continue or correct an assistant task](/docs/guide/use/continue-an-assistant-task/).
After publication, use [Load the next version of a workbook](/docs/guide/use/load-the-next-version-of-a-workbook/)
with the saved profile. A missing key or a new sheet can require the assistant again.
