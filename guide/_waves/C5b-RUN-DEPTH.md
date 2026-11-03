# C5b: "Run refiroo" in full detail

Read `guide/AGENTS.md` and `_waves/COMPLETE-COMMON.md`. Reader: operators, people who install and run
refiroo for their organisation and are not its developers.

What the person who owns refiroo said: Run refiroo is a good start but feels incomplete and not detailed
enough. The pages name the right topics; most are too short to follow (install 600 words, database 480,
HTTPS 520, upgrades 620, the production checklist 450, the overview 330) and carry few commands. Bring
every page to the standard an operator needs to do the work from the page alone:

**Every task page is a procedure:** what you need before you start (versions, hardware as measured or "not
measured", ports, DNS names, access); the steps, each with the exact command or file excerpt to type and
what it prints or shows when it worked; how to check the result; what can go wrong, each refusal or error
message quoted exactly as refiroo prints it, with its cause and what to do; how to undo or roll back where
that exists.

**Reference tables** where an operator looks things up (on the page that owns the topic, or a new page in
the fitting group of `sidebar/run.mjs`):
- every setting from `backend/app/config.py` and `python -m app.cli.settings_template`: name, default,
  secret or not, needs a restart or not, what it changes, when to change it; grouped as the template groups
  them (AI and agent settings stay with `run/ai.md`: link there);
- the files and volumes: what each Compose service stores where, what must be backed up, what may be lost;
- network: services, ports, which talk to which, what must be reachable from outside and what must not;
- every command in `backend/app/cli/`: purpose, options, example, output, exit codes;
- every startup refusal and health state, with the message and what to do;
- the metrics refiroo exports (names, labels, meaning) and the log fields, each with an example line;
- the Compose services and images, with the environment file (`.env.example`) explained line by line.

Sources: `docs/OPERATIONS.md` in full, `compose.yml`, `.env.example`, `backend/Dockerfile`,
`frontend/Dockerfile`, `frontend/nginx/`, `backend/app/config.py`, `backend/app/cli/`, `backend/app/main.py`
and the startup checks, the metrics and logging code, and the journeys J12 and J45 in
`docs/product-functionality/USER_JOURNEYS.md`. The code wins; anything you cannot confirm goes into your
report, not onto the page. Document only what is supported (the Compose reference installation); say where
something is not measured or not supported.

`run/ai.md` and `run/set-up-ai.md` are not rewritten here: link to them.

## Files you may edit

- `src/content/docs/run/*.md` (except `ai.md` and `set-up-ai.md`)
- `sidebar/run.mjs`
- `_waves/coverage/run.md`
- `_waves/screens-wanted/C5b-RUN-DEPTH.md`

## Report

As `COMPLETE-COMMON.md` says, with the word count of each page before and after.
