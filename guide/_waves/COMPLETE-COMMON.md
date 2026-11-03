# Completing the documentation: rules for every wave

These rules apply to every wave named `C*-...`. Read them after `guide/AGENTS.md` and before your assignment.

**The goal.** The documentation tells each reader everything refiroo does that concerns them. Completeness
comes from the product's own record, not from a topic list: `_waves/coverage/<section>.md` lists every
item of that record for one section, the reader it concerns and the page that covers it. Several waves run
at the same time, each in its own files. Your wave covers its section's items until none
is left uncovered.

**The structure stays.** The sections are settled: About, Use, Example applications, Model, Administer,
Run, Integrate, plus User journeys. Do not move pages between sections and do not reorganise a section.
Add pages and guides where an item has no home, and add them to the section's sidebar file
`sidebar/<section>.mjs` (under the right group; a page not listed there is not shown). Other sections' pages and coverage files are read-only for you; link to them. Within a section, you may add a
group when it has grown past about eight entries without one; keep the existing groups and their order.
Edit only your own section's sidebar file.

**Content in the wrong section.** Where `_waves/NOT-YET-COVERED.md` section C says a part of a page belongs
to another reader, write that part on the other reader's page and leave a short link in its place. Never
delete a page; if a whole page should go, say so in your report.

**Sources.** Your coverage file names each item's source. Check facts in the source and in the code
(`frontend/src/` for labels exactly as shown, `backend/app/` for rules); the code wins. Screens and labels
must exist as written. Unsure → say so in the report, never guess.

**Depth.** A documentation page explains what the capability is, how it works, its rules, states, limits,
who may do what, and what a reader may wonder ("Why can't I…?": take these from `_waves/BEHAVIOUR-RULES.md`,
each rule as the reader meets it, with what to do instead). A guide takes one task step by step, naming
each button and what the reader then sees, and what can go wrong.

**Screenshots.** Reference existing ones from `public/screens/` where they show the right screen. For a
screen not yet taken, insert `![what it shows](/docs/screens/<name>.png)` with a name saying what it shows,
and add an entry for it to `_waves/screens-wanted/<your wave>.md` (name, page, the screen and its state, what must be
visible). They are taken afterwards.

**After 0.16.** The AI features (asking a list in words, proposed targets, the assistant, changing a model
from words, accounts of changes, AI settings, agent access) are not written now; leave their rows as they
are in the coverage file. Digests and following a workspace are not AI and are written now.

**Update your section's coverage file.** For each item you cover, put the page (and section anchor where useful) in
its "Covered by" column. An item you find is not for readers (internal tooling, tests, a superseded
decision) gets "not for readers: <reason>". Leave no row of your section empty or "uncovered".

**Before you stop.** Run `GUIDE_OUT=_build/<your wave> npm run verify` in `guide/`; it must pass (build, terms, brand, links). End with
a report: the pages written or changed, the coverage rows of your section still open and why, the
screenshots added to your screens-wanted file, anything you were unsure of, and anything in refiroo that looked wrong.
