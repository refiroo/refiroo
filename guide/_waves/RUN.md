# Run refiroo

Read `guide/AGENTS.md`, then the "run" section of `guide/_waves/OUTLINE.md`: it lists every page of this
section, what each must cover and its sources (mainly `docs/OPERATIONS.md`, `compose.yml`, `.env.example`,
`backend/Dockerfile`, `backend/app/config.py` and the commands in `backend/app/cli/`).

Reader: operators. Pages carry the commands an operator types and the settings that matter, each with what
it changes, its default and when to change it; what a refused start or a failing check says and what to do.
Document only what is supported and tested (the Docker Compose reference installation; a developer
instance is a development setup, say so). Sizing: only measured figures with their date and conditions,
otherwise "not measured". Secrets: say which settings are secrets and must never be committed.

Write every page the outline lists for "run" that does not exist yet. `run/ai.md` and `run/set-up-ai.md`
exist; link to them, do not rewrite them. Where an administrator does something in the browser (people,
sign-in providers in Settings, clients), link to the Administer pages instead of repeating them; where a
screen of Settings › Administration helps an operator (Operations, Jobs, Deployment), say what it shows and
list the screenshot you would want.

## Files you may edit

- `src/content/docs/run/*.md` (except `ai.md` and `set-up-ai.md`)

## Report

The pages written, the screenshots wanted, anything you could not confirm, and anything in refiroo that
looked wrong.
