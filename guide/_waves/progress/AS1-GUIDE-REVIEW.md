
- 2026-11-19T00:43:37+01:00 — Finished `guide/src/content/docs/guide/administer/manage-agent-access.md`: corrected both dialog labels, described the number boxes and day range, and added the Security administration requirement for Change… and New assistant. Checked against AgentAccessPage.tsx; no uncertainty. No steering file was present.

- 2026-11-19T00:43:55+01:00 — Finished `guide/src/content/docs/integrate/signing-in-and-tokens.md`: bounded reuse of a spent assistant refresh token by its issue time and the days without use; explained invalid_grant, the surviving session, newest token and old copies. Verified sessions.renew and the OAuth route; the route misleadingly says “The session has ended; sign in again” even for this refusal, although the session remains open. No steering file was present.

- 2026-11-19T00:44:08+01:00 — Finished `guide/src/content/docs/guide/integrate/connect-an-assistant.md`: clarified the issue-time window for spent tokens, invalid_grant afterwards, continued renewal with the newest token and the limited usability of old copies. Kept the other instructions and pictures unchanged; no uncertainty. No steering file was present.

- 2026-11-19T00:44:29+01:00 — Finished `guide/src/content/docs/run/sign-in-and-mail-setup.md`: qualified spent-token reuse by the issue-time window, explained refusal without ending the session, and advised keeping the newest token. Named Sign-ins as the limits location; no uncertainty. No steering file was present.

- 2026-11-19T00:44:29+01:00 — Reviewed `guide/src/content/docs/administer/agent-access.md`: its Sign-ins text has no field labels containing “(days)”, so it remains unchanged as instructed. No uncertainty. No steering file was present.

- 2026-11-19T00:44:53+01:00 — Validation complete: reviewed the scoped page diff and ran `GUIDE_OUT=_build/AS1-GUIDE-REVIEW npm run build` in `guide/`; exit 0, 259 pages, 3.87 seconds. Build warned of a conflicting /404 route. Existing pictures were preserved; no new screenshots needed for this text-only correction. No steering file was present. Remaining product concern: the OAuth invalid_grant description incorrectly says the session ended when a spent assistant token ages out; code was not changed.
