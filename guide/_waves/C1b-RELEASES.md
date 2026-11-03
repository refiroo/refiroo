# C1b: finish reading the record, one release at a time

Read `guide/AGENTS.md`, `_waves/COMPLETE-COMMON.md` and `_waves/C1-RECORD.md` (the task and the formats).
C1 read CHANGELOG 0.3–0.6 fully; its second turn read the rest of the CHANGELOG and plans 0.7–0.9 but
stopped before writing most of it down. Its notes and extracts are in `_coverage/c1-notes/` (`notes.json`:
what was read, facts, supersessions, corrections already applied; `plan*-packets.json`,
`records*.json`: extracts of plans 0.9–0.12 and 0.16). Reuse them; do not re-extract.

**Work in small steps and save after each.** Take the releases one at a time: 0.7, 0.8, 0.9, 0.10, 0.11,
0.12, 0.16 (and any other release section the CHANGELOG has). For each release: read its CHANGELOG section
and the delivered packages of its plan, reconcile that release's leads in `PROMISES.md` (merge, rule,
superseded, or drop as not about the product), add its rules to `BEHAVIOUR-RULES.md`, update the affected
`COVERAGE.md` rows, and **write all three files before starting the next release**. At the top of
`PROMISES.md`, keep a line "Releases reconciled: …" up to date, so a stop loses at most one release. Keep
your context small: read in parts, do not hold several releases at once.

When every release is done: merge the semantic duplicates in `COVERAGE.md`; for rows marked partly only
because a page was not read clause by clause, read the page and mark the row covered or name what is
missing; update the counts and remove the "Provisional" note.

## Files you may edit

- `_waves/PROMISES.md`
- `_waves/BEHAVIOUR-RULES.md`
- `_waves/COVERAGE.md`
- `_coverage/notes/C1b-RELEASES/**` (working notes)

## Report

The releases reconciled, rows added, merged, superseded or dropped per release, the final counts, and
anything in refiroo that looked wrong.
