# SH1: the frame changed

Package SH1 of 0.17 changed the application's frame (the specification is
`docs/BASE_0_17_IMPLEMENTATION_PLAN.md`, section "SH1: One frame, one location line", decisions PP-D33 to
PP-D37; the delivered behaviour is in `CHANGELOG.md` under "Changed (0.17 SH1: one frame, one location line)"
and in `docs/UI_MODEL.md`). Bring the pages listed below in line with it. Change only sentences that the facts
below make wrong or incomplete, and add a sentence only where a reader would otherwise not find the new place.
Do not restructure pages, do not rewrite correct text, do not touch screenshots or their captions' file names.
Work page by page and save each page before the next.

## What is true now

Check each fact against the code under `frontend/src` before you write it (`app/TopBar.tsx`,
`app/DataContextBand.tsx`, `features/workspaces/WorkspacePage.tsx`, `features/workspaces/WorkspaceSearch.tsx`,
`features/objects/ObjectDetail.tsx`, `features/objects/RecordActionMenu.tsx`, `features/objects/Explorer.tsx`,
`features/settings/navigation.ts`, `features/settings/SettingsIndex.tsx`, `features/workspaces/ChangeSets.tsx`,
`features/workspaces/ChangeSetReview.tsx`, `ui/DataTable.tsx`, `features/home/HomePage.tsx`).

1. **A workspace has a page.** A workspace card on Home opens the workspace's page, not its first list. The
   page has a search over the names of all records in the workspace (results grouped by list, each with its
   path; arrow keys and Enter open one), the workspace's applications, the person's own waiting change sets,
   the five latest changes, **Edit model** and a ⋯ menu leading to the workspace's Settings pages. Each action
   shows only to a person who may use it.
2. **The top bar has the same search** ("Find any record") on every application page. Applications that do not
   fit in the top bar are under **More**.
3. **The band under the top bar** shows the data context only: Live, a change set, or a publication, one
   sentence, and the Live · Change sets · Publications switch. On a computer it no longer repeats the workspace
   and the application; on a phone it still shows both.
4. **In a change set** the band is one row: the change set's name, its number of changes and state, and
   **Details** (who started it, when, version, model).
5. **Opening a change set from the change set list** opens "Changes in this change set" (formerly "Review
   changes"). **See the data with these changes** leads to the lists in that change set. A change set a person
   has just started, and their own open change set from Home's Continue, open on the data as before.
6. **A record page** has one line above the title: "← ‹the list›" followed by the record's parents. There is
   no separate "Back to list" button and no application entry. The record's ID and version are under
   **Details** in the header; **Copy ID** is also in the record's ⋯ menu.
7. **The sidebar's Browse records** is folded until a person opens it (remembered in that browser) and has no
   search box of its own; the top bar search finds a record by name.
8. **A list page is titled by its list** (the sidebar entry); its views are tabs under the title.
9. **Tables** keep the name column whole and fold the columns that do not fit behind **Columns · n of m**.
10. **Settings** opens on an index of all pages by task. The groups are: You; Workspaces and models; People and
    access; Connections; This instance (About is last). The former group names (General, Security,
    Administration, Integration, Data operations) are gone: read `features/settings/navigation.ts` for which
    page is in which group and correct every path such as "Settings › Security › People". Inside Settings the
    top bar shows **← Back to ‹workspace›** instead of the application tabs. Settings pages have one trail
    line; there is no separate Back button beside it.
11. **Home cards** show a workspace's roles on one line (the first roles, then "and n more").

## Files you may edit

- `src/content/docs/use/applications.md`
- `src/content/docs/use/records.md`
- `src/content/docs/use/lists-and-filters.md`
- `src/content/docs/use/hierarchies.md`
- `src/content/docs/use/change-sets.md`
- `src/content/docs/use/history.md`
- `src/content/docs/use/inbox-and-approvals.md`
- `src/content/docs/guide/use/*.md`
- `src/content/docs/guide/use/*.mdx`
- `src/content/docs/guide/model/*.md`
- `src/content/docs/guide/model/*.mdx`
- `src/content/docs/model/*.md`
- `src/content/docs/model/*.mdx`
- `src/content/docs/guide/administer/*.md`
- `src/content/docs/guide/administer/*.mdx`
- `src/content/docs/administer/*.md`
- `src/content/docs/administer/*.mdx`
- `src/content/docs/guide/integrate/*.md`
- `src/content/docs/guide/integrate/*.mdx`
- `src/content/docs/integrate/*.md`
- `src/content/docs/integrate/*.mdx`
- `src/content/docs/run/*.md`
- `src/content/docs/run/*.mdx`
- `src/content/docs/about/security-and-trust.md`
- `src/content/docs/examples/the-consumer-api.md`
- `src/content/docs/journeys/work-with-an-assistant.md`

## How to find the sentences

Search the listed pages for: "Back to list", "breadcrumb", "Browse records", "Search this explorer",
"Review changes", "Open change set", "Settings ›", "Settings >", "General", "Security", "Administration",
"Integration", "Data operations", "About", "Copy ID", "ID under", "version", "band", "workspace card",
"Home". Read each hit in its paragraph and decide by the facts above; most hits need no change.

## Report

Per page: the sentences changed (old and new), or "no change". Then the screenshots that now show an outdated
frame, by file name, without changing them. Then anything in the facts above that the code contradicts.
