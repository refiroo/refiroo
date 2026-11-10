# MS-PICS: pictures of the Microsoft 365 mail form, and two wording fixes

Read `guide/AGENTS.md`. Reader of `administer/mail.md`: the access administrator; of `run/sign-in-and-mail-setup.md`:
the operator. The pages describe the Microsoft 365 form in words (waves MS and MS-MI) and have no picture of it.
Screens file: `MS.screens.json`

## What the pictures show

Three pictures, taken on 2026-11-10 from the reference instance with `node tools/screens.mjs --file MS.screens.json`.
Look at each before you write. All three are Settings › Integration › Mail at 1440 px, the Mail page with the settings
menu on the left. In all three **Send mail through** is set to **Microsoft 365**, and **Sending mailbox** holds the
example address `mail@example.org`. Nothing is saved and no message is sent: the pictures show an unsaved form (the
reference instance keeps an SMTP configuration of its own, which is why **Remove settings…**, **Cancel** and **Save** are
visible below the form). The example's data is the guide's reference instance; do not say more about it than the caption
rule of `guide/AGENTS.md` allows.

1. `public/screens/admin-mail-microsoft365-menu.png`. **Sign in with** is shown as an open list with its four entries:
   **Client secret** (highlighted), **Certificate**, **Managed identity – this tenant**, **Managed identity – hosted in
   another tenant**. Under the list the line "The simplest. The secret expires and has to be renewed." Below it the empty
   **Tenant ID**, **Application (client) ID** and **Client secret** fields, **Sending mailbox** with `mail@example.org`, the
   two folded sections **What to set up in Microsoft Entra** and **Other Microsoft clouds (token and Graph addresses)**,
   **Application address** and the buttons. The list is the menu's choices laid open for the picture; in the application it
   opens as an ordinary drop-down.
2. `public/screens/admin-mail-microsoft365-secret.png`. **Sign in with** is **Client secret**. **Tenant ID** and
   **Application (client) ID** hold two example GUIDs (11111111-2222-3333-4444-555555555555 and
   66666666-7777-8888-9999-000000000000), **Client secret** shows masked dots, **Sending mailbox** `mail@example.org`.
   Below: the two folded sections (closed), **Application address**, the buttons, and the start of **Test message** with
   **Send to** and **Send test message** (unavailable).
3. `public/screens/admin-mail-microsoft365-entra.png`. **Sign in with** is **Managed identity – this tenant**, with the
   line "No secret is stored. refiroo runs in Azure, in the same tenant as Microsoft 365, and Azure gives it its token."
   One field, **Identity client ID** (empty, "Empty: the identity of the host itself (system-assigned)"), and the note that
   a managed identity works only when refiroo runs in Azure (App Service, Container Apps or a virtual machine). **Sending
   mailbox** `mail@example.org`. **What to set up in Microsoft Entra** is open with three numbered steps: run refiroo on
   Azure with a managed identity; give the identity's service principal the Microsoft Graph Mail.Send app role (no portal
   button; the operator guide has the command; admin consent is not asked for); limit it to the sending mailbox with an
   application access policy or RBAC for Applications, naming the identity's client ID. **Other Microsoft clouds** is closed.

## What to do

- `src/content/docs/administer/mail.md`, in **Send through Microsoft 365**: insert picture 1 after the paragraph that
  introduces **Sign in with** (before its table) and picture 2 after the table and the paragraph under it ("For a tenant
  ID, ..."), picture 3 after the bullet list of the two folded sections. Each as
  `![alt](/docs/screens/<name>.png)` followed by an italic caption of two or three sentences, in the page style used on
  `use/loading-with-the-assistant.md` (the picture, a blank line, `*Above: ...*`). Alt text is one sentence saying what the
  screen shows. Say only what the picture shows (above); say that the values are examples and that nothing is saved. Do
  not name the reference instance's data as a real organisation: the address and the IDs are examples.
- `src/content/docs/run/sign-in-and-mail-setup.md`: where the page says the form lists the Entra steps for the selected
  entry (near "Open **Other Microsoft clouds**", about line 390), insert picture 3 once with its own alt and caption, only if
  the sentence is about that fold; otherwise do not add it.
- Fix one wording, in both pages: where the page says HTTP 409 on a rejected message is a "temporary conflict", say only
  that it is retried; the code (`backend/app/engine/mail/graph.py`, `_send_failure`) retries a 409 and does not say why.
  In `administer/mail.md` this is the last row of the failure table ("A temporary conflict leaves it waiting") and the
  paragraph on retries; in the operator page the `rejected` row of the failure table.
- Check against `frontend/src/features/settings/MailPage.tsx` and `mailText.ts` that every label you name in a caption is
  exactly as the page shows it, and against the pictures. Change nothing else on either page.

## Files you may edit

- `src/content/docs/administer/mail.md`
- `src/content/docs/run/sign-in-and-mail-setup.md`
- `_waves/progress/MS-PICS.md`

## Checks

Run `npm run build` in `guide/`; it must pass. `node tools/codex-wave.mjs check MS-PICS` runs `npm run verify` and the link
check.

## Report

The alt text and caption of each picture as written, where each was inserted, the wording fixes, and anything on the two
pages that looked wrong (listed, not fixed).
