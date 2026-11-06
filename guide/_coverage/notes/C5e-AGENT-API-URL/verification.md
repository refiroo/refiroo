# Verification and scope

- Read `guide/AGENTS.md` and the wave brief first. No steering or previous progress file was present.
- Checked `compose.yml` engine environment, `.env.example` AI settings, `docs/OPERATIONS.md` AI settings rows, and `backend/app/engine/tasks/agent.py` command parsing, `_container`, `_as_assistant`, `_safeguards`, and `_api_url`.
- Searched all `guide/src/content/docs/` for the assistant API setting and related statements. Only the four assigned pages required changes.
- Updated only the four named pages, this notes directory, and the wave progress file. Preserved pre-existing edits, including production-installation content, automatic-HTTPS cautions and screenshot wording.
- Reviewed the changed passages against the source facts. No live assistant task or provider request was run; the documentation describes the operator's check.
- `GUIDE_OUT=_build/C5e-AGENT-API-URL npm run build` in `guide/` passed (exit 0): 247 pages, reported build time 3.60 seconds. Warnings: unsupported `caddyfile` highlighting in `run/https.md` falls back to plain text; duplicate `/404` route rendering is skipped. Neither warning blocked the build.
- No new screenshots are needed for these text changes.

## Existing discrepancy outside this wave

`run/ai.md` says Compose does not mount assistant folders or the Claude Code directory as volumes, and `run/set-up-ai.md` similarly warns that Compose does not persist working directories. Current `compose.yml` mounts both `assistant` and `assistant-claude` volumes. These existing statements were not changed: this wave requests API-address and permission-prompt corrections only. No product defect was identified in the code inspected.
