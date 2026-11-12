# UX1-GUIDE completion report

Written 2026-11-12T04:44:12+01:00.

73 existing pages updated; 182 allowed pages unchanged. No new page, sidebar entry, screenshot file or screenshot reference was added or renamed. The pre-existing content was saved before editing; the per-page report below compares that snapshot with the delivered text.

## Added sections

- `use/appearance-and-devices.md`: theme frame arrangements and reduced-motion behavior.
- `use/home.md`: Find a record, plus the revised placement of waiting work.
- `use/workspaces.md`: The workspace’s page, including shelf, search, application lists and activity.
- `use/records.md`: beside-list opening, in-place controls, switches, Undo and form disclosures.
- `model/the-model-editor.md`: short-operation popovers and side sheets.
- `administer/mail.md`: E-mail template, with Write and preview the layout and Add a logo and send a test.
- The existing mail setup guide and operator runbook link to that section. A separate template page would need `guide/sidebar/administer.mjs`, outside the allowed files. The wave’s explicit fallback to the nearest existing page was used.

## Checks

- `GUIDE_OUT=_build/UX1-GUIDE npm run build` in `guide/`: passed, 257 built pages.
- `GUIDE_OUT=_build/UX1-GUIDE npm run check` in `guide/`: passed terms, brand and sidebar checks.
- `GUIDE_OUT=_build/UX1-GUIDE npm run check:links` in `guide/`: passed.
- Screenshot references in all edited pages match their original references, in the original order.
- Application code was read, not changed. No application test suite or live browser task was run. Screenshot pixels and e-mail rendering in a real mail client were not verified. No server or background service was started.

## Steering applied

- Read the 04:37 steering before subsequent units. Re-read `ObjectDeleteDialog.tsx` immediately before revising each deletion page: the delivered guide describes one read of the impact and one confirmation, including failed reads and a changed impact.
- Home’s Waiting for your approval and Your change sets are described above workspace cards.
- File dropping is mentioned on pages that already describe the shared file chooser.
- The list-header pin is described on the list page and linked to the workspace shelf.

## Code and changelog differences

- `frontend/src/features/objects/ObjectFormDialog.tsx` still submits a whole-record edit with **Save changes**. It was retained in `guide/use/correct-a-record.md`, despite the general Save wording in the wave/changelog. The title is the record’s name.
- `frontend/src/features/workspaces/WorkspacePage.tsx` renders **Find a record** above the shelf, rather than beneath it as the UX1 changelog says. The guide does not prescribe the changelog’s order. Shelf counts come from live counts of the source record type, including when the tile is a matrix or another view; they are not filtered-view or cell counts.
- `frontend/src/features/security/PeoplePage.tsx` asks when switching Keeps local sign-in off, even if local sign-in is currently enabled. It saves immediately when switching it on. The guide follows that behavior rather than limiting the confirmation to a case where a password route is removed.
- `frontend/src/features/workspaces/Publications.tsx` still uses **Change set name** and **Create change set** for starting from a publication. Those labels were retained on the publication page; the live-data form instead uses Name and Start change set.
- `frontend/src/features/objects/RelationMatrixCellDialog.tsx` still offers **Create ‹type›** to enter creation, then submits with **Add ‹type›**. Only the obsolete form-submission instruction was corrected.
- Model operations keep **Apply** for short multi-selection popovers, including a new field group and navigation-group entry selection. They are not uniformly Save or Add; `surfaceOf` and `submitLabel` in `frontend/src/features/model-editor/operations.ts` determine the label.

## Uncertainties and things that looked wrong

- `guide/model/add-a-relation-matrix.md` already described a dedicated Add a relation matrix entry. The inspected model-editor operation catalogue exposes addition through **Add a view…**, selecting the matrix kind; The dedicated entry was absent from the inspected catalogue. The guide now names Add a view and the exact relation-matrix kind, as well as the corrected submission labels.
- Name/attribute Undo handlers in `InlineAttributeEditor.tsx` and the Yes/No handler in `EditableField.tsx` swallow a failed Undo request. A concurrent change can therefore prevent Undo without a failure notice. Documentation does not promise that Undo can overwrite a newer save.
- Template changes are not written to the security audit, as the MT1 changelog also records. The Mail section says this. Real mail-client rendering remains unverified.
- The pages were checked against local code. No claim of live application or release acceptance is made.

## Screenshots showing affected, older controls

The following existing files need recapture or review against the changed controls and layout. Their references and files were left untouched. This list is based on the documented captures and changed execution paths, not a pixel inspection. Other screenshots may also show an older frame.

| Existing filenames | What the replacement must show |
| --- | --- |
| `use-appearance-themes.png` | Five themes with Current selected; Light or dark as a separate choice. |
| `use-home.png`, `home.png`, `use-home-continue.png`, `appr-home-waiting.png` | Home search, waiting approvals and own change sets above workspace cards. |
| `stop-details.png`, `stop-relationships.png`, `stop-edit-field.png`, `save-conflict.png`, `relationships-stop.png` | Current record layout and in-place editor, Yes/No switch, small-panel menu, save or refusal state. |
| `new-record-required-connections.png`, `stop-edit-record.png`, `stop-add-translation.png`, `matrix-missing-name-add.png` | Side sheet, correct title/action, supplied parent with Change, required-first fields and More fields. |
| `relationship-picker-mode.png`, `relationship-picker-operator.png` | Related-type lookup label, relationship wording, Add/Set/Change controls in a sheet. |
| `relationship-delete-confirm.png` | The old confirmation no longer exists: capture the remaining records and the removal notice with Undo instead. Keep the existing filename when refreshing it. |
| `record-delete-impact.png` | One confirmation after the impact read, dependant names/counts and Delete N records. No initial delete followed by Confirm deletion. |
| `mapping-grid-map-dialog.png` | Save, Cancel and Remove mapping inside the form, with the current source and chosen target. |
| `change-sets-list.png`, `change-set-open.png`, `change-set-publish-confirm.png` | New change set; Review changes and Publish; Validate now under the menu; the new plain publication summary confirmation. |
| `use-history-changes.png` | A grouped model-draft line, collapsed and expandable, with the step count. |
| `admin-role-new.png`, `admin-client-new.png`, `admin-group-new.png`, `admin-webhook-new.png`, `admin-webhook-workspace-events.png`, `admin-signin-provider-new.png`, `workspaces-new-dialog.png` | New-thing sheet and the corresponding Add button. |
| `admin-agent-new-client.png`, `admin-agent-register.png` | Add agent client, and New assistant with Add assistant. |
| `admin-client-rotate.png`, `admin-client-inactive-rotate.png`, `admin-webhook-rotate.png` | Rotation sheet with Rotate secret or Rotate key and the overlap choices. |
| `admin-grant-dialog.png`, `admin-grant-consumer-api.png`, `admin-grant-narrowed.png` | Add grant or Add N grants, with the intended roles, scope and restrictions. |
| `admin-client.png`, `admin-group-members.png`, `use-workspaces-detail.png`, `use-account.png` | Name/description edited where it stands and the saved change’s Undo notice, rather than Rename forms. |
| `model-hierarchy-dialog.png`, `model-field-dialog.png`, `model-relation-dialog.png`, `model-add-tree-view.png`, `model-add-mapping-grid.png`, `model-add-relationships-table-layout.png`, `model-view-matrix-dialog.png`, `model-add-panel-relationship.png`, `model-consumer-add-dialog.png`, `model-consumer-relationship-field-picker.png`, `model-consumer-add-field.png`, `model-consumer-add-filter.png`, `model-type-split-dialog.png`, `model-attribute-list-type-dialog.png` | Current sheet placement and the operation’s Add/Save action. |
| `model-type-rename-dialog.png`, `model-type-change-key-dialog.png`, `model-type-merge-dialog.png`, `model-layout-sort-dialog.png`, `model-table-columns-related-fields.png`, `model-table-menu-size.png`, `model-panel-columns-where-it-sits.png`, `model-group-add-entries-dialog.png` | Short operation beneath its triggering control; Save or Apply as appropriate. |
| `model-header-breadcrumbs.png`, `model-panel-settings.png` | Save for the longer settings sheet. |
| `use-wb-dialog.png`, `model-draft-new-dialog.png`, `use-assistant-workbook.png` | Current side-sheet file field, including its drop affordance and the original task controls. |

### Additional captures needed

No new image reference was inserted. Capture these states from the reference instance when screenshots are refreshed:

- Workspace page: an empty shelf with Add a list, then a shelf containing a list and another view; tile menu with Move earlier, Move later and Take off your shelf; search, Applications, Needs you and What changed visible.
- Studio and Instrument, light and dark: application navigation, search, lists and the Live/change-set/publication context in their actual locations. Include a phone frame.
- Home: search results from two browseable workspaces, grouped by workspace; current waiting-work order.
- Record inspector: the list still visible and Expand to full page available.
- Record edit: one Yes/No switch and a saved-value Undo notice; separately a removal Undo notice.
- New change set: name-only form and expanded Options.
- Import: chosen file and automatically selected fitting profile, with Options folded and expanded.
- E-mail template: Markdown with the allowed placeholders, uploaded logo, Light paper/Dark paper/Plain text preview choices, Save and Send a test to me. Include an invalid placeholder warning and the saved-template test notice.

## Per-page sentence changes

Each changed passage below quotes the exact old and delivered text. An addition has no old passage; a removal has no new passage. Unchanged pages are explicitly listed afterwards. The guide’s existing screenshot captions were generally retained because they describe the captured state; outdated interfaces are listed above.

### about/accessibility.md

Old:

```markdown
**Settings → Appearance** offers **Normal** and **Website purple** under **Theme**.
The separate **Light or dark** choice offers **System**, **Light** and **Dark**; System follows
the device's light or dark setting. Both colour themes work with either light or dark. **Table density** sets a comfortable or compact default; a table's own display choice can override it. **Type colours** offers two palettes, and **Edit pencil** controls whether edit hints appear on hover and focus or remain faintly visible. Touch screens always show the hints.

Choices take effect immediately without a Save button and are saved in that browser, so another
browser or device keeps its own settings. To reset them, choose **Normal**, **System**,
**Comfortable**, **B: magenta and olive** and **On hover and focus** again. Panel widths can be adjusted where the layout offers a separator. See [Change how refiroo looks](/docs/guide/use/change-how-refiroo-looks/).
```

New:

```markdown
**Settings → Appearance** offers **Current**, **Hearth**, **Studio**, **Instrument** and **Website purple** under **Theme**.
The separate **Light or dark** choice offers **System**, **Light** and **Dark**; System follows
the device's light or dark setting. Every theme works with either light or dark. **Table density** sets a comfortable or compact default; a table's own display choice can override it. **Type colours** offers two palettes, and **Edit pencil** controls whether edit hints appear on hover and focus or remain faintly visible. Touch screens always show the hints.

Choices take effect immediately without a Save button and are saved in that browser, so another
browser or device keeps its own settings. To reset them, choose **Current**, **System**,
**Comfortable**, **B: magenta and olive** and **On hover and focus** again. Panel widths can be adjusted where the layout offers a separator. See [Change how refiroo looks](/docs/guide/use/change-how-refiroo-looks/).
```

### administer/agent-access.md

Old:

```markdown
The operator can allow assistants to register themselves. Self-registration permits return addresses on the same computer or approved HTTPS hosts. Otherwise an administrator must use **Register an assistant**, providing a name and exact return addresses. A registration accepts at most ten return addresses, each at most 2,000 characters, without fragments. The default permits self-registration with no external hosts approved. Self-registered assistants unused for 30 days are removed when they have no open session. Administrator registrations and blocked registrations remain; at most 1,000 unused self-registrations may stand.
```

New:

```markdown
The operator can allow assistants to register themselves. Self-registration permits return addresses on the same computer or approved HTTPS hosts. Otherwise an administrator must choose **New assistant**, then **Add assistant**, providing a name and exact return addresses. A registration accepts at most ten return addresses, each at most 2,000 characters, without fragments. The default permits self-registration with no external hosts approved. Self-registered assistants unused for 30 days are removed when they have no open session. Administrator registrations and blocked registrations remain; at most 1,000 unused self-registrations may stand.
```

### administer/clients.md

Old:

```markdown
A client has a stable **Client ID**, a display name and a secret. **Rename…** changes the name
without changing its ID or requiring the system to be reconfigured. The dialog explains **The client ID does not change, so the system using it needs nothing new.** Choose **Save** to keep the new name. **New client** asks for **Name**. **Create and show its secret** opens **Copy the client's secret**. Store the ID and secret securely before **I have copied it**; the secret is shown once. A new client starts
with no access. Follow [Create a client](/docs/guide/administer/create-a-client/) to create
it, save its one-time secret and grant what it needs.
```

New:

```markdown
A client has a stable **Client ID**, a display name and a secret. Select the name where it stands and choose **Save** to rename it. The save notice offers **Undo**. Its ID stays the same, so the connected system needs no new configuration. **New client** asks for **Name**. **Add client** opens **Copy the client's secret**. Store the ID and secret securely before **I have copied it**; the secret is shown once. A new client starts
with no access. Follow [Create a client](/docs/guide/administer/create-a-client/) to create
it, save its one-time secret and grant what it needs.
```

Old:

```markdown
**Rotate secret…** opens **Rotate the secret of …**. **Make a new secret** makes the replacement with a chosen overlap: **1 hour**, **24 hours**,
**7 days**, or **Stop it now**. During an overlap the system can switch without interruption;
after it, the previous secret no longer works. **End now** in the Secrets table ends a
previous secret's overlap early. Its accessible label, **End the secret ending … now**, identifies the last four characters; it acts immediately. **No valid secret: rotate to make one.** means there is no usable secret left. Use the recorded ending and last-use times to check the handover.
Follow [Rotate a client secret](/docs/guide/administer/rotate-a-client-secret/).
```

New:

```markdown
**Rotate secret…** opens **Rotate the secret of …**. **Rotate secret** makes the replacement with a chosen overlap: **1 hour**, **24 hours**,
**7 days**, or **Stop it now**. During an overlap the system can switch without interruption;
after it, the previous secret no longer works. **End now** in the Secrets table ends a
previous secret's overlap early. Its accessible label, **End the secret ending … now**, identifies the last four characters; it acts immediately. **No valid secret: rotate to make one.** means there is no usable secret left. Use the recorded ending and last-use times to check the handover.
Follow [Rotate a client secret](/docs/guide/administer/rotate-a-client-secret/).
```

Old:

```markdown
For a leaked secret, choose **Deactivate** first and confirm. Select the client in
**Deactivated**, choose **Rotate secret…**, then **Stop it now** and **Make a new secret**.
Save the replacement from its one-time dialog and have the integration owner configure it.
Review retained grants before choosing **Restore**. Rotation does not restore a client:
the new secret takes effect when the client is restored.
```

New:

```markdown
For a leaked secret, choose **Deactivate** first and confirm. Select the client in
**Deactivated**, choose **Rotate secret…**, then **Stop it now** and **Rotate secret**.
Save the replacement from its one-time dialog and have the integration owner configure it.
Review retained grants before choosing **Restore**. Rotation does not restore a client:
the new secret takes effect when the client is restored.
```

### administer/mail.md

Old:

```markdown
Every message includes plain text and an HTML version with the refiroo mascot and wordmark embedded in the message, so opening it does not load images from the server. If the model gives the product its own name, that name appears beside the wordmark.
```

New:

```markdown
Every message includes plain text and an HTML version. The default layout embeds the refiroo mascot and wordmark; an operator can replace the layout and logo under **E-mail template**. If the model gives the product its own name, that name appears in the message.
```

Old: none (added passage).

New:

```markdown
## E-mail template

**Settings › This instance › E-mail template** changes the layout around every invitation, password reset, notice, digest and test message. One saved template applies to the whole instance. This page needs the instance-wide **Operations** permission, included in the **Operator** role; Security administration for the Mail page alone does not grant it. Until a template is saved, refiroo uses its own layout.

### Write and preview the layout

1. Open **E-mail template**. In **Markdown**, write the surrounding message. The toolbar offers **Bold**, **Italic**, **Link**, **Heading** and **List**. Use **Insert placeholder…** to insert a value where the caret stands.
2. Keep the message placeholder exactly once. The available placeholders are:

   | Placeholder | What appears in the mail |
   | --- | --- |
   | `{{content}}` | The message's own heading, text and action; required exactly once. |
   | `{{product_name}}` | The product's name. |
   | `{{instance_url}}` | The address of this instance. |
   | `{{recipient_name}}` | The person's name, or “there” when no name is available. |
   | `{{logo}}` | The uploaded logo, or the default mark. |

3. Read **Preview** beside the editor. It updates with sample values after you stop typing. Choose **Light paper**, **Dark paper** and **Plain text** to inspect the alternatives. Preview saves and sends nothing. A refused draft shows **The draft cannot be previewed** and leaves the last good preview visible: correct the error before relying on that preview.
4. Choose **Save**. Unknown placeholders, a missing or repeated message placeholder, or more than 20,000 characters are refused. Raw HTML and Markdown images are not carried into mail. Links may use HTTP, HTTPS or mail addresses; unsafe links are omitted. Use the logo control for your image.

### Add a logo and send a test

1. Under **Logo**, choose **Upload a logo**, or drop the image onto the field. Use PNG, JPEG or SVG without script, up to 512 KB. Uploading saves the logo immediately; **Remove logo** returns to the default mark. The logo is embedded in the mail. Many mail programs do not draw SVG, so use PNG or JPEG when recipients need wider support.
2. Save your Markdown before choosing **Send a test to me**. The test uses the saved template, not unsaved text, and goes to your own account's e-mail address. Mail delivery must be configured and your account must have an address. If **The test could not be sent** appears, read its reason and correct the address or delivery problem before retrying.
3. Check the actual message, including its plain-text version, in the recipient's mail program. The preview is not proof of how every mail program draws the message or that delivery reaches the inbox.
4. To restore the original layout, choose **Reset to default…**, then **Reset to default** in the confirmation. This deletes both the saved Markdown and uploaded logo. Cancel keeps them.

If another operator saves first, your older save is refused. Reload, review their changes and reapply only what is still needed. Template changes are not included in the security audit.
```

### administer/people-and-groups.md

Old:

```markdown
**Rename…** changes a group's name and description. **Delete group** asks for confirmation,
then removes its memberships and grants. It does not delete people or their direct roles.
Follow [Manage a group](/docs/guide/administer/manage-a-group/).
```

New:

```markdown
Select a group's name or description where it stands, then choose **Save**. The save notice offers **Undo**. **Delete group** asks for confirmation,
then removes its memberships and grants. It does not delete people or their direct roles.
Follow [Manage a group](/docs/guide/administer/manage-a-group/).
```

### administer/roles-and-grants.md

Old:

```markdown
Choose **New role**, enter **Name**, and choose **Start from**: **Nothing** for an empty role
or an existing role to copy its action groups. **Create role** returns to the matrix with
the new role available for editing. Tick its action groups, adjust its name or optional
description and choose **Save role**. Creating a copy does not change the source role.
```

New:

```markdown
Choose **New role**, enter **Name**, and choose **Start from**: **Nothing** for an empty role
or an existing role to copy its action groups. **Add role** returns to the matrix with
the new role available for editing. Tick its action groups, adjust its name or optional
description and choose **Save**. Creating a copy does not change the source role.
```

### administer/sign-in.md

Old:

```markdown
1. Choose **New provider**. Enter **Name on the sign-in button**; the button reads
   “Continue with” followed by that name. Enter a **Key**, which cannot change once saved.
2. With your organisation's sign-in administrator, enter **Issuer**, **Client ID** and
   **Client secret** from its application registration. The issuer must match exactly.
   The secret is saved securely and is never shown again. Changing an unused issuer requires the secret again; a secret is not silently carried to a different provider endpoint.
3. Set **Groups claim** only if the provider supplies group memberships. Empty means its
   groups are not used. Ask the sign-in administrator for the correct field name.
4. Leave **Offer it on the sign-in page now** selected to enable it, then choose **Save provider**.
   An enabled provider is checked when saved. If discovery, connection or certificate checks
   fail, read the reason and correct the provider details with the operator.
5. Open the saved provider's page and copy its **Redirect address** under
   **Address to register with the provider**. Have that address registered with the provider.
   Prove a complete sign-in before turning local sign-in off.
```

New:

```markdown
1. Choose **New provider**. Enter **Name on the sign-in button**; the button reads
   “Continue with” followed by that name. Enter a **Key**, which cannot change once saved.
2. With your organisation's sign-in administrator, enter **Issuer**, **Client ID** and
   **Client secret** from its application registration. The issuer must match exactly.
   The secret is saved securely and is never shown again. Changing an unused issuer requires the secret again; a secret is not silently carried to a different provider endpoint.
3. Set **Groups claim** only if the provider supplies group memberships. Empty means its
   groups are not used. Ask the sign-in administrator for the correct field name.
4. Leave **Offer it on the sign-in page now** selected to enable it, then choose **Add provider**.
   An enabled provider is checked when saved. If discovery, connection or certificate checks
   fail, read the reason and correct the provider details with the operator.
5. Open the saved provider's page and copy its **Redirect address** under
   **Address to register with the provider**. Have that address registered with the provider.
   Prove a complete sign-in before turning local sign-in off.
```

### administer/webhooks.md

Old:

```markdown
Use **Edit…** on the selected webhook to change **Name**, **URL**, chosen events, filters
or delivery choices, then **Save changes**. A rename preserves a request being retried.
Other configuration edits clear that saved retry and build the next request from the
first event not acknowledged, using the new configuration. The receiver may already have
seen an earlier attempt, so agree the change with its owner. Editing a suspended webhook
does not resume it; use **Resume…** after correcting its findings.
```

New:

```markdown
Use **Edit…** on the selected webhook to change **Name**, **URL**, chosen events, filters
or delivery choices, then **Save**. A rename preserves a request being retried.
Other configuration edits clear that saved retry and build the next request from the
first event not acknowledged, using the new configuration. The receiver may already have
seen an earlier attempt, so agree the change with its owner. Editing a suspended webhook
does not resume it; use **Resume…** after correcting its findings.
```

### guide/administer/add-a-sign-in-provider.md

Old:

```markdown
1. Open **Settings › People and access › Sign-in** and choose **New provider**. The catalogue keeps **Local accounts** separate from **Providers**.
2. Enter **Name on the sign-in button**. People see **Continue with** followed by that name. Check the suggested **Key**: it forms part of the registered address and cannot change after saving. The names password, passkey and local are reserved; choose a distinct key.
3. Enter **Issuer**, **Client ID** and **Client secret** from the sign-in administrator’s registration. The issuer must match the provider exactly. The saved secret is kept sealed and never shown again.
4. If the provider supplies groups, enter **Groups claim**, using the field name supplied by its administrator. Empty means provider groups are not used. You can [create provider groups and grant their roles](/docs/guide/administer/manage-a-group/#use-a-provider-group) before anyone signs in.
5. Keep **Offer it on the sign-in page now** selected if it should be enabled, then choose **Save provider**. It shows **Checking and saving…** while checking an enabled provider. If **The provider was not saved** appears, correct the stated issuer, connectivity, certificate or registration problem with the sign-in administrator. **Cancel** leaves it uncreated.
```

New:

```markdown
1. Open **Settings › People and access › Sign-in** and choose **New provider**. The catalogue keeps **Local accounts** separate from **Providers**.
2. Enter **Name on the sign-in button**. People see **Continue with** followed by that name. Check the suggested **Key**: it forms part of the registered address and cannot change after saving. The names password, passkey and local are reserved; choose a distinct key.
3. Enter **Issuer**, **Client ID** and **Client secret** from the sign-in administrator’s registration. The issuer must match the provider exactly. The saved secret is kept sealed and never shown again.
4. If the provider supplies groups, enter **Groups claim**, using the field name supplied by its administrator. Empty means provider groups are not used. You can [create provider groups and grant their roles](/docs/guide/administer/manage-a-group/#use-a-provider-group) before anyone signs in.
5. Keep **Offer it on the sign-in page now** selected if it should be enabled, then choose **Add provider**. It shows **Checking and adding…** while checking an enabled provider. If **The provider was not saved** appears, correct the stated issuer, connectivity, certificate or registration problem with the sign-in administrator. **Cancel** leaves it uncreated.
```

### guide/administer/create-a-client.md

Old:

```markdown
1. Open **Settings › Connections › Clients**. Search by **Name** to check whether the system
   already has a client. Check **Deactivated** as well before creating a duplicate.
2. Choose **New client**. Enter **Name**, a name people can recognise in access lists and
   history. Choose **Create and show its secret**. **Cancel** creates nothing.
3. In **Copy the client's secret**, copy **Client secret** and **Client ID** into the
   integration's agreed secure store. The full secret is shown once; after closing, only
   its last four characters identify it. Choose **I have copied it** after saving both.
4. If creation is refused, read the message and correct the problem. If the client exists
   but its one-time secret was lost, rotate its secret instead of creating it again.
```

New:

```markdown
1. Open **Settings › Connections › Clients**. Search by **Name** to check whether the system
   already has a client. Check **Deactivated** as well before creating a duplicate.
2. Choose **New client**. Enter **Name**, a name people can recognise in access lists and
   history. Choose **Add client**. **Cancel** creates nothing.
3. In **Copy the client's secret**, copy **Client secret** and **Client ID** into the
   integration's agreed secure store. The full secret is shown once; after closing, only
   its last four characters identify it. Choose **I have copied it** after saving both.
4. If creation is refused, read the message and correct the problem. If the client exists
   but its one-time secret was lost, rotate its secret instead of creating it again.
```

Old:

```markdown
1. On the new client's page, choose **Grant** in **Access**. A new client has no access.
2. Choose **Roles** under **What** for management operations. Select the least role or roles that cover
   the agreed work and choose where they apply. Narrow writes if appropriate, as described
   in [Grant a role](/docs/guide/administer/grant-a-role/).
3. For reading declared consumer APIs, choose **Consumer APIs** under **What**. Tick the
   grid cell for each API and workspace it needs, then choose **Grant**. Row and column
   headings tick the whole line; a ticked grey cell is already granted. A management role
   does not substitute for these consumer grants.
4. Check **Access** on the client page. Confirm the workspace, grant and any write restriction
   before handing the details to the integration owner.
```

New:

```markdown
1. On the new client's page, choose **Grant** in **Access**. A new client has no access.
2. Choose **Roles** under **What** for management operations. Select the least role or roles that cover
   the agreed work and choose where they apply. Narrow writes if appropriate, as described
   in [Grant a role](/docs/guide/administer/grant-a-role/).
3. For reading declared consumer APIs, choose **Consumer APIs** under **What**. Tick the
   grid cell for each API and workspace it needs, then choose **Add grant**, or **Add N grants** when several are selected. Row and column
   headings tick the whole line; a ticked grey cell is already granted. A management role
   does not substitute for these consumer grants.
4. Check **Access** on the client page. Confirm the workspace, grant and any write restriction
   before handing the details to the integration owner.
```

### guide/administer/create-a-custom-role.md

Old:

```markdown
1. Open **Settings › People and access › Roles**. Read the matrix first: each column is a role and each row is an action group. A predefined role cannot be edited or deleted.
2. Choose **New role**. Enter **Name**, then choose **Start from**. **Nothing** creates an empty role; selecting an existing role copies its action groups. It does not change the source role or keep the two linked.
3. Choose **Create role**. The new role appears in the matrix with its editing controls. If **The role was not created** appears, correct the stated problem. **Cancel** closes without creating it.
4. Tick the action groups it needs. Set the name and optional description, then choose **Save role**. An empty role permits nothing. Administrative groups do not imply Browse; add Browse only if the responsibility needs workspace data.
5. Follow [Grant a role](/docs/guide/administer/grant-a-role/) to give it to a person, group or client in the intended scope. Roles containing only instance responsibilities must be granted for **The whole instance**.
6. Check the recipient’s effective access, including other direct and group grants. Their own **Account › What you can do** shows the result. Changes apply on the next request.
```

New:

```markdown
1. Open **Settings › People and access › Roles**. Read the matrix first: each column is a role and each row is an action group. A predefined role cannot be edited or deleted.
2. Choose **New role**. Enter **Name**, then choose **Start from**. **Nothing** creates an empty role; selecting an existing role copies its action groups. It does not change the source role or keep the two linked.
3. Choose **Add role**. The new role appears in the matrix with its editing controls. If **The role was not created** appears, correct the stated problem. **Cancel** closes without creating it.
4. Tick the action groups it needs. Set the name and optional description, then choose **Save**. An empty role permits nothing. Administrative groups do not imply Browse; add Browse only if the responsibility needs workspace data.
5. Follow [Grant a role](/docs/guide/administer/grant-a-role/) to give it to a person, group or client in the intended scope. Roles containing only instance responsibilities must be granted for **The whole instance**.
6. Check the recipient’s effective access, including other direct and group grants. Their own **Account › What you can do** shows the result. Changes apply on the next request.
```

Old:

```markdown
To change a custom role later, use its edit control in the matrix, change its action groups and choose **Save role**. This changes access for everyone holding that role. Read **The role was not saved** before retrying a failure; reload if the role changed meanwhile.
```

New:

```markdown
To change a custom role later, use its edit control in the matrix, change its action groups and choose **Save**. This changes access for everyone holding that role. Read **The role was not saved** before retrying a failure; reload if the role changed meanwhile.
```

### guide/administer/create-a-webhook.md

Old:

```markdown
1. Under **Delivery › Requests**, keep **One event per request**, or choose **Batched** and set **Up to (events)** within the displayed limit. A batch sends available events without waiting to fill up.
2. For a consumer source, choose **Content**: **With the object** for the current record, or **Notification only** when the receiver reads details itself. Workspace events describe a change-set step instead. For either source, agree **Format** with the receiving system’s owner: **RDM JSON** or **CloudEvents 1.0**.
3. Choose **Create webhook**. A refusal appears beside the relevant field or as **The webhook was not created**. Correct the stated problem and try again. **Cancel** leaves without creating it.
```

New:

```markdown
1. Under **Delivery › Requests**, keep **One event per request**, or choose **Batched** and set **Up to (events)** within the displayed limit. A batch sends available events without waiting to fill up.
2. For a consumer source, choose **Content**: **With the object** for the current record, or **Notification only** when the receiver reads details itself. Workspace events describe a change-set step instead. For either source, agree **Format** with the receiving system’s owner: **RDM JSON** or **CloudEvents 1.0**.
3. Choose **Add webhook**. A refusal appears beside the relevant field or as **The webhook was not created**. Correct the stated problem and try again. **Cancel** leaves without creating it.
```

### guide/administer/find-out-why-a-webhook-paused.md

Old:

```markdown
1. Open **Settings › Connections › Webhooks** and select the intended receiver. **Retrying** means refiroo is still trying a failed request; **Suspended** means sending has stopped.
2. Read **Configuration**, especially the suspension heading, listed findings, last error, attempt count and next attempt. A failed request prevents later changes passing it. After 24 hours of unsuccessful delivery it is suspended.
3. Open **Deliveries**, filter **Status** if needed and choose **Refresh**. Open the affected event. Inspect **Attempts** and the selected attempt’s answer. An unreachable host, TLS failure, timeout, redirect and receiver error need different repairs. Give the relevant reason to the operator or receiver owner; do not share record content unnecessarily.
4. For **Delivery failed**, fix the receiver or use **Edit…** to correct its URL. Changing a failed destination retries at once. For **The model changed** or **A filter matches nothing**, edit the fields identified in the findings and choose **Save changes**. If another person changed the webhook, review the reloaded configuration before saving again.
5. For **The contract version changed**, read **Accepted** and **Served now**. The version the receiver accepted is no longer served. Ask its owner to check the current version before resuming: resume accepts that version. A version retained by the active model keeps delivering in its own shape; simply raising the current version does not suspend it. If events or filters no longer exist, fix the findings under **The model changed** first. For **The workspace was retired**, ask a workspace administrator to reactivate it if delivery should continue. Otherwise delete the subscription after agreeing this with its owner.
```

New:

```markdown
1. Open **Settings › Connections › Webhooks** and select the intended receiver. **Retrying** means refiroo is still trying a failed request; **Suspended** means sending has stopped.
2. Read **Configuration**, especially the suspension heading, listed findings, last error, attempt count and next attempt. A failed request prevents later changes passing it. After 24 hours of unsuccessful delivery it is suspended.
3. Open **Deliveries**, filter **Status** if needed and choose **Refresh**. Open the affected event. Inspect **Attempts** and the selected attempt’s answer. An unreachable host, TLS failure, timeout, redirect and receiver error need different repairs. Give the relevant reason to the operator or receiver owner; do not share record content unnecessarily.
4. For **Delivery failed**, fix the receiver or use **Edit…** to correct its URL. Changing a failed destination retries at once. For **The model changed** or **A filter matches nothing**, edit the fields identified in the findings and choose **Save**. If another person changed the webhook, review the reloaded configuration before saving again.
5. For **The contract version changed**, read **Accepted** and **Served now**. The version the receiver accepted is no longer served. Ask its owner to check the current version before resuming: resume accepts that version. A version retained by the active model keeps delivering in its own shape; simply raising the current version does not suspend it. If events or filters no longer exist, fix the findings under **The model changed** first. For **The workspace was retired**, ask a workspace administrator to reactivate it if delivery should continue. Otherwise delete the subscription after agreeing this with its owner.
```

### guide/administer/grant-a-consumer-api-to-a-client.md

Old:

```markdown
1. Open **Settings › Connections › Clients**, find the intended system with **Search clients** and select it. Check its **Client ID** and active state; do not grant to a similarly named system by guesswork.
2. Under **Access**, choose **Grant**. In **What**, choose **Consumer APIs**. This is normally the initial choice for a client. **Roles** is the separate choice for management access.
3. In the grid, find the API’s row and the workspace’s column. Tick the intersection. Each tick is a separate grant. A row or column heading selects the whole line; Shift extends a range, so review every selected cell before proceeding.
4. A grey tick means already granted. **not in this model** means the workspace’s model does not declare that API. **unavailable** means the choices could not be read; reopen the dialog after resolving that load failure. It is not proof that the API is absent.
5. Read the sentence describing what the client may read and choose **Grant**. If some grants fail, the successful ones remain; the failed choices stay selected with their reasons. Correct those choices and use **Try again**. Closing does not undo grants already made.
6. Check **Access** for **Consumer API:** followed by the API’s name and the intended workspace. Give the integration owner the agreed access and point them to [The API reference and Consumer APIs pages](/docs/administer/api-reference-and-consumer-api-pages/) for connection details.
7. Ask the integration owner to verify a new request with that client. Its available consumer API list includes only granted APIs. A grant for another workspace does not carry over, and consumer grants cannot be narrowed to selected record types.
```

New:

```markdown
1. Open **Settings › Connections › Clients**, find the intended system with **Search clients** and select it. Check its **Client ID** and active state; do not grant to a similarly named system by guesswork.
2. Under **Access**, choose **Grant**. In **What**, choose **Consumer APIs**. This is normally the initial choice for a client. **Roles** is the separate choice for management access.
3. In the grid, find the API’s row and the workspace’s column. Tick the intersection. Each tick is a separate grant. A row or column heading selects the whole line; Shift extends a range, so review every selected cell before proceeding.
4. A grey tick means already granted. **not in this model** means the workspace’s model does not declare that API. **unavailable** means the choices could not be read; reopen the dialog after resolving that load failure. It is not proof that the API is absent.
5. Read the sentence describing what the client may read and choose **Add grant**, or **Add N grants** for several. If some grants fail, the successful ones remain; the failed choices stay selected with their reasons. Correct those choices and use **Try again**. Closing does not undo grants already made.
6. Check **Access** for **Consumer API:** followed by the API’s name and the intended workspace. Give the integration owner the agreed access and point them to [The API reference and Consumer APIs pages](/docs/administer/api-reference-and-consumer-api-pages/) for connection details.
7. Ask the integration owner to verify a new request with that client. Its available consumer API list includes only granted APIs. A grant for another workspace does not carry over, and consumer grants cannot be narrowed to selected record types.
```

### guide/administer/grant-a-role.md

Old:

```markdown
1. Tick the role or roles. Read **May** beside each role to check its action groups.
   More than one role adds those permissions together.
2. Under **Where**, choose **Workspaces** and use **Add workspace** to select the intended
   workspaces. Remove any initially selected workspace that should not receive this grant.
3. Choose **The whole instance** only for access that should apply to every workspace,
   including future workspaces. Roles greyed out for workspace grants require this reach.
4. If one role is selected in one workspace and narrowing is offered, review
   **Narrow what they may change**. Keep **Everything in …** for all permitted writes there,
   or choose **Only these applications and record types** and add the intended entries.
   This never restricts reading. To narrow several grants, make them one role and workspace at a time.
5. Read the summary in **Grant access** and choose **Grant**. **Cancel** before submitting makes no grants. Closing after some were saved does not undo those grants. If several grants are
   attempted and some fail, the dialog lists the failures and says whether the others were
   made. Successful grants remain. Failed choices stay selected with their reasons; correct them and use **Try again**.
```

New:

```markdown
1. Tick the role or roles. Read **May** beside each role to check its action groups.
   More than one role adds those permissions together.
2. Under **Where**, choose **Workspaces** and use **Add workspace** to select the intended
   workspaces. Remove any initially selected workspace that should not receive this grant.
3. Choose **The whole instance** only for access that should apply to every workspace,
   including future workspaces. Roles greyed out for workspace grants require this reach.
4. If one role is selected in one workspace and narrowing is offered, review
   **Narrow what they may change**. Keep **Everything in …** for all permitted writes there,
   or choose **Only these applications and record types** and add the intended entries.
   This never restricts reading. To narrow several grants, make them one role and workspace at a time.
5. Read the summary in **Grant access** and choose **Add grant**, or **Add N grants** for several. **Cancel** before submitting makes no grants. Closing after some were saved does not undo those grants. If several grants are
   attempted and some fail, the dialog lists the failures and says whether the others were
   made. Successful grants remain. Failed choices stay selected with their reasons; correct them and use **Try again**.
```

### guide/administer/manage-a-group.md

Old:

```markdown
1. Open **Settings › People and access › Groups**. Use **Search groups** (**Group name**) first to see whether the
   intended group already exists. Choose a result to manage it, or **New group** to create one.
2. Enter **Name** and **Description (optional)**. The description can explain who belongs
   and why. If a **Members** choice is offered, choose **Added here** for membership managed in refiroo.
3. Choose **Create group**. The group opens with its roles and members. **Cancel** closes
   without creating it. If saving fails, read **Not saved**, correct the problem and retry.
```

New:

```markdown
1. Open **Settings › People and access › Groups**. Use **Search groups** (**Group name**) first to see whether the
   intended group already exists. Choose a result to manage it, or **New group** to create one.
2. Enter **Name** and **Description (optional)**. The description can explain who belongs
   and why. If a **Members** choice is offered, choose **Added here** for membership managed in refiroo.
3. Choose **Add group**. The group opens with its roles and members. **Cancel** closes
   without creating it. If saving fails, read **Not saved**, correct the problem and retry.
```

Old:

```markdown
1. Find the group by name and select it. Choose **Rename…** to change its name or description,
   then **Save**. This does not change who belongs or the group's grants.
2. To remove a local member, use their row’s **Remove**. For several, tick their rows, or use **Select every member shown**, and
   choose **Remove … from the group**. **Clear** clears the selection without removing anyone. Check the resulting list. Their direct roles and
   roles from other groups remain.
3. To remove the whole group, choose **Delete group** and read the confirmation. Confirm
   **Delete group** only if its memberships and all its grants should be removed.
   The people remain and keep their direct grants.
```

New:

```markdown
1. Find the group by name and select it. Select its name or description where it stands, edit it and choose **Save**. The save notice offers **Undo**. This does not change who belongs or the group's grants.
2. To remove a local member, use their row’s **Remove**. For several, tick their rows, or use **Select every member shown**, and
   choose **Remove … from the group**. **Clear** clears the selection without removing anyone. Check the resulting list. Their direct roles and
   roles from other groups remain.
3. To remove the whole group, choose **Delete group** and read the confirmation. Confirm
   **Delete group** only if its memberships and all its grants should be removed.
   The people remain and keep their direct grants.
```

### guide/administer/manage-agent-access.md

Old:

```markdown
1. On **Agent access**, under **Agent clients**, choose **New agent client**. This is different from **New client** on the ordinary Clients page.
2. Enter **Name**, then choose **Create and show its secret**. The dialog **Copy the client's secret** shows **Client ID** and the secret once. Give these to the responsible integrator through your organisation's secure handover method. Choose **I have copied it** only after keeping what they need; the secret cannot be shown again.
3. Open the new client's name under **Agent clients**. Its normal client detail page opens. In **Access**, use **Grant access** to grant only the required role and workspaces. The **Agent** role gives Browse and Work in change sets; a custom role can provide a smaller set. A consumer API grant alone allows only that API's lookup tool and information about the connection's access.
4. Ask the integrator to configure the system's assistant with this client and the copied connection address. The [integration instructions](/docs/integrate/assistants-and-agents/) explain the connection details.
5. Return to **Agent access**. Check **Access**, **Last used** and **Calls, 30 days** on its row, then inspect **Calls** for the result. A new client has no access until you grant it.
```

New:

```markdown
1. On **Agent access**, under **Agent clients**, choose **New agent client**. This is different from **New client** on the ordinary Clients page.
2. Enter **Name**, then choose **Add agent client**. The dialog **Copy the client's secret** shows **Client ID** and the secret once. Give these to the responsible integrator through your organisation's secure handover method. Choose **I have copied it** only after keeping what they need; the secret cannot be shown again.
3. Open the new client's name under **Agent clients**. Its normal client detail page opens. In **Access**, use **Grant access** to grant only the required role and workspaces. The **Agent** role gives Browse and Work in change sets; a custom role can provide a smaller set. A consumer API grant alone allows only that API's lookup tool and information about the connection's access.
4. Ask the integrator to configure the system's assistant with this client and the copied connection address. The [integration instructions](/docs/integrate/assistants-and-agents/) explain the connection details.
5. Return to **Agent access**. Check **Access**, **Last used** and **Calls, 30 days** on its row, then inspect **Calls** for the result. A new client has no access until you grant it.
```

Old:

```markdown
1. Under **Assistants people sign in with**, choose **Register an assistant**.
2. Enter **Name**, the name people see on the sign-in page. Under **Return addresses**, enter the exact addresses supplied by the assistant's administrator, one per line. They must use HTTPS, or HTTP loopback addresses on the same computer. Enter at most ten addresses, each at most 2,000 characters, without a fragment.
3. Choose **Register**. The assistant appears in the list and people can sign in with it. If **The assistant was not registered** appears, correct the reported problem and try again.
```

New:

```markdown
1. Under **Assistants people sign in with**, choose **New assistant**.
2. Enter **Name**, the name people see on the sign-in page. Under **Return addresses**, enter the exact addresses supplied by the assistant's administrator, one per line. They must use HTTPS, or HTTP loopback addresses on the same computer. Enter at most ten addresses, each at most 2,000 characters, without a fragment.
3. Choose **Add assistant**. The assistant appears in the list and people can sign in with it. If **The assistant was not registered** appears, correct the reported problem and try again.
```

### guide/administer/narrow-a-grant-to-record-types.md

Old:

```markdown
1. Open **Settings › People and access › People** or **Groups**, or **Settings › Connections › Clients** and select the recipient. Inspect their direct and inherited grants first. Grants combine: another unrestricted grant can allow writes outside the restriction you are adding.
2. Choose **Grant**. For a client, choose **Roles**, rather than **Consumer APIs**. Select exactly one role containing a group that can be narrowed: **Edit live**, **Work in change sets**, **Publish**, **Bulk and import**, or **Copy and move**.
3. Under **Where**, choose **Workspaces** and select exactly one workspace with **Add workspace**. The narrowing control appears only for one role in one workspace. Instance grants and consumer API grants cannot be narrowed.
4. Under **Narrow what they may change**, choose **Only these applications and record types**. Select the intended applications and record types from that workspace’s model. Selecting an application permits its records; selecting a record type permits that type. Either match is enough, so choose a type alone when the whole application would be too broad.
5. Read the resulting permission sentence and the warning that reading is never narrowed. Check the selected role, workspace and restrictions, then choose **Grant**.
6. Inspect the resulting **Narrowed to (writes)** entry. Have the recipient check **Account › What you can do** and try the intended task. A relationship can be changed when either endpoint is writable. A batch or import can refuse individual items outside the allowed types; publishing a change set with any unpermitted type is refused as a whole.
```

New:

```markdown
1. Open **Settings › People and access › People** or **Groups**, or **Settings › Connections › Clients** and select the recipient. Inspect their direct and inherited grants first. Grants combine: another unrestricted grant can allow writes outside the restriction you are adding.
2. Choose **Grant**. For a client, choose **Roles**, rather than **Consumer APIs**. Select exactly one role containing a group that can be narrowed: **Edit live**, **Work in change sets**, **Publish**, **Bulk and import**, or **Copy and move**.
3. Under **Where**, choose **Workspaces** and select exactly one workspace with **Add workspace**. The narrowing control appears only for one role in one workspace. Instance grants and consumer API grants cannot be narrowed.
4. Under **Narrow what they may change**, choose **Only these applications and record types**. Select the intended applications and record types from that workspace’s model. Selecting an application permits its records; selecting a record type permits that type. Either match is enough, so choose a type alone when the whole application would be too broad.
5. Read the resulting permission sentence and the warning that reading is never narrowed. Check the selected role, workspace and restrictions, then choose **Add grant**.
6. Inspect the resulting **Narrowed to (writes)** entry. Have the recipient check **Account › What you can do** and try the intended task. A relationship can be changed when either endpoint is writable. A batch or import can refuse individual items outside the allowed types; publishing a change set with any unpermitted type is refused as a whole.
```

### guide/administer/rotate-a-client-secret.md

Old:

```markdown
1. Open **Settings › Connections › Clients** and select the intended client. Check its name
   and **Client ID**. Inspect **Secrets**, including the last four characters, **Valid until**
   and **Last used**, so you can distinguish the current secret from a previous one.
2. Choose **Rotate secret…**. Select how long the current secret should keep working:
   **1 hour**, **24 hours** (the default), or **7 days**. Use enough time for the agreed handover.
3. If the secret may have leaked, choose **Stop it now**. The system is refused when it
   next tries to authenticate with the old secret until it has the replacement.
4. Choose **Make a new secret**. **Cancel** leaves the secrets unchanged. If creation fails,
   read **No new secret was made**, reload the client and check its current secrets before retrying.
```

New:

```markdown
1. Open **Settings › Connections › Clients** and select the intended client. Check its name
   and **Client ID**. Inspect **Secrets**, including the last four characters, **Valid until**
   and **Last used**, so you can distinguish the current secret from a previous one.
2. Choose **Rotate secret…**. Select how long the current secret should keep working:
   **1 hour**, **24 hours** (the default), or **7 days**. Use enough time for the agreed handover.
3. If the secret may have leaked, choose **Stop it now**. The system is refused when it
   next tries to authenticate with the old secret until it has the replacement.
4. Choose **Rotate secret**. **Cancel** leaves the secrets unchanged. If creation fails,
   read **No new secret was made**, reload the client and check its current secrets before retrying.
```

Old:

```markdown
1. Open the client and choose **Deactivate**. Confirm the deactivation. Its requests are
   refused from their next request, including requests using access already issued. Its
   name, ID and grants remain.
2. In **Deactivated**, select the same client and choose **Rotate secret…**. The dialog
   explains that the new secret takes effect when you restore the client. Rotation does
   not restore it.
3. Choose **Stop it now**, then **Make a new secret**. This ends every older still-valid
   secret immediately. Copy the replacement from **New secret for …** and store it before
   choosing **I have copied it**. Have the integration owner configure the replacement.
4. Review the retained grants and the lifetime of access issued before deactivation with
   the integration owner. Restoring the client can allow that earlier access again if it
   has not expired; replacing a secret does not revoke it.
5. When the client is safe to use, choose **Restore**. It takes effect immediately. Have
   the integration owner prove fresh authentication with the new secret and the intended
   operation, then check **Last used**.
```

New:

```markdown
1. Open the client and choose **Deactivate**. Confirm the deactivation. Its requests are
   refused from their next request, including requests using access already issued. Its
   name, ID and grants remain.
2. In **Deactivated**, select the same client and choose **Rotate secret…**. The dialog
   explains that the new secret takes effect when you restore the client. Rotation does
   not restore it.
3. Choose **Stop it now**, then **Rotate secret**. This ends every older still-valid
   secret immediately. Copy the replacement from **New secret for …** and store it before
   choosing **I have copied it**. Have the integration owner configure the replacement.
4. Review the retained grants and the lifetime of access issued before deactivation with
   the integration owner. Restoring the client can allow that earlier access again if it
   has not expired; replacing a secret does not revoke it.
5. When the client is safe to use, choose **Restore**. It takes effect immediately. Have
   the integration owner prove fresh authentication with the new secret and the intended
   operation, then check **Last used**.
```

Old:

```markdown
An overlap starts when **Make a new secret** succeeds, including time spent deactivated.
It does not restart when you choose **Restore**. For example, restoring two hours after a
one-hour overlap leaves only the new secret usable. Restoring within that hour lets an
older secret authenticate until its existing deadline. Use **Stop it now** for a leaked
secret rather than leaving that window open.

```

New:

```markdown
An overlap starts when **Rotate secret** succeeds, including time spent deactivated.
It does not restart when you choose **Restore**. For example, restoring two hours after a
one-hour overlap leaves only the new secret usable. Restoring within that hour lets an
older secret authenticate until its existing deadline. Use **Stop it now** for a leaked
secret rather than leaving that window open.

```

### guide/administer/rotate-a-webhook-key.md

Old:

```markdown
1. Open **Settings › Connections › Webhooks**, select the intended webhook and check its **URL**, consumer API and workspace. Under **Configuration**, note **Signing key created** and any **Previous key signs until** date.
2. Choose **Rotate key…**. In **Rotate the signing key of …**, choose **1 hour**, **24 hours** (the usual choice) or **7 days**. During this overlap each delivery has signatures for the new and old keys, so the receiver can accept either.
3. For a key that leaked, choose **Stop it now**. The old key stops signing immediately. Until the receiver has the replacement, it may refuse delivery and refiroo retries.
4. Choose **Make a new key**. **Cancel** keeps the current key. If **No new key was made** appears, read the reason and reload the webhook to establish its state before another attempt.
5. In **Keep the new signing key**, copy the replacement into the agreed secure store and pass it securely to the receiver’s owner. Check the displayed overlap deadline. Choose **I have stored the key** only after saving it; it cannot be displayed again.
6. Have the receiver owner switch to the new key and verify a fresh delivery. Check **Deliveries**, its attempts and response. A successful delivery during overlap alone does not prove the receiver uses the replacement; ask its owner to confirm which key verified it.
7. Check that delivery continues after the overlap. If it fails, have the receiver owner check its configured key, then follow [Find out why a webhook paused](/docs/guide/administer/find-out-why-a-webhook-paused/).
```

New:

```markdown
1. Open **Settings › Connections › Webhooks**, select the intended webhook and check its **URL**, consumer API and workspace. Under **Configuration**, note **Signing key created** and any **Previous key signs until** date.
2. Choose **Rotate key…**. In **Rotate the signing key of …**, choose **1 hour**, **24 hours** (the usual choice) or **7 days**. During this overlap each delivery has signatures for the new and old keys, so the receiver can accept either.
3. For a key that leaked, choose **Stop it now**. The old key stops signing immediately. Until the receiver has the replacement, it may refuse delivery and refiroo retries.
4. Choose **Rotate key**. **Cancel** keeps the current key. If **No new key was made** appears, read the reason and reload the webhook to establish its state before another attempt.
5. In **Keep the new signing key**, copy the replacement into the agreed secure store and pass it securely to the receiver’s owner. Check the displayed overlap deadline. Choose **I have stored the key** only after saving it; it cannot be displayed again.
6. Have the receiver owner switch to the new key and verify a fresh delivery. Check **Deliveries**, its attempts and response. A successful delivery during overlap alone does not prove the receiver uses the replacement; ask its owner to confirm which key verified it.
7. Check that delivery continues after the overlap. If it fails, have the receiver owner check its configured key, then follow [Find out why a webhook paused](/docs/guide/administer/find-out-why-a-webhook-paused/).
```

### guide/administer/set-up-mail.md

Old: none (added passage).

New:

```markdown
For the layout and logo around every message, an operator uses [E-mail template](/docs/administer/mail/#e-mail-template). Saving mail delivery settings does not change that template.
```

### guide/administer/turn-off-local-sign-in.md

Old:

```markdown
1. Follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/) and prove a complete sign-in through **Continue with …**. Check that the right person and roles are reached.
2. Open **Settings › People and access › People** and select the recovery administrator. Under **Sign-in**, check that their password is set and **Keeps local sign-in** is on. This is separate from their Security administrator role.
3. If needed, turn **Keeps local sign-in** on. Read the named confirmation and choose **Keep local sign-in**. Test the retained account before proceeding. It still needs any required second factor; keep that device or recovery route available.
4. Tell affected people to use the organisation’s provider. Arrange links for existing accounts so they keep their roles and history rather than acquiring duplicate identities.
```

New:

```markdown
1. Follow [Add a sign-in provider](/docs/guide/administer/add-a-sign-in-provider/) and prove a complete sign-in through **Continue with …**. Check that the right person and roles are reached.
2. Open **Settings › People and access › People** and select the recovery administrator. Under **Sign-in**, check that their password is set and **Keeps local sign-in** is on. This is separate from their Security administrator role.
3. If needed, turn **Keeps local sign-in** on. It saves immediately and offers **Undo**; turning it off asks for confirmation. Test the retained account before proceeding. It still needs any required second factor; keep that device or recovery route available.
4. Tell affected people to use the organisation’s provider. Arrange links for existing accounts so they keep their roles and history rather than acquiring duplicate identities.
```

### guide/model/add-a-record-type-and-fields.md

Old:

```markdown
1. Select the application that should list the type. If the draft is empty, use **Application**
   to add one first, enter its name and apply it.
2. In the application's **Object types** section, choose **Object type**. In **Add an object type**,
   enter **Name** and, if needed, **Plural name**. Leaving the plural empty uses the name with an s;
   fill it explicitly when that would read incorrectly.
3. Choose **Stands**: **At the top level** for independent records, or **Under** a type for children.
   For children, choose the **Containment relation**. If creating one, fill both **Relation name
   (from the parent)** and **Reverse name (from the child)**. These describe the same connection
   from each end.
4. Choose **Apply**. The type appears in the model pane and application table. A new type gets
   a generated table view and record page. Check where it stands before adding fields. If Apply
   is unavailable, complete the required names and choices; read any refusal before trying again.
```

New:

```markdown
1. Select the application that should list the type. If the draft is empty, use **Application**
   to add one first, enter its name and choose **Add application**.
2. In the application's **Object types** section, choose **Object type**. In **Add an object type**,
   enter **Name** and, if needed, **Plural name**. Leaving the plural empty uses the name with an s;
   fill it explicitly when that would read incorrectly.
3. Choose **Stands**: **At the top level** for independent records, or **Under** a type for children.
   For children, choose the **Containment relation**. If creating one, fill both **Relation name
   (from the parent)** and **Reverse name (from the child)**. These describe the same connection
   from each end.
4. Choose **Add type**. The type appears in the model pane and application table. A new type gets
   a generated table view and record page. Check where it stands before adding fields. If Add type
   is unavailable, complete the required names and choices; read any refusal before trying again.
```

Old:

```markdown
1. Select the type and open **Attributes**. Review the existing rows before creating another field.
2. Choose **New attribute**. Enter **Name** and select **Value type**: for example **Text**,
   **Long text**, **Whole number**, **Decimal number**, **Yes or no**, **Date**, **Date and time**
   or **JSON** for structured values.
   Choose for the value's meaning, not its appearance in a spreadsheet. A code containing leading
   zeroes may need text, even if every character is a digit.
3. Review **Features**. **Searchable** includes the field in record search. **Filterable** allows
   filtering; the view decides which filter controls it shows. **Unique** prevents another record
   in the workspace from holding that attribute value. It is an attribute-wide rule, including
   other types that share the attribute. **Sortable** is still shown, but ordinary non-structured
   fields sort from list headers regardless of that checkbox.
4. Choose **Required** if records of this type must hold a value. Consider existing records:
   making a field mandatory does not fill it for them. Choose **Apply** and wait for the row.
5. Check its value type, Required and Unique settings. The new row is marked **New**, its type
   may be **Changed**, and the header's draft version advances. Expand **Issues and history**
   to see the saved step. No live record has acquired a value from adding the definition alone.
```

New:

```markdown
1. Select the type and open **Attributes**. Review the existing rows before creating another field.
2. Choose **New attribute**. Enter **Name** and select **Value type**: for example **Text**,
   **Long text**, **Whole number**, **Decimal number**, **Yes or no**, **Date**, **Date and time**
   or **JSON** for structured values.
   Choose for the value's meaning, not its appearance in a spreadsheet. A code containing leading
   zeroes may need text, even if every character is a digit.
3. Review **Features**. **Searchable** includes the field in record search. **Filterable** allows
   filtering; the view decides which filter controls it shows. **Unique** prevents another record
   in the workspace from holding that attribute value. It is an attribute-wide rule, including
   other types that share the attribute. **Sortable** is still shown, but ordinary non-structured
   fields sort from list headers regardless of that checkbox.
4. Choose **Required** if records of this type must hold a value. Consider existing records:
   making a field mandatory does not fill it for them. Choose **Add attribute** and wait for the row.
5. Check its value type, Required and Unique settings. The new row is marked **New**, its type
   may be **Changed**, and the header's draft version advances. Expand **Issues and history**
   to see the saved step. No live record has acquired a value from adding the definition alone.
```

Old:

```markdown
For business validity, attach two **Date** fields, then edit **Effective period**. Select
**Starts on** and **Ends on**, and **Apply**. The fields must differ; the end is exclusive and
must be later than the start when both are filled. Empty dates leave that end open. Adding
the rule does not repair existing dates: review compatibility before activation.
```

New:

```markdown
For business validity, attach two **Date** fields, then edit **Effective period**. Select
**Starts on** and **Ends on**, then **Save**. The fields must differ; the end is exclusive and
must be later than the start when both are filled. Empty dates leave that end open. Adding
the rule does not repair existing dates: review compatibility before activation.
```

### guide/model/add-a-relation-matrix.md

Old:

```markdown
1. Select an application and choose **Add a relation matrix…** from its menu, or **Relation
   matrix** in its panel. The form has a preview beside it.
2. Choose **Rows**, then **Each cell shows**. Read the explanation of the relationship offered.
   If a type is missing, check its allowed relationships and the cell type's parent structure.
3. Choose **Columns**. There is one column per record of a type the cell records sit under.
   Choose **Column heading** to identify those column records clearly.
4. Choose and order **Fields in a cell** and **Row columns**. Use the add, remove and up/down
   controls to inspect the intended order. The first text or number cell field is used for the
   cell display; if none is available, it uses the record name.
5. Set **What people can do in a cell** from the offered **Create**, **Edit**, **Link existing**
   and **Unlink** choices. Availability depends on the declared structure. A checked action
   still needs the person's record or relationship permissions at runtime.
6. Enter **Name**, inspect the preview and choose **Apply**. Review **Issues** before installing.
   A preview is a design aid, not proof that every user has permission to perform its actions.
7. For an existing relation matrix, open its row in **Views** and choose **Change…**. Use
   **Rename…** for its label or **Remove relation matrix** to remove the view. Removing the
   view does not delete the data it displayed. **Undo** can restore the draft step.
```

New:

```markdown
1. Select an application and choose **Add a view…** from its menu. In **Kind of view**, choose **Relation matrix: rows and columns with the related records in the cells**. The form has a preview beside it.
2. Choose **Rows**, then **Each cell shows**. Read the explanation of the relationship offered.
   If a type is missing, check its allowed relationships and the cell type's parent structure.
3. Choose **Columns**. There is one column per record of a type the cell records sit under.
   Choose **Column heading** to identify those column records clearly.
4. Choose and order **Fields in a cell** and **Row columns**. Use the add, remove and up/down
   controls to inspect the intended order. The first text or number cell field is used for the
   cell display; if none is available, it uses the record name.
5. Set **What people can do in a cell** from the offered **Create**, **Edit**, **Link existing**
   and **Unlink** choices. Availability depends on the declared structure. A checked action
   still needs the person's record or relationship permissions at runtime.
6. Enter **Name**, inspect the preview and choose **Add view**. Review **Issues** before installing.
   A preview is a design aid, not proof that every user has permission to perform its actions.
7. For an existing relation matrix, open its row in **Views** and choose **Change…**. Use
   **Rename…** for its label or **Remove relation matrix** to remove the view. Removing the
   view does not delete the data it displayed. **Undo** can restore the draft step.
```

Old:

```markdown
Choose **Apply**, review **Issues**, then install and activate the release through your usual
[model release process](/docs/model/releases/). Check the actions after changing
row types or cell fields: dependent choices can be reset or removed when they no longer fit.
```

New:

```markdown
Choose **Save**, review **Issues**, then install and activate the release through your usual
[model release process](/docs/model/releases/). Check the actions after changing
row types or cell fields: dependent choices can be reset or removed when they no longer fit.
```

### guide/model/add-a-relationship.md

Old:

```markdown
1. Choose **Allow a relation…**. Select **To**, the target record type.
2. Under **Relation type**, reuse an existing meaning where appropriate, or choose **A new relation
   type**. For a new one, enter **Name (from …)** and **Reverse name**. Read them as sentences from
   both ends so people understand the same relationship whichever record they open.
3. Set **Cardinality** using the from and to types shown below. Do not infer it from the plural
   wording of a label.
4. Review **Required**. This is a dependent-ownership rule, not a general request that every source
   record have a target. For the supported required one-to-one or one-to-many connection, the
   target is created with its owner relationship. **Many to one** cannot be required. Leave it
   unticked for an optional association.
5. Choose **Apply**. Check the new row's direction and limits, its **New** mark and the saved
   history step. If refused, correct the named combination or migration problem. **Cancel**
   leaves the draft unchanged.
```

New:

```markdown
1. Choose **Allow a relation…**. Select **To**, the target record type.
2. Under **Relation type**, reuse an existing meaning where appropriate, or choose **A new relation
   type**. For a new one, enter **Name (from …)** and **Reverse name**. Read them as sentences from
   both ends so people understand the same relationship whichever record they open.
3. Set **Cardinality** using the from and to types shown below. Do not infer it from the plural
   wording of a label.
4. Review **Required**. This is a dependent-ownership rule, not a general request that every source
   record have a target. For the supported required one-to-one or one-to-many connection, the
   target is created with its owner relationship. **Many to one** cannot be required. Leave it
   unticked for an optional association.
5. Choose **Add relation**. Check the new row's direction and limits, its **New** mark and the saved
   history step. If refused, correct the named combination or migration problem. **Cancel**
   leaves the draft unchanged.
```

Old:

```markdown
1. On **Relations**, open the **Which records** cell, or the row menu's
   **Which records may be chosen…**. The criteria editor separates the two ends; check which
   type's choices you are changing.
2. Add criteria on the name, a field or a field of an ancestor. Choose the condition and value
   for the intended end. Several criteria are combined with “and”; several **is** choices on
   one field are alternatives.
3. Apply the change and inspect the row's summary. These conditions restrict new choices in
   every record picker, not just one panel. Existing relationships remain if a record later
   stops meeting the condition. Recheck Issues before activation.
```

New:

```markdown
1. On **Relations**, open the **Which records** cell, or the row menu's
   **Which records may be chosen…**. The criteria editor separates the two ends; check which
   type's choices you are changing.
2. Add criteria on the name, a field or a field of an ancestor. Choose the condition and value
   for the intended end. Several criteria are combined with “and”; several **is** choices on
   one field are alternatives.
3. Choose **Save** and inspect the row's summary. These conditions restrict new choices in
   every record picker, not just one panel. Existing relationships remain if a record later
   stops meeting the condition. Recheck Issues before activation.
```

Old:

```markdown
1. On **Relations**, edit the pair’s **Carries** cell or choose **Attributes of the relationship…**
   from its menu. If there are no attribute types, create the shared definitions first.
2. Select the **Attributes** whose values belong to the connection itself, then **Apply**.
   Carries now names them; an empty selection reads **Nothing**. Endpoints’ fields are unchanged.
   Select shared definitions of the right value type: a date stays a date, and a Yes or no value
   becomes a checkbox. Check the from and to types in the dialog title: this choice applies to
   that directed pair, not every pair using the relation type.
3. To revise limits together, choose **Cardinality and required…** and apply the intended
   combination. Released pairs may withhold these structural actions. Use the refusal and
   compatibility check to decide whether a migration is necessary.
4. Select the shared **Relation type** to review both names and its **Settings**. Change
   **Oriented** only after reviewing its effect on record deletion; see
   [relationship settings](/docs/model/types-attributes-relations/#visibility-help-and-relationship-settings).
```

New:

```markdown
1. On **Relations**, edit the pair’s **Carries** cell or choose **Attributes of the relationship…**
   from its menu. If there are no attribute types, create the shared definitions first.
2. Select the **Attributes** whose values belong to the connection itself, then **Apply**.
   Carries now names them; an empty selection reads **Nothing**. Endpoints’ fields are unchanged.
   Select shared definitions of the right value type: a date stays a date, and a Yes or no value
   becomes a checkbox. Check the from and to types in the popover title: this choice applies to
   that directed pair, not every pair using the relation type.
3. To revise limits together, choose **Cardinality and required…** and choose **Save** for the intended
   combination. Released pairs may withhold these structural actions. Use the refusal and
   compatibility check to decide whether a migration is necessary.
4. Select the shared **Relation type** to review both names and its **Settings**. Change
   **Oriented** only after reviewing its effect on record deletion; see
   [relationship settings](/docs/model/types-attributes-relations/#visibility-help-and-relationship-settings).
```

### guide/model/add-a-relationships-table.md

Old:

```markdown
1. Select an application in the draft and choose **Add a view…**.
2. In **Kind of view**, choose **Relationships table: each relationship in a row, with its own attributes**. If it is absent, allow a relationship
   between two types first. Containment is not offered for this view.
3. In **Relationships**, choose the directed pair and relation. Read the arrow: the from end
   supplies grid rows, and the to end supplies column groups. The view reads this one pair,
   even when the relation type also connects other pairs.
4. In **Columns of the from record** and **Columns of the to record**, select and order the
   fields that identify each end. Keep at least one in each. Name and scalar fields are
   offered; fields holding JSON are not endpoint-column choices. The initial choice is Name
   and, where available, a unique scalar field. Changing Relationships resets these choices.
5. Under **Attributes of the relationship**, select the values to show. Only attributes carried
   by this pair are offered. An empty choice is allowed. Change the pair's **Carries** first if
   a needed value is missing. For a grid, choose the attributes people need under each column group.
6. Set **Layout** to **One row per relationship** or **Grid: each record once, a column group per
   related record**. Rows show existing connections. A grid also exposes gaps where people can
   link records. The first selected to-record field labels each grid column group.
7. For rows, **Head the rows by** chooses **Nothing: one list**, **The from record** or **The to
   record**. Group headings include counts. This choice does not group the grid.
8. Enter **Name** and choose **Apply**. Check the saved step, **Views** and **Issues**. The
   application lists either endpoint type if it was not already listed. No data is created.
```

New:

```markdown
1. Select an application in the draft and choose **Add a view…**.
2. In **Kind of view**, choose **Relationships table: each relationship in a row, with its own attributes**. If it is absent, allow a relationship
   between two types first. Containment is not offered for this view.
3. In **Relationships**, choose the directed pair and relation. Read the arrow: the from end
   supplies grid rows, and the to end supplies column groups. The view reads this one pair,
   even when the relation type also connects other pairs.
4. In **Columns of the from record** and **Columns of the to record**, select and order the
   fields that identify each end. Keep at least one in each. Name and scalar fields are
   offered; fields holding JSON are not endpoint-column choices. The initial choice is Name
   and, where available, a unique scalar field. Changing Relationships resets these choices.
5. Under **Attributes of the relationship**, select the values to show. Only attributes carried
   by this pair are offered. An empty choice is allowed. Change the pair's **Carries** first if
   a needed value is missing. For a grid, choose the attributes people need under each column group.
6. Set **Layout** to **One row per relationship** or **Grid: each record once, a column group per
   related record**. Rows show existing connections. A grid also exposes gaps where people can
   link records. The first selected to-record field labels each grid column group.
7. For rows, **Head the rows by** chooses **Nothing: one list**, **The from record** or **The to
   record**. Group headings include counts. This choice does not group the grid.
8. Enter **Name** and choose **Add view**. Check the saved step, **Views** and **Issues**. The
   application lists either endpoint type if it was not already listed. No data is created.
```

Old:

```markdown
1. In **Views**, open the relationships table's menu and choose **Layout…**.
2. Select either layout and **Apply**. This changes the presentation of the same relationship;
   it does not duplicate or remove its connections.
3. Review **Issues**, then [install and activate the release](/docs/guide/model/install-and-activate-a-release/).
   Open the view in a workspace using the release and check its fields and available actions.
```

New:

```markdown
1. In **Views**, open the relationships table's menu and choose **Layout…**.
2. Select either layout in the popover and choose **Save**. This changes the presentation of the same relationship;
   it does not duplicate or remove its connections.
3. Review **Issues**, then [install and activate the release](/docs/guide/model/install-and-activate-a-release/).
   Open the view in a workspace using the release and check its fields and available actions.
```

### guide/model/add-a-view.md

Old:

```markdown
1. Select the application and choose **Add a view…** from its menu.
2. Choose **Kind of view**. Only suitable kinds are offered. A table needs a type; a tree
   needs a listed type that permits records without a parent; a mapping grid needs an optional
   non-containment relationship. Add those definitions first if the kind is missing.
3. Complete the form for that kind below. Enter **Name**, then **Apply**. Check **Views** and
   **Issues**. **Not applied** means the step was refused: read its reason and revise the
   choices. **Cancel** leaves the draft unchanged.
```

New:

```markdown
1. Select the application and choose **Add a view…** from its menu.
2. Choose **Kind of view**. Only suitable kinds are offered. A table needs a type; a tree
   needs a listed type that permits records without a parent; a mapping grid needs an optional
   non-containment relationship. Add those definitions first if the kind is missing.
3. Complete the form for that kind below. Enter **Name**, then **Add view**. Check **Views** and
   **Issues**. **Not applied** means the step was refused: read its reason and revise the
   choices. **Cancel** leaves the draft unchanged.
```

Old:

```markdown
Choose **Table: the records of one type in rows**, select **Type**, and enter **Name**.
The application also lists the type if necessary. Columns, filters and sorting start from
its attributes. After Apply, select the type and open **Preview**, **Edit layout**, **Table**;
choose this view in **View** to [arrange it](/docs/guide/model/choose-table-columns-filters-and-sort/).
```

New:

```markdown
Choose **Table: the records of one type in rows**, select **Type**, and enter **Name**.
The application also lists the type if necessary. Columns, filters and sorting start from
its attributes. After adding it, select the type and open **Preview**, **Edit layout**, **Table**;
choose this view in **View** to [arrange it](/docs/guide/model/choose-table-columns-filters-and-sort/).
```

Old:

```markdown
1. Choose **Tree: records under the records that contain them**.
2. Select **Top of the tree**. These are types that can stand without a parent. The tree
   includes the types beneath them that this application lists. List missing child types in
   the application before adding the tree.
3. Set **Each record reads** to Name or a field shared by every shown type. **Second line**
   adds another shared field; **None** removes it.
4. Set **Records under a record are ordered by**. The form applies that one field to child
   types. It starts with Name. More detailed per-type or descending ordering needs a specialist.
5. For an on/off control, choose a common Yes or no field in **Switch a record on and off with**.
   Choose None for no availability action. A read-only field cannot support this action.
6. Enter the name and Apply. Review Issues. The form sets availability actions only; do not
   expect Create, Rename or Move just from choosing a tree. Ask a specialist to declare those
   separately when needed.
```

New:

```markdown
1. Choose **Tree: records under the records that contain them**.
2. Select **Top of the tree**. These are types that can stand without a parent. The tree
   includes the types beneath them that this application lists. List missing child types in
   the application before adding the tree.
3. Set **Each record reads** to Name or a field shared by every shown type. **Second line**
   adds another shared field; **None** removes it.
4. Set **Records under a record are ordered by**. The form applies that one field to child
   types. It starts with Name. More detailed per-type or descending ordering needs a specialist.
5. For an on/off control, choose a common Yes or no field in **Switch a record on and off with**.
   Choose None for no availability action. A read-only field cannot support this action.
6. Enter the name and choose **Add view**. Review Issues. The form sets availability actions only; do not
   expect Create, Rename or Move just from choosing a tree. Ask a specialist to declare those
   separately when needed.
```

Old:

```markdown
1. Choose **Mapping grid: records of one type matched to records of another**.
2. In **Matches records through**, choose the permitted relationship and its two types.
   Containment and required ownership are not offered.
3. In **Rows are**, choose the first or second type. This decides which end chooses records
   at the other end. Changing the relationship or row end resets the column and search choices
   to Name: select them again afterwards.
4. Choose and order **Columns of a row** and **Columns of the matched record**. Keep at
   least one in each list. Fields holding JSON are not offered. In **Columns of a row**,
   **From the parents** offers the types the row can stand beneath. Add one to show the name
   of each row record's nearest parent of that type, even several levels above it. The type's
   name heads the column. These parent names give context but are not searched when people
   search the grid's rows.
5. Choose **Find a record to match by**. Name and searchable attributes of the matched type
   are offered. This controls candidate searching, not a relationship’s eligibility rules.
6. Enter the name, Apply and check the resulting view and type listings. The new grid starts
   with 20 rows per page. A specialist can change that reading size.
```

New:

```markdown
1. Choose **Mapping grid: records of one type matched to records of another**.
2. In **Matches records through**, choose the permitted relationship and its two types.
   Containment and required ownership are not offered.
3. In **Rows are**, choose the first or second type. This decides which end chooses records
   at the other end. Changing the relationship or row end resets the column and search choices
   to Name: select them again afterwards.
4. Choose and order **Columns of a row** and **Columns of the matched record**. Keep at
   least one in each list. Fields holding JSON are not offered. In **Columns of a row**,
   **From the parents** offers the types the row can stand beneath. Add one to show the name
   of each row record's nearest parent of that type, even several levels above it. The type's
   name heads the column. These parent names give context but are not searched when people
   search the grid's rows.
5. Choose **Find a record to match by**. Name and searchable attributes of the matched type
   are offered. This controls candidate searching, not a relationship’s eligibility rules.
6. Enter the name, choose **Add view** and check the resulting view and type listings. The new grid starts
   with 20 rows per page. A specialist can change that reading size.
```

Old:

```markdown
In **Views**, open a tree or mapping grid’s menu and choose **Change…**. Apply changes and
review the saved step. On a tree, the form rebuilds actions from its availability choice:
review any actions a specialist had previously declared. New trees start with 50 records per
branch page; the change form preserves an existing reading size.
```

New:

```markdown
In **Views**, open a tree or mapping grid’s menu and choose **Change…**. Choose **Save** and
review the saved step. On a tree, the form rebuilds actions from its availability choice:
review any actions a specialist had previously declared. New trees start with 50 records per
branch page; the change form preserves an existing reading size.
```

### guide/model/arrange-applications-and-views.md

Old:

```markdown
1. In the model pane, choose **Add**, **Application…**. Enter **Name** and, if useful,
   **Description**, then apply. In an existing application, select its row instead.
2. Check **Object types** and **Stands** to see what it lists and where records belong. Use
   **Object type** to create a definition, or **List an existing type…** to list a shared type
   here. Check the intended type before applying: listing it does not copy its records.
3. Open a listed type's menu. Use **Stop listing in this application** where offered to remove
   only that listing. For containment or a move between applications, use
   [Split, merge and move types](/docs/guide/model/split-merge-and-move-types/) instead. Released
   listings and placements can be refused when data uses them; read the impact before proceeding.
4. Inspect **Views**, including each view's kind, **Shows** and state. **Rename…** changes a
   view's label. To add or configure a relation matrix, follow
   [Add a relation matrix](/docs/guide/model/add-a-relation-matrix/).
5. Use [Group collections in navigation](/docs/guide/model/group-collections-in-navigation/) for
   sidebar sections, their order and initial folded state. This does not change record parents.
6. Use [Preview a type](/docs/guide/model/preview-a-type/), then
   [Edit a record page](/docs/guide/model/edit-a-record-page/) or
   [Choose table columns, filters and sort](/docs/guide/model/choose-table-columns-filters-and-sort/)
   for screen layout. Use [Add a table, tree or mapping grid](/docs/guide/model/add-a-view/)
   for the other view forms.
7. Check **Issues** and review the saved steps before installing. A **Not applied** notice means
   the attempted step was refused; correct its named problem. **Undo** reverses unwanted saved work.
```

New:

```markdown
1. In the model pane, choose **Add**, **Application…**. Enter **Name** and, if useful,
   **Description**, then choose **Add application**. In an existing application, select its row instead.
2. Check **Object types** and **Stands** to see what it lists and where records belong. Use
   **Object type** to create a definition, or **List an existing type…** to list a shared type
   here. Check the intended type before applying: listing it does not copy its records.
3. Open a listed type's menu. Use **Stop listing in this application** where offered to remove
   only that listing. For containment or a move between applications, use
   [Split, merge and move types](/docs/guide/model/split-merge-and-move-types/) instead. Released
   listings and placements can be refused when data uses them; read the impact before proceeding.
4. Inspect **Views**, including each view's kind, **Shows** and state. **Rename…** changes a
   view's label. To add or configure a relation matrix, follow
   [Add a relation matrix](/docs/guide/model/add-a-relation-matrix/).
5. Use [Group collections in navigation](/docs/guide/model/group-collections-in-navigation/) for
   sidebar sections, their order and initial folded state. This does not change record parents.
6. Use [Preview a type](/docs/guide/model/preview-a-type/), then
   [Edit a record page](/docs/guide/model/edit-a-record-page/) or
   [Choose table columns, filters and sort](/docs/guide/model/choose-table-columns-filters-and-sort/)
   for screen layout. Use [Add a table, tree or mapping grid](/docs/guide/model/add-a-view/)
   for the other view forms.
7. Check **Issues** and review the saved steps before installing. A **Not applied** notice means
   the attempted step was refused; correct its named problem. **Undo** reverses unwanted saved work.
```

### guide/model/choose-table-columns-filters-and-sort.md

Old:

```markdown
1. Choose **Columns…**. The dialog lists **Name**, the type's fields and its relationships,
   including its parent relationship where applicable. Check the columns you want to show.
2. Check a relationship to show the names of related records as a column. To show one of
   their fields, open **Fields of** followed by the relationship's name beneath that choice.
   Opening the list does not select the relationship or its fields.
3. Select a field of the related records. Each checked field becomes a separate column;
   you can keep the relationship's name column as well, or leave it unchecked.
4. To show information from a containing record, look under **Where they sit ·** followed
   by a type's name. Choose its **Name** or one of its fields. These choices include types
   further up the related records' hierarchy. Fields holding JSON are not offered here.
5. Choose **Apply**. Check the resulting column frames. A field column's heading combines
   the relationship name and the field label. Its cells show the related records' values,
   with **—** where a related record has no value. These columns cannot sort.
6. Reorder frames by their grips, or open a column's menu and use **Move left** or
   **Move right**. **Remove column** takes it out of this view without deleting any values.
```

New:

```markdown
1. Choose **Columns…**. The popover lists **Name**, the type's fields and its relationships,
   including its parent relationship where applicable. Check the columns you want to show.
2. Check a relationship to show the names of related records as a column. To show one of
   their fields, open **Fields of** followed by the relationship's name beneath that choice.
   Opening the list does not select the relationship or its fields.
3. Select a field of the related records. Each checked field becomes a separate column;
   you can keep the relationship's name column as well, or leave it unchecked.
4. To show information from a containing record, look under **Where they sit ·** followed
   by a type's name. Choose its **Name** or one of its fields. These choices include types
   further up the related records' hierarchy. Fields holding JSON are not offered here.
5. Choose **Apply**. Check the resulting column frames. A field column's heading combines
   the relationship name and the field label. Its cells show the related records' values,
   with **—** where a related record has no value. These columns cannot sort.
6. Reorder frames by their grips, or open a column's menu and use **Move left** or
   **Move right**. **Remove column** takes it out of this view without deleting any values.
```

Old:

```markdown
1. Choose **Filters…** and select the fields and relationships people may filter by.
   Choose the relationship itself to offer a relationship filter. The dialog does not unfold
   its fields: a related-field column does not provide a filter on that field.
2. Choose **Apply** and check the selection. This defines available filters; it does not
   restrict everyone's table to particular values. In the live table, a relationship filter
   can find records linked to selected records, linked to any record, or with no link.
```

New:

```markdown
1. Choose **Filters…** and select the fields and relationships people may filter by.
   Choose the relationship itself to offer a relationship filter. The popover does not unfold
   its fields: a related-field column does not provide a filter on that field.
2. Choose **Apply** and check the selection. This defines available filters; it does not
   restrict everyone's table to particular values. In the live table, a relationship filter
   can find records linked to selected records, linked to any record, or with no link.
```

Old:

```markdown
1. In the **Table** layout, choose **Inactive records…**, beside **Filters…** and
   **Sort menu and page size…**. The dialog is titled **Inactive records of** followed by
   the view's name.
2. Under **A record is inactive when this is No**, select a Yes/No field of this record type.
   Choose **None** if this table should have no inactive mark or switch. If the field you
   need is missing, check that it belongs to this type and is Yes/No. A field of another
   type, or a field with another kind of value, is refused for this setting.
3. Choose **Apply**. This saves a draft step; it does not change any record's value or make
   a read-only field editable. The field does not need to be selected in **Filters…**.
   If **Not applied** appears, read the reason, correct the choice and apply again. Use
   **Undo** to reverse an unwanted draft step.
4. Review **Issues** before [installing and activating the release](/docs/guide/model/install-and-activate-a-release/).
   In the active table, records with **No** stay in their usual order with a quieter name
   and a grey **Inactive** pill if the field is called Active. For another field name,
   the pill says **Not** followed by that name in lower case. Records with no value have
   no inactive mark.
5. Check **Hide inactive (N)** beside **Filter**. It starts off unless the page address
   already applies its filter. Turn it on and check the added pill, such as **Active: not No**:
   only marked records disappear, and records with no value stay visible. Turn it off or
   remove the pill to restore the results. The number counts **No** values after the list's
   search and other filters, including **0** when none match. Choosing **Yes** in the ordinary
   **＋ Filter** menu instead excludes records with no value; it does not turn this switch on.
```

New:

```markdown
1. In the **Table** layout, choose **Inactive records…**, beside **Filters…** and
   **Sort menu and page size…**. The popover is titled **Inactive records of** followed by
   the view's name.
2. Under **A record is inactive when this is No**, select a Yes/No field of this record type.
   Choose **None** if this table should have no inactive mark or switch. If the field you
   need is missing, check that it belongs to this type and is Yes/No. A field of another
   type, or a field with another kind of value, is refused for this setting.
3. Choose **Save**. This saves a draft step; it does not change any record's value or make
   a read-only field editable. The field does not need to be selected in **Filters…**.
   If **Not applied** appears, read the reason, correct the choice and apply again. Use
   **Undo** to reverse an unwanted draft step.
4. Review **Issues** before [installing and activating the release](/docs/guide/model/install-and-activate-a-release/).
   In the active table, records with **No** stay in their usual order with a quieter name
   and a grey **Inactive** pill if the field is called Active. For another field name,
   the pill says **Not** followed by that name in lower case. Records with no value have
   no inactive mark.
5. Check **Hide inactive (N)** beside **Filter**. It starts off unless the page address
   already applies its filter. Turn it on and check the added pill, such as **Active: not No**:
   only marked records disappear, and records with no value stay visible. Turn it off or
   remove the pill to restore the results. The number counts **No** values after the list's
   search and other filters, including **0** when none match. Choosing **Yes** in the ordinary
   **＋ Filter** menu instead excludes records with no value; it does not turn this switch on.
```

Old:

```markdown
1. Choose **Default sort**, whose control shows the current field and direction arrow.
2. Select **Sorted by** from the view's allowed sort fields. Check **Descending** to reverse
   the order. Related-field columns cannot be chosen as the initial sort.
3. Choose **Apply** and check the arrow on the control.
4. Return to preview and inspect real records, including ones with several related records
   and ones with none. An empty table explains what it will show; it does not mean the view
   is broken. Use **Undo** for an unwanted step and review **Issues** before
   [installing and activating the release](/docs/guide/model/install-and-activate-a-release/).
```

New:

```markdown
1. Choose **Default sort**, whose control shows the current field and direction arrow.
2. Select **Sorted by** from the view's allowed sort fields. Check **Descending** to reverse
   the order. Related-field columns cannot be chosen as the initial sort.
3. Choose **Save** and check the arrow on the control.
4. Return to preview and inspect real records, including ones with several related records
   and ones with none. An empty table explains what it will show; it does not mean the view
   is broken. Use **Undo** for an unwanted step and review **Issues** before
   [installing and activating the release](/docs/guide/model/install-and-activate-a-release/).
```

### guide/model/create-a-model-draft.md

Old:

```markdown
For an existing model document, choose **Import JSON** under **Starting document**. A specialist
model author can paste it in **JSON document** or use **Or choose a JSON file**, then create the
draft. Read validation issues before installing; importing does not activate it. For ordinary
changes, starting from a release and using the model editor keeps the work in named controls.

```

New:

```markdown
For an existing model document, choose **Import JSON** under **Starting document**. A specialist
model author can paste it in **JSON document** or use **Or choose a JSON file** (or drop the file onto that field), then create the
draft. Read validation issues before installing; importing does not activate it. For ordinary
changes, starting from a release and using the model editor keeps the work in named controls.

```

### guide/model/create-a-workspace.md

Old:

```markdown
1. Open **Settings › Workspaces**. Search for the intended dataset before creating another.
   Choose **New workspace**.
2. Enter **Name** and review **Key**. The suggested key follows the name until you edit it.
   Use lowercase letters and digits separated by single hyphens. The key is permanent and
   identifies this workspace in links; renaming later does not change it.
3. Under **Model**, choose **The default workspace’s model** or **Another installed release**.
   For the latter choose **Installed release** and check the model name and version. The
   picker initially shows each model's newest usable release; reveal older versions if needed.
4. Confirm creation. The new workspace starts empty. It copies the selected definitions,
   not the default workspace's records, change sets or publications. Changing the default
   workspace later does not change this workspace's selected release.
5. Check its **Overview**, model and applications. Use **Open workspace** to browse its data.
   Arrange data access separately; workspace creation does not grant every person access.
   To start an empty hierarchy, open its tree view and choose **Add …** for its top-level
   type. Create that record first, then add children beneath it; see
   [Arrange records in a tree](/docs/guide/use/arrange-records-in-a-tree/#add-the-first-top-level-record).
```

New:

```markdown
1. Open **Settings › Workspaces**. Search for the intended dataset before creating another.
   Choose **New workspace**.
2. Enter **Name** and review **Key**. The suggested key follows the name until you edit it.
   Use lowercase letters and digits separated by single hyphens. The key is permanent and
   identifies this workspace in links; renaming later does not change it.
3. Under **Model**, choose **The default workspace’s model** or **Another installed release**.
   For the latter choose **Installed release** and check the model name and version. The
   picker initially shows each model's newest usable release; reveal older versions if needed.
4. Choose **Add workspace**. The new workspace starts empty. It copies the selected definitions,
   not the default workspace's records, change sets or publications. Changing the default
   workspace later does not change this workspace's selected release.
5. Check its **Overview**, model and applications. Use **Open workspace** to browse its data.
   Arrange data access separately; workspace creation does not grant every person access.
   To start an empty hierarchy, open its tree view and choose **Add …** for its top-level
   type. Create that record first, then add children beneath it; see
   [Arrange records in a tree](/docs/guide/use/arrange-records-in-a-tree/#add-the-first-top-level-record).
```

### guide/model/define-a-consumer-api.md

Old:

```markdown
1. Select **Consumer APIs** in the model pane, then the add button's **Consumer API…**.
   Enter **Name**, review **Key** and choose **Types to expose**. A blank key is made from
   the name. Create the API. The initial definition includes identifiers, names, attached
   attributes, Get by ID and a list per type. Inspect these starting choices before sharing
   the contract: exposing a type does not mean every attached field belongs in a public API.
2. On **Types and related**, inspect each type's public name. Use **Expose a type…** to add
   another type. Consumers receive that public name as the object's type. Choose only the
   types they need as business objects; related blocks can carry information from other
   types without exposing those records as business objects in their own right.
3. On **Fields**, open **Parent, path and hierarchy…** if consumers need containment information. The
   parent is the immediate containing record; a path or hierarchy names ancestors from
   the root down, excluding the current record. Review those outputs as part of the contract.
4. Use **Add related…** to include information reached through a relationship. Set
   **Output name**, **Via** and **Fields**. Each related field pairs a public name with a
   value on the related record. Check the relationship's direction and whether it serves
   one record or several: the answer is respectively an object or an array. A missing
   relationship gives null or an empty array, rather than an invented related record. The
   field picker's group **Attributes of the relationship** lists the values stored on the
   relationship itself, when the relation's binding carries any. Give each selected value a
   public output name and check its served type in **Schema**. A connection without that value
   answers null; the same value can differ on two connections to the same related record.
5. To add these values to an existing block, use its **Fields…** and select from **Attributes
   of the relationship**. If the group is empty, review **Via** and the pair's **Carries** in
   [Add a relationship](/docs/guide/model/add-a-relationship/#choose-what-each-relationship-carries).
   Do not add connection values to the main object's Fields: they need the related block's context.
```

New:

```markdown
1. Select **Consumer APIs** in the model pane, then the add button's **Consumer API…**.
   Enter **Name**, review **Key** and choose **Types to expose**. A blank key is made from
   the name. Choose **Add consumer API**. The initial definition includes identifiers, names, attached
   attributes, Get by ID and a list per type. Inspect these starting choices before sharing
   the contract: exposing a type does not mean every attached field belongs in a public API.
2. On **Types and related**, inspect each type's public name. Use **Expose a type…** to add
   another type. Consumers receive that public name as the object's type. Choose only the
   types they need as business objects; related blocks can carry information from other
   types without exposing those records as business objects in their own right.
3. On **Fields**, open **Parent, path and hierarchy…** if consumers need containment information. The
   parent is the immediate containing record; a path or hierarchy names ancestors from
   the root down, excluding the current record. Review those outputs as part of the contract.
4. Use **Add related…** to include information reached through a relationship. Set
   **Output name**, **Via** and **Fields**. Each related field pairs a public name with a
   value on the related record. Check the relationship's direction and whether it serves
   one record or several: the answer is respectively an object or an array. A missing
   relationship gives null or an empty array, rather than an invented related record. The
   field picker's group **Attributes of the relationship** lists the values stored on the
   relationship itself, when the relation's binding carries any. Give each selected value a
   public output name and check its served type in **Schema**. A connection without that value
   answers null; the same value can differ on two connections to the same related record.
5. To add these values to an existing block, use its **Fields…** and select from **Attributes
   of the relationship**. If the group is empty, review **Via** and the pair's **Carries** in
   [Add a relationship](/docs/guide/model/add-a-relationship/#choose-what-each-relationship-carries).
   Do not add connection values to the main object's Fields: they need the related block's context.
```

Old:

```markdown
1. On **Fields**, choose **Parent, path and hierarchy…**, select **Serve the parent
   (objectType, id, code, name)** and apply the choice. The **Parent** section appears below
   the object's fields. If it is already served, open that section directly.
2. Review the parent's **Output name**. Select **Fields**, or choose **Parent fields…**,
   to open **Fields of the parent**. Each row pairs a public name with the source it reads.
   Choose built-in values or attributes from **Attributes of the parent types** and review
   the proposed camelCase name. Edit that name if consumers need another one, then apply.
   The Parent table shows name=source where they differ. These sources belong to types that
   directly contain exposed records, rather than to the child. A missing or unbound value
   answers null unless a default supplies a value; with no parent, the whole output is null.
   Existing short lists remain valid: built-in fields keep their role's output name, and
   other sources become camelCase words, such as categoryCode for category-code. Editing
   writes the parent fields out with explicit output names.
3. Under **Parent's related records**, choose **Add related**, or open the consumer API's
   ⋯ menu and choose **Add related to the parent…** to open the same dialog. Give the block an **Output
   name**, choose **Via**, and select **Fields**, including their public output names.
   The offered relationships start from the possible parent types. Apply and inspect the
   new row. Its block sits inside the parent's answer; do not add a parent prefix to its
   output name here.
4. In **Served**, choose **Always** to return that block in ordinary answers, or **On request**
   to return it only when a consumer asks. You can also set Served in the add dialog.
   The related table on **Types and related** has the same choices for the object's blocks.
   Use **Fields** on a parent block to adjust what it shows.
5. Open **Operations**. If any block is on request, **Include** shows the accepted choices,
   with the parent's blocks distinguished by a parent prefix. This list is generated from
   Served; there is nothing to enter here. Share it with the consuming team. An omitted
   block is absent, rather than null or an empty list; when requested it uses the usual
   object-or-list shape.
6. To filter through the parent's block, open **Filters**, choose **Add filter…**, set
   **Verb** to **On related**, and select the parent's entry in **Related block**. Choose
   **Name** and **Matches on**. Select **Keep only matching records** if children whose
   parent has no matching item should disappear. Leave it clear to trim only the block.
   The filter still works when the block is not requested. Leave **Crosswalk** clear:
   a parent's block cannot be a crosswalk target. The parameter used by Include is
   reserved for requesting blocks; choose a different filter name.
7. Review **Issues**, **Schema**, **Message example** and compatibility. The parent has
   one level; another parent, path or hierarchy cannot be added inside it. Values from the
   parent's ancestors are supported through specialist editing, rather than new choices
   in the parent field picker. An invalid field or relationship must be corrected before
   activation. Changing **Always** to **On request** on a released block needs a higher
   contract version because the block leaves the ordinary answer.
```

New:

```markdown
1. On **Fields**, choose **Parent, path and hierarchy…**, select **Serve the parent
   (objectType, id, code, name)** and choose **Save**. The **Parent** section appears below
   the object's fields. If it is already served, open that section directly.
2. Review the parent's **Output name**. Select **Fields**, or choose **Parent fields…**,
   to open **Fields of the parent**. Each row pairs a public name with the source it reads.
   Choose built-in values or attributes from **Attributes of the parent types** and review
   the proposed camelCase name. Edit that name if consumers need another one, then choose **Save**.
   The Parent table shows name=source where they differ. These sources belong to types that
   directly contain exposed records, rather than to the child. A missing or unbound value
   answers null unless a default supplies a value; with no parent, the whole output is null.
   Existing short lists remain valid: built-in fields keep their role's output name, and
   other sources become camelCase words, such as categoryCode for category-code. Editing
   writes the parent fields out with explicit output names.
3. Under **Parent's related records**, choose **Add related**, or open the consumer API's
   ⋯ menu and choose **Add related to the parent…** to open the same dialog. Give the block an **Output
   name**, choose **Via**, and select **Fields**, including their public output names.
   The offered relationships start from the possible parent types. Choose **Add related block** and inspect the
   new row. Its block sits inside the parent's answer; do not add a parent prefix to its
   output name here.
4. In **Served**, choose **Always** to return that block in ordinary answers, or **On request**
   to return it only when a consumer asks. You can also set Served in the add dialog.
   The related table on **Types and related** has the same choices for the object's blocks.
   Use **Fields** on a parent block to adjust what it shows.
5. Open **Operations**. If any block is on request, **Include** shows the accepted choices,
   with the parent's blocks distinguished by a parent prefix. This list is generated from
   Served; there is nothing to enter here. Share it with the consuming team. An omitted
   block is absent, rather than null or an empty list; when requested it uses the usual
   object-or-list shape.
6. To filter through the parent's block, open **Filters**, choose **Add filter…**, set
   **Verb** to **On related**, and select the parent's entry in **Related block**. Choose
   **Name** and **Matches on**. Select **Keep only matching records** if children whose
   parent has no matching item should disappear. Leave it clear to trim only the block.
   The filter still works when the block is not requested. Leave **Crosswalk** clear:
   a parent's block cannot be a crosswalk target. The parameter used by Include is
   reserved for requesting blocks; choose a different filter name.
7. Review **Issues**, **Schema**, **Message example** and compatibility. The parent has
   one level; another parent, path or hierarchy cannot be added inside it. Values from the
   parent's ancestors are supported through specialist editing, rather than new choices
   in the parent field picker. An invalid field or relationship must be corrected before
   activation. Changing **Always** to **On request** on a released block needs a higher
   contract version because the block leaves the ordinary answer.
```

Old:

```markdown
1. On **Operations**, review **Get by ID**, **XREF** and **Resolve**. Get by ID reads a
   stable record ID; XREF matches values such as a code or name. Resolve performs many
   such reads in a batch and needs both Get by ID and XREF. Leave off operations the
   contract does not need: consumers cannot use an undeclared operation.
2. Use **Add list…** and set **Key**, **Of**, **Within the filter** and **Sorted by**.
   **Of** selects a type; sorting selects its order. None for Within gives the list no
   special parent parameter. With an Under filter, a consumer can supply a parent ID to
   list records below it. Omitting that parameter still returns the whole type.
3. Enable XREF if needed, then use **Add XREF rule…**. Review the fields with
   **Matches on…** and **Fields…** where offered. **Exact** and **Contains** are numeric
   weights, not mutually exclusive modes. Give reliable identifiers stronger weights
   than broad name fragments. Contains applies to text terms of at least three characters.
4. Use **Add a match through a related block…** when related data should help identify an
   exposed record. Review **Also match through**, **First of** and **Prefers**. A match
   through a system code can identify its owning record; a shared code can identify several.
   Use that row’s **Preferred types…**, select **Prefer records of these types**, and Apply
   to prefer exposed owner types; select none to remove the preference. Review ties with the
   consuming team rather than relying on the first result.
5. On **Filters**, choose **Add filter…**, **Name** and **Verb**. **By type** selects types;
   **Under** reads containment; **Linked to** selects **Through**; **On related** selects
   **Related block**. Review **Matches on** and the offered **Options**. **Keep only
   matching records** narrows the returned records. A related filter also narrows the
   related block's items; **Score only matching items** limits which items contribute
   lookup scores. **Crosswalk** lets consumers ask for a target representation from
   that block. Enable only the choices the contract needs.
6. For a filter on connection values, use **On related**, choose the block, then **Matches on…**
   and a field under **Attributes of the relationship**. Keep only matching records if objects
   without a matching connection should disappear too. To score a carried value instead, use
   a text attribute in the related match's **First of**. Review **Schema** and **Message example**:
   only the connection with that value supplies a match, even when other records share its target.
```

New:

```markdown
1. On **Operations**, review **Get by ID**, **XREF** and **Resolve**. Get by ID reads a
   stable record ID; XREF matches values such as a code or name. Resolve performs many
   such reads in a batch and needs both Get by ID and XREF. Leave off operations the
   contract does not need: consumers cannot use an undeclared operation.
2. Use **Add list…** and set **Key**, **Of**, **Within the filter** and **Sorted by**.
   **Of** selects a type; sorting selects its order. None for Within gives the list no
   special parent parameter. With an Under filter, a consumer can supply a parent ID to
   list records below it. Omitting that parameter still returns the whole type.
3. Enable XREF if needed, then use **Add XREF rule…**. Review the fields with
   **Matches on…** and **Fields…** where offered. **Exact** and **Contains** are numeric
   weights, not mutually exclusive modes. Give reliable identifiers stronger weights
   than broad name fragments. Contains applies to text terms of at least three characters.
4. Use **Add a match through a related block…** when related data should help identify an
   exposed record. Review **Also match through**, **First of** and **Prefers**. A match
   through a system code can identify its owning record; a shared code can identify several.
   Use that row’s **Preferred types…**, select **Prefer records of these types**, and choose **Apply** in the popover
   to prefer exposed owner types; select none to remove the preference. Review ties with the
   consuming team rather than relying on the first result.
5. On **Filters**, choose **Add filter…**, **Name** and **Verb**. **By type** selects types;
   **Under** reads containment; **Linked to** selects **Through**; **On related** selects
   **Related block**. Review **Matches on** and the offered **Options**. **Keep only
   matching records** narrows the returned records. A related filter also narrows the
   related block's items; **Score only matching items** limits which items contribute
   lookup scores. **Crosswalk** lets consumers ask for a target representation from
   that block. Enable only the choices the contract needs.
6. For a filter on connection values, use **On related**, choose the block, then **Matches on…**
   and a field under **Attributes of the relationship**. Keep only matching records if objects
   without a matching connection should disappear too. To score a carried value instead, use
   a text attribute in the related match's **First of**. Review **Schema** and **Message example**:
   only the connection with that value supplies a match, even when other records share its target.
```

### guide/model/edit-a-record-page.md

Old:

```markdown
1. At the foot of **Main**, choose **Add panel…**, beside **New field group**.
2. In **Add panel**, choose **What the panel shows**:
   - **Related records** lists the records reached through one relationship. It is offered
     when this type has relationships other than containment.
   - **Contained records** lists records inside the open record. It is offered only when
     the type contains types that this application lists. Select at least one **Contained types** choice.
   - **Fields** creates a group of this type's fields. Select **Fields**; chosen fields move
     from their current groups into the new one.
3. For **Related records**, select **Relationship**. The names read from this type's side
   of the relationship, including relationships pointing towards it. **(on the page)** means
   an existing panel already lists that relationship; it does not prevent another panel.
   Read the **Columns:** line beneath the choice to see the columns the new panel gets.
4. Choose **Region**: **Main** or **Side**. Review **Title**. For related or contained records,
   it starts from your choice and you can change it. For a field group, enter a title.
5. Choose **Apply**. The panel appears in the chosen region as one draft step. Use **Undo**
   if it was not what you wanted. Adding the panel does not create or change records.
```

New:

```markdown
1. At the foot of **Main**, choose **Add panel…**, beside **New field group**.
2. In **Add panel**, choose **What the panel shows**:
   - **Related records** lists the records reached through one relationship. It is offered
     when this type has relationships other than containment.
   - **Contained records** lists records inside the open record. It is offered only when
     the type contains types that this application lists. Select at least one **Contained types** choice.
   - **Fields** creates a group of this type's fields. Select **Fields**; chosen fields move
     from their current groups into the new one.
3. For **Related records**, select **Relationship**. The names read from this type's side
   of the relationship, including relationships pointing towards it. **(on the page)** means
   an existing panel already lists that relationship; it does not prevent another panel.
   Read the **Columns:** line beneath the choice to see the columns the new panel gets.
4. Choose **Region**: **Main** or **Side**. Review **Title**. For related or contained records,
   it starts from your choice and you can change it. For a field group, enter a title.
5. Choose **Add panel**. The panel appears in the chosen region as one draft step. Use **Undo**
   if it was not what you wanted. Adding the panel does not create or change records.
```

Old:

```markdown
1. Open the menu of a related-record, contained-record or table panel and choose **Columns…**.
2. Select **Name** and the fields you need. Under **Where it sits**, select a containing type
   to show the containing record's name. This can be an ancestor further up the hierarchy,
   not just the immediate parent. **Type** is also offered when the panel lists several types.
3. Choose **Apply** and inspect the column frames. Keep at least one column.
4. On a related-record panel whose menu offers **Sort…**, choose it, select **Sorted by**
   and choose **Apply**. The choices come from the panel's allowed sort fields.
```

New:

```markdown
1. Open the menu of a related-record, contained-record or table panel and choose **Columns…**.
2. Select **Name** and the fields you need. Under **Where it sits**, select a containing type
   to show the containing record's name. This can be an ancestor further up the hierarchy,
   not just the immediate parent. **Type** is also offered when the panel lists several types.
3. Choose **Apply** and inspect the column frames. Keep at least one column.
4. On a related-record panel whose menu offers **Sort…**, choose it, select **Sorted by**
   and choose **Save**. The choices come from the panel's allowed sort fields.
```

Old:

```markdown
1. Open a panel's menu. **Move up**, **Move down** and **Move to Main** or **Move to Side**
   change its position. A grip can also drag it within a region or into the other region.
   On a phone, or with a keyboard, use the menu.
2. Choose **Rename…** to change **Title**. **Hide** keeps a panel in the layout but hides it
   from the record page; **Show** restores it. **Remove from page** takes it off the page,
   with **Undo** available afterwards. Stored records and values remain.
3. For a field, use **Move up**, **Move down** or **Move to …** to place it in a field group.
   **Remove from panel** takes it off that group. Dragging a field onto another group or
   field is another way to move it.
4. To make a field group in **Main**, choose **New field group**, give it **Title** and select
   **Fields**. Choose **Apply**. Selected fields move into it from their current positions.
   To add an omitted field to an existing group, use its **Add fields…** menu and select
   from **Fields not on the page**. This does not create a new field definition.
```

New:

```markdown
1. Open a panel's menu. **Move up**, **Move down** and **Move to Main** or **Move to Side**
   change its position. A grip can also drag it within a region or into the other region.
   On a phone, or with a keyboard, use the menu.
2. Choose **Rename…** to change **Title**. **Hide** keeps a panel in the layout but hides it
   from the record page; **Show** restores it. **Remove from page** takes it off the page,
   with **Undo** available afterwards. Stored records and values remain.
3. For a field, use **Move up**, **Move down** or **Move to …** to place it in a field group.
   **Remove from panel** takes it off that group. Dragging a field onto another group or
   field is another way to move it.
4. To make a field group in **Main**, choose **New field group**, give it **Title** and select
   **Fields**. Choose **Apply** in the popover. Selected fields move into it from their current positions.
   To add an omitted field to an existing group, use its **Add fields…** menu and select
   from **Fields not on the page**. This does not create a new field definition.
```

Old:

```markdown
1. In **Record page**, choose **Header and breadcrumbs…**.
2. Select **Title of the record** from Name or an attached field. **Line under the title**
   adds a second field; choose **None** to remove it.
3. Choose **Show the type’s name in the header** as needed. **Breadcrumbs name the type**
   also shows the type in the header; **Breadcrumbs name the records above it** shows parents
   in the line above the title. That line starts with the list link when opened from a list,
   without an application entry. These choices do not change a record’s parent or name.
4. Apply and inspect the preview with a record that has parents. Undo restores the saved step.
```

New:

```markdown
1. In **Record page**, choose **Header and breadcrumbs…**.
2. Select **Title of the record** from Name or an attached field. **Line under the title**
   adds a second field; choose **None** to remove it.
3. Choose **Show the type’s name in the header** as needed. **Breadcrumbs name the type**
   also shows the type in the header; **Breadcrumbs name the records above it** shows parents
   in the line above the title. That line starts with the list link when opened from a list,
   without an application entry. These choices do not change a record’s parent or name.
4. Choose **Save** and inspect the preview with a record that has parents. Undo restores the saved step.
```

Old:

```markdown
1. Open the panel’s menu and choose **Settings…**. Fields groups have no extra settings.
2. For related records, select **Relationships listed** and **Listed from**. Choose **This
   record to the others**, **The others to this record**, or **Both ways**. Tick **Show which
   relationship joins each record** when one panel combines several meanings.
3. Select **Fields a reader can sort by** if people need a sort menu. Leaving these unchecked
   lists related records by name. A default sort no longer in the list moves to the first
   remaining choice, or is cleared when the list is empty.
4. For hierarchy, set **Show the parent** and **Show the records above the parent**. For a
   contained-record or table panel, choose **Rows on a page**. A table also offers **List
   only the records under this one**; clear it only when the page should show that type’s
   records beyond the open record’s direct children.
5. Apply and review columns, sorting and Issues. Changing settings does not rewrite stored
   connections. A panel with no matching records is empty; check its direction and selection
   before concluding that data is missing.
```

New:

```markdown
1. Open the panel’s menu and choose **Settings…**. Fields groups have no extra settings.
2. For related records, select **Relationships listed** and **Listed from**. Choose **This
   record to the others**, **The others to this record**, or **Both ways**. Tick **Show which
   relationship joins each record** when one panel combines several meanings.
3. Select **Fields a reader can sort by** if people need a sort menu. Leaving these unchecked
   lists related records by name. A default sort no longer in the list moves to the first
   remaining choice, or is cleared when the list is empty.
4. For hierarchy, set **Show the parent** and **Show the records above the parent**. For a
   contained-record or table panel, choose **Rows on a page**. A table also offers **List
   only the records under this one**; clear it only when the page should show that type’s
   records beyond the open record’s direct children.
5. Choose **Save** and review columns, sorting and Issues. Changing settings does not rewrite stored
   connections. A panel with no matching records is empty; check its direction and selection
   before concluding that data is missing.
```

### guide/model/group-collections-in-navigation.md

Old:

```markdown
1. Select the application. Choose **Add a navigation group…** from its menu, or **Navigation
   group…** from **Add** and choose **Application**.
2. Enter **Label** and choose whether it is **Folded when the sidebar opens**. Apply and check
   **Navigation groups** in the application panel. An empty group is allowed.
3. Choose the group's name in that table, or select it in the model pane. Its panel shows the
   application it belongs to, its starting state and entry count. The **Entries** table lists
   **Entry**, **Kind**, **Opens on** and **State**. A new group has no entries yet.
```

New:

```markdown
1. Select the application. Choose **Add a navigation group…** from its menu, or **Navigation
   group…** from **Add** and choose **Application**.
2. Enter **Label** and choose whether it is **Folded when the sidebar opens**. Choose **Add group** and check
   **Navigation groups** in the application panel. An empty group is allowed.
3. Choose the group's name in that table, or select it in the model pane. Its panel shows the
   application it belongs to, its starting state and entry count. The **Entries** table lists
   **Entry**, **Kind**, **Opens on** and **State**. A new group has no entries yet.
```

Old:

```markdown
1. In the group panel, choose **Add to group…**. The dialog lists **Collections** and
   **Relation matrices** separately. Entries already in this group are left out.
2. Use **Search collections and matrices** to find entries by name. Tick all the entries you
   want to add. Beside each, **Top of the sidebar** means an ungrouped collection;
   **Inside** followed by a type's name means a matrix available through that row collection.
   **In** followed by a group name means the entry is in another group. Ticking it changes
   that note to **Moves from** followed by the old group name.
3. Review those moves, then choose **Add** with the selected count. The entries appear in
   the group's table. A collection or matrix belongs to at most one group in this application;
   choosing a new group replaces its old placement. This does not move records under a parent.
4. Check the result. Adding several entries at once is one saved step: one **Undo** takes
   the whole addition back.
```

New:

```markdown
1. In the group panel, choose **Add to group…**. The popover lists **Collections** and
   **Relation matrices** separately. Entries already in this group are left out.
2. Use **Search collections and matrices** to find entries by name. Tick all the entries you
   want to add. Beside each, **Top of the sidebar** means an ungrouped collection;
   **Inside** followed by a type's name means a matrix available through that row collection.
   **In** followed by a group name means the entry is in another group. Ticking it changes
   that note to **Moves from** followed by the old group name.
3. Review those moves, then choose **Apply** in the popover. The same button saves selections made from the application's **Add to a group…** control. The entries appear in
   the group's table. A collection or matrix belongs to at most one group in this application;
   choosing a new group replaces its old placement. This does not move records under a parent.
4. Check the result. Adding several entries at once is one saved step: one **Undo** takes
   the whole addition back.
```

Old:

```markdown
From the application panel, **In no group:** lists ungrouped collections. Its **Add to a group…**
opens the same dialog with those collections ticked; choose **Group** and adjust the selection
before adding them.
```

New:

```markdown
From the application panel, **In no group:** lists ungrouped collections. Its **Add to a group…**
opens the same popover with those collections ticked; choose **Group** and adjust the selection
before adding them.
```

### guide/model/propose-again-with-a-newer-workbook.md

Old:

```markdown
1. Open the draft and read **History** before replacing its source. In **More actions**, choose
   **Upload a newer workbook…**. A draft without a source offers **Add a workbook…** instead.
2. Choose **Workbook**, an XLSX workbook or CSV file, and review **Compare with the records of**.
   Upload and wait for the new source to be profiled. If it fails, read the file error and retry
   with a corrected file; do not rely on the previous source's counts.
3. Inspect every sheet, changed header and list range. Existing reading instructions may no
   longer fit the columns. Check your row keys and reference matching before accepting proposals.
4. Choose **Propose again…**. Review **A new application**, **A new model**, **Additions to the
   model** or **Nothing: I will map it by hand**, with **Application name** where offered.
   Apply the intended choice. **Proposing from the workbook** pauses editing until it finishes.
5. Only elements still as proposed follow the new proposal. Manual edits remain yours and
   undone proposals stay undone. Review conflicting column choices in **Issues**, rather
   than assuming the engine replaced your decision.
6. Inspect **Proposed because**, **Evidence** and **History**, then obtain a
   [new dry run](/docs/guide/model/check-a-workbook-with-a-dry-run/) before loading.
```

New:

```markdown
1. Open the draft and read **History** before replacing its source. In **More actions**, choose
   **Upload a newer workbook…**. A draft without a source offers **Add a workbook…** instead.
2. Choose **Workbook**, an XLSX workbook or CSV file, or drop it onto the field. Review **Compare with the records of**.
   Upload and wait for the new source to be profiled. If it fails, read the file error and retry
   with a corrected file; do not rely on the previous source's counts.
3. Inspect every sheet, changed header and list range. Existing reading instructions may no
   longer fit the columns. Check your row keys and reference matching before accepting proposals.
4. Choose **Propose again…**. Review **A new application**, **A new model**, **Additions to the
   model** or **Nothing: I will map it by hand**, with **Application name** where offered.
   Apply the intended choice. **Proposing from the workbook** pauses editing until it finishes.
5. Only elements still as proposed follow the new proposal. Manual edits remain yours and
   undone proposals stay undone. Review conflicting column choices in **Issues**, rather
   than assuming the engine replaced your decision.
6. Inspect **Proposed because**, **Evidence** and **History**, then obtain a
   [new dry run](/docs/guide/model/check-a-workbook-with-a-dry-run/) before loading.
```

### guide/model/rename-or-re-key-an-element.md

Old:

```markdown
1. Open the element in a draft with **Model authoring**. Read **Key editable until released**
   or **Released: a key change needs a migration** in its facts.
2. To change the displayed words, choose **Rename…** or select the editable title. Enter **Name**;
   a record type also offers **Plural name**. Save, then check navigation and views using it.
   A shared attribute rename appears on every type that attaches it.
3. To change identity, choose **Change key…** and enter the new key. Relation types offer
   **Change keys…**. Save and inspect the affected definitions and **Issues**. The editor follows
   references in the draft; check documents and external systems you maintain separately.
4. For a released key, read **Needs a migration when installed: integrations naming the key must change**.
   The step applies and **History** marks it **Needs a migration**. When installing, review the key
   change and the consumer APIs of the base release naming it. Coordinate integrations before
   confirming the [migration](/docs/guide/model/migrate-a-workspace/). A label-only rename does
   not change the key.
5. If a save is refused, read **Not applied**. A key already in use needs a different key;
   for a newer draft, review [concurrent changes](/docs/guide/model/work-on-a-draft-with-others/).
```

New:

```markdown
1. Open the element in a draft with **Model authoring**. Read **Key editable until released**
   or **Released: a key change needs a migration** in its facts.
2. To change the displayed words, choose **Rename…** or select the editable title. The short form opens beneath the control. Enter **Name**;
   a record type also offers **Plural name**. Save, then check navigation and views using it.
   A shared attribute rename appears on every type that attaches it.
3. To change identity, choose **Change key…** and enter the new key. Relation types offer
   **Change keys…**. Save and inspect the affected definitions and **Issues**. The editor follows
   references in the draft; check documents and external systems you maintain separately.
4. For a released key, read **Needs a migration when installed: integrations naming the key must change**.
   The step applies and **History** marks it **Needs a migration**. When installing, review the key
   change and the consumer APIs of the base release naming it. Coordinate integrations before
   confirming the [migration](/docs/guide/model/migrate-a-workspace/). A label-only rename does
   not change the key.
5. If a save is refused, read **Not applied**. A key already in use needs a different key;
   for a newer draft, review [concurrent changes](/docs/guide/model/work-on-a-draft-with-others/).
```

### guide/model/reuse-and-change-attributes.md

Old:

```markdown
1. Select the receiving type and open **Attributes**. Choose **Attach an existing attribute…**
   and select the field. Already attached fields are not offered. Choose **Required** only if
   every record of this type must supply it, then apply the attachment.
2. Check **Shared with**. A shared attribute's name, value type and uniqueness are used by all
   attached types. Open **Attribute types** to inspect the common definition and its attachments.
3. In the type's table, select an editable **Required** or **Read-only** cell, choose **Yes**
   or **No**, then **Save**. The menu also offers **Make required** / **Make optional** and
   **Make read-only** / **Make editable**. These choices apply to this type's attachment.
4. To change the shared field, use **Rename…**, **Value type…**, **Make unique** or **Allow
   repeated values**. On the attribute type, **Features…** chooses **Searchable**, **Filterable**,
   **Sortable** and **Unique**. Inspect every attached type before applying a shared change.
5. Use **Move up** or **Move down** to order attributes. **Move to…**, or dragging a field onto
   a type in the model pane, moves the attachment; its columns and panel placement move with it.
   Check the destination rather than creating a duplicate attribute definition. For a released
   field, read **Needs a migration when installed**: moving the attachment removes its values
   from the original type's records. They cannot be carried onto a different type's records.
6. Review **Issues** and **History**. A released field change that affects stored data applies
   and is marked **Needs a migration**, with affected records, values and relationships.
   Installing the draft shows the migration to review. Check conversions, loss and records that
   break tighter rules before [confirming it](/docs/guide/model/migrate-a-workspace/).
   Use **Undo** if the draft change is unwanted.
```

New:

```markdown
1. Select the receiving type and open **Attributes**. Choose **Attach an existing attribute…**
   and select the field. Already attached fields are not offered. Choose **Required** only if
   every record of this type must supply it, then choose **Add attribute**.
2. Check **Shared with**. A shared attribute's name, value type and uniqueness are used by all
   attached types. Open **Attribute types** to inspect the common definition and its attachments.
3. In the type's table, select an editable **Required** or **Read-only** cell, choose **Yes**
   or **No**, then **Save**. The menu also offers **Make required** / **Make optional** and
   **Make read-only** / **Make editable**. These choices apply to this type's attachment.
4. To change the shared field, use **Rename…**, **Value type…**, **Make unique** or **Allow
   repeated values**. On the attribute type, **Features…** chooses **Searchable**, **Filterable**,
   **Sortable** and **Unique**. Inspect every attached type before applying a shared change.
5. Use **Move up** or **Move down** to order attributes. **Move to…**, or dragging a field onto
   a type in the model pane, moves the attachment; its columns and panel placement move with it.
   Check the destination rather than creating a duplicate attribute definition. For a released
   field, read **Needs a migration when installed**: moving the attachment removes its values
   from the original type's records. They cannot be carried onto a different type's records.
6. Review **Issues** and **History**. A released field change that affects stored data applies
   and is marked **Needs a migration**, with affected records, values and relationships.
   Installing the draft shows the migration to review. Check conversions, loss and records that
   break tighter rules before [confirming it](/docs/guide/model/migrate-a-workspace/).
   Use **Undo** if the draft change is unwanted.
```

Old:

```markdown
1. Select the shared definition under **Attribute types**. For Whole number or Decimal number,
   edit **Minimum** or **Maximum** in **Settings**. Both open **Minimum and maximum…**. Enter
   either or both, or leave them empty to remove bounds, then **Apply**. A minimum greater
   than the maximum is invalid. All uses of the shared field receive these bounds.
2. Edit **Hidden** or **Help text** in the same Settings table and **Save**. These are shared
   presentation choices. Hidden leaves the field off record forms without deleting its data.
3. To provide guidance for just one type, select that type’s **Attributes** table and edit
   **Hidden** or **Help text** there. A local help text replaces the shared help; clearing it
   returns to shared help. A field hidden by the shared definition remains hidden even when
   the local cell says No. Review a populated and an empty record in Preview.
4. Check Issues and the release comparison. Bounds apply to stored values too; saving the draft
   does not convert or fill data. Correct incompatible records or review a migration before
   activating the release.
```

New:

```markdown
1. Select the shared definition under **Attribute types**. For Whole number or Decimal number,
   edit **Minimum** or **Maximum** in **Settings**. Both open **Minimum and maximum…**. Enter
   either or both, or leave them empty to remove bounds, then **Save** in the popover. A minimum greater
   than the maximum is invalid. All uses of the shared field receive these bounds.
2. Edit **Hidden** or **Help text** in the same Settings table and **Save**. These are shared
   presentation choices. Hidden leaves the field off record forms without deleting its data.
3. To provide guidance for just one type, select that type’s **Attributes** table and edit
   **Hidden** or **Help text** there. A local help text replaces the shared help; clearing it
   returns to shared help. A field hidden by the shared definition remains hidden even when
   the local cell says No. Review a populated and an empty record in Preview.
4. Check Issues and the release comparison. Bounds apply to stored values too; saving the draft
   does not convert or fill data. Correct incompatible records or review a migration before
   activating the release.
```

### guide/model/review-an-assistants-workbook-design.md

Old:

```markdown
1. Open the intended workspace and its **⋯** menu beside the workspace selector. Choose
   **Import**. With the assistant enabled, **Load a workbook** opens first.
2. Choose an XLSX or CSV **Workbook**. Check **Into** names the intended workspace.
3. In **Tell the assistant about this file (optional)**, explain whether this updates existing
   records or adds something new. Say which column identifies a record and how new types
   should relate to the existing ones, if you know. A stable key matters more than a row number.
   A list of records not yet held needs a key too; otherwise a later load can create them again.
4. Read what is sent, then choose **Read the workbook**. **Import without the assistant…**
   uses the manual import instead. **Cancel** sends nothing.
5. Wait on the task page. The bar below the top bar shows the current stage and next action.
   It follows you into the model editor and change set. **Stop** ends the current turn;
   it does not discard the task.
```

New:

```markdown
1. Open the intended workspace and its **⋯** menu beside the workspace selector. Choose
   **Import**. With the assistant enabled, **Load a workbook** opens first.
2. Choose an XLSX or CSV **Workbook**, or drop it onto the field. Check **Into** names the intended workspace.
3. In **Tell the assistant about this file (optional)**, explain whether this updates existing
   records or adds something new. Say which column identifies a record and how new types
   should relate to the existing ones, if you know. A stable key matters more than a row number.
   A list of records not yet held needs a key too; otherwise a later load can create them again.
4. Read what is sent, then choose **Read the workbook**. **Import without the assistant…**
   uses the manual import instead. **Cancel** sends nothing.
5. Wait on the task page. The bar below the top bar shows the current stage and next action.
   It follows you into the model editor and change set. **Stop** ends the current turn;
   it does not discard the task.
```

### guide/model/split-merge-and-move-types.md

Old:

```markdown
1. Select the type and choose **Split…** from its menu. It needs attributes to split.
2. Enter **New type’s name** and, where needed, **Plural name**. Choose **Attributes that move
   to it**. The selected attachments belong to the new type after the split.
3. Enter **Relation name** from the original type, **Reverse name** and **Cardinality** for the
   connection between them. Apply and inspect both types, their relationship and layouts.
4. If stored data uses the released type, **History** marks the step **Needs a migration**.
   Installing proposes related records holding the moved values. In the preview, open **Created**:
   a source record with no moved value gets no new record; with **Many to one**, records holding
   identical moved values share one new record. Its name comes from the first moved value,
   or the source record's name if that value supplies no name.
```

New:

```markdown
1. Select the type and choose **Split…** from its menu. It needs attributes to split.
2. Enter **New type’s name** and, where needed, **Plural name**. Choose **Attributes that move
   to it**. The selected attachments belong to the new type after the split.
3. Enter **Relation name** from the original type, **Reverse name** and **Cardinality** for the
   connection between them. Choose **Add type** and inspect both types, their relationship and layouts.
4. If stored data uses the released type, **History** marks the step **Needs a migration**.
   Installing proposes related records holding the moved values. In the preview, open **Created**:
   a source record with no moved value gets no new record; with **Many to one**, records holding
   identical moved values share one new record. Its name comes from the first moved value,
   or the source record's name if that value supplies no name.
```

Old:

```markdown
1. Select the type to absorb and choose **Merge into…**.
2. Choose **Into** carefully. Its attributes, relations and layout join the chosen type.
3. Apply and inspect the combined type and **Issues**. Use **Undo** if the result is unwanted.
4. When stored data uses the released type, review its **Needs a migration** mark in **History**.
   Installing proposes that its records become the receiving type, keeping their identities
   and history. Check the proposed destination and all outcomes in the migration preview.
```

New:

```markdown
1. Select the type to absorb and choose **Merge into…**.
2. Choose **Into** carefully. Its attributes, relations and layout join the chosen type.
3. Choose **Save** in the popover and inspect the combined type and **Issues**. Use **Undo** if the result is unwanted.
4. When stored data uses the released type, review its **Needs a migration** mark in **History**.
   Installing proposes that its records become the receiving type, keeping their identities
   and history. Check the proposed destination and all outcomes in the migration preview.
```

### guide/model/start-a-draft-from-a-workbook.md

Old:

```markdown
1. Open **Settings**, **Model**. Choose **New from a workbook**. **New draft** starts model
   authoring without this workbook proposal task.
2. Enter **Draft name** and choose the **Workbook**, an Excel workbook or CSV file.
3. Under **Propose**, choose **A new application**, **A new model**, **Additions to the model**
   or **Nothing: I will map it by hand**. Read the explanations: a new application adds to the
   starting model, while a new model starts empty. Set **Application name** where offered.
4. Choose **Compare with the records of**. The dry run uses that workspace; choose the intended
   data, not simply a similarly named workspace. Check **Starting document** and **Base release**
   where offered so the draft starts from the definitions you intend.
5. Choose **Create and propose**, or **Cancel** to leave without creating the draft.
   Wait for the file to be read and the editor to open. If the upload fails, correct the reported
   file problem and try again before proceeding.
```

New:

```markdown
1. Open **Settings**, **Model**. Choose **New from a workbook**. **New draft** starts model
   authoring without this workbook proposal task.
2. Enter **Draft name** and choose the **Workbook**, an Excel workbook or CSV file, or drop it onto the field.
3. Under **Propose**, choose **A new application**, **A new model**, **Additions to the model**
   or **Nothing: I will map it by hand**. Read the explanations: a new application adds to the
   starting model, while a new model starts empty. Set **Application name** where offered.
4. Choose **Compare with the records of**. The dry run uses that workspace; choose the intended
   data, not simply a similarly named workspace. Check **Starting document** and **Base release**
   where offered so the draft starts from the definitions you intend.
5. Choose **Create and propose**, or **Cancel** to leave without creating the draft.
   Wait for the file to be read and the editor to open. If the upload fails, correct the reported
   file problem and try again before proceeding.
```

### guide/model/turn-an-attribute-into-a-list.md

Old:

```markdown
1. In a draft, select the type and open **Attributes**. Open the attribute's menu and choose
   **Turn into a list type…**. You need **Model authoring**.
2. Enter **List type’s name** and **Plural name**. Enter **Relation name** from the original
   type and **Reverse name** from the list records back to it.
3. Review **Which records may be chosen**. Leave it unrestricted to offer any list record,
   or add the offered criteria. A new list type initially offers criteria on its name.
4. Apply and inspect the new type and relationship. Check the original type's fields and
   layouts and resolve **Issues** before previewing or installing.
5. If the released attachment holds values, the step applies and **History** marks it
   **Needs a migration**. Saving the draft does not populate live list records. Use **Undo**
   to reverse an unwanted draft step.
6. When installing, review **Activation needs a migration** and choose **Install … and preview
   the migration…**. The preview includes the proposed list conversion. Open **Created** to
   inspect the list records and relationships it creates: one record per distinct value,
   named by the value, connected to every source record holding it. The values leave the
   source records. Review any loss or items to fix, then
   [confirm the migration](/docs/guide/model/migrate-a-workspace/) when acceptable.
```

New:

```markdown
1. In a draft, select the type and open **Attributes**. Open the attribute's menu and choose
   **Turn into a list type…**. You need **Model authoring**.
2. Enter **List type’s name** and **Plural name**. Enter **Relation name** from the original
   type and **Reverse name** from the list records back to it.
3. Review **Which records may be chosen**. Leave it unrestricted to offer any list record,
   or add the offered criteria. A new list type initially offers criteria on its name.
4. Choose **Save** and inspect the new type and relationship. Check the original type's fields and
   layouts and resolve **Issues** before previewing or installing.
5. If the released attachment holds values, the step applies and **History** marks it
   **Needs a migration**. Saving the draft does not populate live list records. Use **Undo**
   to reverse an unwanted draft step.
6. When installing, review **Activation needs a migration** and choose **Install … and preview
   the migration…**. The preview includes the proposed list conversion. Open **Created** to
   inspect the list records and relationships it creates: one record per distinct value,
   named by the value, connected to every source record holding it. The values leave the
   source records. Review any loss or items to fix, then
   [confirm the migration](/docs/guide/model/migrate-a-workspace/) when acceptable.
```

### guide/use/add-a-record.md

Old:

```markdown
1. Open the intended workspace, application and collection. Check **Live** or the named change
   set before choosing **Add …**. If you see **Propose a new …**, follow
   [Propose a change](/docs/guide/use/propose-a-change/) first.
2. The **New …** form opens. Enter the name and editable fields. Required fields must have
   values, including at least one field where the form gives that rule. Read-only fields
   cannot be filled through this form. Keep numbers, dates and Yes/No values in their proper controls.
   Read help below the fields before filling them. Fields hidden by the model are omitted;
   ask the model administrator if a required piece of information cannot be supplied.
3. Where **Parent** is offered, select the allowed parent type and search for the record.
   Some types require a parent and cannot be created at the top. **No parent available** means
   you must first provide an allowed parent. Open the hierarchy view and use **Add …**
   for its top-level type, then add the child records beneath it. If that action is absent,
   check your editing access and ask the model administrator about the view’s actions and placement rules.
4. Complete required relationships in the same form. Search only offers eligible records in
   this workspace and context. A general search result elsewhere does not guarantee eligibility.
5. Choose **Create**. Fields, parent and required relationships save together. A refusal leaves
   no partially created record: correct the named missing value, duplicate value, invalid date
   period, placement or relationship and try again.
6. Check the new record's path, fields and save notice. A Live save takes effect immediately;
   a change-set save stays proposed until publication.
```

New:

```markdown
1. Open the intended workspace, application and collection. Check **Live** or the named change
   set before choosing **Add …**. If you see **Propose a new …**, follow
   [Propose a change](/docs/guide/use/propose-a-change/) first.
2. The **New …** form opens beside the page on a desktop. Enter the name and required fields first; optional fields wait under **More fields (n)**. That choice is remembered per type in this browser. Required fields must have
   values, including at least one field where the form gives that rule. Read-only fields
   cannot be filled through this form. Keep numbers, dates and Yes/No values in their proper controls.
   Read help below the fields before filling them. Fields hidden by the model are omitted;
   ask the model administrator if a required piece of information cannot be supplied.
3. If the page already supplies the parent, the form says **In** followed by its name; choose **Change** only to pick another. Where **Parent** is offered, select the allowed parent type and search for the record.
   Some types require a parent and cannot be created at the top. **No parent available** means
   you must first provide an allowed parent. Open the hierarchy view and use **Add …**
   for its top-level type, then add the child records beneath it. If that action is absent,
   check your editing access and ask the model administrator about the view’s actions and placement rules.
4. Complete required relationships in the same form. Search only offers eligible records in
   this workspace and context. A general search result elsewhere does not guarantee eligibility.
5. Choose **Add** followed by the record type's name. Fields, parent and required relationships save together. A refusal leaves
   no partially created record. Missing and wrongly typed values are explained below their fields; correct the named missing value, duplicate value, invalid date
   period, placement or relationship and try again.
6. Check the new record's path, fields and save notice. A Live save takes effect immediately;
   a change-set save stays proposed until publication.
```

### guide/use/approve-a-change-set.md

Old:

```markdown
If **Publish change set** is offered instead, your permissions and the policy allow direct
publication. Use the [publish steps](/docs/guide/use/prepare-and-publish-a-change-set/#publish).
Do not change workspace policy merely to make a button appear; ask an administrator if the
available actions do not match your responsibility.
```

New:

```markdown
If **Publish** is offered instead, your permissions and the policy allow direct
publication. Use the [publish steps](/docs/guide/use/prepare-and-publish-a-change-set/#publish).
Do not change workspace policy merely to make a button appear; ask an administrator if the
available actions do not match your responsibility.
```

### guide/use/arrange-records-in-a-tree.md

Old:

```markdown
In an editable tree, choose **Add …** for the intended top-level type in the header or empty
view. Complete the new record’s name and required fields, then choose **Create**. This form
has no parent field: the record starts at the top of this tree. Add children from its menu
afterwards. The action appears only for types allowed at the top, when the view allows creation
and your permissions allow writing that type.
```

New:

```markdown
In an editable tree, choose **Add …** for the intended top-level type in the header or empty
view. Complete the new record’s name and required fields, then choose **Add** followed by the record type's name. This form
has no parent field: the record starts at the top of this tree. Add children from its menu
afterwards. The action appears only for types allowed at the top, when the view allows creation
and your permissions allow writing that type.
```

Old:

```markdown
1. Open the record's menu and choose its rename action, or press **F2** on the focused record.
   Enter the intended name and confirm the rename. Check the new label; the record retains
   its identity and connections.
2. To add within a parent, choose the menu's add-child action for an offered type. Complete
   the new record form, check its parent and choose **Create**. If the needed type is absent,
   ask a model administrator about the permitted children.
3. Where an availability action is offered, use it only to change whether the record is
   available under that model's rule. It does not delete the record.
```

New:

```markdown
1. Open the record's menu and choose its rename action, or press **F2** on the focused record.
   Enter the intended name and confirm the rename. Check the new label; the record retains
   its identity and connections.
2. To add within a parent, choose the menu's add-child action for an offered type. Complete
   the new record form, check its parent and choose **Add** followed by the record type's name. If the needed type is absent,
   ask a model administrator about the permitted children.
3. Where an availability action is offered, use it only to change whether the record is
   available under that model's rule. It does not delete the record.
```

### guide/use/change-how-refiroo-looks.md

Old:

```markdown
1. Open **All settings** from your account menu, then **Appearance** under **You**.
   On a phone, open **Settings: …** to reach the settings navigation.
2. Under **Theme**, choose **Normal** or **Website purple** for the colours. Under **Light
   or dark**, choose **System**, **Light** or **Dark**. System follows the device. Both themes
   work in either mode. The page changes immediately; there is no Save button.
3. Under **Table density**, choose **Comfortable** for more space or **Compact** for more
   rows. If one table does not change, open its **Display** menu: its own density overrides
   this default. Choose Default there to use the browser preference again.
4. Under **Type colours**, choose **B: magenta and olive** or **A: plum and gold**. Read the
   record-type labels as well as colours when identifying records.
5. Under **Edit pencil**, choose **On hover and focus** or **Always, faintly**. On a touch
   screen, editable fields show their pencils regardless of this choice.
```

New:

```markdown
1. Open **All settings** from your account menu, then **Appearance** under **You**.
   On a phone, open **Settings: …** to reach the settings navigation.
2. Under **Theme**, choose **Current**, **Hearth**, **Studio**, **Instrument** or **Website purple** for the colours, typography and frame. Under **Light
   or dark**, choose **System**, **Light** or **Dark**. System follows the device. Every theme
   works in either mode. The page changes immediately; there is no Save button.
3. Under **Table density**, choose **Comfortable** for more space or **Compact** for more
   rows. If one table does not change, open its **Display** menu: its own density overrides
   this default. Choose Default there to use the browser preference again.
4. Under **Type colours**, choose **B: magenta and olive** or **A: plum and gold**. Read the
   record-type labels as well as colours when identifying records.
5. Under **Edit pencil**, choose **On hover and focus** or **Always, faintly**. On a touch
   screen, editable fields show their pencils regardless of this choice.
```

### guide/use/correct-a-record.md

Old:

```markdown
1. Open an application in the current workspace and [find the record](/docs/guide/use/find-records/).
   Check its heading and hierarchy path before editing.
2. Choose **Live** for a correction that should take effect immediately. Check the green
   **Live** banner. To prepare work for later publication, [open a change set
   first](/docs/guide/use/prepare-and-publish-a-change-set/), then check its name in the orange banner.
3. Select the value you need to correct in the heading or a details panel. An editor opens for
   that field. Enter the verified replacement using the control shown: text, number, date or
   Yes/No. Where **Set null** is offered, it stores an explicit null value. To make an optional
   field **Not set** instead, cancel this edit and use its remove-value button and confirmation.
4. Choose **Save**. On success, the editor closes and the saved value appears. Check it before
   leaving. Choose **Cancel** instead to abandon the correction.
```

New:

```markdown
1. Open an application in the current workspace and [find the record](/docs/guide/use/find-records/).
   Check its heading and hierarchy path before editing.
2. Choose **Live** for a correction that should take effect immediately. Check the green
   **Live** banner. To prepare work for later publication, [open a change set
   first](/docs/guide/use/prepare-and-publish-a-change-set/), then check its name in the orange banner.
3. Select the value you need to correct in the heading or a details panel. An editor opens for
   that field where the value stands. Enter the verified replacement using the text, number or date control. A Yes/No value is a switch that saves as soon as you change it. Where **No value** is offered, it stores an explicit cleared value. To make an optional field **Not set** instead, cancel this edit and use its remove-value button. Removal saves immediately and offers **Undo**.
4. Choose **Save**. On success, the editor closes and the saved value appears. Check it before
   leaving. The save notice offers **Undo** for a name or a field that had a value before. Choose **Cancel** instead to abandon an unsaved correction.
```

Old:

```markdown
1. Open the **…** menu in the record’s header and choose **Edit record**.
   The record’s ID and version are under **Details**.
   The **Edit object** form opens with the current values.
2. Correct the fields you need. **Name** identifies the record; the other fields describe it.
   Check each field's label rather than assuming similarly named fields change together.
3. Leave **Parent** selected as it is unless you intend to move the record. To move it, search
   for and select the intended parent, checking its path to distinguish matching names.
4. Scroll through the form and choose **Save changes**. On success, the form closes and the
   record page shows the result. If a message identifies an invalid or missing value, correct
   it and save again. Choose **Cancel** to leave without saving the form.
```

New:

```markdown
1. Open the **…** menu in the record’s header and choose **Edit record**.
   The record’s ID and version are under **Details**.
   The form is titled with the record's name and opens beside the page on a desktop, with the current values.
2. Correct the fields you need. **Name** identifies the record; the other fields describe it.
   Check each field's label rather than assuming similarly named fields change together.
3. Keep **In** followed by the current parent's name unless you intend to move the record. Choose **Change** to show **Parent**, then search
   for and select the intended parent, checking its path to distinguish matching names.
4. Scroll through the form and choose **Save changes**. On success, the form closes and the
   record page shows the result. If a message identifies an invalid or missing value, correct
   it and save again. Choose **Cancel** to leave without saving the form.
```

### guide/use/delete-a-record.md

Old:

```markdown
1. Open the record and check its workspace and Live or change-set band. Open **⋯** and choose
   **Delete record**. You need permission for the record and dependants the deletion removes.
2. Read **Delete …?**. Choose **Delete** to request removal. If it has dependants or
   relationships, refiroo shows their impact before another confirmation.
3. Review the record count, dependent records with their types, **Relationships to remove**
   and the count of connections leading to independent records. Children and owned dependants
   go with the record, including owned records in another application. Independent records
   and their hierarchies remain.
4. Choose **Confirm deletion** only if that is the intended impact. Cancel to leave it in place.
   If there are no dependants, the first Delete can complete the removal.
5. After success, the list opens. In Live the removal is immediate; in a change set it stays
   proposed until publication. Earlier publications and history are not erased.

If someone changes the record or adds a dependant before confirmation, the stale deletion
is refused. Choose **Retry** to obtain the current record, then request deletion and review
the fresh impact. Retry does not silently confirm a larger cascade.
```

New:

```markdown
1. Open the record and check its workspace and Live or change-set band. Open **⋯** and choose
   **Delete record**. You need permission for the record and dependants the deletion removes.
2. Read **Delete …?**. Wait while **Checking what deleting it would take…** is shown. Nothing is deleted while refiroo reads the impact. If that read fails, choose **Retry** after resolving the stated problem, or **Cancel** to leave it.
3. Review the counts of records and relationships removed. Dependants are named with their types, up to eight names followed by **and N more** for a longer list. Children and owned dependants
   go with the record, including owned records in another application. Independent records
   and their hierarchies remain.
4. Confirm once, only when that is the intended impact. The button says **Delete N records** when dependants are included, or **Delete** followed by the record type's name for a single record. **Cancel** leaves everything in place.
5. After success, the list opens. In Live the removal is immediate; in a change set it stays
   proposed until publication. Earlier publications and history are not erased.

If someone changes the record or adds a dependant before confirmation, the stale deletion
is refused. The confirmation refreshes the impact and says **The record changed after this was shown**. Review the new impact before confirming again; it does not silently delete a larger set. If the refresh fails, resolve that error before proceeding.
```

### guide/use/fill-in-a-relation-matrix.md

Old:

```markdown
1. Open the intended **None** cell. Check the row and column in the heading and the message
   that no related record exists yet.
2. Choose **Create** followed by the related type's name, where offered. The form identifies
   the row and column under **For** and **under**.
3. Check **Name**, which identifies the new record. Review the proposed name rather than
   treating it as the field content. Under **Goes in**, check where it will belong. The relationship's rules can fix a group;
   otherwise refiroo selects the group already holding the most records used by this view
   in this column. A tie leaves the choice open. An unused group is never selected just
   because it is the only one. Use **Search places…** to choose another offered group.
4. Fill the type's content fields. Set any checkbox or field that determines whether it counts
   according to the legend. Fill **Attributes of the relationship**, if shown: these describe
   the new connection rather than the record itself. Choose the form's **Create** action. On success, the dialog closes
   and the cell refreshes; check its state and displayed content.
5. Use **Back** to abandon the creation form and return to the cell, then **Close** to leave
   without creating anything. If creation is refused, correct the named problem before retrying.
```

New:

```markdown
1. Open the intended **None** cell. Check the row and column in the heading and the message
   that no related record exists yet.
2. Choose **Create** followed by the related type's name, where offered. The form identifies
   the row and column under **For** and **under**.
3. Check **Name**, which identifies the new record. Review the proposed name rather than
   treating it as the field content. Under **Goes in**, check where it will belong. The relationship's rules can fix a group;
   otherwise refiroo selects the group already holding the most records used by this view
   in this column. A tie leaves the choice open. An unused group is never selected just
   because it is the only one. Use **Search places…** to choose another offered group.
4. Fill the type's content fields. Set any checkbox or field that determines whether it counts
   according to the legend. Fill **Attributes of the relationship**, if shown: these describe
   the new connection rather than the record itself. Choose the form's **Add** action followed by the cell type's name. On success, the dialog closes
   and the cell refreshes; check its state and displayed content.
5. Use **Back** to abandon the creation form and return to the cell, then **Close** to leave
   without creating anything. If creation is refused, correct the named problem before retrying.
```

### guide/use/find-records.md

Old:

```markdown
1. On Home, find the workspace you need under **Your workspaces**. Choose its name or tile
   to open its page, then choose an application. An application link on its card opens it directly.
2. Check **Workspace** in the sidebar. If it names a different workspace, select the intended
   one before searching: a record with the same name elsewhere may hold different data.
3. Choose the collection you need under **Collections**. In an application with more than
   ten sidebar entries, type part of its name in **Find a list** to narrow the entries across
   all groups. Choose a result, or press **Enter** to open the first match. **Esc** clears
   the box and restores the groups' previous folds. If **No list matches** appears, shorten
   or clear the text. This finds list names, not records; see
   [Applications](/docs/use/applications/#find-a-list-in-the-sidebar) for the sidebar's counts
   and groups. The collection's heading identifies the list. Available collections and their
   labels depend on your workspace's model.
4. Choose **Live** at the top to search current data. Check the green **Live** banner. To
   inspect proposed or previously published data, open that change set or publication instead;
   check the context before interpreting the results.
```

New:

```markdown
1. On Home, find the workspace you need under **Your workspaces**. Choose its name or tile
   to open its page, then choose an application. An application link on its card opens it directly.
2. Check **Workspace** in the sidebar. If it names a different workspace, select the intended
   one before searching: a record with the same name elsewhere may hold different data.
3. Choose the collection you need under **Collections**. To find a list by name, use the search above the page and choose a result under **Lists**. Press ⌘K on a Mac or Ctrl+K elsewhere to focus search. See [Applications](/docs/use/applications/#find-a-list-in-the-sidebar) for lists and places in search. The collection's heading identifies the list. Available collections and their
   labels depend on your workspace's model.
4. Choose **Live** at the top to search current data. Check the green **Live** banner. To
   inspect proposed or previously published data, open that change set or publication instead;
   check the context before interpreting the results.
```

Old:

```markdown
1. To search names across the workspace, use **Find any record** in the top bar or **Find a
   record** on the workspace’s page. Check the list and path beside a result; use the arrow
   keys and Enter to open one in **Live**. To stay in a change set or publication, or search
   just this collection, type all or part of the record’s name in the search box above the list. Wait for the results
   to update. Use a shorter part of the name if you are unsure of its spelling.
2. Check the result names and identifying fields before opening one. Several records may have
   similar names; a number, date or related record can distinguish them.
3. If the record is missing, check the workspace, application and context first. Clear filters
   that may exclude it. Clear the search text to see the list without that search. If the list
   reports a loading failure, use its retry control rather than treating it as an empty result.
```

New:

```markdown
1. To search names across the workspace, use **Find a record in this workspace** above the page or **Find a
   record** on the workspace’s page. Check the list and path beside a result; use the arrow
   keys and Enter to open one in **Live**. To stay in a change set or publication, or search
   just this collection, type all or part of the record’s name in the search box above the list. Wait for the results
   to update. Use a shorter part of the name if you are unsure of its spelling.
2. Check the result names and identifying fields before opening one. Several records may have
   similar names; a number, date or related record can distinguish them.
3. If the record is missing, check the workspace, application and context first. Clear filters
   that may exclude it. Clear the search text to see the list without that search. If the list
   reports a loading failure, use its retry control rather than treating it as an empty result.
```

Old:

```markdown
1. Choose the result's name. Its page opens with a heading and identifying fields. Check the
   path above the heading to confirm its place in the hierarchy, especially if names repeat.
2. Read the fields in the heading and details panels. The labels depend on the record type.
   An unset value differs from zero or No; see [Records](/docs/use/records/#what-a-record-holds)
   if you need to interpret a field.
3. Read the relationship sections for connected records. Scroll down to find further sections.
   **No relationships yet** means that section has no connections. If a panel reports an error,
   retry that panel; the error does not mean there are no related records.
4. Choose **←** and the list’s name above the title when finished. Your search, filters, sort and position are preserved,
   so you can inspect the next result. To make a correction, follow
   [Correct a record](/docs/guide/use/correct-a-record/).
```

New:

```markdown
1. Choose the result's name. On a desktop, the record opens beside its list with a heading and identifying fields. Choose **Expand to full page** for the full record page. On a phone, it opens the page directly. Check the
   path above the heading to confirm its place in the hierarchy, especially if names repeat.
2. Read the fields in the heading and details panels. The labels depend on the record type.
   An unset value differs from zero or No; see [Records](/docs/use/records/#what-a-record-holds)
   if you need to interpret a field.
3. Read the relationship sections for connected records. Scroll down to find further sections.
   **No relationships yet** means that section has no connections. If a panel reports an error,
   retry that panel; the error does not mean there are no related records.
4. Choose **←** and the list’s name above the title when finished. Your search, filters, sort and position are preserved,
   so you can inspect the next result. To make a correction, follow
   [Correct a record](/docs/guide/use/correct-a-record/).
```

### guide/use/import-a-file.md

Old:

```markdown
1. Open the intended workspace and collection. Choose **Workspace actions › Import**. To
   choose another destination, open **Settings › This instance › Jobs › New import** and
   choose the workspace and **Load into** context.
2. Choose **File**. The chooser accepts Excel workbooks, CSV and supported technical export
   files. Choose the stored **Profile** for an ordinary workbook or CSV, or **None** for a
   file exported by refiroo. Read any profile problems before continuing. For an exported CSV,
   keep the protective single quotes added to formula-like text. With **None**, import removes
   exactly one such quote from names and text fields; an unchanged export changes nothing.
   XLSX is unaffected. See [CSV text rules](/docs/use/importing-and-exporting/#text-in-csv-files).
3. Under **Rows that cannot load**, choose **Load the rows that can load** or **Load nothing
   unless every row loads**. Under **Records the file finds**, decide whether to update or
   refuse them. For an export, **Only if unchanged since the export** protects newer work;
   **Update them anyway** deliberately relaxes that protection.
4. If the file names another workspace's records, choose **Load them as this workspace's own**
   for separate destination records, or **Refuse them**. Check this choice before continuing.
5. Choose **Preview**. The job page opens while the file is read. Check its context, counts,
   column report, **How the file is read** where shown, and refused rows. Each failing cell identifies its column and reason.
   If only part of a large file was tried, its sample is not a promise about every row.
6. Choose **Load the file**, or **Cancel import** if the result is wrong. Loading checks
   current data and can refuse rows that passed preview. Read the final applied and refused counts.
7. Correct refused rows in the file and import it again. Resend the whole file: rows already
   loaded should be unchanged when their values and matching rules are unchanged.
```

New:

```markdown
1. Open the intended workspace and collection. Choose **Workspace actions › Import**. To
   choose another destination, open **Settings › This instance › Jobs › New import** and
   choose the workspace and **Load into** context.
2. Choose **File**, or drop the file onto that field. The chooser accepts Excel workbooks, CSV and supported technical export
   files. After choosing the file, check **Profile**: refiroo selects it when exactly one valid profile fits. You may choose **None** or another fitting profile. A JSON Lines file takes none; CSV offers profiles with CSV settings or one source; a workbook offers any valid profile for this workspace's model. Invalid profiles and other models' profiles are omitted. Use **None** for a file exported by refiroo. Read any profile problems before continuing. For an exported CSV,
   keep the protective single quotes added to formula-like text. With **None**, import removes
   exactly one such quote from names and text fields; an unchanged export changes nothing.
   XLSX is unaffected. See [CSV text rules](/docs/use/importing-and-exporting/#text-in-csv-files).
3. Open **Options**. Under **Rows that cannot load**, choose **Load the rows that can load** or **Load nothing
   unless every row loads**. Under **Records the file finds**, decide whether to update or
   refuse them. For an export, **Only if unchanged since the export** protects newer work;
   **Update them anyway** deliberately relaxes that protection.
4. If the file names another workspace's records, choose **Load them as this workspace's own**
   for separate destination records, or **Refuse them**. Check this choice before continuing.
5. Choose **Preview**. The job page opens while the file is read. Check its context, counts,
   column report, **How the file is read** where shown, and refused rows. Each failing cell identifies its column and reason.
   If only part of a large file was tried, its sample is not a promise about every row.
6. Choose **Load the file**, or **Cancel import** if the result is wrong. Loading checks
   current data and can refuse rows that passed preview. Read the final applied and refused counts.
7. Correct refused rows in the file and import it again. Resend the whole file: rows already
   loaded should be unchanged when their values and matching rules are unchanged.
```

### guide/use/load-a-workbook-with-the-assistant.md

Old:

```markdown
1. Open an application in the current workspace and check that it is writable. Open the
   workspace's **⋯** menu and choose **Import…**. When the assistant is offered, **Load a
   workbook** opens first. To use a known manual import instead, choose **Import without the
   assistant…** and follow [Import a file](/docs/guide/use/import-a-file/).
2. In **Workbook**, choose one XLSX or CSV file. To follow the illustrated example,
   <a download="Haltestellen_Busbetrieb_Nord.xlsx" href="/docs/downloads/Haltestellen_Busbetrieb_Nord.xlsx">download the example workbook</a>,
   a fictional operator’s stop list from the guide’s reference data.
   Check **Into** names the intended workspace.
   In **Tell the assistant about this file (optional)**, explain the result you need: for an
   update, say how rows correspond to the records already held and what must stay unchanged.
   Read the sending note, then choose **Read the workbook**. If the file exceeds the instance's
   size limit, reduce it or ask the operator about that limit; nothing has been loaded.
3. The task page shows **Working on it** and the steps actually completed. You can leave and
   return from **Settings › Jobs**, or choose **Stop**. A fitting saved profile can prepare
   the file without starting AI; the page then follows that saved layout.
4. Read **The assistant’s proposal** and **What the load does**. Check the totals for new
   records, existing records matched, new relationships, refused items and rows read. New
   relationships include the links of new records to their parents; the summary says how many
   of those links it includes. Open each
   type's row to inspect example records, their values, relationships and source cells. Read
   **One name twice in one type** if shown, and expand **Where each part of the file goes**.
   Check **Show the model change**, **Checks** and **Columns left out**. Unexpected new records
   instead of matches, unexplained repeated names and omitted filled cells need a correction.
5. Under **Questions**, inspect the assumed choices. Change wrong ones and choose **Answer and
   design again**. For other corrections, use **Tell the assistant what to change** and **Send
   to the assistant**. **Open in the model editor** opens the draft if you need to edit it.
   Close the editor to return. If the draft changed after the check, accepting checks every
   record and relationship again first. Ask for a revised proposal if the shown examples no
   longer describe what you intend.
6. When the proposal matches your intent, choose **Accept and load to change set**. The engine installs the
   model if it changed and loads exactly the checked records and relationships into a new
   change set, as one batch. No assistant turn runs and nothing is published or activated.
   If any item is refused, none of the batch is loaded and its change set is discarded.
   Read the task's reason, then tell the assistant what to correct and review its new proposal.
   A release already installed before a load failure can remain installed.
   A saved-layout task instead shows **What the load would do** and a load button: inspect the
   per-sheet figures, expand changed records, read refused row examples and
   **What confirming does, in this order** before loading. Its button explicitly says when it
   also activates a model; that activation is not undone if the subsequent load fails.
7. On **Loaded into the change set**, compare the actual record and relationship counts with
   the checked result: the same relationships, including parent links, are counted in both. A load
   prepared by the assistant does not save an import profile. Send the next file of the same
   layout to the assistant again.
8. Choose **Review the change set**. Check the actual record and relationship changes, validate,
   obtain any required approval and publish through
   [Prepare and publish a change set](/docs/guide/use/prepare-and-publish-a-change-set/).
   If the change set uses a different model version, review offers **Move** followed by the
   workspace name, the proposed version and **and publish…**. A model administrator with
   publication permission can use this to preview the migration and choose **Migrate and
   publish**. This moves the workspace to that model and publishes the change set together;
   a separate activation first is not required. Follow
   [Migrate a workspace](/docs/guide/model/migrate-a-workspace/) to inspect the preview and
   resolve any blockers or approval requirement. Loaded records reach Live only when published.
```

New:

```markdown
1. Open an application in the current workspace and check that it is writable. Open the
   workspace's **⋯** menu and choose **Import…**. When the assistant is offered, **Load a
   workbook** opens first. To use a known manual import instead, choose **Import without the
   assistant…** and follow [Import a file](/docs/guide/use/import-a-file/).
2. In **Workbook**, choose one XLSX or CSV file, or drop it onto the field. To follow the illustrated example,
   <a download="Haltestellen_Busbetrieb_Nord.xlsx" href="/docs/downloads/Haltestellen_Busbetrieb_Nord.xlsx">download the example workbook</a>,
   a fictional operator’s stop list from the guide’s reference data.
   Check **Into** names the intended workspace.
   In **Tell the assistant about this file (optional)**, explain the result you need: for an
   update, say how rows correspond to the records already held and what must stay unchanged.
   Read the sending note, then choose **Read the workbook**. If the file exceeds the instance's
   size limit, reduce it or ask the operator about that limit; nothing has been loaded.
3. The task page shows **Working on it** and the steps actually completed. You can leave and
   return from **Settings › Jobs**, or choose **Stop**. A fitting saved profile can prepare
   the file without starting AI; the page then follows that saved layout.
4. Read **The assistant’s proposal** and **What the load does**. Check the totals for new
   records, existing records matched, new relationships, refused items and rows read. New
   relationships include the links of new records to their parents; the summary says how many
   of those links it includes. Open each
   type's row to inspect example records, their values, relationships and source cells. Read
   **One name twice in one type** if shown, and expand **Where each part of the file goes**.
   Check **Show the model change**, **Checks** and **Columns left out**. Unexpected new records
   instead of matches, unexplained repeated names and omitted filled cells need a correction.
5. Under **Questions**, inspect the assumed choices. Change wrong ones and choose **Answer and
   design again**. For other corrections, use **Tell the assistant what to change** and **Send
   to the assistant**. **Open in the model editor** opens the draft if you need to edit it.
   Close the editor to return. If the draft changed after the check, accepting checks every
   record and relationship again first. Ask for a revised proposal if the shown examples no
   longer describe what you intend.
6. When the proposal matches your intent, choose **Accept and load to change set**. The engine installs the
   model if it changed and loads exactly the checked records and relationships into a new
   change set, as one batch. No assistant turn runs and nothing is published or activated.
   If any item is refused, none of the batch is loaded and its change set is discarded.
   Read the task's reason, then tell the assistant what to correct and review its new proposal.
   A release already installed before a load failure can remain installed.
   A saved-layout task instead shows **What the load would do** and a load button: inspect the
   per-sheet figures, expand changed records, read refused row examples and
   **What confirming does, in this order** before loading. Its button explicitly says when it
   also activates a model; that activation is not undone if the subsequent load fails.
7. On **Loaded into the change set**, compare the actual record and relationship counts with
   the checked result: the same relationships, including parent links, are counted in both. A load
   prepared by the assistant does not save an import profile. Send the next file of the same
   layout to the assistant again.
8. Choose **Review the change set**. Check the actual record and relationship changes, validate,
   obtain any required approval and publish through
   [Prepare and publish a change set](/docs/guide/use/prepare-and-publish-a-change-set/).
   If the change set uses a different model version, review offers **Move** followed by the
   workspace name, the proposed version and **and publish…**. A model administrator with
   publication permission can use this to preview the migration and choose **Migrate and
   publish**. This moves the workspace to that model and publishes the change set together;
   a separate activation first is not required. Follow
   [Migrate a workspace](/docs/guide/model/migrate-a-workspace/) to inspect the preview and
   resolve any blockers or approval requirement. Loaded records reach Live only when published.
```

### guide/use/map-codes-between-systems.md

Old:

```markdown
1. Choose **Map** on an unmapped row or **Change** on a filled row. **Change mapping** opens
   with the source name in its heading and the current targets, or **Not mapped**, under
   **Currently**. Check these before searching.
2. Search for the intended target and inspect its identifying fields. Select its radio button.
   If nothing matches, shorten the search and check the model's candidate rules. Do not select
   a similar name merely to fill the row.
3. Choose **Save mapping**. This sets the row to the selected target, replacing any previous
   targets, including all targets of an ambiguous row. Check the refreshed target and state.
   If the row no longer matches the active state filter, switch to **All** and find it again.
4. Choose **Cancel** if no correction is needed. Where **Save and next** is offered, it saves
   this choice and opens the next row; check that new source before choosing again.
```

New:

```markdown
1. Choose **Map** on an unmapped row or **Change** on a filled row. **Change mapping** opens
   with the source name in its heading and the current targets, or **Not mapped**, under
   **Currently**. Check these before searching.
2. Search for the intended target and inspect its identifying fields. Select its radio button.
   If nothing matches, shorten the search and check the model's candidate rules. Do not select
   a similar name merely to fill the row.
3. Choose **Save**. This sets the row to the selected target, replacing any previous
   targets, including all targets of an ambiguous row. Check the refreshed target and state.
   If the row no longer matches the active state filter, switch to **All** and find it again.
4. Choose **Cancel** if no correction is needed. Where **Save and next** is offered, it saves
   this choice and opens the next row; check that new source before choosing again.
```

Old:

```markdown
1. Search carefully first. If a new record is needed, choose **Create new** followed by its
   type name. The target creation form opens.
2. Check its application and parent where offered, then fill **Name** and the required fields.
   Choose **Create**, or **Cancel** to return without creating a target.
3. After creation, review the selected target in the mapping dialog and choose **Save mapping**.
   Creating a record does not itself finish the mapping. If you cancel now, the new record remains.
```

New:

```markdown
1. Search carefully first. If a new record is needed, choose **Create new** followed by its
   type name. The target creation form opens.
2. Check its application and parent where offered, then fill **Name** and the required fields.
   Choose **Add** followed by the target type's name, or **Cancel** to return without creating a target.
3. After creation, review the selected target in the mapping dialog and choose **Save**.
   Creating a record does not itself finish the mapping. If you cancel now, the new record remains.
```

Old:

```markdown
1. Choose **Change** on the row and review **Currently**.
2. Choose **Remove mapping** where offered. This clears the row's mapping and keeps the source
   and target records. Check **Unmapped**, using **All** if your previous filter hides the row.
3. If the dialog says the mapping is required, choose an allowed replacement instead of clearing
   it. **Cancel** keeps the current mapping.
```

New:

```markdown
1. Choose **Change** on the row and review **Currently**.
2. Choose **Remove mapping** inside the form where offered. This clears the row's mapping and keeps the source
   and target records. Check **Unmapped**, using **All** if your previous filter hides the row.
3. If the dialog says the mapping is required, choose an allowed replacement instead of clearing
   it. **Cancel** keeps the current mapping.
```

### guide/use/prepare-and-publish-a-change-set.md

Old:

```markdown
1. Open an application in the current workspace. Check **Workspace** in the sidebar, then
   choose **Change sets** at the top. The list identifies existing change sets by name and
   shows their versions, starting data and creators.
2. To continue existing work, find its name and choose **Open change set**. **Changes in this
   change set** opens first. Choose **See the data with these changes** to reach its lists,
   and check the name in the band before editing. Opening a change set does not publish it.
3. To start separate work, choose **Start from current live data**. Enter a **Change set name**
   that helps other people recognise the work. If **Model version** appears, keep the active
   version for ordinary data corrections; coordinate a different choice with a model administrator.
4. Choose **Create change set**. The new set opens with a copy of the current live data.
   If creation is refused, read the message and resolve the named problem before retrying.
   Choose **Cancel** if you do not intend to create it.
```

New:

```markdown
1. Open an application in the current workspace. Check **Workspace** in the sidebar, then
   choose **Change sets** at the top. The list identifies existing change sets by name and
   shows their versions, starting data and creators.
2. To continue existing work, find its name and choose **Open change set**. **Changes in this
   change set** opens first. Choose **See the data with these changes** to reach its lists,
   and check the name in the band before editing. Opening a change set does not publish it.
3. To start separate work, choose **New change set**. Enter a **Name**
   that helps other people recognise the work. **Options** shows the starting point, today's live data. A **Model version** choice appears there when you have Model release access and another release is available. Keep the workspace's version for ordinary corrections; coordinate a different choice with a model administrator.
4. Choose **Start change set**. The new set opens with a copy of the current live data.
   If creation is refused, read the message and resolve the named problem before retrying.
   Choose **Cancel** if you do not intend to create it.
```

Old:

```markdown
1. Choose **Review changes** in the banner. On **Records**, inspect every intended addition,
   change or removal. Expand a row with its arrow to compare the before and after values.
   Check names and paths to confirm that you changed the intended records.
2. Choose **Relationships** and review the connection changes too. If a long review is hard to
   inspect, use **Filter** to narrow it, then remove the restriction to check the remaining work.
   An empty filtered review does not mean the whole proposal is empty.
3. Choose **See the data with these changes** to correct anything unexpected. Save those corrections and
   review again before proceeding.
4. Choose **Validate change set**. If problems are reported, use the named records and reasons
   to correct them in the change set, then validate again. Do not proceed while problems remain.
5. Check for **Change set validation passed**. In the direct publication flow, this enables
   **Publish change set**. Validate again after any further edits.
```

New:

```markdown
1. Choose **Review changes** in the banner. On **Records**, inspect every intended addition,
   change or removal. Expand a row with its arrow to compare the before and after values.
   Check names and paths to confirm that you changed the intended records.
2. Choose **Relationships** and review the connection changes too. If a long review is hard to
   inspect, use **Filter** to narrow it, then remove the restriction to check the remaining work.
   An empty filtered review does not mean the whole proposal is empty.
3. Choose **See the data with these changes** to correct anything unexpected. Save those corrections and
   review again before proceeding.
4. Open **More change set actions** (⋯) and choose **Validate now**. If problems are reported, use the named records and reasons
   to correct them in the change set, then validate again. Do not proceed while problems remain.
5. Check for **Change set validation passed**. You can also go straight to **Publish**, which validates the current proposal before asking for confirmation. After further edits, the next publication attempt checks them again.
```

Old:

```markdown
These steps apply when **Publish change set** is offered. When approval is needed, the banner
instead offers **Submit for publication**. Follow [Approve a change set](/docs/guide/use/approve-a-change-set/)
for submission, corrections and the approver's decision. See
[Inbox and approvals](/docs/use/inbox-and-approvals/) for the rules and notices.

1. Choose **Publish change set**. The **Publish this change set?** confirmation opens.
2. Read the confirmation. Check the proposed version and the current publication it would
   replace. Follow **Review changes** if you need another look. Choose **Cancel** if you are
   not ready; the change set stays available for preparation.
3. To apply the reviewed changes, choose **Publish change set** in the confirmation. Wait for
   the result. Success is reported as **Published as Publication** followed by its number.
   Check the changed records in **Live** and find the resulting snapshot under **Publications**.
4. If publication is refused, read the reported reason. For conflicts, compare the named records
   with **Live** and agree which corrections are needed before changing the proposal. Review
   and validate the revised work before attempting publication again. A conflict or failed
   check publishes nothing; the proposed work remains available.
```

New:

```markdown
These steps apply when **Publish** is offered. When approval is needed, the banner
instead offers **Submit for publication**. Follow [Approve a change set](/docs/guide/use/approve-a-change-set/)
for submission, corrections and the approver's decision. See
[Inbox and approvals](/docs/use/inbox-and-approvals/) for the rules and notices.

1. Choose **Publish**. refiroo checks the proposal first. If it fails, nothing is published; use the reported problems and record links to correct it. A passed check opens **Publish this change set?**.
2. Read the confirmation. It names how many records and relationships become live, explains that unrelated live changes stay, and that a conflicting live edit publishes nothing. Follow **Review changes** if you need another look. Choose **Cancel** if you are
   not ready; the change set stays available for preparation.
3. To apply the reviewed changes, choose **Publish** in the confirmation. Wait for
   the result. Success is reported as **Published as Publication** followed by its number.
   Check the changed records in **Live** and find the resulting snapshot under **Publications**.
4. If publication is refused, read the reported reason. For conflicts, compare the named records
   with **Live** and agree which corrections are needed before changing the proposal. Review
   and validate the revised work before attempting publication again. A conflict or failed
   check publishes nothing; the proposed work remains available.
```

Old:

```markdown
1. Open the change set and check all its proposed changes, including work by colleagues.
   If it is waiting for approval, its submitter or an approver must **Withdraw request** first.
2. Open **More change set actions** and choose **Discard change set**.
3. Read **Discard this change set?**. **Discard change set** removes all staged work in it.
   Choose **Cancel** to keep it. Live records and existing publications stay unchanged.
4. If the action fails, read its reason and refresh the change set before trying again.
   There is no undo for discarded work; a fresh change set does not recover those edits.

```

New:

```markdown
1. Open the change set and check all its proposed changes, including work by colleagues.
   If it is waiting for approval, its submitter or an approver must **Withdraw request** first.
2. Open **More change set actions** and choose **Discard**.
3. Read **Discard this change set?**. **Discard change set** removes all staged work in it.
   Choose **Cancel** to keep it. Live records and existing publications stay unchanged.
4. If the action fails, read its reason and refresh the change set before trying again.
   There is no undo for discarded work; a fresh change set does not recover those edits.

```

### guide/use/prepare-under-the-next-model-version.md

Old:

```markdown
1. When creating a change set, choose **Model version** if a choice is offered. The starting
   records must fit it. A refusal leaves Live unchanged; inspect the named incompatibilities.
2. In an editable change set, use **More change set actions › Change model version** to choose
   a **Target release** where the existing content fits without a conversion. Resolve unsaved
   input before switching. Wait for the new model to load before editing further.
3. If the releases differ, read **This change set uses a different model version**. Ordinary
   publication needs matching releases. **Move this change set to …** instead previews
   converting your proposal to the workspace's release, with no change to Live.
4. Review converted values, changed types, removals and items requiring a fix. Resolve refusals
   and explicitly accept losses before confirming **Move change set**. If the review is stale,
   choose **Preview again**. This move needs background jobs and suitable change-set rights.
5. The alternative **Move … to … and publish…** previews moving the workspace to the proposal's
   release. It needs model-release and publication rights and follows the same approval policy
   as publication. Have the responsible model administrator review it. **Migrate and publish**
   changes the workspace and publishes together, or does neither.
```

New:

```markdown
1. When creating a change set, open **Options**, then choose **Model version** if your Model release access and the available releases offer a choice. The starting
   records must fit it. A refusal leaves Live unchanged; inspect the named incompatibilities.
2. In an editable change set, use **More change set actions › Change model version** to choose
   a **Target release** where the existing content fits without a conversion. Resolve unsaved
   input before switching. Wait for the new model to load before editing further.
3. If the releases differ, read **This change set uses a different model version**. Ordinary
   publication needs matching releases. **Move this change set to …** instead previews
   converting your proposal to the workspace's release, with no change to Live.
4. Review converted values, changed types, removals and items requiring a fix. Resolve refusals
   and explicitly accept losses before confirming **Move change set**. If the review is stale,
   choose **Preview again**. This move needs background jobs and suitable change-set rights.
5. The alternative **Move … to … and publish…** previews moving the workspace to the proposal's
   release. It needs model-release and publication rights and follows the same approval policy
   as publication. Have the responsible model administrator review it. **Migrate and publish**
   changes the workspace and publishes together, or does neither.
```

### guide/use/propose-targets.md

Old:

```markdown
1. Open a mapping grid in the current workspace. Apply search or choose a parent if you want
   only those sources considered. Open **Propose targets**. The dialog counts the unmapped
   sources and states what is sent. If none remain, close it and change the scope if necessary.
2. Under **Into change set**, use the current change set or choose **New change set** and name
   it. Without an open change set, enter **Name of the new change set**. No suggestion writes Live.
3. Choose **Propose**. **Proposing targets…** shows progress. You can **Close** the dialog and
   the job continues; its end is announced. **Stop** ends further work but keeps mappings already
   proposed. If someone changed the change set before the request started, review it and propose
   again against its current state.
4. Read the result counts and warnings. **Left unmapped: no likely target** needs your own
   investigation. **Changed meanwhile, not touched** means someone changed the source while the
   answer was being prepared. A failed or unanswered batch is not a decision that no target exists.
5. When at least one target was proposed, choose **Show proposed** to open the change set's grid with **Proposed** selected. Inspect
   each target, its displayed fields, confidence and reason. On a phone, expand **Why?**.
   Use **Change** and **Save mapping** to replace a wrong target. Its AI mark disappears.
   If no target was proposed, **Show proposed** is absent. Choose **Close** and investigate
   the unmapped sources manually.
6. Review the whole change set, including any earlier work in it. Follow
   [Prepare and publish a change set](/docs/guide/use/prepare-and-publish-a-change-set/) to validate,
   obtain any required approval and publish. The published history says which mappings were
   proposed by AI and who published them.
```

New:

```markdown
1. Open a mapping grid in the current workspace. Apply search or choose a parent if you want
   only those sources considered. Open **Propose targets**. The dialog counts the unmapped
   sources and states what is sent. If none remain, close it and change the scope if necessary.
2. Under **Into change set**, use the current change set or choose **New change set** and name
   it. Without an open change set, enter **Name of the new change set**. No suggestion writes Live.
3. Choose **Propose**. **Proposing targets…** shows progress. You can **Close** the dialog and
   the job continues; its end is announced. **Stop** ends further work but keeps mappings already
   proposed. If someone changed the change set before the request started, review it and propose
   again against its current state.
4. Read the result counts and warnings. **Left unmapped: no likely target** needs your own
   investigation. **Changed meanwhile, not touched** means someone changed the source while the
   answer was being prepared. A failed or unanswered batch is not a decision that no target exists.
5. When at least one target was proposed, choose **Show proposed** to open the change set's grid with **Proposed** selected. Inspect
   each target, its displayed fields, confidence and reason. On a phone, expand **Why?**.
   Use **Change** and **Save** to replace a wrong target. Its AI mark disappears.
   If no target was proposed, **Show proposed** is absent. Choose **Close** and investigate
   the unmapped sources manually.
6. Review the whole change set, including any earlier work in it. Follow
   [Prepare and publish a change set](/docs/guide/use/prepare-and-publish-a-change-set/) to validate,
   obtain any required approval and publish. The published history says which mappings were
   proposed by AI and who published them.
```

### guide/use/relate-records.md

Old:

```markdown
1. Choose **Add relationship**, or **Set** followed by the relationship name when the empty
   section permits just one. The connection dialog opens.
2. Check **Relationship**, including its direction. **Outgoing** reads the relationship from
   this record towards the chosen one; **incoming** reads it from the other end. If several
   choices are offered, select the intended meaning before searching.
3. Under **Object**, type part of the related record's name or a searchable field. Read any
   hint explaining which records are offered. Select a result, checking its path. Typing alone
   leaves **Nothing selected** and does not enable saving.
4. Fill any fields carried by the relationship. These describe the connection, rather than
   changing the other record's fields.
5. Choose **Create**, or **Set** in the single-connection dialog. On success the dialog closes;
   check that the connected record appears in the section. **Cancel** abandons the connection;
   if asked to discard unsaved changes, confirm only if that is what you intend.
```

New:

```markdown
1. Choose **Add relationship**, or **Set** followed by the relationship name when the empty
   section permits just one. The connection form opens beside the page on a desktop.
2. Where the relationship is known, the form says **Add a** followed by the related type **to** this record (or **Add an** where appropriate). Read the relationship named beneath it. If several choices are offered, choose the intended type and relationship under **What to add** before searching.
3. Under the related record type's name, type part of the related record's name or a searchable field. Read any
   hint explaining which records are offered. Select a result, checking its path. Typing alone
   leaves **Nothing selected** and does not enable saving.
4. Fill any fields carried by the relationship. These describe the connection, rather than
   changing the other record's fields.
5. Choose **Add** followed by the related type's name, or **Set** in the single-connection form. On success the dialog closes;
   check that the connected record appears in the section. **Cancel** abandons the connection;
   if asked to discard unsaved changes, confirm only if that is what you intend.
```

Old:

```markdown
1. In a section that allows one related record, choose its **Change** action. Read **Now:**
   to confirm the connection you intend to replace.
2. Search and select the replacement under **Object**. Check its identifying fields and path.
   The currently connected record is not offered as its own replacement.
3. Choose **Change**. The replacement is saved together; check the section's new entry.
   Choose **Cancel** to keep the existing connection.
4. If the dialog says the relationship changed after the list was read, close it and review
   the refreshed section. Reopen **Change** only if replacement is still appropriate.
```

New:

```markdown
1. In a section that allows one related record, choose its **Change** action. Read **Now:**
   to confirm the connection you intend to replace.
2. Search and select the replacement under the related type's name. Check its identifying fields and path.
   The currently connected record is not offered as its own replacement.
3. Choose **Change**. The replacement is saved together; check the section's new entry.
   Choose **Cancel** to keep the existing connection.
4. If the dialog says the relationship changed after the list was read, close it and review
   the refreshed section. Reopen **Change** only if replacement is still appropriate.
```

Old:

```markdown
1. Find the exact relationship row and choose its delete button. Check both record names
   first, especially where a section contains several connections.
2. Read **Delete relationship?**. The connected records remain; only this connection is removed.
3. Choose **Delete relationship** to proceed, or **Cancel** to keep it. Check the refreshed
   section after success. If removal is refused because the connection is required, keep it
   and review the intended correction; use a replacement where allowed.
```

New:

```markdown
1. Find the exact relationship row and check both record names, especially where a section contains several connections.
2. Choose **Remove relationship**. It removes the connection immediately, without a confirmation; both records remain.
3. Check the refreshed section. The removal notice offers **Undo** to create the connection again. If removal is refused because it is required, review the intended correction and use a replacement where allowed.
```

Old:

```markdown
1. Choose that section's add action. Check the new record form and its already supplied
   connection to the source record.
2. Under **Parent**, search and select the intended container where requested. Check the
   selected path; search text alone does not select it.
3. Fill **Name** and the type's other fields. Set any field that determines whether the record
   counts as current according to the model's rule.
4. Choose **Create** and check the new entry in the original section. Correct any reported
   missing values or duplicate before retrying. **Cancel** leaves without creating the record.
```

New:

```markdown
1. Choose that section's add action. Check the new record form and its already supplied
   connection to the source record.
2. Under **Parent**, search and select the intended container where requested. Check the
   selected path; search text alone does not select it.
3. Fill **Name** and the type's other fields. Set any field that determines whether the record
   counts as current according to the model's rule.
4. Choose **Add** followed by the new record type's name and check the new entry in the original section. Correct any reported
   missing values or duplicate before retrying. **Cancel** leaves without creating the record.
```

### guide/use/review-what-a-change-set-changes.md

Old:

```markdown
1. From **Change sets**, choose **Open change set** to open **Changes in this change set**.
   If you are already browsing its data, choose **Review changes** in the amber band. Confirm
   its name; open **Details** for its source. If it started from a publication, the earlier values come from that publication,
   not today's Live.
2. Under **Records**, filter by change kind or record type. Open a row to read before/after
   values and paths. A moved record names both parents. A type-change filter can match either
   its old or new type, so check the difference itself.
3. Open **Relationships** and inspect additions, changes and removals separately. A record
   review alone does not account for every changed connection.
4. Scroll or jump through the lists. The address retains the tab, filters and position so
   you can return to the same part of the review.
5. Choose **See the data with these changes** to return to editing for corrections, then
   choose **Validate change set**. Resolve its named
   problems and validate the new version again before publishing or submitting.
```

New:

```markdown
1. From **Change sets**, choose **Open change set** to open **Changes in this change set**.
   If you are already browsing its data, choose **Review changes** in the amber band. Confirm
   its name; open **Details** for its source. If it started from a publication, the earlier values come from that publication,
   not today's Live.
2. Under **Records**, filter by change kind or record type. Open a row to read before/after
   values and paths. A moved record names both parents. A type-change filter can match either
   its old or new type, so check the difference itself.
3. Open **Relationships** and inspect additions, changes and removals separately. A record
   review alone does not account for every changed connection.
4. Scroll or jump through the lists. The address retains the tab, filters and position so
   you can return to the same part of the review.
5. Choose **See the data with these changes** to return to editing for corrections, then
   choose **More change set actions › Validate now**. You can also choose **Publish**, which checks before confirmation. Resolve its named
   problems and validate the new version again before publishing or submitting.
```

### journeys/work-with-an-assistant.md

Old:

```markdown
Use **Show proposed** and the **Proposed** filter to review the mappings, confidence and reasons.
A low-confidence or missing answer leaves its source unmapped; a source changed meanwhile is
left alone and counted. **Stop** keeps proposals already saved. Correct a target with **Change**
and **Save mapping**; the replaced mapping loses its AI mark. Validate and publish through the
workspace's normal approval process. Live stays unchanged until publication, and published
history records the AI origin and publisher. See [Mapping grids](/docs/use/mapping-grids/#targets-proposed-by-ai).
```

New:

```markdown
Use **Show proposed** and the **Proposed** filter to review the mappings, confidence and reasons.
A low-confidence or missing answer leaves its source unmapped; a source changed meanwhile is
left alone and counted. **Stop** keeps proposals already saved. Correct a target with **Change**
and **Save**; the replaced mapping loses its AI mark. Validate and publish through the
workspace's normal approval process. Live stays unchanged until publication, and published
history records the AI origin and publisher. See [Mapping grids](/docs/use/mapping-grids/#targets-proposed-by-ai).
```

### model/managing-workspaces.md

Old:

```markdown
Open a workspace row to inspect **Overview**, **Access**, **Approval** and **Activity**.
**Open workspace** returns to its data; **Activity** shows [history across records](/docs/use/history/).
The other actions require administrative permissions: **New workspace**, **Edit model**,
**Copy or move data…**, **Rename…** and **Retire…** change the workspace or its configuration.
Opening the page does not perform them.
```

New:

```markdown
Open a workspace row to inspect **Overview**, **Access**, **Approval** and **Activity**.
**Open workspace** returns to its data; **Activity** shows [history across records](/docs/use/history/).
The other actions require administrative permissions: **New workspace**, **Edit model**,
**Copy or move data…** and **Retire…** change the workspace or its configuration.
Opening the page does not perform them.
```

Old:

```markdown
1. Open **Settings › Workspaces**. Search the list before creating another dataset. Active
   workspaces appear first, then retired ones.
2. Choose **New workspace**. Complete its name and key. The key forms its address; choose it
   carefully. Use the default workspace's model, or choose another usable installed release.
3. Confirm creation and check the new workspace's **Overview**, model and applications. It has
   its own data; creation copies no records from the default workspace. Read any refusal before
   retrying. Cancel leaves the list unchanged.
4. To change its displayed name later, choose **Rename…**, enter the new name and save.
   Renaming does not change its key or create a new dataset.
```

New:

```markdown
1. Open **Settings › Workspaces**. Search the list before creating another dataset. Active
   workspaces appear first, then retired ones.
2. Choose **New workspace**. Complete its name and key. The key forms its address; choose it
   carefully. Use the default workspace's model, or choose another usable installed release.
3. Choose **Add workspace** and check the new workspace's **Overview**, model and applications. It has
   its own data; creation copies no records from the default workspace. Read any refusal before
   retrying. Cancel leaves the list unchanged.
4. To change its displayed name later, select the name where it stands, enter the new name and choose **Save**. The save notice offers **Undo**.
   Renaming does not change its key or create a new dataset.
```

Old:

```markdown
**Cannot be opened** on a workspace whose model language is unsupported needs the offered
model-language repair or operator help; see [Model language versions](/docs/model/model-language-versions/). A missing application
bookmark can instead mean **Not in this model**: open a collection declared by this workspace.
**Rename…** changes the displayed name, with the permanent key retained. A stale save asks you
to review newer state; it does not silently overwrite another administrator's edit.
```

New:

```markdown
**Cannot be opened** on a workspace whose model language is unsupported needs the offered
model-language repair or operator help; see [Model language versions](/docs/model/model-language-versions/). A missing application
bookmark can instead mean **Not in this model**: open a collection declared by this workspace.
Editing the displayed name keeps the permanent key. A stale save asks you
to review newer state; it does not silently overwrite another administrator's edit.
```

### model/the-model-editor.md

Old: none (added passage).

New:

```markdown
A short operation, such as renaming or choosing a value type, opens beneath its control in a small popover. Pick several items there with **Apply**; save a single setting with **Save**. Longer forms and forms needing a preview open beside the page as sheets. Adding uses **Add** followed by the thing's name; moving uses **Move**. Confirmations remain small centred dialogs. The same validation and draft **Undo** apply whichever form is shown.
```

### run/sign-in-and-mail-setup.md

Old: none (added passage).

New:

```markdown
For the layout of outgoing messages, an operator uses [E-mail template](/docs/administer/mail/#e-mail-template). It is separate from the delivery connection: changing the template does not set up SMTP or Microsoft 365.
```

### use/account.md

Old:

```markdown
**Rename …** opens the passkey's **Name** field. Choose **Save** after changing it. **Remove …**
opens a separate confirmation with **Remove passkey**; it does not remove the device's other
passkeys. **New recovery codes…** asks for **Code from the app, or a recovery code**, then
**Make new codes**. Save the replacements: the old recovery codes stop working. Removing the
authenticator app uses **Remove the second factor** and **Remove it**; your recovery codes then
stop working too.
```

New:

```markdown
Select the passkey's name where it stands to edit it. Choose **Save** after changing it; the notice offers **Undo**. **Remove …**
opens a separate confirmation with **Remove passkey**; it does not remove the device's other
passkeys. **New recovery codes…** asks for **Code from the app, or a recovery code**, then
**Rotate recovery codes**. Save the replacements: the old recovery codes stop working. Removing the
authenticator app uses **Remove the second factor** and **Remove it**; your recovery codes then
stop working too.
```

### use/appearance-and-devices.md

Old:

```markdown
| Setting | Choices and effect |
|---|---|
| Theme | **Normal** or **Website purple** changes the application colours. Either works in light or dark mode. |
| Light or dark | **System**, **Light**, **Dark**. System follows your device's light or dark setting. |
| Table density | **Comfortable** or **Compact** sets the default; a table's own Display choice overrides it. |
| Type colours | **B: magenta and olive** or **A: plum and gold**. The palettes differ in their third and fourth colours. |
| Edit pencil | **On hover and focus** or **Always, faintly**. Touch screens always show edit hints. |
```

New:

```markdown
| Setting | Choices and effect |
|---|---|
| Theme | **Current**, **Hearth**, **Studio**, **Instrument** or **Website purple** changes colours, title typeface, corners, type sizes, control height and the arrangement of the frame. Every theme works in light and dark. |
| Light or dark | **System**, **Light**, **Dark**. System follows your device's light or dark setting. |
| Table density | **Comfortable** or **Compact** sets the default; a table's own Display choice overrides it. |
| Type colours | **B: magenta and olive** or **A: plum and gold**. The palettes differ in their third and fourth colours. |
| Edit pencil | **On hover and focus** or **Always, faintly**. Touch screens always show edit hints. |

On a desktop, **Current**, **Hearth** and **Website purple** keep the applications in the top bar and lists in the sidebar. **Studio** puts the applications and lists in one side column beside a raised page. Its search remains above the page and the Live, change-set or publication band stays above the data. **Instrument** puts application tiles, Help, Inbox, Settings and your account in a narrow strip, with lists in the panel beside it. Search stays above the page; the data context appears along the bottom. Pages without search need no top bar in Instrument. On a phone, every theme uses the bar and navigation drawer.

Hearth, Studio and Instrument add short motions when surfaces open. These stop when your device requests reduced motion. A theme changes presentation; it does not change the model, records or permissions.
```

Old:

```markdown
In tables, Up/Down moves row focus. Space toggles a focused selection checkbox; Shift extends
a range. Cmd/Ctrl+A inside a selectable table selects all matching records. Ctrl+Home and
Ctrl+End jump through long lists. These keys apply in their local controls; there is no global
command palette, search shortcut or shortcut-reference screen. Use each list's search: the
browser's Find sees only drawn rows of long lists.
```

New:

```markdown
In tables, Up/Down moves row focus. Space toggles a focused selection checkbox; Shift extends
a range. Cmd/Ctrl+A inside a selectable table selects all matching records. Ctrl+Home and
Ctrl+End jump through long lists. These keys apply in their local controls. Press ⌘K on a Mac or Ctrl+K elsewhere to focus search. On Home it searches record names across your workspaces; within a workspace it also finds lists and places such as Settings under **Go to**. Use refiroo's search: the
browser's Find sees only drawn rows of long lists.
```

Old:

```markdown
Settings groups its pages under **General**, **Administration**, **Data operations**,
**Security** and **Integration**. Your permissions determine which pages and groups appear.
**Jobs** lets you inspect background work; **Import profiles** needs Bulk and import, and
**Copy and move** needs the corresponding permission. A missing navigation entry does not
grant access through a copied address. Ask an administrator about missing permissions.
```

New:

```markdown
Settings groups its pages under **You**, **Workspaces and models**, **People and access**,
**Connections** and **This instance**, with **About** last. Your permissions determine which pages and groups appear.
**Jobs** lets you inspect background work; **Import profiles** needs Bulk and import, and
**Copy and move** needs the corresponding permission. A missing navigation entry does not
grant access through a copied address. Ask an administrator about missing permissions.
```

Old:

```markdown
The initial choices are **Normal**, **System**, **Comfortable**, **B: magenta and olive**
and **On hover and focus**. To return to those defaults, select them again. Clearing this
site's browser storage also loses display preferences, so keep any collection addresses you
need separately. Display preferences do not change your roles or the workspace model.

```

New:

```markdown
The initial choices are **Current**, **System**, **Comfortable**, **B: magenta and olive**
and **On hover and focus**. To return to those defaults, select them again. Clearing this
site's browser storage also loses display preferences, so keep any collection addresses you
need separately. Display preferences do not change your roles or the workspace model.

```

### use/applications.md

Old:

```markdown
Open an application to reach the records and views you need in the current workspace.
Choose a workspace’s name or tile on Home to open its page: it offers record search, applications,
your waiting change sets and the five latest changes. **Edit model** and the workspace’s **⋯**
menu offer the actions and Settings pages your access allows.
Follow [Open an application](/docs/guide/use/open-an-application/) for the steps.
```

New:

```markdown
Open an application to reach the records and views you need in the current workspace.
Choose a workspace’s name or tile on Home to open its page: it offers record search, applications,
your shelf, waiting change sets and recent activity grouped by day. **Edit model** and the workspace’s **⋯**
menu offer the actions and Settings pages your access allows.
Follow [Open an application](/docs/guide/use/open-an-application/) for the steps.
```

Old:

```markdown
Choose an application in the top bar, then a collection in the sidebar. A collection can have
several views, shown as tabs under the list’s title. Changing tabs changes how you inspect the records; it does not
copy them. The model can choose which view opens when you select a collection in the
sidebar or on a group page. That choice may differ from the application's starting view;
use the tabs to switch to another view when needed. **Browse records** offers another route to individual records through their hierarchy. Open it to browse; it starts folded and remembers your choice in this browser.
```

New:

```markdown
Choose an application in the top bar, then a collection in the sidebar. In Studio the applications share the side column with the lists; Instrument puts application tiles in the narrow strip beside the lists. See [Appearance and devices](/docs/use/appearance-and-devices/) for the frame arrangements. A collection can have
several views, shown as tabs under the list’s title. Changing tabs changes how you inspect the records; it does not
copy them. The model can choose which view opens when you select a collection in the
sidebar or on a group page. That choice may differ from the application's starting view;
use the tabs to switch to another view when needed. **Browse records** offers another route to individual records through their hierarchy. Open it to browse; it starts folded and remembers your choice in this browser.
```

Old:

```markdown
When an application has more than ten sidebar entries, **Find a list** appears under
**Collections**. Collections and relation matrices with their own sidebar entry count together,
including entries in folded groups. With ten entries or fewer, this search is not shown.

Type part of a list's name. The search ignores upper and lower case and matches your words
as one phrase within a name, in the order you type them. Reversing the words does not match
the same phrase. Matching letters appear in bold. It searches entries in every group and
those in no group, rather than the names of groups or records. The count beside **Collections**
shows the total, such as **25 lists**, then the matching count, such as **3 of 25**, while you
search. Screen readers announce count changes without interrupting you.

Groups with matches open and show only those entries; groups without matches disappear.
Their fold buttons are unavailable during the search. Choose a result, or press **Enter** in
the box to open the first match. The hint **Enter opens the first match · Esc clears** reminds
you of these keys. If **No list matches** appears, shorten or clear the text. Press **Esc** in
the box to clear it and restore each group's previous fold choice.

**Find any record** in the top bar searches record names across the workspace instead. Results
are grouped by record type and show each record’s place. Use the arrow keys to choose a result and
Enter to open it. Workspace search opens the record in **Live**; use a collection’s own search
to stay in a change set or publication. **Browse records** has no search box of its own. The group page's
**Find a collection or matrix** searches only that group's entries.

```

New:

```markdown
Use the workspace search above the page to find a list by name, including lists in folded groups. Press ⌘K on a Mac or Ctrl+K elsewhere to focus it. Matching lists appear under **Lists**; select one to open its view. **Go to** offers matching places such as Home, Change sets and Settings. The sidebar no longer has a separate list search.

The same search finds record names across the workspace. Results are grouped by record type and show each record's place. Use the arrow keys to choose a record and Enter to open it. Workspace search opens records in **Live**; use a collection's own search to stay in a change set or publication. **Browse records** has no search box of its own. The group page's **Find a collection or matrix** searches only that group's entries.

```

### use/change-sets.md

Old:

```markdown
**Start from current live data** creates the first kind. A publication's menu offers
**Start a change set from this publication** for the second. Neither action changes live data or
creates a publication. See the
[starting instructions](/docs/guide/use/prepare-and-publish-a-change-set/#start-or-open-a-change-set).
```

New:

```markdown
**New change set**, then **Start change set**, creates the first kind. The form asks for a name; **Options** shows its start point and, where your Model release access and installed releases allow a choice, its model version. A publication's menu offers
**Start a change set from this publication** for the second. Neither action changes live data or
creates a publication. See the
[starting instructions](/docs/guide/use/prepare-and-publish-a-change-set/#start-or-open-a-change-set).
```

Old:

```markdown
**Validate change set** checks the complete proposed data against its model, including required
values and relationships, allowed structure and uniqueness rules. Some problems can only be
judged across the whole set of records. Individual successful saves do not replace this check.

Validation changes no live data and creates no publication. Problems identify what needs
attention. A successful check displays **Change set validation passed**. In the direct publication
flow, that check enables **Publish change set** for the validated version. Editing afterwards
requires validation again.
```

New:

```markdown
**Validate now** in **More change set actions** (⋯) checks the complete proposed data against its model, including required
values and relationships, allowed structure and uniqueness rules. Some problems can only be
judged across the whole set of records. Individual successful saves do not replace this check.

Validation changes no live data and creates no publication. Problems identify what needs
attention. A successful check displays **Change set validation passed**. **Publish** also runs validation before opening a confirmation; a separate validation step is optional. A failed check publishes nothing and lists the problems with links to the affected records. After editing, publication checks the new version again.
```

Old:

```markdown
**Discard change set** is on the change-set menu when the set is editable. A pending request
must first leave its submitted state. Discarding is still possible when the change set's model
release differs from the workspace's release. See the
[change-set guide](/docs/guide/use/prepare-and-publish-a-change-set/) for the editing context.
```

New:

```markdown
**Discard** is on the change-set menu when the set is editable. A pending request
must first leave its submitted state. Discarding is still possible when the change set's model
release differs from the workspace's release. See the
[change-set guide](/docs/guide/use/prepare-and-publish-a-change-set/) for the editing context.
```

Old:

```markdown
A submitted change set cannot be edited or moved to another release until its request is
withdrawn by the submitter or an approver. Open work is shared with authorised workers, not
reserved for its creator. **More change set actions** holds discard and version actions;
there is no rename form here.
```

New:

```markdown
A submitted change set cannot be edited or moved to another release until its request is
withdrawn by the submitter or an approver. Open work is shared with authorised workers, not
reserved for its creator. **More change set actions** holds **Validate now**, **Change model version**, **Rename** and **Discard**. **Rename** opens a form for the name; it keeps the proposed data.
```

### use/history.md

Old:

```markdown
The workspace’s page shows its five **Latest changes**. For more activity, where your access
opens workspace management, choose **Settings**, **Workspaces**, the workspace,
then **Activity**. Its **What** choices are **Everything**, **Records**, **Relationships**,
**Change sets** and **Publications**. Entries identify the action, person and time, and can also
name its change set or publication context.
```

New:

```markdown
The workspace’s page shows **What changed**, grouped by day with consecutive repeats folded into a count. For more activity, where your access
opens workspace management, choose **Settings**, **Workspaces**, the workspace,
then **Activity**. Its **What** choices are **Everything**, **Records**, **Relationships**,
**Change sets** and **Publications**. Entries identify the action, person and time, and can also
name its change set or publication context.
```

Old:

```markdown
On [Home](/docs/use/home/), **Your recent changes** gives a short list. **See all your changes**
opens **Your changes**. Choose **Workspace**, **What** and **Period** to narrow it. A person's
linked name can also lead to their changes, within the workspaces you may read.
```

New:

```markdown
On [Home](/docs/use/home/), **Your recent changes** gives a short list. **See all your changes**
opens **Your changes**. Consecutive steps on one model draft fold into one expandable line with their count. Expand it to read the individual steps. Choose **Workspace**, **What** and **Period** to narrow it. A person's
linked name can also lead to their changes, within the workspaces you may read.
```

### use/home.md

Old:

```markdown
Select the refiroo name in the top bar to return to **Home**. It brings together the workspaces
you can read and the work waiting for you.
```

New:

```markdown
Select the refiroo name in the top bar to return to **Home**. It brings together the workspaces
you can read and the work waiting for you. **Waiting for your approval**, where you may approve, and **Your change sets** appear above the workspace cards.
```

Old: none (added passage).

New:

```markdown
## Find a record

Use **Find a record in any workspace** to search record names across every workspace you may browse. Results are grouped by workspace and show the record's type and where it stands. Press ⌘K on a Mac or Ctrl+K elsewhere to focus the search, Up/Down to choose a result and Enter to open it. Escape closes the results. Check the workspace after opening a result.
```

Old:

```markdown
**Your recent changes** lists your five latest actions. **See all your changes** opens the longer list,
with workspace, kind and period filters. See [History](/docs/use/history/) for what those entries mean.
```

New:

```markdown
**Your recent changes** shows your latest actions. Consecutive steps on one model draft fold into one expandable line with their count; expand it to read each step. **See all your changes** opens the longer list,
with workspace, kind and period filters. See [History](/docs/use/history/) for what those entries mean.
```

### use/importing-and-exporting.md

Old:

```markdown
An import profile tells refiroo how sheets and columns become records, names, fields, parents
and relationships, and which values identify existing records. Choose a stored profile for a
CSV or workbook that was not exported by refiroo. Profile setup belongs to
[Workbook onboarding](/docs/model/workbook-onboarding/); a steward can
[load its next version](/docs/guide/use/load-the-next-version-of-a-workbook/).
```

New:

```markdown
An import profile tells refiroo how sheets and columns become records, names, fields, parents
and relationships, and which values identify existing records. Choose the file first, or drop it onto the file field. The form selects a profile when exactly one valid profile fits; you can still choose **None** or another fitting profile. JSON Lines uses none; CSV accepts a profile with CSV settings or a single source, and a workbook accepts any valid profile for this workspace's model. Invalid profiles and profiles for other models are omitted. The three loading-policy choices are under **Options**. Profile setup belongs to
[Workbook onboarding](/docs/model/workbook-onboarding/); a steward can
[load its next version](/docs/guide/use/load-the-next-version-of-a-workbook/).
```

### use/lists-and-filters.md

Old: none (added passage).

New:

```markdown
Use the pin button in the list's header to bring this view to **Your shelf** on the [workspace's page](/docs/use/workspaces/#the-workspaces-page). The shelf stays in this browser.
```

Old:

```markdown
**Not set**, **Null** and **Empty text** distinguish missing, stored null and empty text.
Related-record chips open those records. Opening a record can take you to the application
where it belongs, even if its type was listed in the application you started from.
On phones, **Show all … columns** and **Show fewer columns** control extra columns.
Selecting text does not open or edit a row. Full-text popups close with Escape.
```

New:

```markdown
**Not set**, **Cleared** and **Empty text** distinguish missing, stored null and empty text.
Related-record chips open those records. Opening a record can take you to the application
where it belongs, even if its type was listed in the application you started from.
On phones, **Show all … columns** and **Show fewer columns** control extra columns.
Selecting text does not open or edit a row. Full-text popups close with Escape.
```

### use/mapping-grids.md

Old:

```markdown
Where offered, **Create new** followed by the target type opens a record creation form.
Creating a target and saving its mapping are distinct steps: review the selected target and
finish **Save mapping**. Cancelling the mapping does not undo a target already created.
```

New:

```markdown
Where offered, **Create new** followed by the target type opens a record creation form.
Creating a target and saving its mapping are distinct steps: review the selected target and
finish **Save**. Cancelling the mapping does not undo a target already created.
```

Old:

```markdown
Creating a missing target asks for its application. Parent choices belong to that application;
if no required parent can stand there, creation is refused. Create or select a suitable parent
rather than choosing one from another application. Creating the target selects it in the mapping
form but does not save the mapping: finish **Save mapping** separately.
```

New:

```markdown
Creating a missing target asks for its application. Parent choices belong to that application;
if no required parent can stand there, creation is refused. Create or select a suitable parent
rather than choosing one from another application. Creating the target selects it in the mapping
form but does not save the mapping: finish **Save** separately.
```

Old:

```markdown
Correct a wrong target through **Change** and **Save mapping**, or remove the mapping if allowed.
Changing the target removes its AI mark because the replacement is your choice. Publishing
uses the usual approval and conflict checks. The published relationship's history keeps the
proposal's origin and model, and separately names the person who published it.
```

New:

```markdown
Correct a wrong target through **Change** and **Save**, or remove the mapping if allowed.
Changing the target removes its AI mark because the replacement is your choice. Publishing
uses the usual approval and conflict checks. The published relationship's history keeps the
proposal's origin and model, and separately names the person who published it.
```

### use/records.md

Old: none (added passage).

New:

```markdown
On a desktop, opening a table row shows the record beside its list, keeping your place. Choose **Expand to full page** to open the record's page. On a phone, the row opens the full page directly.
```

Old:

```markdown
**Delete record** on the record menu requests permanent removal. The confirmation describes what
is being removed. If there are dependent records or relationships, refiroo shows their impact
before the additional confirmation:
```

New:

```markdown
**Delete record** on the record menu opens one confirmation. It reads what deletion would remove before offering the delete button; opening it deletes nothing. The impact follows these rules:
```

Old:

```markdown
The impact lists affected records and relationships and gives their counts. Cancelling leaves
everything in place. If the record or the impact changes before confirmation, deletion is refused;
**Retry** obtains the current record so the deletion can be reviewed again. A required connection
cannot simply be removed on its own while leaving a dependant without its owner.
```

New:

```markdown
The confirmation counts the records and relationships removed and names up to eight dependants with their types, followed by **and N more** where needed. Choose **Delete N records** when dependants are included, or **Delete** followed by the type's name for one record. Cancelling leaves everything in place. A failed impact read offers **Retry** and no delete button. If the record or impact changes before deletion, the stale attempt is refused and the refreshed impact must be reviewed and confirmed again. A required connection
cannot simply be removed on its own while leaving a dependant without its owner.
```

Old:

```markdown
Click a value on the record page, or focus it and press Enter, to open its editor. Selecting
text to copy does not start an edit. Choose **Save** or press Enter to save where offered;
Escape cancels. Click an empty field to add a value. An optional value's trash button asks for
confirmation before clearing it. Read-only fields have no editing control.

The header's title and subtitle edit the same way. An empty subtitle offers **Add**.
Open **Details** in the header for the record’s ID, its copy button and version.
**Copy ID** is also in the record’s **⋯** menu. Use **Edit record** in the **⋯** menu
for the form containing all fields. A new record form saves its fields, allowed parent and
required relationships together: complete all required choices before choosing **Create**.
A refusal leaves the invalid record uncreated; correct the named field or connection.
```

New:

```markdown
Click a value on the record page, or focus it and press Enter, to open its editor. Selecting
text to copy does not start an edit. Choose **Save** or press Enter to save where offered;
Escape cancels. The value becomes its field where it stands. Click an empty field to add a value. An editable Yes/No value in the details is a switch: changing it saves immediately. After saving a name or changing a field that already had a value, the save notice offers **Undo**. A field set for the first time has no previous value to restore. An optional value's trash button clears it immediately and offers **Undo** in the notice. Read-only fields have no editing control.

The header's title and subtitle edit the same way. An empty subtitle offers **Add**.
Open **Details** in the header for the record’s ID, its copy button and version.
**Copy ID** is also in the record’s **⋯** menu. Use **Edit record** in the **⋯** menu
for the form containing all fields. A new record form saves its fields, allowed parent and
required relationships together: complete all required choices before choosing **Add** followed by the type's name. Required fields come first; optional fields are under **More fields (n)**, remembered per type in this browser. Missing or wrongly typed values are explained beneath their fields. On a desktop, forms open as sheets beside the page; confirmations stay centred.
A refusal leaves the invalid record uncreated; correct the named field or connection.
```

Old:

```markdown
To clear an optional field, confirm **Remove value** in **Remove …?**. It makes the value unset
and keeps the record. If **Value removed; refresh needed** appears, removal succeeded but the
screen could not refresh. Choose **Retry refresh** and inspect the saved state before trying
another edit.
```

New:

```markdown
To clear an optional field, use its remove-value button. It makes the value **Not set** and keeps the record, without asking for confirmation. The removal notice offers **Undo** to put it back. **No value** in the inline editor instead stores an explicit cleared value; it does not remove the field's stored entry. After any refusal or refresh problem, inspect the current saved state before another edit.
```

Old:

```markdown
**Object unavailable** is a failed read, not an empty record. Read its reason and choose
**Retry**, or **Back to list** to inspect another result. A record belonging to another
application follows that application's route where the model allows it. A record belonging
to another workspace cannot be read by silently substituting the workspace you have open.
Check the workspace and original address with its sender.
```

New:

```markdown
**Record unavailable** is a failed read, not an empty record. Read its reason and choose
**Retry**, or **Back to list** to inspect another result. A record belonging to another
application follows that application's route where the model allows it. A record belonging
to another workspace cannot be read by silently substituting the workspace you have open.
Check the workspace and original address with its sender.
```

### use/relationships.md

Old:

```markdown
The **Delete relationship?** confirmation says that the connected objects remain. This action
removes a permitted connection, not either record. A required-relationship refusal leaves it in
place; do not delete an owner to work around the refusal. Review the intended data change first.
```

New:

```markdown
Choose **Remove relationship** to remove a permitted connection immediately. Both records remain, and the notice offers **Undo**. A required-relationship refusal leaves it in
place; do not delete an owner to work around the refusal. Review the intended data change first.
```

Old:

```markdown
**Add …** can create an owned record with its required relationship already filled. Its
creation and connection succeed together. **Set relationship** fills an empty single-valued
connection; the dialog offers **Object** and any fields on the connection, then **Set**.
Other actions use **Create**, **Change** or **Save** as appropriate. **Delete relationship**
in its confirmation removes only the connection, keeping the objects.
```

New:

```markdown
**Add …** can create an owned record with its required relationship already filled. Its
creation and connection succeed together. **Set relationship** fills an empty single-valued
connection; the form offers a search labelled with the related type's name and any fields on the connection, then **Set**. Other actions use **Add** followed by the type's name, **Change** or **Save** as appropriate. **Remove relationship** removes only the connection immediately, keeping both records; the notice offers **Undo**.
```

Old: none (added passage).

New:

```markdown
A related-record panel with all its rows loaded, five rows or fewer and no active search puts **Search**, **Display** and any available **Sort** in its ⋯ menu. Choose an item to reveal that control. Larger panels and panels with an active search keep the controls visible.
```

### use/workspaces.md

Old: none (added passage).

New:

```markdown
## The workspace's page

Choose a workspace's name on Home to open its page. **Find a record** searches names across its applications and lists. Up/Down chooses a result; Enter opens it. **Applications** offers each application's starting view and links straight to its lists.

**Your shelf** keeps the lists and other views you use most, from any application in this workspace. Choose **Add a list** and tick the lists, trees or matrices you want. You can also use the pin button in a list's header. A tile opens that view; its count, when available, is the number of live records of its source type, not a count of matrix cells or a filtered view.

Drag tiles to arrange them. For keyboard or touch use, open a tile's menu and choose **Move earlier** or **Move later**. Right-click also opens that menu. **Take off your shelf** removes the shortcut, leaving its data in place. The shelf and its order stay in this browser, separately for each workspace.

**Needs you** lists your waiting change sets. **What changed** groups recent activity by day; consecutive repeats of one kind of change fold with a count such as **4 in a row**. These are summaries, not a complete history. Workspace actions, including **Edit model**, appear only when your permissions allow them.
```

## Pages with no change

- `about/compatibility-and-licence.md` — no change.
- `about/data-quality-rules.md` — no change.
- `about/how-it-is-built.md` — no change.
- `about/how-it-works.md` — no change.
- `about/people-and-access.md` — no change.
- `about/security-and-trust.md` — no change.
- `about/sharing-data-with-other-systems.md` — no change.
- `about/three-kinds-of-change.md` — no change.
- `about/what-is-refiroo.md` — no change.
- `administer/ai.md` — no change.
- `administer/api-reference-and-consumer-api-pages.md` — no change.
- `administer/approval-policies.md` — no change.
- `administer/audit.md` — no change.
- `administer/deployment-pages.md` — no change.
- `administer/jobs-and-limits.md` — no change.
- `administer/permissions-reference.md` — no change.
- `administer/signing-keys.md` — no change.
- `examples/the-consumer-api.md` — no change.
- `examples/the-example-data.md` — no change.
- `examples/the-starter-model.md` — no change.
- `examples/translations.md` — no change.
- `guide/administer/add-a-person.md` — no change.
- `guide/administer/check-the-ai-provider.md` — no change.
- `guide/administer/find-who-changed-something.md` — no change.
- `guide/administer/help-someone-who-lost-a-device.md` — no change.
- `guide/administer/link-a-provider-person.md` — no change.
- `guide/administer/require-a-second-factor.md` — no change.
- `guide/administer/rotate-signing-keys.md` — no change.
- `guide/administer/set-an-approval-policy.md` — no change.
- `guide/integrate/connect-an-assistant.md` — no change.
- `guide/integrate/exchange-a-supplier-file.md` — no change.
- `guide/integrate/get-a-token.md` — no change.
- `guide/integrate/load-then-follow-changes.md` — no change.
- `guide/integrate/move-records-between-models.md` — no change.
- `guide/integrate/read-a-collection-completely-and-resume.md` — no change.
- `guide/integrate/read-as-of-a-date.md` — no change.
- `guide/integrate/read-through-a-consumer-api.md` — no change.
- `guide/integrate/resolve-a-file-of-codes.md` — no change.
- `guide/integrate/submit-a-bulk-change.md` — no change.
- `guide/integrate/subscribe-a-webhook-and-verify-it.md` — no change.
- `guide/model/change-a-model-with-the-assistant.md` — no change.
- `guide/model/change-a-workspaces-model.md` — no change.
- `guide/model/check-a-workbook-with-a-dry-run.md` — no change.
- `guide/model/choose-what-moves.md` — no change.
- `guide/model/compare-releases.md` — no change.
- `guide/model/delete-a-draft.md` — no change.
- `guide/model/delete-a-model-mapping.md` — no change.
- `guide/model/edit-a-draft-as-json.md` — no change.
- `guide/model/edit-a-mapping-row.md` — no change.
- `guide/model/edit-a-workspaces-model.md` — no change.
- `guide/model/explain-a-model-change.md` — no change.
- `guide/model/export-a-release.md` — no change.
- `guide/model/find-your-way-around-the-editor.md` — no change.
- `guide/model/fix-issues-before-installing.md` — no change.
- `guide/model/install-and-activate-a-release.md` — no change.
- `guide/model/load-a-workbook-into-a-change-set.md` — no change.
- `guide/model/make-a-workspace-the-default.md` — no change.
- `guide/model/map-a-column.md` — no change.
- `guide/model/migrate-a-workspace.md` — no change.
- `guide/model/move-records-to-another-model.md` — no change.
- `guide/model/preview-a-type.md` — no change.
- `guide/model/raise-a-contract-version.md` — no change.
- `guide/model/raise-a-model-language-version.md` — no change.
- `guide/model/read-lists-in-a-sheet.md` — no change.
- `guide/model/remove-an-element.md` — no change.
- `guide/model/retire-or-delete-a-release.md` — no change.
- `guide/model/retire-or-delete-a-workspace.md` — no change.
- `guide/model/see-a-consumer-apis-documents.md` — no change.
- `guide/model/stop-serving-an-earlier-contract-version.md` — no change.
- `guide/model/undo-and-review-the-draft-history.md` — no change.
- `guide/model/work-on-a-draft-with-others.md` — no change.
- `guide/use/add-a-language-with-a-workbook.md` — no change.
- `guide/use/ask-a-list-in-words.md` — no change.
- `guide/use/browse-a-publication.md` — no change.
- `guide/use/change-records-with-the-assistant.md` — no change.
- `guide/use/change-relationship-values-in-bulk.md` — no change.
- `guide/use/change-relationships-of-many-records.md` — no change.
- `guide/use/change-values-of-many-records.md` — no change.
- `guide/use/continue-a-long-list.md` — no change.
- `guide/use/continue-an-assistant-task.md` — no change.
- `guide/use/continue-live-work-while-a-change-set-is-open.md` — no change.
- `guide/use/copy-or-move-records.md` — no change.
- `guide/use/delete-many-records.md` — no change.
- `guide/use/edit-in-excel-and-import-back.md` — no change.
- `guide/use/explain-a-period-in-history.md` — no change.
- `guide/use/export-records.md` — no change.
- `guide/use/follow-a-workspace.md` — no change.
- `guide/use/follow-and-cancel-a-job.md` — no change.
- `guide/use/load-the-next-version-of-a-workbook.md` — no change.
- `guide/use/move-several-records-together.md` — no change.
- `guide/use/open-a-retired-or-unavailable-workspace.md` — no change.
- `guide/use/open-an-application.md` — no change.
- `guide/use/propose-a-change.md` — no change.
- `guide/use/replace-a-records-related-records.md` — no change.
- `guide/use/reshape-a-hierarchy.md` — no change.
- `guide/use/see-who-changed-what.md` — no change.
- `guide/use/set-up-email-notices.md` — no change.
- `guide/use/start-from-an-earlier-publication.md` — no change.
- `guide/use/stop-offering-a-value.md` — no change.
- `guide/use/switch-workspace.md` — no change.
- `guide/use/withdraw-a-publication.md` — no change.
- `integrate/api-reference.md` — no change.
- `integrate/assistant-tasks.md` — no change.
- `integrate/assistants-and-agents.md` — no change.
- `integrate/business-dates.md` — no change.
- `integrate/changes-approvals-and-publication.md` — no change.
- `integrate/compatibility.md` — no change.
- `integrate/consumer-apis.md` — no change.
- `integrate/consumer-events-and-webhooks.md` — no change.
- `integrate/discovering-the-model.md` — no change.
- `integrate/files-imports-and-exports.md` — no change.
- `integrate/following-changes.md` — no change.
- `integrate/identifiers-paging-and-errors.md` — no change.
- `integrate/jobs.md` — no change.
- `integrate/looking-up-and-resolving.md` — no change.
- `integrate/model-and-release-operations.md` — no change.
- `integrate/overview.md` — no change.
- `integrate/reading-business-objects.md` — no change.
- `integrate/reading-records.md` — no change.
- `integrate/relationships-and-their-values.md` — no change.
- `integrate/security-model-for-integrators.md` — no change.
- `integrate/signing-in-and-tokens.md` — no change.
- `integrate/versions-and-conflicts.md` — no change.
- `integrate/workspaces-contexts-and-models.md` — no change.
- `integrate/writing-in-bulk.md` — no change.
- `journeys/change-with-approval.md` — no change.
- `journeys/index.md` — no change.
- `journeys/integrate-a-system.md` — no change.
- `journeys/look-after-data.md` — no change.
- `journeys/manage-access.md` — no change.
- `journeys/receive-notices.md` — no change.
- `journeys/run-the-service.md` — no change.
- `journeys/shape-a-model.md` — no change.
- `model/ai-model-changes.md` — no change.
- `model/applications-and-views.md` — no change.
- `model/consumer-apis.md` — no change.
- `model/issues-and-dry-run.md` — no change.
- `model/json-view.md` — no change.
- `model/migrations.md` — no change.
- `model/model-change-accounts.md` — no change.
- `model/model-language-versions.md` — no change.
- `model/model-mappings.md` — no change.
- `model/models.md` — no change.
- `model/record-pages-and-tables.md` — no change.
- `model/releases.md` — no change.
- `model/types-attributes-relations.md` — no change.
- `model/workbook-onboarding.md` — no change.
- `model/workbook-proposals.md` — no change.
- `run/ai.md` — no change.
- `run/background-jobs.md` — no change.
- `run/backup-and-restore.md` — no change.
- `run/command-line.md` — no change.
- `run/configure.md` — no change.
- `run/database.md` — no change.
- `run/developer-instance.md` — no change.
- `run/health-and-startup-checks.md` — no change.
- `run/https.md` — no change.
- `run/install-with-compose.md` — no change.
- `run/licence-and-source.md` — no change.
- `run/model-releases-and-rollback.md` — no change.
- `run/monitoring.md` — no change.
- `run/overview.md` — no change.
- `run/production-checklist.md` — no change.
- `run/secrets-and-keys.md` — no change.
- `run/security-checklist.md` — no change.
- `run/set-up-ai.md` — no change.
- `run/several-processes.md` — no change.
- `run/troubleshooting.md` — no change.
- `run/upgrades.md` — no change.
- `run/webhook-delivery.md` — no change.
- `use/ai-and-your-data.md` — no change.
- `use/ask-in-words.md` — no change.
- `use/changing-many-records.md` — no change.
- `use/copying-and-moving.md` — no change.
- `use/hierarchies.md` — no change.
- `use/inbox-and-approvals.md` — no change.
- `use/jobs.md` — no change.
- `use/loading-with-the-assistant.md` — no change.
- `use/notifications-settings.md` — no change.
- `use/publications.md` — no change.
- `use/relation-matrices.md` — no change.
- `use/relationship-tables.md` — no change.
