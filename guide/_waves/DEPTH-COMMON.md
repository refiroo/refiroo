# Full documentation: rules for every D-* wave

Read `guide/AGENTS.md` first, then `_waves/COMPLETE-COMMON.md` (its "After 0.16" paragraph no longer applies: the AI
pages are written and are completed like every other page), then this file, then your wave file.

**The requirement.** The owner of refiroo asked for a full documentation: everything refiroo does, documented so a
reader can do the work from the pages alone. Each time the owner read a section, a lot was missing (how to set up
HTTPS and what happens at certificate renewal, how to add a navigation bar), and they had to ask piece by piece. These
waves end that. Do not wait to be asked for anything: if a reader of your section would need it, it belongs on a page.

**What "everything" is.** Not a topic list. Two lists made from the code:

1. `_coverage/inventory/<kind>.json`: every setting, command, permission, screen and editor action, model feature,
   consumer API operation, MCP tool and deployment piece, each with `section`, `key`, `labels` and `source`
   (file:line). `_coverage/inventory/uncovered.md` lists the entries of each section that no page names yet. Your
   section's entries are your scope.
2. The depth questions below, asked of every capability of your section, also the ones already "covered". Covered
   only means a page names it.

**The depth questions.** For each capability, answer every question that applies, on the page that owns it:

- What is it, and when does a reader need it?
- How is it set up? (each screen and button, or each command, file excerpt and setting, with what the reader sees when
  it worked)
- How is it changed later, and what happens to existing data or users when it changes?
- Does it expire, renew, rotate or grow? What happens then, and what does the reader do or watch for?
- How does it fail? Each refusal or error message exactly as refiroo shows it, its cause, what to do.
- How is it recovered, moved to another server, backed up and restored?
- How is it turned off or removed, and what remains?
- Its limits and defaults, and which permission it needs (who may, who may not, what the others see).

A question that does not apply is skipped, not answered with filler. An answer comes from the code (`backend/app/`,
`frontend/src/` for labels exactly as shown, `compose*.yml`, `caddy/`, the Dockerfiles), never from memory; the code
wins over `docs/`. If the code does not answer it, write it in your notes and the report, never guess.

**How you work.** One unit at a time, saved before the next (the tool's prompt says how): a unit is one page, or one
capability across its documentation page and its guide. Order: first the uncovered entries of your section, then the
existing pages in sidebar order, each held against the depth questions. For each page note in
`_coverage/notes/<wave>/depth.md` which questions you answered and which do not apply.

**Exclusions.** An entry not for readers (an internal mechanism, a test, a field the engine does not read) gets a line
in `_coverage/exclusions.md`: `kind key — reason`, the reason checked in the code. Never exclude something because it is
hard to write.

**Product defects.** Where the product does not do what a reader would expect, or a screen is missing, document what
it does, and list the defect in the report with the code reference. Do not describe intended behaviour.

**Done.** In `guide/`: `GUIDE_OUT=_build/<wave> npm run verify` passes, and `node tools/check.mjs coverage` lists no
entry of your section in `_coverage/inventory/uncovered.md` (run `../backend/.venv/bin/python tools/inventory.py` first
if the inventory is missing). Report: pages written or changed (words before and after), entries covered or excluded,
depth questions left open and why, screenshots wanted, defects found.
