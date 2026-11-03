# Selected source headings and bounded excerpts

## CHANGELOG.md:60 — [0.16.0] - 2026-11-02

The assistant and the agents: a person says a few words, uploads a workbook and gets the model and the import, with an AI assistant that runs as a Claude Code session through the engine's own capabilities and is limited only by what they can express. An AI proposal provider (Claude or an OpenAI-compatible one) with a send level and call records, targets for unmapped values, the assistant's instruction-driven tasks that design, check and load, a change of a workspace's model with its records move

## CHANGELOG.md:71 — Fixed (the 0.16 release review)

- An assistant's refresh token no longer opens the API console's management token or the engine's own pages (it is no browser session). - A Claude Code session never writes live data: a batch or an import naming no change set is refused `403` for it, and the write unit refuses it again. An assistant task takes a draft or a change set on its word only when its own client made it, so discarding or expiring a task never deletes a person's draft; the grants a turn leaves behind are removed first and

## CHANGELOG.md:86 — Added (notification digests and following a workspace, AO3)

- **A digest instead of many mails (0.16 AO3).** On Settings › Notifications each kind of notice is mailed **at once** (what every kind stays until changed), **in the digest** or **not at all**, and the digest comes every morning or on Mondays at 07:00 in the time zone the browser reports; the page says when the next is. One message says in a sentence how many notices of each kind wait ("3 change sets wait for your approval; 1 job you started failed"), then lists up to 50 newest first with their

## CHANGELOG.md:92 — Added (always a way out, AP13)

- **A task is never left with only Back (0.16 AP13).** A turn that failed shows its reason on the page (the task's own notes) and takes the person's words: `POST /ai/tasks/{id}/model` now works in every state a task can go on in (a proposal, a failed or stopped task, a saved layout's load stage, a loaded change set not yet published), and `POST /ai/tasks/{id}/retry` takes optional `words`. The same session goes on, or starts again on the same task, file and words when it never ran. The page's wo

## CHANGELOG.md:103 — Added (a job's page says what it did)

- **A move's and a migration's job page (0.16).** Settings › Jobs › one job shows a move's sentence and four counts, its record and relationship types (made, refused, not moved), and its items filtered by outcome and reason, refused first; names link to the records in the source workspace and a refusal by a model rule links to the model. A migration shows its counts and items by outcome. A job with nothing to list (an assistant task, a model draft's inference or check, a mapping proposal, an imp

## CHANGELOG.md:107 — Added (change the model from the workspace, and move the records with it, AP12)

- **"Change this model…" on a workspace's ⋯ menu (0.16 AP12).** Where the assistant is on and the person holds Use AI proposals, Model authoring and Model release in the workspace, the menu opens the same dialog as Load a workbook with the workspace fixed, the words first and a workbook optional. The task page's title and crumb no longer say "Load a workbook" for a task with no file. - **Two ways to move records between types.** A whole type that becomes another (a rename, a merge, into another 

## CHANGELOG.md:116 — Fixed (a removal in the model editor leaves nothing dangling, and every broken page is named)

- **Removing an application, a type or a relation binding takes the panels and views that depended on it.** A relations panel on another application's page that listed a relation its page's type no longer has loses that relation (and the columns only the dropped types gave it), and goes when none is left; a mapping grid or relation matrix over a gone binding goes, with the navigation entry it leaves empty. The relation types and attribute types a removal leaves without a binding go too, released

## CHANGELOG.md:123 — Added (what changed in a period, AO2)

- **"What changed" above a workspace's Activity and on a record's History (0.16 AO2).** Where a provider is set and the person may browse and holds Use AI proposals, Explain this period puts the changes of a period (7 days on a workspace, 30 on a record, or dates) into a few plain statements, each followed by numbers that lead to the facts it rests on. The engine counts the facts in the database over every change to live data: records per type and action, fields, relationships, sources (a job, a

## CHANGELOG.md:129 — Added (an account of a model change, AO1)

- **"What this change does" in the activation dialog and in Apply (0.16 AO1).** Where a provider is set and the person may activate releases and holds Use AI proposals in the workspace, pressing Explain this change puts the change into a few plain statements, each followed by numbers that lead to the facts it rests on. The engine writes the facts (each difference between the models, each rule the workspace's data would break with its count, what the consumer APIs would notice, whether activation

## CHANGELOG.md:134 — Changed (a hint beside the relationship panel's heading)

- Why a record is not offered a relationship ("Only … can have this relationship.") is no longer text under the panel's toolbar: a small blue circled "i" beside the panel's heading shows it on hover, on keyboard focus and on a tap, one reason per line. The hint is a shared `InfoHint`; it appears only when the reason applies to that record.

## CHANGELOG.md:138 — Changed (the model's language in the API, AP11)

- The API's OpenAPI document now describes the model: the `model` field of model requests and responses names `EngineModel` and its definitions. Validation is unchanged, so a wrong model still gets the compiler's diagnostics. - An assistant session's log is kept beside its folder rather than inside it, and goes with the folder.

## CHANGELOG.md:143 — Changed (one path for the assistant, AP10)

- A session builds everything the words ask for, as they place it and also with no data in the file; a question no longer replaces building. - Switching workspace from a page the other workspace's model lacks now writes the start page it opens to the address, so a reload no longer says the page is not in the model. - A session no longer stops with an internal error when its stream carries a system event whose message is text, as a refused permission does. - An assistant check counts a row skippe

## CHANGELOG.md:168 — Added (a key of several columns, AP10)

- **`SourceKey.attributeTypeKeys`** in an import profile: two or more attributes, each bound by a column, whose values together find one record, live and in a change set. A combination two records hold refuses the row (`KEY_AMBIGUOUS`); an empty cell is a row without a key (`MISSING_RECORD_KEY`, or `rowsWithoutKey`); an unbound attribute is `KEY_NOT_BOUND`. The assistant gives each source such a key. Batch `upsert` keys are unchanged.

## CHANGELOG.md:176 — Added (who did the assistant's changes, AP9)

- **Provenance on a session's changes:** a record or relationship the assistant proposed carries `origin` (who asked, who edited it afterwards, the task) in the change set and, once published, in history, removals included. `ProposalOrigin` gains `editedBy`, `editedByName`, `proposedByName` and `taskId`. - **One client per task:** `ai_tasks.client_id`, client kind `session`, left out of `GET /clients` unless `kind=session`; `409 CLIENT_HAS_NO_SECRETS`. - **The call record holds a session's runs:

## CHANGELOG.md:187 — Added (changing a workspace's model)

- **Edit model from the workspace:** a ⋯ menu beside the workspace selector, and a button on the workspace's page in Settings › Workspaces, open the model editor on that workspace's draft. **Apply to this workspace** says what changes and what happens to the records, installs, then activates or migrates there alone, and returns to the workspace. `POST /workspaces/{key}/model/draft`; a draft's `workspaceKey`. Model release in a draft's workspace now allows installing that draft.

## CHANGELOG.md:195 — Changed (Import and Export)

- **Import and Export moved** from the collection's header into the workspace's ⋯ menu. Export still exports what the page shows.

## CHANGELOG.md:200 — Fixed (the assistant's pages)

- **Load a workbook is offered only where a session is set up** (`ai.assistant` on `GET /system`, `AI_AGENT_COMMAND`), and says what the session is given. With a provider alone, Import is the ordinary dialog. - **The proposal's correction box** is three lines, not 440px. **The loaded page** no longer says a session's changes note the assistant, which they do not yet.

## CHANGELOG.md:207 — Added (asking a list in words)

- **Ask a table list in words (0.16 AG4).** Where a provider is set and the person holds Use AI proposals, a Search | Ask switch sits at a table list's search box. Pressing Enter on a question sends it (nothing is sent as you type; Cancel stops it); the list shows the filters it became as ordinary pills, with "Your question became these filters. Change or remove any of them." A part the list cannot express (an order, who changed a record, a record that is not found or is named by several) is nam

## CHANGELOG.md:212 — Added (agent access)

- **An assistant can prepare a change (0.16 AG3).** With Work in change sets, an assistant creates a change set, adds and changes records and relationships, sets a field's value, reads the validation and submits it for approval, in change sets its own person or client created and never a colleague's. It cannot remove or clear anything, withdraw, discard, batch, restructure, approve or publish; change reaches live data only when a person approves it. A refused call tells the assistant the engine'

## CHANGELOG.md:220 — Fixed (the AI import)

- **The same words give the same kind of model:** a session separates what a workbook repeats into types of its own and raises it as a question if it keeps it flat; what the workspace holds decides whether it adds to the model or may start anew. The proposal shows attributes and records per type from the engine's figures, counts relationships apart from records, and warns when a model leaves out types holding records. - **A session's own jobs run:** an assistant's session held the only job worke

## CHANGELOG.md:231 — Fixed (opening a record from another application)

- **A record opens where it stands:** opening a record from an application that lists its type but does not hold it, such as from a matrix row, now goes to the record's own application. It said "This object belongs to another application" before. - **The session's checklist shows what happened:** a step was ticked as soon as a command mentioned its address, so "Model changed" and "Every row checked" appeared before either happened, and a refused load counted as loaded. Steps now come from what t

## CHANGELOG.md:242 — Fixed (relation matrix cells)

- **A matrix cell shows the view's cell fields:** a cell now reads the first of "Fields in a cell" with a text or number value, and the record's name only when none has one. It always showed the name before, so records named by a code showed the code.

## CHANGELOG.md:248 — Added (model editor, relation matrices)

- **Add a relation matrix in the editor:** an application's panel has a Views section listing its views. "Relation matrix" there opens a dialog offering only rows, cells, columns and actions that can work, with a preview of the shape chosen. The types the matrix needs are listed in the application in the same step; their records stay where they stand. A matrix can be changed, renamed and removed, and a removal takes along the types only it needed. - **List a type in another application:** `listO

## CHANGELOG.md:259 — Changed (model editor, released elements)

- **A released element nothing uses can be changed:** a removal or other draft-only change applies when it would affect 0 records, values and relationships in the workspaces running the model and their change sets; above 0 it is refused with its impact, and activating the release checks the data again. A released key stays fixed whatever the data, and the refusal now says so.

## CHANGELOG.md:266 — Changed (model editor, choosing a relation)

- **Types and relation types sharing a name can be told apart:** in the model editor's pickers, a type whose name another type shares shows the applications listing it, and its key where those match too, with a note that the two hold separate records. A relation type shows the types it stands between; those already reaching the chosen type come first, and a note says how it reads in reverse, which pairs use it with their rules, and what choosing a new one leaves out. The draft's outline gives a 

## CHANGELOG.md:275 — Added (0.16 AP6, the assistant designs and loads)

- **The assistant is a Claude Code session:** with `AI_AGENT_COMMAND` set, the person's words, the workbook, the model and the OpenAPI document go to one session working through the API. It stops at a model draft with every row checked; the person opens it in the model editor, answers or says what to change, and the same session goes on. Accepting installs one release, unactivated, and loads a change set; activation stays with publishing. The page shows what the session has reached while it work

## CHANGELOG.md:349 — Removed (0.16 AP6, the reading turns)

- The assistant's read, match and fix turns of AP6a and the task phases `asking`, `matching` and `fixing`: with the assistant offered a task is designed; without it, read by the rules and planned by the person as before.

## CHANGELOG.md:355 — Added (0.16 AP6a, loading a workbook with the assistant)

- **Import with the assistant:** with AI proposals offered, Import opens the assistant first ("Import without the assistant…" opens the manual import). `POST /ai/tasks` takes a workbook and a workspace; a job (kind `aiTask`) reads it: a stored import profile that fits the file is followed, other tables are read by the rules (an update of a type when most of a column's values are its records' keys or names), note and title rows are set apart, and the assistant checks the reading and matches value

## CHANGELOG.md:372 — Removed (0.16 AP6a, the AI naming helper)

- The AI naming helper of New from a workbook and Propose again is removed ("Also ask the AI assistant for clearer names", the inference's `assistant` option and read fields, `phase` and `assistantOutcome`, the purpose `modelNames` and the proposal pattern `assistant`): the inference runs on its rules; the workbook assistant replaces it.

## CHANGELOG.md:379 — Changed (0.16 AP1, the naming helper sees the whole file)

- The inference's AI assistant no longer sends each sheet's first 50 rows. It sends each table's profile, computed in the database over every row: per column the counts, value type, candidate key, delimiters, placeholders, overlaps with other columns and, from `samples` up, the most frequent values with counts (at most `AI_SAMPLE_VALUES` at `samples`); `structure` sends no value. A request over half of `AI_CONTEXT_TOKENS` drops the values of the columns with the most distinct values first. Promp

## CHANGELOG.md:388 — Added (0.16 AP2, AI targets for unmapped values)

- **Propose targets in a mapping grid:** `POST /workspaces/{key}/mapping-proposals` (a job of kind `aiProposal`) asks the provider for a target for each unmapped source of a view, among the targets the grid would offer (all up to 100, else each source's 20 closest), and writes them into a new or open change set; never into live data. The job counts proposed, unmatched, changed, refused and not-answered sources. Needs Use AI proposals and send level `values`. - **Provenance on change-set changes:

## CHANGELOG.md:404 — Added (0.16 AP1, the AI proposal provider)

- **An AI provider for proposals**, set in the environment: `AI_PROVIDER` (`claude`, `openai-compatible` or a factory), `AI_MODEL`, `AI_API_KEY`, `AI_BASE_URL`, and how much may leave the instance, `AI_SEND_LEVEL` (`structure`, `samples`, `values`, default `values`) with `AI_SAMPLE_VALUES`; `AI_MIN_CONFIDENCE`, `AI_LOG_CONTENT`, `AI_LOG_CONTENT_DAYS`, `AI_TIMEOUT_SECONDS`. A setting that cannot work refuses the start. Without a provider nothing is sent anywhere. - **Settings › Administration › A

## CHANGELOG.md:421 — Changed (0.16 AP1)

- **`INFERENCE_ASSISTANT` and `INFERENCE_ASSISTANT_ROWS` are retired**; the start is refused while either is set, naming `AI_PROVIDER` or `AI_SAMPLE_VALUES`. `httpx` is now a runtime dependency (both adapters use it). - **Every setting in both settings files:** `python -m app.cli.settings_template` writes every engine setting from the settings catalogue, commented out at its default with its description. `scripts/dev.sh settings` uses it for a new `.dev/settings.env` and, run again, adds what an

## CHANGELOG.md:437 — Fixed (0.16 AP2)

- **Mapping sources ignored the binding's criteria:** a mapping grid applied `candidates` only to targets, so coverage, its counts and state filters, the Proposed filter and the AI proposal job's unmapped sources included records that can never be mapped there. Sources are now the source-type records meeting the criteria at the source end, plus any that already holds a relationship of the binding (kept, D175).

## CHANGELOG.md:444 — Fixed (0.16 AP1)

- **A burst of requests froze the engine:** a page asking for many lists at once (a sidebar of 101 types) left the requests holding database connections without a worker thread to finish on, while the rest held every thread waiting for a connection; everything waited for `DATABASE_POOL_TIMEOUT` and answered 503. At most as many requests as the pool has connections are now inside the application; the rest wait for their turn without a thread (503 `poolExhausted` only after `DATABASE_POOL_TIMEOUT`

