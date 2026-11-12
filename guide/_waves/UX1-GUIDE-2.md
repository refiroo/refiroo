# UX1-GUIDE-2: two entries the guide does not cover yet

`npm run check:coverage` in `guide/` reports two inventory entries that are on no page
(`guide/_coverage/inventory/uncovered.md`). Cover each with one or two plain sentences on the page where a reader
would look, changing nothing else:

1. **Permission `action:mail-template.manage`**, shown to people as "Editing the e-mail template" (Edit the e-mail
   template, its logo and send a test of it; `backend/app/engine/authorization/catalogue.py`). It is in the
   Operations action group, which the Operator role holds. Put it where the administer pages list what each
   action group or role allows (the roles, grants or permissions reference), with its label exactly as the
   application shows it so the coverage check finds it.
2. **The confirmation "Stop keeping local sign-in"** on a person's page
   (`frontend/src/features/security/PeoplePage.tsx`): turning the "Keeps local sign-in" switch on saves at once
   with Undo; turning it off asks once, with the button "Stop keeping local sign-in". Put it on the page that
   describes a person's sign-in or local sign-in, in the section it belongs to (the entry is filed under `use`;
   read `guide/tools/check.mjs` and `guide/_coverage/exclusions.md` to see how an entry is matched to a page
   section, and place the sentence where the check will find it).

Read the code before writing. After editing, run `GUIDE_OUT=_build/UX1-GUIDE-2 npm run build` and
`npm run check:coverage` in `guide/` and repeat until coverage reports no uncovered entry.

## Files you may edit

- `src/content/docs/administer/*.md`
- `src/content/docs/guide/administer/*.md`
- `src/content/docs/use/*.md`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/run/*.md`

## Report

The sentences added, with their page, and the coverage check's last line.
