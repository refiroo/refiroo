# C11 fix 2: what the fresh reader and the clean-host rehearsal found

Read `guide/AGENTS.md`. Readers: the guide's readers, as each page names.

## Why

DOC11 (`docs/BASE_0_13_IMPLEMENTATION_PLAN.md`, "DOC11: Fresh-reader check") was done a second time on
2026-11-08, this time by doing the steps rather than reading them:

- A reader followed every journey (except "Work with an assistant") in a real browser and with real
  requests on the reference installation. Their findings are in
  `_coverage/notes/C11-READER2/findings.md` (numbered 1–10) and `_coverage/notes/C11-READER2/report.md`
  ("Remaining coverage gaps").
- The run pages' commands were run on a clean host, including an upgrade. Those findings are in
  `_coverage/notes/C11-HOST/findings.md` (numbered 1–13).

## Already fixed in the product (bring the pages in line)

These were product defects. They are fixed in the code now, so the pages must describe the product as
it is. Check each one against the code; the code wins.

- C11-READER2 1: an empty hierarchy now offers "Add <type>" for its top-level type, with no parent field.
- C11-READER2 5: a follower notice for a publication that is no longer current opens the workspace's
  Publications.
- C11-READER2 6: a retired workspace's band says "Retired: read only."; the read-only notice box keeps the
  full sentence.
- C11-READER2 7, 8, 9, 10: see the "Fixed (found by the fresh-reader check, 0.13 DOC11)" entries in
  `../CHANGELOG.md` under Unreleased (supplier-profile save in the browser, Preview again after a partly
  refused deletion, the draft conflict summary's names, "Update them anyway" on an exported workbook).
- C11-HOST 7: `create_admin` without a terminal now says to use `--password-stdin` and exits 2.
- C11-HOST 13: `generate_key --help` and `database_upgrade --help` print help and do nothing else.

## What to do

- Fix every other finding the pages can fix, in the page where the reader got stuck. Check the fix
  against the product (`backend/app/`, `frontend/src/`, `docs/`, `docker-compose*.yml`, `deploy/`): the
  code wins.
- C11-HOST 1: `v0.16.0` cannot be built and a tag cannot be changed. No page may tell a reader to check
  out `v0.16.0`. Find out from the pages and `../CHANGELOG.md` what the pages should name instead, and
  say in the report what you chose and why.
- C11-HOST 4: give the role keys where a page asks for one (`create_client --role`, API grants), next to
  the names the screens show. Take the keys from the code.
- The two remaining coverage gaps in `report.md` that are not findings: the Conflict state of a
  matrix (valid writes cannot produce it in the reader's model), and raising an older model language
  (this version accepts only the current schema version for a new draft). Check whether each page
  tells a reader honestly when the state arises, or what they need before the steps apply. Fix the
  page if it does not.
- The visual editor's refusal of a released-field type change says "migration (planned for 1.0)"
  (findings.md, near screenshot 14), while the specialist JSON route allows the change and its reviewed
  migration. If a page sends a reader to the visual route for this, fix the page. If the product's
  sentence is wrong, report it as a product defect.
- A finding that is still a product defect (the product does something the guide cannot honestly
  describe around) is not fixed in the page by working around it: list it in your report with the
  evidence.
- A finding you judge wrong (the page already says it, the reader misread): say why in the report.
- Findings 2 and 3 of C11-READER2 were the installation's setup: nothing to do.
- No new pages unless a finding cannot be fixed without one; no new pictures. A picture that no longer
  matches the product after these fixes: list it in the report.

## Files you may edit

- `src/content/docs/**/*.md`
- `src/content/docs/**/*.mdx`
- `_coverage/notes/C11-FIX2/**`
- `_waves/progress/C11-FIX2.md`

## Report

Per finding (C11-READER2 1–10, C11-HOST 1–13, the two coverage gaps and the released-field sentence):
fixed (page and what changed), a product defect (evidence), or not changed (why). Then the pictures
that no longer match.
