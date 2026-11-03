# Run refiroo: setting up AI

Read `guide/AGENTS.md`. Reader: operators. These pages carry the commands and settings an operator types;
no screenshots are needed yet (Settings › AI will be captured later).

The person who owns refiroo will follow these pages to switch AI on in the documentation's own Docker
reference instance, so they must be complete and exact for the Docker Compose installation, and also say
what differs on other installations.

Write:

- `run/ai.md` ("About AI in refiroo", the operator's view): the two independent switches (the assistant via
  `AI_AGENT_COMMAND`, the provider via `AI_PROVIDER`) and what each gives; agent access (`MCP_ENABLED`) as a
  third, separate switch; what leaves the instance (`AI_SEND_LEVEL`, `AI_SAMPLE_VALUES`); who may use AI (the
  action group and the roles that hold it); costs and the call log on Settings › AI; what is kept and for
  how long; the guards around the assistant's session (its own user in a container, its own folder, a client
  that cannot publish or activate, none of the server's secrets; the container does not limit its network).
- `run/set-up-ai.md` (the steps, Docker Compose): Claude Code is already in the engine image (no
  `docker exec`, nothing to install); set `AI_AGENT_COMMAND` (for example
  `claude --model sonnet --permission-mode bypassPermissions`) and `AI_AGENT_SANDBOX=container`; give the
  session its credentials through the environment (`.env`): Claude Code's own variables pass to the session
  (`ANTHROPIC_*` and `CLAUDE_*` names), so an Anthropic API key (`ANTHROPIC_API_KEY`) or a Claude Code token
  made with `claude setup-token` on a computer with a Claude subscription (`CLAUDE_CODE_OAUTH_TOKEN`); for
  mapping targets, `AI_PROVIDER=claude` with `AI_API_KEY`; optionally `MCP_ENABLED` for agent access; restart
  the engine (`docker compose up -d`, or for the documentation's reference instance
  `guide/reference/reference.sh up`); check on Settings › AI with **Send a test request**, and try the
  assistant; what a refused start or a failing session says and what to do. Say clearly which settings
  are secrets and must never be committed.

Sources: `docs/OPERATIONS.md` (sections "AI proposals", "Agent access", and the runtime rows for
`AI_AGENT_COMMAND`, `AI_AGENT_SANDBOX`, `AI_AGENT_API_URL`), `.env.example`, `compose.yml`,
`backend/Dockerfile` (the assistant's user and `CLAUDE_CONFIG_DIR`), `backend/app/config.py` (the setting
catalogue), `backend/app/engine/tasks/agent.py` (which environment names reach the session, around
`_session_environment`), `guide/reference/README.md` and `guide/reference/.env.example`. Where Claude Code's
own behaviour is concerned (its variables, `setup-token`), say it is Claude Code's and keep to what the
sources show; mark anything you cannot confirm in your report.

## Files you may edit

- `src/content/docs/run/ai.md`
- `src/content/docs/run/set-up-ai.md`

## Report

The pages, anything you could not confirm, and anything in refiroo that looked wrong.
