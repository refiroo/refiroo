# C5e: the assistant's API address in Docker installations

Read `guide/AGENTS.md`. Reader: an operator who installs refiroo with Docker Compose and turns the assistant on.

## Why

A guide must lead to a working result. On the reference instance (`PUBLIC_URL=http://localhost:8480`) every assistant task
stopped at once with "internal error": the assistant's session runs inside the engine's container and fetched
`openapi.json` from `PUBLIC_URL`, which there names the container itself (connection refused). `AI_AGENT_API_URL`
(`backend/app/engine/tasks/agent.py` `_api_url`; default `PUBLIC_URL`) gives the session another address.

Two product changes follow (read the files; they are the facts, the code wins):

- `compose.yml` now sets `AI_AGENT_API_URL` for the engine to `http://127.0.0.1:8000` unless `.env` sets it: the engine
  inside its own container. `.env.example` and `docs/OPERATIONS.md` (settings table) say the same.
- In a container (`AI_AGENT_SANDBOX=container`) the session now runs without Claude Code's permission prompts; the
  separate `assistant` user is its boundary (read `_safeguards` in `agent.py` and OPERATIONS' `AI_AGENT_SANDBOX` row).
  Before this, it could not run shell commands in a container.

## What to change

- `run/set-up-ai.md`: today it says "Set it only when the assistant must use a different, reachable address". Say what
  the setting is, that Compose sets it for you, when an operator sets it themselves (a host installation whose
  `PUBLIC_URL` the engine's machine cannot reach from inside, for example behind a proxy that only answers outside
  callers), and how to check it works (an assistant task that reaches its proposal; what the failure looks like:
  the task stops at once with an internal error). In the container section, state what the container sandbox setting
  now means for the session, in plain words for an operator.
- `run/install-with-compose.md` ("Deploy to production with Docker"): where the assistant is turned on (or in its
  settings step), one sentence that Compose sets the assistant's API address, with a link to Set up AI.
- `run/ai.md` (settings table row, which says "Empty uses `PUBLIC_URL`": under Compose it is `http://127.0.0.1:8000`)
  and `run/configure.md`: the default as Compose sets it. `run/ai.md`'s container-boundary paragraph (around lines
  89–92): add that in a container the session runs with Claude Code's permission prompts off, and the `assistant`
  user, which cannot read the engine's secrets or job files, is its boundary.
- Anything else under `src/content/docs/` that states the old default for Compose: find it with grep.

## Files you may edit

- `src/content/docs/run/set-up-ai.md`
- `src/content/docs/run/install-with-compose.md`
- `src/content/docs/run/ai.md`
- `src/content/docs/run/configure.md`
- `src/content/docs/run/*.md` (only where a grep finds the old statement)
- `_coverage/notes/C5e-AGENT-API-URL/**`
- `_waves/progress/C5e-AGENT-API-URL.md`

## Report

Pages changed and what each now says; anything unsure.
