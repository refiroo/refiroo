# Handover: the refiroo documentation (0.13)

Written 2026-11-02 at the end of a long session, for the session that continues the work.

## What is being built

refiroo's product documentation and user guide, served by the engine at `/docs` (the API reference moved
to `/docs/api`). Readers: evaluators, data stewards, model administrators, access administrators,
operators and integrators. Documentation pages explain a capability and its rules; guides take the reader
through a task; the guide pages sit under their documentation page in the sidebar. Everything refiroo does
is already recorded for developers (CHANGELOG, the release plans `docs/BASE_0_*`, the technical documents);
the documentation tells it to each reader, completely. Applications (the starter model's three, the
Graubünden example's three) are examples of capabilities, never features of their own.

## How the work is done

- **Codex writes every page.** Claude writes none. The guidance Codex follows is `guide/AGENTS.md`; each
  job is an assignment file in `guide/_waves/` run with `node guide/tools/codex-wave.mjs run <NAME>`, then
  `check <NAME>` (see `guide/tools/CODEX_TOOL.md`). One Codex job runs at a time.
- **Screenshots** come from the Graubünden reference instance (`guide/reference/`, Docker project
  `refiroo-guide-ref`, http://localhost:8480, sign-in in `guide/reference/.env`) through
  `guide/tools/screens.mjs` and a `*.screens.json` list. Name files by what they show.
- **Claude's usage was the problem this session** (about 10% of a weekly limit since the switch to Codex,
  mostly screenshot passes, inventories and a very long Opus conversation). Give reading, inventories and
  screenshot passes to Codex as well; keep Claude's turns short: prepare a job, check its report, talk with
  the user.

## Where things stand

Written by Codex (about 64 pages, building and linking cleanly): Use refiroo (home, account, applications
and workspaces, records, relationships, hierarchies, mapping grids, relation matrices, change sets,
publications, history, inbox and approvals), Model your data (first version, too thin), Administer access,
Example applications, and Run refiroo (written last; not yet reviewed against the record).

Material for completeness, in `guide/_waves/`:
- `OUTLINE.md`: every page the documentation needs, with sources; `NOT-YET-COVERED.md`: what existing pages
  miss.
- `MODEL-EDITOR-INVENTORY.md`, `UI-INVENTORY-SETTINGS.md`, `UI-INVENTORY-DATA.md`: what every
  screen lets a person do, in its own words.
- `BEHAVIOUR-RULES.md`: 97 rules (add-only relationships, cascade deletes, narrowed grants…); partial: the
  CHANGELOG and most release plans were not read in full.
- `PROMISES.md`: 3,034 rows; journeys and capabilities read in full, the changelog, plans and git history extracted mechanically (leads only, not deduplicated against the rest).
- `../_coverage/restored/INVENTORY.md`: the restored 853-item inventory (settings, error codes, commands,
  roles, events, model-language fields included).

## Structure: settled, not to be changed

The user (2026-11-02): no new direction and no reorganisation. The current sections stay as they are and
are completed. Pages are not moved between sections. Within a section that is only a flat list of pages
(Run refiroo), group the pages into subsections. Add a User journeys section: every journey in categories,
each described on a documentation page that links the guide pages it uses. The life-of-data concept that
an earlier session proposed was rejected.

## Delivery status (2026-11-03, stopped: Codex usage limit)

The delivery chain is written as waves `C1-RECORD` … `C11-FINAL` in `_waves/`, with the shared rules in
`_waves/COMPLETE-COMMON.md`; run them in order, one at a time, `run` then `check`. Run refiroo's sidebar
already has its groups (`astro.config.mjs`). C1 ran one turn: CHANGELOG 0.3–0.6 read in full, later
releases only selectively; `COVERAGE.md` has 3,920 provisional rows; 1,246 release leads unreconciled. Its
second turn read the whole CHANGELOG and plans 0.7–0.9, applied a few corrections, then failed while
compacting its context on Codex's usage limit; most of what it read was not written down. Its notes and
extracts are kept in `_coverage/c1-notes/`. To resume: run `C1b-RELEASES` (one release at a time, saving
after each, reusing the notes), then C2 onwards. If Codex runs out again, stop; Claude does not take over.

## Next

1. Group Run refiroo's pages into subsections; plan the User journeys section.
2. Have Codex read the CHANGELOG and the release plans release by release and complete `PROMISES.md` and
   `BEHAVIOUR-RULES.md`; build one coverage list from all the material above against the pages.
3. Codex writes from that list section by section until nothing is uncovered: the larger Model section
   from the editor inventory, the new Use pages, Integrate (`_waves/INTEGRATE.md` is ready), About, the
   catalog, the Journeys, the start page.
4. The AI pages for stewards and model administrators once the user has set up Claude Code in the
   reference instance (`/docs/run/set-up-ai/`).
5. Small loose ends: Run refiroo links to four screenshots it asked for (`run-jobs`, `run-backup-rehearsal`,
   `run-deployment`, `run-operations`) and to four pages not written yet (`check:links` lists them); a 404 page;
   rebuild the reference instance's image so it serves the current documentation; nothing is committed yet
   (the tree is shared with other sessions: commit only this work's files, on the user's request).

## What went wrong, briefly

Pages were written from short topic lists instead of from the product's own record, so they missed most
of what refiroo does; reusable work was deleted when the approach changed; questions were taken as
instructions; the user's words were read too literally. Read the user for intent, keep what was right, and
let completeness come from the record.
