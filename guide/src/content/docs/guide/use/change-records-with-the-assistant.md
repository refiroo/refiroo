---
title: Change records with the assistant
description: Give instructions without a workbook and review the prepared changes before publication.
reader: steward
---

Use this to ask the assistant to prepare changes to records the workspace already holds.
It needs **Use AI proposals**, **Bulk and import**, **Work in change sets**, available jobs
and an enabled assistant at the values send level. Your words and the workspace model go
to Claude Code, which reads records as needed. Turns can incur costs and task files are
retained. See [AI and your data](/docs/use/ai-and-your-data/) and
[Loading with the assistant](/docs/use/loading-with-the-assistant/) for the rules.

1. Open the current workspace's **⋯** menu and choose **Ask about these records…** where it is
   offered. You can also choose **Import…** and leave **Workbook** empty in **Load a workbook**.
   Confirm **Into** names the intended workspace.
2. In **Tell the assistant about this file (optional)**, say which records should change, how to
   find them and the desired result. Words are required when there is no workbook. For example,
   with the reference data: “Set the Abbreviation of the stop ‘Thusis Süd’ to ‘THSD-REVIEW’.” Use the names of fields and relationships in your
   model. Instructions are limited to 4,000 characters.
3. Read the sending note and choose **Ask the assistant**. This starts a saved task; it is
   different from **Ask** on a table list, which only chooses filters.
4. Read the proposal and any counts or checks shown. Check that it affects the intended
   records and reuses existing types and records where appropriate. Answer any **Questions** with **Answer and
   design again**, or use **Tell the assistant what to change** and **Send to the assistant**.
   If the task proposes a model change, inspect **Show the model change** and involve a model
   administrator before accepting it. When the page says **No change to the model.**, there
   is no model draft, model-change detail or model editor button.
5. When the proposal and any checks match your request, choose **Accept** for a task with no
   model change, or **Accept the model** for one with a model draft. With no model change,
   acceptance prepares a new change set on the workspace’s current release; it installs and
   activates nothing. It changes no Live record.
   If the assistant cannot do the task, read its reason and correct the instructions rather
   than assuming a partial or empty load completed the request.
6. Choose **Review the change set**. Review the actual differences, validate and follow the
   [approval and publication steps](/docs/guide/use/prepare-and-publish-a-change-set/).
   The workspace's normal approval rules apply, including a second person where required.

![Record-change proposal showing No change to the model, Accept and the correction box](/docs/screens/use-assistant-words.png)

*Above: the proposal changes the Abbreviation of Chur Wiesental in the reference data. Accepting prepares a change set for review; nothing is published.*

For a wrong result, [continue or correct the same task](/docs/guide/use/continue-an-assistant-task/)
while its session is available. Instructions alone do not necessarily produce a saved import
profile: the page says why if the work cannot be repeated as a file import.
