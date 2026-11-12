# The reference instance

A local refiroo instance with the guide's reference set loaded: the public transport stops of
Graubünden (about 3,500 records). It serves the screenshots (DOC10) and the fresh-reader check (DOC11),
and anyone who wants to repeat the guide's examples on a larger set. It is the engine image from this
checkout, Docker Compose project `refiroo-guide-ref`, on ports 8480 (HTTP) and 8443 (unused). It never
uses ports 8000, 5173, 5000, 7000, 9443, 54320 or 11434.

```bash
guide/reference/reference.sh up      # build, start, create the administrator, load the set
guide/reference/reference.sh load    # load again (safe to repeat)
guide/reference/reference.sh stop    # stop, keeping the data     (start: start again)
guide/reference/reference.sh down    # remove the instance and its data; .env stays
```

Open http://localhost:8480 and sign in as `guide`. The password is `GUIDE_ADMIN_PASSWORD` in
`guide/reference/.env`, generated from `.env.example` on the first `up` and git-ignored. The API
reference is at http://localhost:8480/docs.

What is loaded, and the command that loads either set on any instance, is in
[`../samples/README.md`](../samples/README.md); the sources and their licences are in
[`../samples/SOURCES.md`](../samples/SOURCES.md). The reference set also holds an open change set,
"December 2026 timetable change", and a client "Stops reader (guide)" holding the `stops` consumer API
(its credentials are `GUIDE_CONSUMER_CLIENT_ID` and `_SECRET` in `.env`).

## Taking the pictures

The guide's pictures are taken with `node guide/tools/screens.mjs --file <WAVE>.screens.json --only a,b`
(`--pictures a,b` runs every screen of `--only` but saves only a and b). A failed screen stops the run, because
later screens may build on its state; `--keep-going` runs on, for screens that do not build on each other. Other waves make test
workspaces, people, drafts, mappings, change sets and notices; a picture taken after them lists those
leftovers, and a picture of activity shows what earlier runs did twice. So the pictures that list
workspaces, show activity, recent changes, a person's recent activity or the bell's notices are taken
first on a fresh instance (`reference.sh down`, then `up`), once, in this order, and the other waves
only afterwards:

1. Workspace lists and the notices of the loaded set (nothing else has run yet):
   `CAPABILITIES`: workspaces-home, workspace-switcher; `PILOT`: home, stop-history; `USE2`: use-home,
   use-home-continue, use-workspace-default, use-workspaces-manage, use-inbox-panel,
   use-notifications-page, use-notification-job; `NEW-PAGES`: workspaces-new-dialog; `MODEL`:
   model-workspaces-list.
2. The mapping, once (`MODEL`: model-moves-setup, then model-moves-list).
3. One publication, once (`USE2`: use-pub-setup, use-pub-confirm with `--pictures` use-history-activity,
   use-history-changes, use-history-stop-changed; the run takes those three after the publication).
4. One approval flow, once, the whole file in order but the workbook screens (`APPROVALS`: appr-setup
   to appr-policy-off with `--pictures` appr-home-waiting, appr-inbox-notice, appr-sent-back-notice,
   appr-approved-notice, appr-activity). appr-setup makes Rita Approver when the instance has not.
5. The people pages, last of the set (`ADMIN`: admin-setup, admin-person-admin, admin-person-rita,
   admin-audit-person). They address a person by name (`{person:Name}`), never by ID.

6. `OLD54` (pictures that were left in earlier looks), once, after the set above and in file order:
   `node guide/tools/screens.mjs --file OLD54.screens.json`. It makes and deletes its own model draft
   "Guide draft" (the model editor pictures), then takes the Jobs, notification-settings, list,
   record-page and delete pictures, registers the assistant "Guide example assistant" for C10
   `admin-agent-block` (which blocks it; run `old54-assistant-restore` right after), and takes
   `import-preview-columns` and `run-jobs`. Take `jobs-list` before any run that adds jobs. Pictures
   with a special state in other waves: C10 `admin-mail-settings` and `contributor-propose-change`
   (`contributor-account` state) need nothing more; `admin-agent-access`, `admin-ai-test-failed` and
   `model-account-provider-failure` need a window with MCP off and an unreachable AI provider
   (edit `guide/reference/.env`, `reference.sh start`, take the three, restore the file, `reference.sh start`).

Every recipe of the set works on a fresh instance: it names what it opens, and the states it needs
(`approver-account`, the mapping) are made by its own setup screen once. Do not run a setup of this
list twice on one instance: its activity would show twice. If a picture needs another state, make it
with its own setup in the wave and add the wave to this list; never reuse a workspace made by another
wave (the C10 pictures) for it.

## Switch on AI with a Claude subscription

After the first `up`, edit the ignored `guide/reference/.env`. Keep its generated secrets. Obtain a
subscription token with `claude setup-token` on a computer signed in to Claude Code, then add:

```dotenv
CLAUDE_CODE_OAUTH_TOKEN=replace-with-your-private-token
AI_AGENT_COMMAND="claude --model sonnet --permission-mode bypassPermissions"
AI_AGENT_SANDBOX=container
AI_SEND_LEVEL=values
AI_PROVIDER=claude-code
AI_MODEL=sonnet
```

Leave `ANTHROPIC_API_KEY` and `AI_API_KEY` unset for this subscription setup. Never commit the token.
The command enables the built-in assistant; the provider enables mapping targets, questions in words
and explanations. Both are needed for all features. `claude-code` is built into the engine image;
it uses Claude Code's token and limits, and each call's cost at API prices appears in **Calls**.
For production use `AI_PROVIDER=claude` with `AI_API_KEY`, or `openai-compatible`.

Settings are read at startup. Apply them from the repository root:

```bash
guide/reference/reference.sh start
```

This recreates containers with changed settings without rebuilding images or loading the data again.
A plain container restart does not reload an edited environment file. Finish or discard active assistant
tasks before recreation: their working folders are not mounted persistently by the shipped Compose file.
Check **Settings › Administration › AI** and test the provider and assistant separately; see
[Set up AI](../src/content/docs/run/set-up-ai.md) for credentials, checks and recovery.

For webhooks, also set `CONSUMER_SUBSCRIPTIONS_ENABLED=true` and run `reference.sh start` again.
That switch enables webhook subscriptions; it does not enable AI or subscribe a receiver for you.
