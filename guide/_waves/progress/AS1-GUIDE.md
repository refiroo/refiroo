# AS1-GUIDE progress

- 2026-11-18 23:23 CET, unit 1: Finished `guide/src/content/docs/administer/agent-access.md`. Added the Sign-ins rows, defaults, allowed values, timing of changes, security event and ways access still ends, with the supplied screenshot and caption. Checked the screen, frontend dialog, session renewal code and operator/API documentation; no steering file was present and no uncertainty remains for this page.

- 2026-11-18 23:24 CET, unit 2: Finished `guide/src/content/docs/guide/administer/manage-agent-access.md`. Added the two-field procedure, validation messages, save failure recovery and when changes take effect, distinguishing person sign-ins from system clients. No steering file was present; no uncertainty remains for this page.

- 2026-11-18 23:24 CET, unit 3: Finished `guide/src/content/docs/guide/integrate/connect-an-assistant.md`. Explained keeping the newest refresh token while allowing earlier tokens in other windows, the administrator-set limits and expiry, with a link to the Agent access API reference. No steering file was present; no uncertainty remains for this page.

- 2026-11-18 23:24 CET, unit 4: Finished `guide/src/content/docs/integrate/signing-in-and-tokens.md`. Added the assistant-session exception and separate limits in Assistant connections, preserving every existing sentence, including the browser-session paragraph. No steering file was present; no uncertainty remains for this page.

- 2026-11-18 23:24 CET, unit 5: Finished `guide/src/content/docs/run/sign-in-and-mail-setup.md`. Replaced only the reused-refresh-token sentence to specify browser sign-ins and their recovery grace, and explain the assistant exception and separate settings; every other sentence is unchanged. No steering file was present; no uncertainty remains for this page.

- 2026-11-18 23:25 CET, final review: Reviewed all five page diffs and corrected `guide/src/content/docs/administer/agent-access.md` to locate Sign-ins just after How to connect. First isolated build passed (259 pages, 3.70 seconds); it reported a conflicting /404 route warning. No steering file was present; rebuilding after this wording correction and checking links next.

- 2026-11-18 23:25 CET, validation complete: Final `GUIDE_OUT=_build/AS1-GUIDE npm run build` passed (259 pages, 2.84 seconds), followed by `GUIDE_OUT=_build/AS1-GUIDE npm run check:links`, `npm run check:terms`, `npm run check:brand` and scoped `git diff --check`. Used `admin-agent-sign-ins.png` on the Agent access documentation page; it shows Access, Sign-ins, Change…, all three rows and their kind chips. No further screenshot or unresolved product question; the build reports a /404 route conflict warning without failing.
