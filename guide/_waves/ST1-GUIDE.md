# ST1-GUIDE: the Settings pages changed

Package ST1 of 0.17 redesigned the application's Settings pages (decisions PP-D60 to PP-D67 and section "ST1" in
`docs/BASE_0_17_IMPLEMENTATION_PLAN.md`; the delivered behaviour is the entry headed **Changed (0.17 ST1: Settings
as one family)** at the top of `CHANGELOG.md`). Bring the pages listed below in line with it. Change only sentences
that the facts below make wrong or incomplete, and add a sentence only where a reader would otherwise not find the
new place. Do not restructure pages, do not rewrite correct text, do not touch screenshots, their references or
their file names. Work page by page and save each page before the next. Most listed pages need no change: say so in
the report.

Check every fact against the code before you write it (`frontend/src/features/settings/`, `features/security/`,
`features/workspaces/WorkspaceAdmin.tsx`, `features/model-admin/ModelReleaseDetail.tsx`, `features/changes/ChangesPage.tsx`,
`ui/SettingsParts.tsx`, `ui/Trail.tsx`). The code wins over this list and the changelog; where they differ, write
what the code does and list the difference in your report. Never guess a button's label: read it in the code.

## What is true now

1. **Lists open items as pages.** People, Groups, Clients, Sign-in, Import profiles and Webhooks are full-width
   lists (as Workspaces and Model already were). A row opens the item's own page; the first line of that page leads
   back to the list ("← People", "← Groups", "← Clients", "← Sign-in", "← Import profiles", "← Webhooks", "←
   Workspaces", the Model pages likewise). The narrow list beside the selected item is gone: wording such as "the
   list on the left", "select the person in the list", "with no person selected" must say that the row opens the
   person's page, and that the way back is the first line of the page.
2. **An opened item has a header with at most two actions; the rest are in the ⋯ menu ("More actions").** What cannot
   be undone is last in the menu. Per page, as the code now has it:
   - Person: header **Reset password** or **Make a password link**, **Edit…**, **Restore** (a deactivated person); in
     the menu **See changes**, **Link to an existing person…** (when it applies), **Sign out everywhere**,
     **Deactivate**.
   - Client: header **Rotate secret…** (stays in the header), **Restore** (a deactivated client); in the menu
     **See changes**, **Deactivate**.
   - Webhook: header **Suspend** or **Resume…**; in the menu **Rotate key…**, **Delete…**.
   - Workspace: header **Open workspace**, **Edit model**; in the menu **Set as default**, **Copy or move data…**,
     **Retire…** or **Reactivate**, **Delete…**.
   - Model release: header up to two of **Activate in a workspace…**, **Create draft from release**, **Export JSON**;
     in the menu the rest, **Retire…** or **Bring back**, **Delete…**.
   - Import profile: header **Upload the next version…**, **Load into a change set…**; in the menu **Delete the
     file…** (when a next version is stored), **Delete the profile…**.
   - Not moved: a group's **Delete group** and a sign-in provider's delete stay buttons on their page; on Account
     **Sign out everywhere** stays a button in its own group; Signing keys' **Retire the current key now** is not in
     a menu. Read each in the code before you say where it is.
3. **Logs are on a tab** (the tab is in the address as `?tab=`): Mail has **Server** and **Messages** (the outbox
   and its State filter are on Messages); AI has **Settings** and **Calls**; Agent access has **Access** and
   **Calls**; Jobs has **Jobs** and **Limits**; a webhook has **Configuration** and **Deliveries**; a workspace has its
   own tabs. A log shows the time first as "today, 16:34" with the full time on hover, numbers right-aligned, a
   duration in seconds and minutes, its states as chips, its totals above, and below it "n of m ‹things›" with
   **Show more**. **Show more** replaces **Load more…**, **Load more messages**, **Load more calls**, **Load more
   jobs** and similar on the Settings log pages (Mail messages, AI calls, Agent access calls and lists, Jobs, a
   webhook's deliveries, Signing keys, a person's or a group's lists, the changes page). Where the code still says
   **Load more** or **Show fewer** (a person's or client's Recent activity, Home, a change set list), keep the old
   word.
4. **Operations**: the earlier rehearsals are folded behind **Show earlier rehearsals (n)** / **Hide earlier
   rehearsals**; once open they have **Show more**. Read `OperationsPage.tsx`.
5. **The Settings index** lists every page the person may open, by group, each with one line saying what it is for;
   the groups have colours. Read `features/settings/navigation.ts` for the lines and the groups.
6. **Deployment** shows each setting as a row: its name with what it controls, its value, the default only where the
   value differs, and where the value came from. Nothing is edited there.
7. **Account** and **Notification email** are no longer a centred column: each group (on Account: You, Sign-in,
   Password, Where you're signed in, What you can do; on Notification email: Email) is its own panel with its title
   and a sentence on the left and its rows on the right. Mail's form and every other form saved as a whole sits in
   one panel with **Save** in its foot.
8. **Every Settings page's header** carries the page's group, its glyph in the group's colour, one or two sentences
   and the page's one main action. A person and a client have their initials in a colour of their own; a role keeps
   its coloured chip in the People list and on a person's page.
9. **One person's changes** (**See changes** on a person or a client) begins with a way back (the first line, "←
   Back"), shows its kinds of change with colour markers, and its list ends with "n of m changes" and **Show more**.
10. No route, permission or capability changed. The People list has no Groups column.

## Files you may edit

- `src/content/docs/administer/*.md`
- `src/content/docs/guide/administer/*.md`
- `src/content/docs/use/account.md`
- `src/content/docs/use/notifications-settings.md`
- `src/content/docs/use/jobs.md`
- `src/content/docs/use/importing-and-exporting.md`
- `src/content/docs/use/workspaces.md`
- `src/content/docs/guide/use/set-up-email-notices.md`
- `src/content/docs/guide/use/follow-and-cancel-a-job.md`
- `src/content/docs/guide/use/import-a-file.md`
- `src/content/docs/guide/use/load-the-next-version-of-a-workbook.md`
- `src/content/docs/guide/use/open-a-retired-or-unavailable-workspace.md`
- `src/content/docs/model/managing-workspaces.md`
- `src/content/docs/model/releases.md`
- `src/content/docs/model/models.md`
- `src/content/docs/model/workbook-onboarding.md`
- `src/content/docs/guide/model/create-a-workspace.md`
- `src/content/docs/guide/model/retire-or-delete-a-workspace.md`
- `src/content/docs/guide/model/retire-or-delete-a-release.md`
- `src/content/docs/guide/model/make-a-workspace-the-default.md`
- `src/content/docs/guide/model/compare-releases.md`
- `src/content/docs/guide/model/export-a-release.md`
- `src/content/docs/guide/model/change-a-workspaces-model.md`
- `src/content/docs/guide/model/delete-a-draft.md`
- `src/content/docs/run/ai.md`
- `src/content/docs/run/set-up-ai.md`
- `src/content/docs/run/webhook-delivery.md`
- `src/content/docs/run/background-jobs.md`
- `src/content/docs/run/sign-in-and-mail-setup.md`
- `src/content/docs/run/configure.md`
- `src/content/docs/run/production-checklist.md`
- `src/content/docs/guide/integrate/connect-an-assistant.md`
- `src/content/docs/guide/integrate/subscribe-a-webhook-and-verify-it.md`
- `src/content/docs/integrate/consumer-events-and-webhooks.md`
- `src/content/docs/journeys/manage-access.md`
- `src/content/docs/journeys/work-with-an-assistant.md`
- `src/content/docs/journeys/shape-a-model.md`

A new page needs a sidebar entry, which is outside this list: add no page.

## How to find the sentences

Search the listed pages for: "Settings ›", People, Groups, Clients, Sign-in, Webhooks, Import profiles, Deployment,
Mail, Agent access, Jobs, Calls, Limits, outbox, "Load more", "Deactivate", "Sign out everywhere", "Retire", "Rotate
key", "Rotate secret", "See changes", "Delete", "Account", "Notification email", "with no ... selected", "in the
list", "list on the left", "select". Read each hit in its paragraph and decide by the facts and the code; many hits
need no change.

## Report

Per page: the sentences changed (old and new), or "no change"; anything where the code contradicts this list or the
changelog; the screenshots on the listed pages that now show an outdated Settings page (file name and page).
