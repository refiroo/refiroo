# AS1 guide: assistants stay signed in

Read `guide/AGENTS.md`. Readers: security administrators who manage an assistant's access, and integrators who connect
an assistant. Write plain prose; no package or decision numbers. The code wins over this text wherever they differ.

## Why

Claude Code and other MCP assistants asked people to reconnect every 10 to 20 minutes. Several windows of one assistant
share one sign-in and each renews it on its own; a window that held a refresh token already used ended the whole
session. Now an assistant's session renews from any refresh token it was given and is never ended for a used token.
It has limits of its own, set on the Agent access page. Browser sign-ins are unchanged.

## What the product does now (check each point in the code)

- **Sign-ins** is a new group on the **Access** tab of **Settings › Connections › Agent access**, right after **How to
  connect** (`frontend/src/features/settings/AgentAccessPage.tsx`, `SignInsSection` and `SignInsDialog`). Its text: "How
  long an assistant someone signed in stays signed in. It renews on its own while it is used, also from several windows
  at once." Three rows: **Without use** (Assistants, 30 days), **In all** (Assistants, 90 days, then the person signs in
  again) and **Browser sign-ins** (12 hours without use, 14 days in all, set in the server's environment: a fact, kept
  for comparison). The first two are the assistants' limits; the browser row shows the server's `SESSION_IDLE_HOURS` and
  `SESSION_DAYS`, which no longer apply to assistants.
- **Change…** (a secondary button at the group's title) opens the dialog **Assistant sign-ins** with two number fields:
  **Signed out after no use for (days)** (counted from the assistant's last renewal, 1 to 365) and **Signed out in all
  after (days)** (counted from the sign-in, not fewer than the days without use, applies to new sign-ins), and the note
  that blocking an assistant, or signing out everywhere, still ends its sign-ins at once. **Save** and **Cancel**.
  A value outside 1 to 365 is refused with "Enter a whole number of days from 1 to 365."; days in all fewer than days without use with "Must be at least the days without use."; both next to the field, and Save waits. The change
  is a security event ("Assistant sign-in limits changed"). Security administration is needed, as for the rest of the page.
- A change applies to each session's next renewal (days without use) and to new sign-ins (days in all). Defaults: 30 days
  without use, 90 days in all. They are set on the page, never in the environment.
- An assistant's session renews from any refresh token it was given, also one already used: several windows can share one
  sign-in without ending it. A session still ends by its limits, by signing out (the person ends it under **Settings ›
  Account**), by the person being deactivated or changing their password, by an administrator (**Block**, which ends its
  sessions on their next call), and by signing out everywhere. Browser sessions are unchanged: a used refresh token
  presented again after the 30-second recovery grace still ends them.
- API (for the integrator pages; link the reference, do not repeat fields): `PATCH /api/v1/agent-access` sets the two
  limits; `GET /api/v1/agent-access` answers them. See `docs/API.md` (Sessions) and `docs/OPERATIONS.md` (Agent access).

## What to do

- `src/content/docs/administer/agent-access.md`: say what the **Sign-ins** group shows and that **Change…** sets the two
  limits (defaults, range, when a change applies, what still ends a sign-in at once). Add it where the page's parts are
  explained (the section about connection and sign-in). Add the picture below.
- `src/content/docs/guide/administer/manage-agent-access.md`: add the steps to change how long assistants stay signed in
  (open Sign-ins, **Change…**, the two fields, **Save**, what a refused value says, when it takes effect).
- `src/content/docs/guide/integrate/connect-an-assistant.md`: in the sequence that connects an assistant, replace the line
  that tells the integrator to keep the replacement from every successful renewal as if a spent token ends the session:
  the assistant keeps the newest refresh token but a window that still holds an earlier one does not sign the person
  out; and say how long the sign-in lasts (the limits above) and that an administrator sets them. Step 5 (end or revoke)
  gains one sentence that the limits also end a sign-in.
- `src/content/docs/integrate/signing-in-and-tokens.md`: the paragraph about browser sessions stays true for browsers; the
  section "Assistant connections" says an assistant's session is the exception (renews from any refresh token it was
  given, never ended as a reused one; its limits are its own, 30 days without use and 90 in all by default, set on the
  Agent access page). Keep every other sentence.
- `src/content/docs/run/sign-in-and-mail-setup.md`: only the sentence that says presenting an already-used refresh token
  ends the session: it is about browser sign-ins; an assistant's session is the exception, with limits set on the Agent
  access page, not by `SESSION_IDLE_HOURS` and `SESSION_DAYS`. Keep every other sentence.

## Pictures (taken, in `guide/public/screens/`; look at it, then reference it as `![…](/docs/screens/<name>.png)`)

- `admin-agent-sign-ins`: the **Sign-ins** group on the **Access** tab: its title and **Change…** button, the three rows
  with their kind chips. Use it in `administer/agent-access.md` with a caption that says what to look at. No older
  picture shows it; the older Agent access pictures stay as they are.

## Files you may edit
- `src/content/docs/administer/agent-access.md`
- `src/content/docs/guide/administer/manage-agent-access.md`
- `src/content/docs/guide/integrate/connect-an-assistant.md`
- `src/content/docs/integrate/signing-in-and-tokens.md`
- `src/content/docs/run/sign-in-and-mail-setup.md`
