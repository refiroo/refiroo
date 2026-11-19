# AS1 guide, review fixes: a spent token has a window; the dialog's fields

Read `guide/AGENTS.md`. Readers: security administrators who manage an assistant's access, and integrators who connect
an assistant. Plain prose; no package or decision numbers. The code wins over this text wherever they differ.
Change only the sentences named below; keep every other sentence and every picture as it is.

## What changed in the product (check in the code)

- An assistant's session still renews from any refresh token it was given, also one already used (several windows share
  one sign-in). But a token already used is accepted only while it was issued less than the **days without use** ago
  (30 by default; `engine/identity/sessions.py`, `renew`). After that it is refused with the OAuth error
  `invalid_grant`. The session is not ended by it: the newest refresh token, and any younger one, still renews it.
  The days without use are the ones an administrator sets under **Sign-ins**. So: keep the newest refresh token after
  each renewal; an old token stays usable only within that window; a person is never signed out by it.
- In the **Assistant sign-ins** dialog (`frontend/src/features/settings/AgentAccessPage.tsx`, `SignInsDialog`) the two
  fields are now labelled **Signed out after no use for** and **Signed out in all after**, with the word "days" after
  the number box (no "(days)" in the label). Their help lines are unchanged.
- **Change…**, **New assistant**, **Block** and **Restore** appear only for people who may change agent access
  (Security administration); others see the page without them.

## What to do

- `src/content/docs/guide/administer/manage-agent-access.md`: steps 3 and 4 name the fields **Signed out after no use
  for** and **Signed out in all after** and say each has a box for the number of days (1 to 365). One short sentence
  that **Change…** and **New assistant** are offered only to people with Security administration. Keep the rest.
- `src/content/docs/integrate/signing-in-and-tokens.md` (Assistant connections), `src/content/docs/guide/integrate/connect-an-assistant.md`
  and `src/content/docs/run/sign-in-and-mail-setup.md`: where they say an already-used refresh token can renew an
  assistant's session, add that this holds only within the days without use after the token was issued; later it is
  refused with `invalid_grant`, the session stays open and the newest refresh token renews it. Say that a copy of an old
  token therefore stays usable only inside that window. Keep every other sentence.
- `src/content/docs/administer/agent-access.md`: only if the Sign-ins text there names the fields with "(days)", correct
  it; add nothing else.

## Files you may edit
- `src/content/docs/guide/administer/manage-agent-access.md`
- `src/content/docs/integrate/signing-in-and-tokens.md`
- `src/content/docs/guide/integrate/connect-an-assistant.md`
- `src/content/docs/run/sign-in-and-mail-setup.md`
- `src/content/docs/administer/agent-access.md`
