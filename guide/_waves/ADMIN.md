# Administer access

Read `guide/AGENTS.md` again (documentation pages and guides; generic steps with the example only in
captions; detail). Keep the standard of the "Use refiroo" and "Model your data" pages.

Reader: administrators of people and access, working under Settings in the browser. No JSON, no API paths.
Sources: the screens in `frontend/src/`, `docs/OPERATIONS.md` (authentication, roles and grants, sign-in,
second factors, mail, approvals, audit), `docs/product-functionality/USER_JOURNEYS.md` (J39–J47), the
permission catalogue in the code (the roles and what each may do), and the code where they disagree.
How an operator installs and configures sign-in providers on the server belongs to "Run refiroo"; here,
describe what the administrator sees and sets in the browser, and link to Run for the server part.

| Group | Documentation page | Guides |
| --- | --- | --- |
| People and groups | `administer/people-and-groups.md`: local accounts and people from the organisation's provider, groups, disabling, what happens to a person's work | `guide/administer/add-a-person.md`, `guide/administer/manage-a-group.md` |
| Roles and grants | `administer/roles-and-grants.md`: every role and what it may do (from the catalogue, as a table), instance-wide and per-workspace grants, how grants combine | `guide/administer/grant-a-role.md` |
| Sign-in and second factors | `administer/sign-in.md`: local passwords, the organisation's provider, second factors and passkeys, sessions and their limits, helping someone who lost a device | `guide/administer/require-a-second-factor.md`, `guide/administer/help-someone-who-lost-a-device.md` |
| Clients for other systems | `administer/clients.md`: what a client is, its grants, secrets and rotation, which systems need one (link to Integrate for how they sign in) | `guide/administer/create-a-client.md`, `guide/administer/rotate-a-client-secret.md` |
| Signing keys | `administer/signing-keys.md`: what they sign, rotation | `guide/administer/rotate-signing-keys.md` |
| Approvals | `administer/approval-policies.md`: a workspace's approval policy, the second-person rule, who may approve; link to the steward's approval pages in Use | `guide/administer/set-an-approval-policy.md` |
| Who changed what | `administer/audit.md`: the activity and audit views across the instance, filters, what is recorded | `guide/administer/find-who-changed-something.md` |

What the screenshots found, which the table above assumed differently: there is no separate page for a
role (the roles matrix and the Grant dialog show what each role may do); no session or passkey policy
setting for administrators (only "Require a second factor with a password" under Local accounts, and each
person's own sessions on their account page); no instance-wide audit page ("Who changed what" is a person's
"See changes" view and each person's recent activity; describe what exists, and the workspace Activity tab
from `use/history.md`); no group exists yet on the instance, so there is no group page to show; nobody has
a second factor yet, so its reset button cannot be shown (describe it from the code). "Start a new key"
rotates the signing key at once, without a dialog: say so. Describe only what exists.

If a screen is marked "ai-later" (agent access), leave it out: those pages come later.

## Screenshots

Screens file: `ADMIN.screens.json`

Those screenshots are attached and are the real screens; earlier ones (`use-account*`, `appr-*`,
`use-approval-policy`) may also be referenced. Use `/docs/screens/<name>.png` with captions saying what the
example shows (Rita Approver is a fictional person). List any screenshot still needed.

## Files you may edit

- `src/content/docs/administer/*.md`
- `src/content/docs/guide/administer/*.md`

## Report

The pages written, the screenshots used and still needed, anything you were unsure of, and anything in
refiroo that looked wrong.
