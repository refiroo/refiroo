# C1: read the record and build the coverage list

Read `guide/AGENTS.md`, then `guide/_waves/COMPLETE-COMMON.md`. This wave writes no documentation pages.
It builds the list every later wave writes from.

## 1. Complete the record

`_waves/PROMISES.md` (what refiroo promises its users) and `_waves/BEHAVIOUR-RULES.md` (rules a person
meets: add-only relationships, cascade deletes, narrowed grants…) were built from the journeys and
capabilities in full, but the CHANGELOG and the release plans only mechanically or not at all.

Read `CHANGELOG.md` release by release, from the oldest to 0.16.0, and for each release its plan
(`docs/BASE_0_*_IMPLEMENTATION_PLAN.md`, the delivered packages and their decisions; skip packages marked
superseded or not built). For every capability, screen, setting, rule, limit, message, command, event or
behaviour a reader could meet:
- add it to `PROMISES.md` if no row says it yet, with its source (release and package);
- add each rule a person meets to `BEHAVIOUR-RULES.md` in the form used there, with its source;
- where a later release changed or removed something, record the current behaviour only and mark the
  older row superseded.

Then deduplicate `PROMISES.md`: the mechanically extracted rows (changelog, plans, git history) are leads;
merge rows that say the same thing, drop rows that are not about the product (tooling, tests, delivery
history), and keep each surviving row's sources. Check doubtful rows in the code.

## 2. Build `_waves/COVERAGE.md`

One table, every item once, from all of: `PROMISES.md`, `BEHAVIOUR-RULES.md`, `OUTLINE.md`,
`NOT-YET-COVERED.md`, `MODEL-EDITOR-INVENTORY.md`, `UI-INVENTORY-SETTINGS.md`, `UI-INVENTORY-DATA.md` and
`../_coverage/restored/INVENTORY.md` (settings, error codes, commands, roles, events, model-language fields),
plus every user journey in `docs/product-functionality/USER_JOURNEYS.md`.

Columns: `ID` (C0001…), `Item` (one plain sentence), `Kind` (capability, screen, setting, rule, limit,
message/error, command, event, journey, term), `Reader` (evaluator, steward, model-admin, access-admin,
operator, integrator; several allowed), `Section` (about, use, model, administer, run, integrate,
examples, journeys), `Source`, `Covered by`.

Fill `Covered by` by reading the existing pages in `src/content/docs/`: the page (and heading) that covers
the item fully, or `partly: <page> — <what is missing>`, or `uncovered → <planned page path>` using the
paths in `OUTLINE.md` and `astro.config.mjs` `GROUPS`, or `after 0.16`, or `not for readers: <reason>`.
An item covered for one reader but not another needs both. Group the table by section, then by
capability. At the top, counts per section: covered, partly, uncovered, after 0.16.

Journeys: one row per journey in `USER_JOURNEYS.md`, section `journeys`, with a category (the reader's
goal, for example "Look after data", "Change with approval", "Integrate a system") and the pages and guides
that journey uses. A later wave writes the User journeys section from these rows.

## Files you may edit

- `_waves/PROMISES.md`
- `_waves/BEHAVIOUR-RULES.md`
- `_waves/COVERAGE.md`
- `_coverage/notes/C1-RECORD/**` (working notes)

## Report

The releases and plans read (all of them, or say which not and why), rows added to PROMISES and
BEHAVIOUR-RULES, rows merged or dropped, the counts per section, and anything in refiroo that looked wrong.
