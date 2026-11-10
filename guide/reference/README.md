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
