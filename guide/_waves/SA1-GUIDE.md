# SA1 guide: a person whose sign-in an administrator manages

Read `guide/AGENTS.md`. Readers: administrators who add and look after people, and the people who use such an account.

## Why

One 0.17 package, built and committed (plan `docs/BASE_0_17_IMPLEMENTATION_PLAN.md`, section "SA1: Sign-in managed by an
administrator"; CHANGELOG, Unreleased, the SA1 entry; `docs/API.md`, "Sign-in managed by an administrator"). The pages
below still describe the earlier behaviour. The code wins over the plan wherever they differ:
- the rule and its message: `backend/app/engine/identity/managed.py`;
- where it is applied: `backend/app/engine/identity/resets.py` (`change_password`), `second_factor.py` (`begin`, `confirm`,
  `new_recovery_codes`, `remove`, `prove`, `required_step`), `passkeys.py`, `sessions.py` (`end_own_session`,
  `end_own_sessions`, `own_session_page`), `backend/app/engine/mail/links.py` (`request_reset`);
- the account page: `frontend/src/features/settings/AccountPage.tsx` (`ManagedSignIn`);
- the person form: `frontend/src/features/security/PeoplePage.tsx` (`SignInManagedField`, New person and Edit);
- the security log's wording: `frontend/src/features/security/securityText.ts`.

## What the product does now (check each point in the code)

- **The switch.** New person and a person's Edit dialog have one checkbox, "An administrator manages this person's
  sign-in", with its help text. Only who may administer people sees and sets it. It is off unless ticked. It is meant for
  an account several people use with one known password, or one on a kiosk or a training machine; say so in neutral words.
- **What the person can no longer do.** Change their own password; set up, confirm or remove a second factor; make new
  recovery codes; add, rename or remove a passkey; sign out their other browsers or sign out everywhere. They can still
  sign out of the browser they are in.
- **What their Account page shows.** One line, "An administrator manages the sign-in of this account.", in place of the
  password, passkeys, second factor and "where you're signed in" parts. Those parts are not shown at all. The profile part
  and Sign out stay. Say what to do: ask an administrator.
- **Forgotten password.** A request for such a person's address is answered like any other and sends no mail.
- **What the administrator still does for them.** Makes a password link (the person, or whoever holds the account, sets
  the password with it); removes a second factor; removes a passkey; signs them out. Check each on the person's page.
- **A required second factor.** Where the instance requires a second factor, a person whose sign-in is managed and who has
  none is not asked to set one up at sign-in (decision confirmed 2026-11-11). Say this where the requirement is described,
  with its consequence: such an account signs in with the password alone.
- **Still true.** Wrong passwords typed for the account's e-mail address slow its sign-in for everyone who uses it, as for
  any account. Say it where shared use is described.
- **The security log.** Switching it on or off is recorded on the person; use the wording `securityText.ts` shows.
- **Clients.** The same requests from a client are refused with `403 SIGN_IN_MANAGED`. Mention the code only where the
  page already names error codes; link to the API reference rather than repeat it.

## What to do

- Extend the pages that own each topic rather than duplicate: what the person sees in `use/account.md`; the checkbox and
  when to use it in `guide/administer/add-a-person.md` and `administer/people-and-groups.md`; the exemption in
  `guide/administer/require-a-second-factor.md` and `administer/sign-in.md`; in
  `guide/administer/help-someone-who-lost-a-device.md` what an administrator does for such a person (they cannot help
  themselves); the log line in `administer/audit.md`. Link the pages where a reader needs the next step.
- Neutral examples only (a shared reception account, a training account). Never the example model or its types.
- No new pages. Pictures: list in the report each picture the text calls for that is not taken yet; take none.
- Keep everything else on these pages as it is.

## Files you may edit

- `src/content/docs/use/account.md`
- `src/content/docs/guide/administer/add-a-person.md`
- `src/content/docs/administer/people-and-groups.md`
- `src/content/docs/guide/administer/require-a-second-factor.md`
- `src/content/docs/administer/sign-in.md`
- `src/content/docs/guide/administer/help-someone-who-lost-a-device.md`
- `src/content/docs/administer/audit.md`
- `_waves/progress/SA1-GUIDE.md`

## Report

Per page: what changed and why (one line each), what you checked and left, pictures needed, and any point the guide cannot
describe honestly.
