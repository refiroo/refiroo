# TN guide: an AI task is named by what it asks

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

Package TN (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "TN: An AI task named by what it asks") changed how a task
given in words is named. Before, the task page and the Jobs page showed the request cut at 80 characters, often
mid-word, and the draft was named the same way. Now the task's own session states a short title with its first
answer, the engine stores it and the API returns it as `title`. The code wins: `backend/app/engine/tasks/agent.py`
(prompt `agent/20`, `_proposal_landed`), `backend/app/engine/jobs/origins.py`, `frontend/src/features/ai-tasks/aiTaskText.ts`
(`taskTitle`, `cutAtWord`), `docs/API.md` ("The task", `title`), `../CHANGELOG.md` (Unreleased, 0.13 TN).

## What the product does now (check each point in the code)

- A task given in words is named by a short title the assistant writes with its first answer (a few words naming
  the change, for example "Move types under the person group"). The task page heading, the Jobs page's name for
  the task's group and the draft the task makes (`Assistant: <title>`) carry it.
- What the person typed stays on the page uncut, as "You said: …" on the proposal.
- Until the title arrives, and for a task that ends before its first answer (stopped, or failed with no
  proposal), the name is the person's words cut at a word boundary with "…", never in the middle of a word.
- A task given with a workbook is still named by its file. The journey bar and the trail keep their own names
  ("Change this model", "Import with the assistant").
- The API returns `title` on the task (`null` until written), in the task's response beside `words`.

## What to do

- `src/content/docs/guide/use/change-records-with-the-assistant.md` and
  `src/content/docs/guide/model/change-a-model-with-the-assistant.md`: where the page says how the task page
  and its draft are named, or shows the heading of a words task, add one line: the assistant names the task with a
  short title once it has answered, the draft is named "Assistant:" and that title, and the person's own words
  stay shown in full on the page; until then the task shows the words, cut at a word.
- `src/content/docs/guide/use/continue-an-assistant-task.md`: the same one line where the page names the task
  in the list of jobs or on its heading, if it does.
- `src/content/docs/integrate/assistant-tasks.md`: in the description of the task object, add `title` (a short
  title the assistant writes with its first answer; `null` until then and for a task that ends before one), beside
  `words`. Link the operations to `/docs/api`; do not repeat the reference.
- No new pages; no new pictures. A picture that shows a words task's cut-off heading or a draft named after the
  cut-off words: list it in the report (name and page).

## Files you may edit

- `src/content/docs/guide/use/change-records-with-the-assistant.md`
- `src/content/docs/guide/model/change-a-model-with-the-assistant.md`
- `src/content/docs/guide/use/continue-an-assistant-task.md`
- `src/content/docs/integrate/assistant-tasks.md`
- `_waves/progress/TN.md`

## Report

Per page: what changed and why (one line each), the passages you checked and left as they are, the pictures that
no longer match.
