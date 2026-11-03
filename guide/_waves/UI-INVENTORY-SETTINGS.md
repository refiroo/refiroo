# Settings and administration inventory (what a person can do in the browser outside the applications)

Source: `frontend/src` read 2026-11-02 (read-only, code only; no running instance was used). Paths are under `frontend/src/` unless stated.
Abbreviations: SA = `app/SettingsArea.tsx`, SN = `features/settings/navigation.ts`, SM = `app/SettingsMenu.tsx`, ST = `features/settings/`, SE = `features/security/`, WS = `features/workspaces/`, SI = `features/sign-in/`.
"ai-later" = a 0.16 AI/assistant feature. "Precondition" names the role (action group), the server setting, or the data state that shows or hides the item. The product rule (Z5 D323, SN header): a page or button a person cannot finish is hidden, not shown disabled; the engine also refuses the call. Exceptions that show disabled controls are noted ("disabled when").
Every dialog marked "confirm" is a `ConfirmDialog`/`Modal` with a cancel button; "immediate" means the click acts with no confirmation.

## 0. Where things are (the Settings area)

The Settings area is `SA`, inside `app/SettingsShell.tsx` (left rail, header "Settings", group headings in `h2.nav-label`; on narrow screens the rail folds into a toggle "Settings: <page>"). The rail is built from `SN` by `navigationFor(held)`: a page is listed only to a person holding one of its `requires` action groups somewhere; a group with no page left is not shown. A direct address to a page the person may not open is refused by the engine.

| Group (rail heading) | Page label | page key | requires (any of) | Component |
| --- | --- | --- | --- | --- |
| General | About | about | everyone | ST/AboutPage.tsx |
| General | Appearance | appearance | everyone | ST/AppearancePage.tsx |
| General | Account | account | everyone | ST/AccountPage.tsx |
| General | Notification email | notifications | everyone | ST/NotificationsPage.tsx |
| Administration | Workspaces | workspaces | everyone (buttons gated inside) | WS/WorkspaceAdmin.tsx |
| Administration | Model | model | model-authoring, model-release | model-admin (see MODEL-EDITOR-INVENTORY.md) |
| Administration | Deployment | deployment | operations | ST/DeploymentPage.tsx |
| Administration | Operations | operations | operations | ST/OperationsPage.tsx |
| Administration | AI | ai | operations | ST/AiPage.tsx (ai-later) |
| Data operations | Import profiles | import-profiles | bulk | ST/ImportProfilesPage.tsx |
| Data operations | Copy and move | moves | copy-move | moves/ (see MODEL-EDITOR-INVENTORY.md section 0) |
| Data operations | Jobs | jobs | everyone | ST/JobsPage.tsx |
| Security | People / Groups / Roles / Clients | people, groups, roles, clients | security-admin | SE/PeoplePage.tsx, GroupsPage.tsx, RolesPage.tsx, ClientsPage.tsx |
| Security | Agent access | agent-access | security-admin | ST/AgentAccessPage.tsx (ai-later) |
| Security | Sign-in | sign-in | security-admin | SE/SignInPage.tsx |
| Security | Signing keys | signing-keys | security-admin | SE/SigningKeysPage.tsx |
| Integration | Consumer APIs | consumer-apis | browse | ST/ConsumerApisPage.tsx |
| Integration | Webhooks | webhooks | integration-admin | ST/WebhooksPage.tsx |
| Integration | Mail | mail | security-admin | ST/MailPage.tsx |
| Integration | API reference | api-reference | everyone | ST/ApiReferencePage.tsx |

Not in the rail but routed by SA: `ai-tasks` (the page "Load a workbook", rail keeps Jobs current; ai-later; `features/ai-tasks/AiTaskPage.tsx`, journey bar `AiTaskJourneyBar`), a draft's model editor (`route.page === "model"` with `draftId` and `editor`), and the move editor (`moves` with `move`). Those belong to the model/data inventories.

Other entry points to this area (outside the rail):
| # | Entry | Where | File:line |
| --- | --- | --- | --- |
| 0.1 | Account popover (avatar button, label "Account"): signed-in card (name, e-mail, role line), links "Account", "Notifications" (people only, with unread count), "All settings"; fieldset "Theme" System/Light/Dark ("System follows your device. The choice is saved in this browser."); button "Sign out"; footer "Source code" · licence link | top bar | SM:46-140 |
| 0.2 | Workspace picker in the top bar: "Workspace" combo box, per-workspace badge "Other release" / "Other model" / "Retired · read only", action "Manage workspaces", menu "Workspace actions" | top bar | WS/WorkspaceSelector.tsx:17-18, 94, 133-153 |
| 0.3 | Capability status panel "Capability groups" (Model administration, Workspace administration: on/off and the setting that switches it) | used on the model page | features/administration/CapabilityStatus.tsx:16-36 |

## 1. General

### 1.1 About (ST/AboutPage.tsx)
| # | Action (UI words) | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 1.1.1 | Read the product text "Reference data that stays in step." with three points ("Shape it to your domain.", "Connect, don't copy.", "One API for everything."); link "API reference" opens `/docs/api` | About › refiroo | AboutPage.tsx:30-55 | everyone; skeleton "Loading what this deployment runs" |
| 1.1.2 | Read "Engine": Engine version, Management API, Schema languages, Licence, Source code (link, new tab) | About › Engine | :61-77 | everyone |
| 1.1.3 | "Open release" (goes to the active release page in Settings › Model) | About › Active model release | :79-84 | shown with Name, Key, Version, Schema language, Activated; the Model page itself needs model-authoring or model-release |

### 1.2 Appearance (ST/AppearancePage.tsx) — all choices apply at once and are stored in this browser; no Save button
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 1.2.1 | "Theme": System / Light / Dark ("System follows your device's light or dark setting.") | Appearance › Display | AppearancePage.tsx:43; ThemeChoice in SM:140+ | immediate |
| 1.2.2 | "Table density": Comfortable / Compact | Display | :16-18, 48 | immediate |
| 1.2.3 | "Type colours": "B: magenta and olive" / "A: plum and gold" | Display | :21-23, 70 | immediate (palette A/B per memory note: not yet visibly different) |
| 1.2.4 | "Edit pencil": "On hover and focus" / "Always, faintly" | Display | :26-28, 92 | immediate |

### 1.3 Account (ST/AccountPage.tsx; panels by sign-in kind, AccountPage.tsx:42-60)
Page header eyebrow "General", title "Account". Error: inline error with retry; skeleton "Loading your account".
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 1.3.1 | Read who you are: initials, name, @username, e-mail, pill "Signed in with your password" / "Signed in with a passkey" / "Signed in with <provider>", pill "Since <time>" | Account › You | AccountPage.tsx:63-87 | everyone |
| 1.3.2 | "Sign out" (this browser) | Account › You | :84 | immediate |
| 1.3.3 | "Change password" opens inline form: "Current password", "New password" (reveal buttons "Show/Hide current/new password password"; minimum 15 characters, engine's refusal is the rule), submit, "Cancel"-like close; error as notice; "Changing it signs you out of your other browsers." | Account › Password | :169-232 | only when signed in with a password (`signedInWith === "password"`, :46) |
| 1.3.4 | "Add a passkey" (browser passkey prompt; toast on success) | Account › Passkeys › header | ST/PasskeysPanel.tsx:35 | signed in with a password or a passkey; skeleton "Loading your passkeys" |
| 1.3.5 | Passkey row: pencil "Rename <name>" opens dialog "Rename <name>" (field "Name": "So you can tell your passkeys apart."; "Save", toast "Saved."); button "Remove <name>" opens dialog "Remove <name>?" asking "Your password, or a code from your authenticator app", button "Remove passkey", toast "The passkey <name> was removed." | Account › Passkeys | PasskeysPanel.tsx:51-110, 113-225 | row text "Added <time> · last used <ago>" or "not used yet"; Save disabled until the name changed |
| 1.3.6 | "Set up an authenticator app" (starts: QR code "QR code for the authenticator app", "Cannot scan? Type this key:" with Copy, field "Code from the app", "Confirm", "Cancel") then shows recovery codes with "Copy" , "Download as text", "I have kept them" (toasts "The recovery codes were copied." / "Could not copy them. Select them and copy by hand.") | Account › Authenticator app | ST/SecondFactorPanel.tsx:114-121, 159-280 | password or passkey sign-in; state "Not set up" |
| 1.3.7 | With the factor on ("On · authenticator app"): "New recovery codes…" (dialog "New recovery codes", "The old recovery codes stop working.", "Make new codes", asks "Code from the app, or a recovery code") and "Remove the second factor" dialog ("Your password alone signs you in again, and your recovery codes stop working.", "Remove it"; toast "Your second factor was removed.") | Account › Authenticator app | SecondFactorPanel.tsx:56-150, 282-343 | the remove button is not shown where the instance requires a second factor with a password; text then says "This instance requires a second factor with a password, so a security administrator removes it, or you add a passkey first." (:95) |
| 1.3.8 | "Where you're signed in": per session "Sign out" (aria "Sign out <browser>[, this browser]"); pill "This browser"; assistant sessions are named "<application> (assistant)" (ai-later content); count "N browser(s)" | Account › sessions | AccountPage.tsx:272-320 | Active now / Last active <ago> · signed in <time>; signing out the current one ends this session |
| 1.3.9 | "Sign out everywhere" (confirm "Sign out everywhere?" – "Every browser where you are signed in, this one included, is signed out at its next request.") | Account › sessions footer | :327-345 | confirm |
| 1.3.10 | "What you can do": per workspace card with Your roles, Read, Propose changes, Change live, Publish, Approve; a count opens a per-application panel ("What you may propose in" / "What you may change live in": Application, Record types, "All record types"); workspace and application links open them; "Across the instance" lists instance-wide roles ("Manage people, groups, roles and clients", "Write and release models", "Manage workspaces", "Run and watch the service", "Manage clients' integrations and webhooks"); sources shown "through the group A" | Account › What you can do | AccountPage.tsx:392-410; ST/AccountPermissions.tsx:103-108, 318-330, 393-445, 569-630 | empty: "You have no roles yet. Ask a security administrator to give you one."; otherwise "Reading is never limited. A count opens what each of your roles covers in that workspace. A security administrator gives and removes roles."; becomes a `<dl>` on a phone |

### 1.4 Notification email (ST/NotificationsPage.tsx, NoticeMailPanel.tsx, FollowedWorkspaces.tsx)
Header eyebrow "General", title "Notification email", description "Choose which notices reach you by email, and which workspaces you follow. Your inbox keeps all notices."
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 1.4.1 | Switch "Email me when something arrives in my inbox" (text: sent to <address>; mail never names a record or change set) | Notification email › Email | NoticeMailPanel.tsx:84-102 | shown when mail is set up (`available`) or the switch is already on; immediate save, error as notice |
| 1.4.2 | Radio choice per kind of notice under "How each kind reaches me" (options from `DELIVERIES`, including Digest) | same › fieldset | :105-120 | disabled while the switch is off ("These choices apply only while the switch above is on.") |
| 1.4.3 | "The digest": radio "How often the digest comes" (frequencies), shows time zone and "Next digest: …"; choosing Digest for the first kind starts a daily digest in the browser's time zone; "No mail when there is nothing new; a notice you read before then is left out." | same › fieldset | :123-148 | disabled while the switch is off; empty text "Choose Digest for a kind to start one." |
| 1.4.4 | "Workspaces I follow": list with "Stop following" per workspace (aria "Stop following <label>"); "You do not follow a workspace." (follow from a workspace elsewhere) | Notification email › Workspaces I follow | FollowedWorkspaces.tsx:50-89 | immediate; shown also where mail is not set up, except for a non-person |
| 1.4.5 | Messages replacing the panel: "Your account has no email address, so there is nothing to choose here." / "Only people receive email, so there is nothing to choose here." / "There is nothing to choose here." | page | NotificationsPage.tsx:20-22, 62-72 | mail off and switch off |

### 1.5 The inbox page (`features/inbox/NotificationsPage.tsx`, bell button `InboxButton.tsx`, panel `InboxPanel.tsx`) — reached from the account popover "Notifications"
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 1.5.1 | Bell panel: "Unread" heading with count; "Mark all read"-style ghost button; list; "And N more unread."; "You are all caught up." | top bar bell | InboxPanel.tsx:87-107 | people only (a client has no inbox) |
| 1.5.2 | Page "Notifications": search "Search" (placeholder "Change set, comment, person, job"), selects "All kinds", "All workspaces", "Unread", "Newest first"/"Oldest first" | Notifications | inbox/NotificationsPage.tsx:204-246 | empty: "No notification matches." / "No notifications in the last 90 days." |
| 1.5.3 | Select with checkboxes ("Select every loaded notification"; Shift selects a range, Cmd or Ctrl adds one), then "Mark read", "Mark unread", "Delete" | selection bar | :259-296 | Delete is immediate for ticked items |
| 1.5.4 | "Delete all read notifications?" ("Delete read notifications"); "Notices are kept for 90 days."; link "Notification email settings" | page footer / header | :201, 324-345 | confirm; unread stay |

## 2. Workspaces (Settings › Workspaces; WS/WorkspaceAdmin.tsx)
Header eyebrow "Administration", title "Workspaces"; a pill "Default · <label>". The list is the catalogue on the left, the detail on the right.
`canManage` (:187) = workspace administration on (`WORKSPACE_ADMIN_MUTATIONS_ENABLED`, default true) and the person holds workspace-admin. Tabs (:514-559): Overview always; Access needs security-admin; Approval needs workspace-admin; Activity needs browse.
| # | Action (UI words) | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 2.1 | "New workspace" dialog (eyebrow "Workspace catalogue"): Name, Key ("Lowercase letters and digits, separated by single hyphens. The key is permanent and appears in links and API…"), fieldset "Model": "The default workspace's model" or "Another installed release" with "Installed release"; "The new workspace starts empty on this release…"; "Create workspace" | header button | WorkspaceAdmin.tsx:223, 1041-1125; WS/NewWorkspaceFields.tsx:48-167 | canManage; error notice "The workspace was not created" |
| 2.2 | Pick a workspace; loading "Loading workspace catalogue…", "Loading workspace…"; trail "Workspaces › <label>"; pills "Default", Status "Active" / "Retired · read only"; Model, Created, Last changed | catalogue / Overview | :238, 484-500, 567-572, 720-790 | everyone who may open Settings › Workspaces |
| 2.3 | "Open workspace" (to its start page) | Overview header | :578-582 | needs browse |
| 2.4 | "Edit model" (opens the model editor on the draft of the model the workspace runs) | Overview header | :583-587; WS/useEditModel.ts | needs model-authoring and model-release and browse there; hidden when model administration is off or the workspace is retired |
| 2.5 | "Copy or move data…" (opens Copy and move) | Overview header | :588-592 | needs copy-move capability, active workspace |
| 2.6 | "Rename…" dialog "Rename workspace" (label field, "Save name"; "Not saved" on a version conflict) | Overview header | :594-598, 1127-1210 | canManage; Save disabled until the name differs |
| 2.7 | "Set as default" (immediate) | Overview header | :599-603 | canManage, active, not already the default |
| 2.8 | "Retire…" (confirm "Retire <label>?", "Retire workspace": "The workspace becomes read only. Its live data, change sets, publications and history stay available…"), "Reactivate" (immediate, toast "Workspace reactivated.") | Overview header | :604-627, 680-697 | canManage; Retire disabled on the default (hint "The default workspace cannot be retired or deleted. Make another workspace the default first.") |
| 2.9 | "Delete…" (confirm "Delete <label>?", "Delete workspace") | Overview header | :629-634, 698-715 | canManage and the workspace is deletable; hints say it must be empty, with no publications and no webhook subscriptions ("Only an empty workspace can be deleted. Delete its objects and discard its change sets first, or retire it."; "This workspace has webhook subscriptions, so it cannot be deleted…") |
| 2.10 | "Applications · N" list of the workspace's applications (links open them) | Overview | :796-860 | browse; error with retry |
| 2.11 | "Its webhooks:" list linking to Settings › Webhooks | Overview | :1006-1040 | listed when it has subscriptions |
| 2.12 | Access tab (title "Access", "Who can do what in this workspace: granted here, or for the whole instance; directly or through a group."): the grants table, see 3.5 | Workspace › Access | :542-550 | security-admin |
| 2.13 | Approval tab ("Approval policy"): checkbox "Changes need approval before they are published"; checkbox "The person who submitted a change set cannot approve it" (disabled until the first is on); button "Save approval policy" (becomes "Reload the policy" after a conflict); text "People holding Approve publications decide. Without this, people who may publish still do so directly."; approver count line; warnings "Nobody can approve, so every request will wait until someone is given the Data owner role." / "Only one person can approve, so their own change sets will wait until someone else is given the Data owner role." / "Nobody can approve yet. Give someone the Data owner role (Approve publications) for this workspace."; status "Approval policy saved." | Workspace › Approval | :872-1003 | workspace-admin; the disabled second checkbox is a disabled-with-dependency control |
| 2.14 | Activity tab: filter buttons Everything / Records / Relationships / Change sets / Publications (no Model), days list, change-set groups with expand toggle, tiles and pills "Change set" / "Published" / "Withdrawn", "Show all activity" (clears a narrowing from a link), "Load more", empty "No activity yet." | Workspace › Activity | WS/WorkspaceActivity.tsx:27-286; changes/changeText.ts:133-140 | browse |
| 2.15 | Unavailable workspace page: pill "Cannot be opened"; card "Bring it up to date" with "Raise … to schema N" dialog (Schema language from → to, Consumer APIs rewritten, Workspaces that return, "Records, change sets, publications: unchanged", "This edits the stored release in place (before 1.0 only).", "Raise and reopen"); card "Or continue elsewhere" | opening a workspace whose release is invalid | WS/UnavailableWorkspace.tsx:32-360 | the repair button needs model install rights, else "Ask someone with the Model administrator role to bring this workspace up to date."; after repair "<label> is back." |
| 2.16 | Not-found pages: "Workspace <key> cannot be opened", "No workspace <key>", "<name> is not in this workspace's model" with "Workspaces whose model has <name>" list and buttons to open; "No other workspace's model has it."; buttons (start, back) | wrong address | WS/NotInModel.tsx:51-201 | any |

### 2.A Change sets, review, publications (workspace pages inside an application, not in the Settings rail)
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 2.A.1 | List "Change sets" ("Coordinate changes in an optional change set. Ordinary maintenance remains available in Live."), "Open" per change set, "Load more", empty "No change sets. Keep editing Live, or start a change set…" | application › Change sets | WS/ChangeSets.tsx:38-115 | needs change-sets capability |
| 2.A.2 | Dialog "Start from current live data" (name, "Model version" picker, create) | same | ChangeSets.tsx:118-221 | |
| 2.A.3 | Change set bar: "Review changes" / "Review and decide", "Validate", "Submit for publication" dialog, "Publish change set", "Withdraw" the request, menu "More change set actions": "Change model version", "Discard change set" (confirm "Discard this change set?"); pills "Waiting for approval", "Change set validation passed"; confirm "Publish this change set?" | change set page | ChangeSets.tsx:590-870 | publish needs publish; waiting requests show "Withdraw the request to edit it."; refused notices "Change set needs corrections" |
| 2.A.4 | Review page "Review changes": filter by "Kind of change" Added/Changed/Removed, "Record type"/"Relationship type", "Show parent links"; tabs Records / Relationships; field diff Before/After | change set review | WS/ChangeSetReview.tsx:49-214, 500-520 | |
| 2.A.5 | Decision card: textarea comment ("Required to send back"), "Send back" and "Approve" buttons; "Decisions" history (Approved / Sent back); "A second person must decide this request." | review | ChangeSetReview.tsx:272-390 | approve capability; when approval policy blocks the same person |
| 2.A.6 | Publications list: "Open", menu "More actions": "Start a change set from this publication", "Withdraw publication" (confirm); pill "Current"; "Load older publications"; empty "No publications yet." | application › Publications | WS/Publications.tsx:21-269 | withdraw needs the publish capability |

## 3. Security (all pages need security-admin; SN)
Common pattern: a catalogue (left) with a "Search …" field, a detail (right); conflicts show a "Not saved" warning ("… changed while the page was open. … choose again."); failures show "The action could not be completed".

### 3.1 People (SE/PeoplePage.tsx)
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 3.1.1 | "Search people" (placeholder "Name, username or e-mail"); filter buttons "Active" / "Deactivated" with counts | People catalogue | PeoplePage.tsx:126-143 | empty "Loading people…" |
| 3.1.2 | "New person" dialog (eyebrow Security): "Username" (no spaces, cannot change), "Name", "E-mail (optional)", "Create and make a password link"; field errors e.g. "A username has no spaces and at most 150 characters…" | People header | :175-178, 313-430 | button shown only while local sign-in is on |
| 3.1.3 | "Pass on the password link" dialog: shows the one-time link with Copy, "Mail it to <address>" (only if mail is set up and the person has an address), "I have copied it"; "…is not shown again" | after create / reset | :54-300 | mail failing or not set up: the link is shown to pass on |
| 3.1.4 | "Edit…" dialog "Edit <name>": Name, E-mail (optional), Save | person detail | :551, 939-1042 | |
| 3.1.5 | "See changes" (that person's changes) | person detail | :552-556 | only if the viewer may read changes |
| 3.1.6 | "Link to an existing person…" (dialog "Link this sign-in to an existing person", picker "Person", button "Link to <name>") | person detail | :560-562, 816-875 | active person with a provider identity and no password |
| 3.1.7 | "Reset password" / "Make a password link" (immediate; shows 3.1.3) | person detail | :564-571 | active, local sign-in on or the person keeps local sign-in |
| 3.1.8 | "Sign out everywhere" (confirm "Sign <name> out everywhere?") | person detail | :574, 793 | active person |
| 3.1.9 | "Deactivate" (confirm "Deactivate <name>?" – history keeps their name, restorable) / "Restore" (immediate, toast "<name> was restored and can sign in again.") | person detail | :579-598, 768-790 | |
| 3.1.10 | Section "Sign-in": rows per provider with "Unlink" (confirm "Unlink <provider>?"), "Password: Set / Not set yet", "Second factor: authenticator app" with "Remove second factor…" (confirm), passkeys with "Remove the passkey <name>" (confirm "Remove <name>'s passkey <p>?"), switch "Keeps local sign-in" | person detail | :605-650, 695-760, 877-937 | the switch asks confirm "<name> keeps local sign-in?" / "stops keeping local sign-in?" |
| 3.1.11 | Grants section "Grant", see 3.5; section "Recent activity" with filters "Signing in", "Roles and groups" (SE/RecentActivity.tsx:26-104); section "Groups": "Add to a group" (dialog "Add <name> to a group", "Add to the group"), chip remove "Remove from <group>" (immediate), "Not in any group." | person detail | :654-661, 1045-1110 | |

### 3.2 Groups (SE/GroupsPage.tsx)
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 3.2.1 | "Search groups" (placeholder "Group name"); list shows source and "N seen"/members; empty "No groups yet." / "No group matches “<q>”." | catalogue | GroupsPage.tsx:69-90 | |
| 3.2.2 | "New group" dialog: Name, Description, fieldset "Members": "Added here" / "From a sign-in provider" (then provider and claim value: "The value the provider's groups claim holds for this group (Entra ID sends the group's object ID). Made ahead, its roles are ready before anyone in it signs in."), "Create group" | header | :99, 544-622 | provider option needs a sign-in provider |
| 3.2.3 | "Rename…" (dialog "Rename <name>", Save); "Delete group" (confirm "Delete <name>?", "Delete group") | group detail | :229-232, 253 | |
| 3.2.4 | Members: "Add members" (picker dialog `AddMembersDialog`), checkbox select ("Select every member shown"), selection bar "N members selected" with "Remove N from the group", "Clear", per-row "Remove <name> from <group>" | group detail | :328-440; SE/AddMembersDialog.tsx | for a provider group the section is "Members seen" (columns Person, Username, Status, Last seen in this group), read only, notice "Members come from the sign-in provider" |
| 3.2.5 | Group "Grants" section | group detail | :245 | see 3.5 |

### 3.3 Roles (SE/RolesPage.tsx)
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 3.3.1 | Read the matrix "Roles by action group" (rows: action groups; columns: roles; "Custom" tag on your own roles) | Roles | RolesPage.tsx:139-215 | skeleton "Loading roles"; predefined roles cannot change |
| 3.3.2 | "New role" dialog: Name, Description, "Start from" (Nothing / copy of a role), "Create role" | header | :128, 341-375 | |
| 3.3.3 | Edit a custom role (pencil "Edit <name>"): name, description (max 2000), tick action groups per cell, "Save role"; hint "<role> is held by …; a change applies on their next request" | matrix | :163, 187, 220-270 | |
| 3.3.4 | "Delete role" (confirm "Delete <name>?", "The role is removed. Nobody holds it, so no one loses access.") | role editor | :253-301 | disabled while granted, title "A role still granted cannot be deleted" |

### 3.4 Clients (SE/ClientsPage.tsx)
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 3.4.1 | "Search clients"; filters "Active"/"Deactivated" | catalogue | ClientsPage.tsx:88-135 | |
| 3.4.2 | "New client" (name; "Create and show its secret") then "Copy the client's secret" dialog with Client ID and the secret shown once, "I have copied it" | header | :142, 190-296 | |
| 3.4.3 | "Rename…" (dialog; "The client ID does not change…"); "Rotate secret…" (dialog "Rotate the secret of <name>": overlap hours, "Make a new secret", "stop now" option for leaks); "Deactivate" (confirm) / "Restore" (immediate) | client detail | :422-455, 501-535, 641-690 | rotate and deactivate only while active |
| 3.4.4 | Section "Secrets" (Secret, Created, Valid until, Last used) with "End the secret ending … now" per secret; empty "No valid secret: rotate to make one." | client detail | :560-600 | immediate |
| 3.4.5 | Section "Access" ("Roles let it use the management API; a consumer API grant lets it read that API in one workspace."): grants, see 3.5 | client detail | :470 | |
| 3.4.6 | Section "Webhooks it created" (Webhook, Workspace, Consumer API, State) | client detail | :691-720 | "It created no webhook you administer." |

### 3.5 Grants (shared: SE/GrantsSection.tsx, GrantDialog.tsx, AccessList.tsx, PrincipalPicker.tsx, ConsumerApiGrid.tsx)
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 3.5.1 | "Grant" opens dialog "Grant access": "Who" (person, group or client found by name; only a client can get a consumer API), choice "Roles" / "Consumer APIs", fieldset "Roles" (roles held for the whole instance only are grey: choose “The whole instance”), "Where": "Workspaces" (add workspace, "No workspace chosen yet") or "The whole instance" ("Every workspace, now and later."), "Narrow what they may change": all or "Only these applications and record types" (only one role in one workspace; "Reading is never narrowed…"); buttons "Grant"/"Try again"; failure notice "N could not be granted" | people, group, client and workspace pages | GrantsSection.tsx:118-130; GrantDialog.tsx:292-548 | table columns Where, Role, "Narrowed to (writes)", Through; empty "No access yet. Grant a role or a consumer API." / "No one has a role in this workspace yet."; remove per row (aria "Remove <role> <place>") is immediate with error "The grant was not removed" |
| 3.5.2 | Access list with search "Search people, groups, clients", type filter People/Groups/Clients, legend of role colours (Contributor, Data owner, Administration, Consumer API), per-chip remove (confirm "Remove <role> from <name>?") and "Add a role for <name>" | access list component | AccessList.tsx:32-224 | "No one matches." |

### 3.6 Sign-in (SE/SignInPage.tsx)
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 3.6.1 | Catalogue entries "Local accounts" and "Providers" (names; "No provider yet: people sign in with a password.") | Sign-in | SignInPage.tsx:59-105 | |
| 3.6.2 | "Turn off…" local sign-in (confirm "Turn local sign-in off?", "Turn off") / "Turn on" (immediate, toast "People sign in with a password again.") | Local accounts | :745-775, 819 | can be turned off only once a provider is enabled and has signed someone in ("Local sign-in can be turned off once …, so nobody is locked out."); Turn off shown only if working providers exist |
| 3.6.3 | Switch "Require a second factor with a password" (confirm "Require a second factor?", "Require it") | Local accounts › Second factor | :775-815 | people signing in with a provider are not asked |
| 3.6.4 | "New sign-in provider" dialog: "Name on the sign-in button", "Key", "Issuer", "Client ID", "Client secret", "Groups claim", checkbox "Offer it on the sign-in page now", "Save provider" ("Checking and saving…") | header | :115, 222-340 | enabled providers are checked when saved; error "The provider was not saved" |
| 3.6.5 | Provider: "Enable"/"Disable" (immediate), "Delete" (confirm "Delete <name>?", "Delete provider") | provider detail | :433-453, 487 | Delete shown only when no person signed in with it |
| 3.6.6 | "Address to register with the provider" (Redirect address, Copy); "Signing out" section (switch to sign out of the provider too, with sign-out address; notice "Only this browser"); "Settings" form (fields as above; "Saved · type a new one to replace it") with "Cancel" and "Save" | provider detail | :458-690 | |

### 3.7 Signing keys (SE/SigningKeysPage.tsx)
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 3.7.1 | Table Key ID, State, Created, Replaced, Retired; "No key yet: one is made with the first token." | Signing keys | SigningKeysPage.tsx:77-96 | |
| 3.7.2 | "Start a new key" (immediate; the 30-day rotation also runs on its own) | header | :58 | error "No new key was started" |
| 3.7.3 | "Retire the current key now" (confirm "Retire the current key now?", "Retire it now": every token it signed is refused from the next request) | header | :61, 102-114 | |

### 3.8 Agent access (ST/AgentAccessPage.tsx) — ai-later; needs `MCP_ENABLED=true`
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 3.8.1 | Notice "Agent access is off" with the setting `MCP_ENABLED=true` to set on the server and restart | page | AgentAccessPage.tsx:73-75 | when off, nothing else shows (no disabled controls) |
| 3.8.2 | "How to connect": Address (Copy), "A person's assistant", "A system's assistant" (agent client asks for `scope=agent`), command for Claude Code | page | :89-115 | on |
| 3.8.3 | "Agent clients": "New client" dialog "New agent client" (`NewClientDialog` kind agent; secret dialog); table Name, Access, Last used, Calls 30 days; "Load more agent clients"; row opens the client page | page | :118-195 | empty "No agent client yet…" |
| 3.8.4 | "Assistants people sign in with": "Register an assistant" dialog (Name "What people see on the sign-in page.", "Return addresses" one per line, exact HTTPS or loopback; "Register"); table Assistant, Returns to, Signed in now, Last used; "Block <name>" (confirm "Block <name>?") / "Restore <name>" (immediate) | page | :196-345, 346-431 | empty "No assistant has signed anyone in yet…"; blocking ends sessions on their next call |
| 3.8.5 | "Calls" table When, Who, Through, Tool, Arguments, Outcome (Answered / Refused / Limit reached / Failed); "Argument names are kept, never their values."; "Load more" | page | :433-470 | empty "No call has been made yet." |

## 4. Administration (operations)

### 4.1 Deployment (ST/DeploymentPage.tsx) — read only; operations
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 4.1.1 | Read the API address note and "Capability groups" (Model administration, Workspace administration, Integration jobs, Webhook subscriptions) each "On"/"Off" with its switching setting and limits | Deployment | DeploymentPage.tsx:56-90, 140-180 | description "…they cannot be edited here." |
| 4.1.2 | Read "Database › Migration revision" | Deployment | :91-95 | |
| 4.1.3 | Read settings tables (Setting, Value, Default, Source, What it controls) for Runtime, Capability settings, Batch and job limits, Webhook subscriptions, AI proposals; secrets show "Set"/"Not set" | Deployment | :20-34, 97-135 | warning "Cursors do not survive a restart" when `RDM_CURSOR_SIGNING_KEY` is unset |

### 4.2 Operations (ST/OperationsPage.tsx) — read only; operations
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 4.2.1 | "Refresh" (and automatic refresh every few seconds; "As of <time> · refreshed every N seconds") | header | OperationsPage.tsx:126-134 | warning "Could not refresh" keeps old data |
| 4.2.2 | Summary figures; "Workspaces" table (Workspace, Release, Schema, State Served/Unavailable, Not served by); "Engine processes" (Live/Silent, Ready/Not ready, Background threads Running/Failing/Off, Database connections, Requests since start, Releases it cannot serve) | page | :158-316 | |
| 4.2.3 | "Last backup rehearsal": Passed/Failed, restored copy figures per workspace (Records, Relationships, Open change sets, Publications, Live now), failure title per code; "Show earlier rehearsals (N)" / "Hide earlier rehearsals", "Load more rehearsals"; details "How to rehearse a restore" | page | :318-500 | empty warning "No backup has been rehearsed"; nothing here restores data |
| 4.2.4 | "For monitoring": Liveness, Readiness, Metrics addresses with Copy | page | :514-550 | |

### 4.3 AI (ST/AiPage.tsx) — ai-later; operations
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 4.3.1 | Info notice "Neither the assistant nor an AI provider is set up" (`AI_AGENT_COMMAND`, `AI_PROVIDER` in server environment) | AI | AiPage.tsx:55-57 | |
| 4.3.2 | Read "What is switched on" (Assistant, Provider), "Settings" (Model, Endpoint, Key Set/Not set, What may be sent, Confidence floor, Content kept, Timeout), "What the AI provider is asked" (feature pills Available/Unavailable) | AI | :73-160 | settings are not edited here |
| 4.3.3 | "Send a test request" (sends none of your data; notices "The AI provider answered" / "The test request failed") | AI › Test request | :164-208 | provider configured; label "Sending…" |
| 4.3.4 | "Calls" table (When, What for, Asked by, Model, Outcome, Tokens in / out, Cost, Duration); "Show what was sent and answered"; "Load more" | AI | :210-278 | empty "No call has been made yet…" |

## 5. Data operations in Settings (listed for completeness; also see MODEL-EDITOR-INVENTORY.md for Copy and move)

### 5.1 Jobs (ST/JobsPage.tsx; detail `features/jobs/JobPage.tsx`)
| # | Action | Where | File:line | Precondition / states |
| --- | --- | --- | --- | --- |
| 5.1.1 | "New import" (ImportDialog) | Jobs header | JobsPage.tsx:114 | needs bulk somewhere; only where job creation is on (`INTEGRATION_JOBS_ENABLED`) |
| 5.1.2 | "New export" (ExportDialog) | Jobs header | :118 | job creation on |
| 5.1.3 | Table Job, Workspace, State, Items, Requested by, Created, Finished, Actions; "Refresh"; "Load more"; "Cancel" per running job (confirm "Cancel this job?", "Cancel job"/"Keep the job": applied items stay, atomic job rolled back) | Jobs | :125-230, 272-278 | empty "No jobs yet. A job is created by an import or an export, or when a batch is submitted to POST /api/v1/batches." |
| 5.1.4 | Section "Limits" (deployment settings) | Jobs | :175-200 | |
| 5.1.5 | Job page "Job": State, "Why it failed"/"What stopped it", "This import", "The file", exports table Type/Count, cancel | job | JobPage.tsx:153-330 | |

### 5.2 Import profiles (ST/ImportProfilesPage.tsx) — needs bulk
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 5.2.1 | Catalogue of profiles with pills "Valid"/"Needs a fix", "Not loaded yet" | Import profiles | ImportProfilesPage.tsx:63-100 | empty "No import profiles yet. A profile is saved when a model draft holding a workbook is installed…" |
| 5.2.2 | "Upload the next version…" (dialog "Upload the next version"; check shown before anything is written; notices "The file could not be read", "The check failed") | profile detail | :329, 445-470 | |
| 5.2.3 | "Load into a change set…" (dialog "Load <file> into a change set": Open a change set, Load the rows; "Load"; "Open the change set review") | profile detail | :332-338; ST/ProfileLoadDialog.tsx | disabled until the check allows it |
| 5.2.4 | "Last load": "Open the change set review", "Open the load's job" | profile detail | :342-383 | |

## 6. Integration

### 6.1 Consumer APIs (ST/ConsumerApisPage.tsx) — needs browse
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 6.1.1 | Read per API "<name> · v<contract>": Base URL (Copy), OpenAPI document (Copy, link), route table (Route, What it does); routes link into the API reference | Consumer APIs | ConsumerApisPage.tsx:101-125 | |
| 6.1.2 | "Open the release" link; "Open model" button | Consumer APIs | :60-72 | empty "The active release declares no consumer API." |
| 6.1.3 | "Change feed" section (retention note) | Consumer APIs | :83-95 | |

### 6.2 API reference (ST/ApiReferencePage.tsx)
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 6.2.1 | Table Source, Version, OpenAPI document: link "Management API" (interactive reference), per consumer API link and "openapi.json" download (`DownloadLink`), management "openapi.json" | API reference | ApiReferencePage.tsx:39-70 | skeleton "Loading the API reference's sources" |

### 6.3 Mail (ST/MailPage.tsx) — needs security-admin
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 6.3.1 | Info "Mail is not set up" (nothing is sent; links are shown once to pass on) | Mail | MailPage.tsx:57-59 | |
| 6.3.2 | "Mail server" form: "Server" (SMTP host), "Port", "Connection" (STARTTLS usually 587 / TLS usually 465 / None: not encrypted), "User name" (empty: no login), "Password" (kept sealed), "From address", "Application address"; buttons "Remove settings…" (confirm "Remove the mail settings?", "Remove them"), "Cancel", "Save"; toast "Mail settings saved. Send a test message to try them." | Mail | :172-335 | Save disabled until the form is complete and changed; "A login is not sent over an unencrypted connection. Choose STARTTLS or TLS."; error "The settings were not saved" |
| 6.3.3 | "Test message": "Send to", "Send test message"; notices "Sent" / error title | Mail | :337-394 | disabled until mail is configured |
| 6.3.4 | "Messages": filter "State" (All / Waiting / Sent / Failed with counts), "Refresh", table To, Message, State, Tries, Last problem, Queued, Actions; "Stop sending" (confirm "Stop sending this message?", "Stop sending"/"Keep trying") on waiting messages; "Load more" | Mail | :396-520 | empty "No messages yet. A new person's link and a password reset appear here when they are sent."; texts never shown |

### 6.4 Webhooks (ST/WebhooksPage.tsx, WebhookDialog.tsx, WebhookDeliveries.tsx) — needs integration-admin and `CONSUMER_SUBSCRIPTIONS_ENABLED` ("webhooks")
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 6.4.1 | When off: empty state "Webhooks are off in this deployment. The operator turns them on with <setting>=true, which also needs CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY, and restarts the engine." with button "Open Deployment" | Webhooks | WebhooksPage.tsx:99-112 | no "New webhook" button then |
| 6.4.2 | "New webhook" (disabled when no consumer API declares events: "The active model release declares no consumer API with events… Events are declared in the model, on a consumer API.") | header | :88-93, 78, 195-210 | |
| 6.4.3 | Dialog "New webhook" / "Edit webhook": Webhook (Name, URL: "HTTPS on any host; plain HTTP only to localhost."), Source (Consumer API, Workspace; fixed after creation), Events ("Chosen events"/all, "Choose events"), Filters ("Add filter"), Delivery (Requests "One event per request"/"Batched", "Up to (events)", Content, Format), "Create webhook"/"Save changes" | Webhooks | WebhookDialog.tsx:243-533 | notices "Not saved", "The webhook was not created/saved" |
| 6.4.4 | Key dialog "Keep the signing key" ("I have stored the key"); not shown again | after create / rotate | WebhooksPage.tsx:296-333 | |
| 6.4.5 | Detail tabs Configuration / Deliveries; buttons "Edit…", "Suspend" (immediate, toast), "Resume…" (dialog "Resume this webhook?" with "Continue from": first event not acknowledged / reset after feed head; "Resume" / "Reset and resume"), "Rotate key…" (dialog "Rotate the signing key of <name>", "Make a new key"), "Delete…" (confirm "Delete this webhook?", "Delete webhook"/"Keep the webhook") | Webhooks › a webhook | :546-600, 625-760, 838-925 | status pill Active / Retrying / Suspended; suspension notice per reason (contract version changed, delivery failed, filter matches nothing, events expired, workspace retired) |
| 6.4.6 | Deliveries: filter "Status" (Queued, Sending, Retrying, Succeeded, Failed, Dropped), "Refresh", table Event ID, Event, Object ID, Status, Attempts, Response, Sent; open a delivery (dialog with Attempts, Request body, Response body, "Resend" confirm "Resend a delivered event?", "Resend event"/"Don't resend") | Webhooks › Deliveries | WebhookDeliveries.tsx:42-48, 150-210, 239-467 | empty "Nothing delivered yet…" / "No delivery has this status."; Resend note "Never sent, so there is nothing to resend yet." |

## 7. Sign-in screens (before the application; no account yet) — SI
| # | Action | Where | File:line | States |
| --- | --- | --- | --- | --- |
| 7.1 | Frame: product mark, text "Reference data that stays in step." | all screens | SI/SignInFrame.tsx:26-34 | |
| 7.2 | "Sign in with a passkey" (button) | Sign-in screen | SI/SignInScreen.tsx:199-209 | only when passkeys are offered by the instance; followed by "or with a password" |
| 7.3 | Form: "Username", "Password", "Sign in" ("Signing in…") | Sign-in screen | :214-245 | local sign-in on; otherwise "Sign in with a local administrator account" link (:267) and "Only administrators made on the server sign in with a password here." |
| 7.4 | "Continue with <provider>" buttons (go to the provider) | Sign-in screen | :251-265 | one per enabled provider |
| 7.5 | Link "Forgotten your password?" (to `/reset-password`) or text "Forgotten your password? Ask a security administrator for a reset link." | Sign-in screen | :275-277 | link only when mail is set up |
| 7.6 | Notices: "Your session ended. Sign in again to return to where you were.", "Signing in is not possible right now" with "Try again", CORS message "The engine does not accept sign-ins from this address. Ask an administrator to add it to CORS_ORIGINS.", slow-down warning after repeated failures | Sign-in screen | :42, 175-195 | |
| 7.7 | Second step (titles "Enter your code", "Confirm it is you", "Use a recovery code", "Set up a second factor", "Keep your recovery codes"): "Use a passkey", field "Code from the app" / "Code" / "Recovery code", "Sign in with the code" / "Sign in" / "Confirm and continue", "Use a recovery code instead" / "Use the app's code", start-again link; first-time setup shows QR and key; recovery codes screen with continue button; text "Lost the codes too? A security administrator can remove your second factor." | Sign-in screen | :155-163, 300-442 | setup shown when the instance requires a second factor with a password |
| 7.8 | Reset page `/reset-password` (no token): "Forgotten your password?" – field "Username or e-mail address", "Mail me a link" ("Sending…"); notice about spam folder | ResetPasswordScreen | SI/ResetPasswordScreen.tsx:45, 76-135 | if mail is off: "A new password cannot be asked for by e-mail here. Ask a security administrator for a reset link." with "Back to sign in" |
| 7.9 | Reset page with a link token: "Choose a new password": "New password", "Type it again", "Set password"; success "Your password is set. You were signed out everywhere." with "Sign in" | ResetPasswordScreen | :138-216 | dead link: "This link no longer works" / "This link has been used, replaced by a newer one, or has expired." with "Ask for a new link" |

## 8. Not in the UI (nothing in `frontend/src` offers it; verified by absence in the pages above)
- Editing any deployment setting, secret or capability switch (Deployment is read only; changed by environment and restart): `MODEL_ADMIN_MUTATIONS_ENABLED`, `WORKSPACE_ADMIN_MUTATIONS_ENABLED`, `INTEGRATION_JOBS_ENABLED`, `CONSUMER_SUBSCRIPTIONS_ENABLED`, `MCP_ENABLED`, `AI_*`, `CORS_ORIGINS`, the cursor signing key.
- Restoring a backup, running a rehearsal, or any engine process control (Operations is read only).
- Deleting a person or a client (only deactivate and restore), deleting a signing key, deleting a mail message (only "Stop sending").
- Editing or deleting a predefined role; editing a provider-sourced group's members; changing a person's username after creation.
- Editing a webhook's consumer API or workspace after creation; retrieving a signing key or client secret after it was shown once; reading a mail message's text.
- Setting a person's password directly (only a one-time link, mailed or copied).
- Choosing a provider-specific scope, mapping provider claims other than the groups claim, or testing a provider login from its page.
- Per-user locale/time-zone, language, or notification settings other than e-mail.
- Audit log as such: the "Changes" page (`features/changes/ChangesPage.tsx`: eyebrow "Changes"; filters Workspace / What / Period; "Load more"; empty "You have not changed anything in the workspaces you can read yet.") and a person's "Recent activity" are the only histories; no export or settings-level audit page, and no administrator view of other people's inboxes.
- Consent screen for an assistant signing in (MCP) is not React; `grep` of `frontend/src` finds none (probably a server page: not checked in `backend/`).
- Creating applications or changing a workspace's model outside the model editor (workspace page only offers "Edit model").
- Bulk import of people or groups; invitation by e-mail other than the password link.
- Running AI actions from Settings: AI and Agent access pages only show state and a test request; AI proposals are used in Jobs/"Load a workbook" (ai-later).

## 9. What could not be established
- Exact line numbers for some dialog bodies were read from grep output rather than every line; treat line numbers as entry points (+/- a few lines).
- `DELIVERIES`/`FREQUENCIES` option labels (NoticeMail) and the full list of notice kinds were not read (`ST/mailText.ts`, `inbox/inboxText.ts`).
- Action-group display names in the Roles matrix come from the server (`security.actionGroups()`); the keys seen in code are browse, change-sets, edit-live, publish, approve, copy-move, bulk, workspace-admin, integration-admin, operations, security-admin, model-authoring, model-release.
- Whether passkeys are offered on the sign-in screen depends on server data (`options.passkey`); the setting was not traced.
- Whether the sign-in consent for assistants is backend-rendered.
- Behaviour on a running instance (no server was started).
