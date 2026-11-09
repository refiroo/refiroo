# D-ADMIN: "Administer access" documented in full

Read `guide/AGENTS.md`, `_waves/COMPLETE-COMMON.md` and `_waves/DEPTH-COMMON.md`, in that order. Reader: administrators, who manage people, groups, roles, clients, sign-in, mail and security for their organisation.

Your scope: the entries of section `administer` in `_coverage/inventory/*.json` (those still in `_coverage/inventory/uncovered.md`
first), then every page of the section and its guides, each held against the depth questions of `DEPTH-COMMON.md`.

Every permission in `_coverage/inventory/permission.json` (`engine/authorization/catalogue.py`: groups, actions, predefined roles, the agent ceiling) is named on a page with what it allows, in the words the screens use, and what a person without it sees (screens hide what cannot be done). A reference page listing every action group, its actions and the predefined roles that hold it belongs in this section if none exists.

## Files you may edit

- `src/content/docs/administer/**`
- `src/content/docs/guide/administer/**`
- `sidebar/administer.mjs`
- `_waves/coverage/administer.md`
- `_coverage/exclusions.md` (only lines for section `administer`)
- `_waves/screens-wanted/D-ADMIN.md`
- `_coverage/notes/D-ADMIN/**` (working notes)

## Report

As `DEPTH-COMMON.md` says.
