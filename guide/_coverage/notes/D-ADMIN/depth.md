# Depth review: D-ADMIN

## Permissions reference and roles

- Answered: purpose, setup through linked custom-role/grant guides, every catalogue group and action, predefined holders, reach, write narrowing, current permissions, job permissions, hidden screens and controls, assistant ceiling.
- Removal/change: existing roles page covers additive grants, removing at source, custom-role deletion, next-request effect and stale narrowing. Grants have no expiry control; no rotation applies.
- Recovery/move/backup: database-level operation belongs to Run; no role-only export/import screen.
- Sources: backend/app/engine/authorization/catalogue.py (complete); frontend/src/features/settings/navigation.ts; frontend/src/features/security/RolesPage.tsx; permissionText.ts. Existing roles/custom-role/grant/narrowing guides read in full.
- Internal identifiers for three actions without browser labels and three role spelling aliases appear only in non-rendered inventory comments. No internal names presented to administrators.

## People and groups; add/manage/link guides

- Answered: local and provider identities, creation, reset links, memberships, uniqueness, partial additions versus atomic removal, rename, deletion/deactivation, restoration, sign-out, last-human-admin protection, concurrency and failures. Added unlink membership/session consequences and source-history preservation.
- Expiry: reset link expiry displayed; people/groups do not expire. Restore/move is instance backup, linked to Run; no identity export/restore UI.
- Sources: identity/users.py; links.py (unlink read in full); resets.py; authorization/administration.py relevant creation, membership and refusal sections; PeoplePage.tsx, GroupsPage.tsx, AddMembersDialog.tsx labels and handlers. Existing people/add/manage/link pages read in full.
- No D-ADMIN steering file present.

## Sign-in and second-factor guides

- Answered: OpenID Connect registration, local recovery, enable/disable/delete, group synchronization, secret replacement, session limits, password policy, TOTP/recovery/passkeys, removal and recovery, address changes and operator handoff. Added exact local/provider refusal messages and clarified that policy updates do not end sessions.
- Sources: identity/providers.py set_local, update/delete and refusal sections; identity/settings.py defaults; frontend/features/security/SignInPage.tsx forms/actions/concurrency. Add-provider, require-factor, lost-device and local-off guides read in full (lost-device output initially truncated; relevant remaining text read subsequently).
- Backup is instance-level; provider credentials have provider-controlled expiry and no refiroo automatic renewal. No additional browser expiry/session-policy controls exist.
- No steering file present.

## Clients and signing keys; create/grant/rotate guides

- Answered: identity and least access, consumer grants, one-time credentials, default no-end secrets, rotation overlap including all older secrets, no automatic secret rotation, immediate secret ending versus issued access, deactivation/restoration, current state after lost response, shared signing-key schedule and retirement, retained history and instance backup. No browser identity move/export or key import.
- Sources: identity/clients.py and keys.py read fully; existing clients, create-client, rotate-secret, consumer-grant, signing-keys, rotate-keys pages read fully. UI labels checked against ClientsPage.tsx and SigningKeysPage.tsx in next source pass.
- No steering file present.

## Approval policies and policy guide; audit and find-author guide

- Approval answered: defaults, setup/permissions, approver warnings, current policy on waiting work, frozen submissions, both decision types under second-person rule, exact refusals, conflicts, turning off, retained decisions. Source: change_sets/approvals.py read fully; workspace Approval labels checked in existing page and frontend source search. No expiry/rotation applies to policy.
- Audit answered by existing page/guide: data versus security events, filters, identity/current names, permissions, empty/failure distinctions, retained/deleted subjects, no export/instance-wide screen, unbounded security-history growth. No setup, renewal or administrator delete control. Source: identity/security_events.py and RecentActivity.tsx; cross-workspace history permissions reviewed separately below. Instance-level restore belongs to Run.
- No steering file present.

## Mail and setup guide

- Answered: SMTP setup, exact connection choices, tested delivery versus receipt, secret changes, clearing login, configuration conflicts, outbox states, retry/deadline/pruning, stop race, removal/reconfiguration, password links, notifications/digests and owner preferences. Added all test headings, actionable save refusals, credential replacement and old queued-link consequences after moving site.
- Sources: mail/settings.py save/remove and application address; mail/smtp.py error boundaries; mail/outbox.py stop/limits; mail/sender.py read fully; frontend/settings/MailPage.tsx handlers and mailText.ts fully. No automatic SMTP credential renewal or failed-message restart. Instance restore belongs to Run.
- No steering file present.

## Webhooks; create/rotate/paused guides

- Answered: consumer-event setup, fixed source, filters and current state, formats, batches, start position, delivery states, retries/retention, failures, suspend/resume/reset, resend, changes and repeated key rotation, deletion and restore/repeated-delivery consequences.
- Sources: events/subscriptions.py update/resume/rotate/delete, subscription_rules.py, webhook_urls.py fully; frontend/settings/WebhookDialog.tsx form/save and webhookText.ts fully. Existing webhook docs and three guides read fully.
- D-DF recheck: Workspace events are now offered through Events from. Creation needs no consumer API with events; that source offers the workspace selector, three change-set steps, Requests and Format, with consumer selector, Filters and Content hidden. Documentation and creation guide updated.
- No automatic webhook key rotation; receiver certificates renewed at receiver. Backup belongs to Run.
- No steering file present.

## AI and provider-check guide; Agent access and manage-agent guide

- Answered: separate built-in provider/assistant/external MCP, configured capabilities, actual send ceilings, permissions and task access, human review, settings/test failures, costs, retained content versus metadata/task files, credential configuration, turning off, grants, hidden call lists while off, registration lifecycle, blocking/restoring, replacement addresses, shared caller rate and exact scope of call information, instance restore handoff.
- Sources: proposals/registry.py, context.py values policy, calls.py fully; tasks/store.py ownership/touch/expiry and agent.py boundaries; agent_access/applications.py registration/block/restore/expiry; calls.py fully; management/routers/agent_access.py; frontend/settings/AiPage.tsx, aiText.ts, AgentAccessPage.tsx fully.
- Corrected prior page claim that all unused registrations expire: only unblocked self-registrations do. Administrator registrations remain.
- Product defect: frontend/settings/aiText.ts sendLevelText Values says up to sampleValues per column; engine/proposals/context.py Policy.values returns all wanted values at Values. Docs explicitly state true policy; no UI fix in this wave.
- No steering file present.

## API reference/Consumer APIs; Jobs and limits; About/Deployment/Operations

- API pages answered by existing content: purpose, versions, read-only model release ownership, exact handover controls, no-API versus load failure, Browse versus public contracts and client grants, feed expiry recovery. No configuration/rotation/delete/backup action on these pages.
- Jobs answered: list/details/permissions/requester, limits, cancellation, retained summaries versus expired details, unconfirmed preview expiry and restart, changed grants, creation disabled also hides cancellation. Corrected list confirmation to Cancel job; detail is Stop the job. Backup belongs to Run.
- Deployment pages answered: general versus Operations permission, versions, environment/default and secret indicators, restart boundary, readiness/threads, rehearsal results and earlier entries, refresh failure, operator recovery. No browser settings edit/expiry/delete applies.
- Sources: frontend/settings/ApiReferencePage.tsx, ConsumerApisPage.tsx, JobsPage.tsx fully; limits.ts fully; DeploymentPage.tsx and OperationsPage.tsx relevant state/rendering; jobs/JobPage.tsx cancellation; engine/jobs/store.py expire_jobs and previews; management/routers/changes.py visibility. Existing three pages read fully.
- No steering file present.

## Per-page completion ledger

Each page below was read and held against all eight depth questions. The capability notes
above identify the concrete answers and code sources. “Retained” means the existing page
already supplies its task details and links; no filler or duplicate procedure was added.
For browser pages, moving/backing up the instance is an operator task linked from its
owning capability page. Pages for read-only reporting do not have setup, expiry, renewal,
removal or undo controls of their own. No known factual depth question remains unanswered;
reference-instance execution and appearance were not checked in this writing wave.

| Page | Depth disposition |
| --- | --- |
| `administer/agent-access.md` | Reviewed: agent access; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/ai.md` | Reviewed: AI; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/api-reference-and-consumer-api-pages.md` | Reviewed: reporting pages; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/approval-policies.md` | Reviewed: approval policies; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/audit.md` | Reviewed: audit; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/clients.md` | Reviewed: clients/signing keys; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/deployment-pages.md` | Reviewed: reporting pages; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/jobs-and-limits.md` | Reviewed: reporting pages; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/mail.md` | Reviewed: mail; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/people-and-groups.md` | Reviewed: people and groups; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/permissions-reference.md` | Reviewed: roles; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/roles-and-grants.md` | Reviewed: roles; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/sign-in.md` | Reviewed: sign-in and recovery; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/signing-keys.md` | Reviewed: clients/signing keys; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `administer/webhooks.md` | Reviewed: webhooks; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/add-a-person.md` | Reviewed: people and groups; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/add-a-sign-in-provider.md` | Reviewed: sign-in and recovery; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/check-the-ai-provider.md` | Reviewed: AI; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/create-a-client.md` | Reviewed: clients/signing keys; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/create-a-custom-role.md` | Reviewed: roles; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/create-a-webhook.md` | Reviewed: webhooks; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/find-out-why-a-webhook-paused.md` | Reviewed: webhooks; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/find-who-changed-something.md` | Reviewed: audit; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/grant-a-consumer-api-to-a-client.md` | Reviewed: clients/signing keys; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/grant-a-role.md` | Reviewed: roles; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/help-someone-who-lost-a-device.md` | Reviewed: sign-in and recovery; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/link-a-provider-person.md` | Reviewed: people and groups; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/manage-a-group.md` | Reviewed: people and groups; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/manage-agent-access.md` | Reviewed: agent access; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/narrow-a-grant-to-record-types.md` | Reviewed: roles; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/require-a-second-factor.md` | Reviewed: sign-in and recovery; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/rotate-a-client-secret.md` | Reviewed: clients/signing keys; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/rotate-a-webhook-key.md` | Reviewed: webhooks; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/rotate-signing-keys.md` | Reviewed: clients/signing keys; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/set-an-approval-policy.md` | Reviewed: approval policies; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/set-up-mail.md` | Reviewed: mail; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |
| `guide/administer/turn-off-local-sign-in.md` | Reviewed: sign-in and recovery; purpose, setup/use, later changes, applicable lifetime, failures/recovery, removal/retention and permission limits covered here or by linked owning capability. Non-applicable browser controls identified above. |

## Final source review corrections

- D-DF recheck: ClientsPage.tsx shows Rotate secret for inactive clients too. The inactive note explains restoration and the overlap clock. Recovery now uses Deactivate, Rotate secret, Stop it now, configure replacement, then Restore; the obsolete API handoff was removed.
- identity/authentication.py:99-164 checks a client's current active flag and signed-access expiry, with no client revocation epoch. Documented that restoring can permit previously issued unexpired access again. An inactive client remains blocked; secret rotation alone does not invalidate issued access.
- Inactive-client rotation screen gap resolved; source review only, no live security experiment. Previously issued-access caveat remains applicable.
- Final diff was read; first combined diff output truncated in the middle, then people/sign-in/signing-key changes were read separately. No source edits outside the assignment.
