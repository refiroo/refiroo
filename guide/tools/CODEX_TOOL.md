# codex-wave: driving Codex for the writing waves

`guide/tools/codex-wave.mjs` (Node, no dependencies) lets the primary agent run a writing wave through
Codex (`codex exec`), check what it changed, and send the fact-check list back to the same session.
Run it from anywhere; paths are resolved from the script. Codex is found by `--codex-bin`, then
`CODEX_BIN`, then `codex` on PATH, then `~/.local/bin/codex`. The model is Codex's configured default
(`~/.codex/config.toml`) unless `--model M` is given. The tool never passes `--dangerously-*` flags and
never uses `--worktree` (the guide's files are uncommitted, a worktree would not have them).

## The wave file must match

`guide/_waves/<PACKAGE>.md` needs a heading containing "Files you may edit" (any level, case does not
matter). Under it, one bullet per allowed file or glob, the path in backticks first, anything after
the closing backtick is a comment. The section ends at the next heading.

```
## Files you may edit
- `src/content/docs/use/*.md`
- `src/content/docs/model/*.mdx`
```

- Paths are relative to `guide/` (a leading `guide/` or `./` is accepted and stripped). No `..`, no absolute paths.
- Globs: `*` any characters except `/`, `**` any characters including `/`, `?` one character. No other syntax.
- Bullets without a backticked path are ignored. A missing heading or an empty list stops `run`.
- The prompt tells Codex to read guide/AGENTS.md, then the wave file as its assignment, to edit only the
  listed files, never to commit, and to end with the report the file asks for.

## Screenshots

A wave file may carry a line `Screens file: \`PILOT.screens.json\`` (a name in `_waves/` or a path under
`guide/`). The file lists screens (`name`, `shows`, and how to reach them); `node guide/tools/screens.mjs`
captures them from the reference instance into `guide/public/screens/<name>.png` (`--list`, `--only a,b`).
A screen signs in as the administrator unless it has `"as": "<role>"`: that role's `GUIDE_<ROLE>_USERNAME` and
`GUIDE_<ROLE>_PASSWORD` from `guide/reference/.env` are used (`approver`, `contributor`, ...); sessions are
reused per role and width.
`run` passes every image of the screens file to `codex exec` with one `-i` each and adds the list (name and
what it shows) to the prompt; `--images <glob or comma list>` adds more (names are matched in the current
directory, then in `guide/public/screens/`). `reply --images ...` attaches images to that turn
(`codex exec resume` accepts `-i`). The images sent are in `run.json` (per turn: path and sha1) and in
`turn-N.images.txt`; `run --dry-run` lists them.

A step `{"expand": <locator>, "rows": N}` turns a native `<select>` into an open list (its choices and group headings),
because a headless browser cannot photograph an open native menu.

A `waitFor` step may carry `"timeout"` in milliseconds (default 15000), for slow work such as an AI
proposal or an assistant task (use minutes: 300000).

## Live requests

`node guide/tools/live-requests.mjs [--file C12.requests.json] [--only a,b] [--list] [--allow-writes]` runs the
documentation's example requests (`guide/_waves/<FILE>`: `requests[]` with `name`, `auth` `consumer|admin|none`,
`method`, `path`, `query`, `headers`, `body`, `expectStatus`, `write`, `note`) against the reference instance
and writes each real response to `guide/_coverage/live/<name>.json` (status, ETag/Content-Type/Location/
Retry-After/rdm-*/signature headers, body cut at 200 KB). Use it to check a page's example against the
engine's actual answer. `consumer` uses the consumer client in `.env`; `admin` signs in as the administrator
and uses the browser-flow bearer token. Only reads run (GET, HEAD, POST to resolve/xref/lookup/preview/
dry-run/validate paths); other requests need `"write": true` and `--allow-writes`. Exit 1 if a request fails
unexpectedly (name a deliberate error in `expectStatus`). The instance must be running
(`guide/reference/reference.sh start`).

## Commands

| Command | Does |
| --- | --- |
| `node guide/tools/codex-wave.mjs run <PACKAGE> [--model M] [--timeout MIN] [--dry-run]` | Snapshots the tree, runs `codex exec --json -C <repo> -s workspace-write -o ...` (prompt on stdin), snapshots again. `--dry-run` prints the allowed list and the prompt and starts nothing. Timeout default 90 minutes. |
| `node guide/tools/codex-wave.mjs check <PACKAGE> [--run TS]` | Compares the run's first before-snapshot with its last after-snapshot, then runs `npm run verify` and `npm run check:links` (in `guide/`). Writes `check.md`; exit 1 on a failed check, a file outside the list, a missing allowed file or a failed turn. Flag: `--no-guide-checks`. |
| `node guide/tools/codex-wave.mjs reply <PACKAGE> <message-file> [--run TS]` | Resumes the run's session (`codex exec resume <session-id>`, `workspace-write`, same `-o`) with the file's text as the next turn (turn-2, turn-3, ...). Run `check` again afterwards. |
| `node guide/tools/codex-wave.mjs status [<PACKAGE>]` | Per run: session id, model, turns, exit codes, duration, tokens (input, cached, output, reasoning), last check result. |

`--run TS` defaults to the newest run of the package. Report the `status` token totals to the user
after each wave.

## Network and browser (opt-in)

By default Codex runs in `workspace-write` without network, so `curl http://localhost:8480` is refused.
`run`/`reply --network` adds `-c sandbox_workspace_write.network_access=true` to the turn (new and resumed).
`--browser` implies `--network` and, per turn, starts a headless Chromium outside the sandbox
(`chromium.launchServer`, Playwright from `frontend/node_modules/playwright/index.mjs`) and appends its
WebSocket endpoint plus a short `chromium.connect(...)` example to the turn's prompt (screenshots go under
`guide/_coverage/notes/<PACKAGE>/`). The server is closed when the turn ends, on timeout and on SIGINT/SIGTERM
of the tool. Both are recorded in `run.json` (`network`, `browser`), so a `reply` to such a run keeps them.
Without the flags the `codex exec` command line is unchanged.

## Usage limits and stops

Codex's prompt asks it to work in small units, write each finished unit into its files before the next,
keep notes only under `guide/_coverage/notes/<PACKAGE>/` (never `/tmp`) and continue from its files when an
earlier run stopped. When a turn ends on Codex's usage limit, `run.json` records `usageLimit` for the turn,
the tool prints `USAGE LIMIT: ...` and `run`/`reply` exit 75. `run --wait-on-limit` then waits until the time
the message names (plus two minutes, but at most 20 minutes, since the limit may be lifted earlier; 30 minutes when it names none) and starts the wave again in a fresh
session, up to `--max-restarts` (default 6) times. Never continue a long session with `reply` to finish a
large task: start a fresh run; the files carry the progress.

## Reading a check

`check.md` lists changed files in two groups. Outside-the-list files are reported loudly and never
reverted, because other sessions edit the same tree. Each file is tagged by what Codex's event log
shows: "in Codex file-change events" (Codex wrote it: a real violation), "named in a Codex command
only" (look), or "NOT in Codex events (probably another session)". Codex edits made by a shell
command (not by its patch tool) appear only as "named in a command" or "NOT in events", so the tag is
evidence, not proof; read the diff when it matters. The comparison spans from the start of turn 1, so
edits by other sessions between turns also show.

## Where things are stored

`guide/_waves/runs/<PACKAGE>/<timestamp>/` (git-ignored through `guide/.gitignore`):
`prompt.md`, `run.json` (session id, model, allowed list, per turn: times, exit code, usage, files in
Codex's change events, check result), `last-message.md` (newest turn's final message), and per turn
`turn-N.prompt.md`, `turn-N.events.jsonl` (capped at 20 MB, then a truncation note; stderr capped at
1 MB), `turn-N.last-message.md`, `turn-N.before.json`, `turn-N.after.json`, `check.md`. Delete run
folders when a wave is done.

One run at a time: `guide/_waves/runs/.lock` holds the PID; a second `run` or `reply` refuses while
the PID lives, and a lock of a dead PID is removed.

## Limits of the Codex CLI (0.166.0)

- `codex exec resume` has no `-s` and no `-C`; the tool sets `-c sandbox_mode="workspace-write"` and the
  working directory instead.
- A session id comes from the `thread.started` event (`thread_id`); `reply` stops if turn 1 never reported one.
- Usage comes from the `turn.completed` events; an interrupted turn has none, so its figures are low.
- The model that ran is not in the event stream; the tool reports `--model` or the configured default.
