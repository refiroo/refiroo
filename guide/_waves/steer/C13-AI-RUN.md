# Steering for C13-AI-RUN (from the person who owns refiroo, 2026-11-03)

The person followed `run/set-up-ai.md` with a Claude subscription and expected every AI feature to work, as
it does on their developer instance. The page did not tell them how, so the page is wrong. Fix it:

- **Both switches, with a Claude subscription and with an API key, side by side.** The assistant
  (`AI_AGENT_COMMAND`) runs Claude Code and takes either `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`) or
  `ANTHROPIC_API_KEY`. The provider (`AI_PROVIDER`) is a separate thing: `AI_PROVIDER=claude` calls the
  Anthropic API with `AI_API_KEY` (`backend/app/engine/proposals/claude.py`, `registry.py`) and cannot use a
  subscription; `openai-compatible` takes any chat-completions endpoint (a local model such as Ollama:
  `AI_BASE_URL`, `AI_MODEL`); a factory `package.module:function` can be named.
- **The subscription for the provider:** the repository has a development-only provider that answers
  through Claude Code and so runs on the subscription: `backend/devtools/claude_code_provider.py`, named with
  `AI_PROVIDER=devtools.claude_code_provider:provider` and `AI_MODEL=sonnet` (read its docstring). It is not in
  the engine image. Document exactly where it works: on a developer instance (`run/developer-instance.md`,
  where `.dev/settings.env` names it) and on the documentation's reference instance, which mounts
  `backend/devtools` into its engine (`guide/reference/compose.override.yml`); say it is for development and
  trying, uses the developer's Claude Code sign-in and limits, and logs usage to
  `backend/devtools/usage.jsonl`; a production installation uses `AI_PROVIDER=claude` with `AI_API_KEY` or
  `openai-compatible`.
- **A table** at the top of `run/set-up-ai.md`: which features need which switch (assistant: loading and
  changing with the assistant, Change this model…; provider: proposed mapping targets, asking a list in
  words, explanations), and for each the settings with a subscription and with an API key.
- **`reference/README.md`:** how to switch AI on for the reference instance with a subscription (the lines
  in `guide/reference/.env`, then `guide/reference/reference.sh start`, no rebuild), and that
  `CONSUMER_SUBSCRIPTIONS_ENABLED=true` switches on webhooks.
- Settings are read at start: say that `reference.sh start` (or `docker compose up -d`) recreates the engine
  with changed settings without rebuilding the image.
