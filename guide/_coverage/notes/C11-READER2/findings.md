# C11 reader 2 — findings

Fresh-reader execution started 2026-11-08. Reading is limited to built HTML in `guide/dist/`, its pictures and the running installation. No source or previous-wave notes were consulted. Viewport is 1280 × 900 unless recorded otherwise. Findings distinguish a broken step from a branch not exercised. Secrets are neither recorded nor photographed.

## Quick start — completed browser portion

Read `/docs/`, `/docs/run/overview/` and `/docs/run/install-with-compose/` (all sections). Signed in with the supplied administrator on the already running installation, reached Home and saw accessible workspaces and their applications. Followed Settings (found in Account → All settings) → Security → People → New person, entered username and name, created the person and acknowledged the one-time password-link dialog. The stated controls, no-roles state and recent activity match. The password link was not passed to another person; no secret was retained.

Not run (host): prerequisites, source checkout/private GitHub App, configuration/secrets, Compose, first-admin CLI, HTTPS issuance, backups, upgrades and shutdown. These are explicitly excluded by the wave and cannot be called verified installation instructions. Read-only judgment: expected outputs, recovery links and volume-loss warnings are clearly stated. Fresh installation/first-ever sign-in is not reproduced by signing into the supplied existing installation.

## Numbered findings

Findings are listed below, in the units where they were observed.

## Things created on the installation

- Person `reader-c11`, display name **C11 Reader**. Initially no password set or grants; later checkpoints and the final ledger supersede that initial state. Account creation is permanent (people can be deactivated, not deleted).

### 1. Empty hierarchy has no documented way to create its first root — blocks the reader

Pages: `/docs/guide/model/create-a-workspace/` step 5; `/docs/guide/use/add-a-record/` steps 1–3; `/docs/guide/use/arrange-records-in-a-tree/` “Rename or add a child”. Created `reader` with the default model, opened Network, then Stops → Add Stop. Parent reports **Nothing selected / No matching objects**. Cancelled, selected Cantons: **No cantons in this workspace yet**, with no Add action or node menu. The guide only explains adding a child of an existing record and says to provide an allowed parent first. As a newcomer I cannot create the initial parent through these screens. Not a claim that no API/import workaround exists. Evidence: `01-empty-cantons.png` (visually inspected), `02-no-parent.png`.

Created: workspace `reader`, key `reader`, using Public transport stops of Graubünden 1.0.0. No records copied at creation, as documented.

## Look after data — first group executed

In `reader`, completed **add a record** for a top-level Operator, **correct a record** (single-field save, then whole-record form), **see who changed what** (Values and expanded before/after `C11 → C11R`), and **delete a record** without dependants. Search found the corrected name. Deletion returned to the filtered list with no matches, as expected. Created Operator `2190a18c-f777-410b-9471-181677970f23` (`Reader test operator`, renamed `Reader operator corrected`), then deleted it. No records in Graubünden were deleted. Operator SBOID was required; leaving it empty invoked the browser's required-field validation, then supplying it allowed creation.

The concurrent-edit refusal, dependent cascade and cancellation branches are not covered by these successful saves. Full filtering, hierarchy, relation and workbook paths remain in progress.

## Look after data — reference-data group executed

Completed **start from home/open an application**, **switch workspace** (`reader` → Graubünden via selector), and **find and inspect**: search `Chur`, numeric Is filter `8509006`, open Chur Wiesental, inspect fields/path/relationship sections, Back to list. Search/filter state was retained. In a new isolated change set, completed **relate records** (add Bus to Chur Wiesental, incoming/outgoing label and candidate paths visible), **create an owned related record** (English parent, Translates preselected, Name/Translated name/Active), and **stop offering a value** via exclusive end `2026-12-13`. Review shows the stop field change and added name record. Live was not changed.

Created: Graubünden change set **C11 reader exercises**, ID `ac90f364-d78d-44cd-8fbd-c643be6a219d`, initially from current Live. Contains the Bus relationship, Chur Wiesental end date, and owned Name translation **C11 reader Wiesental English** under English. This set must be removed as a unit during cleanup; do not publish it.

The optional relationship-removal, single-replacement, conflict, stale-preview, and invalid-candidate branches have not yet been executed. No read or save error was observed on these successful branches.

## Look after data — matrix group executed

Completed **see and fill relationship coverage across ancestors** on two collections in the C11 change set: Municipality names → Filter → None → Done correctly yielded **No rows match these filters** across the five shown languages. Operator names offered None cells; focused the first cell and pressed Enter, opened **Aelplibahn Malans Genossenschaft · en**, chose **Create name translation**, supplied Translated name and created it. Cell became **One**. Reopened, cleared Active and saved; cell became **Inactive** with the content still present. These controls and the guide's explanation matched.

Created inside the C11 set: **Aelplibahn Malans Genossenschaft en**, English, translated name `Aelplibahn Malans reader`, then Active = No. No Live publication. History-only, conflict, several-record, link-existing and failure recovery branches are not demonstrated by this matrix execution.

## Look after data — hierarchy group executed

Completed ordinary **build/change hierarchy** move and **reshape across types/change back** inside the C11 set. Used ArrowRight to expand the canton and Shift+F10 on Chur Wiesental's searched tree row; moved it to Bonaduz and checked `Graubünden / Imboden / Bonaduz`. Moved to Top level, which clearly said **Becomes Canton**. Preview required choosing the resulting type; chose Canton and inspected **Ready to apply**, eight values and five relationships kept in history, then applied. Moved the resulting Canton back beneath Chur; preview showed Canton → Stop and **13 values or relationships restored**, including the stop number, dates and mode/operator/system-code relationships. Applied and returned to its original type and parent. ID stayed stable. No publication.

Multi-record selection/move, add-child, insert/remove-level, a 500-record refusal, invalid cycle, concurrent plan change and published-history restoration were not exercised by this single-record round trip. The guide accurately distinguishes a move that preserves type from one that opens restructuring.

## Look after data — bulk group executed

Used explicit selection of Chur Wiesental, Change values → Change a field → Abbreviation → Set to `C11R` → Change none → Preview. Preview said one would change and none refused; Apply reported **1 changed, 0 refused**. Done returned to the table. Change relationships → Served by mode → Remove listed Bus and Train with counts `on 1 of 1`. Selected Bus, Preview, Apply: **1 relationship changed**, no refusals; table retained Train. This exercises both dialogs and result handling on one selected record, not the several-record/all-matching or partial-refusal branches. These actions also created retained bulk-job records; their identifiers are not yet collected.

Export from Workspace actions warned explicitly that search `Chur Wiesental` was not applied, matching the guide. Chose For people; both started/completed notices appeared with Download and View job. Workbook downloaded as `stops-export.xlsx` under this notes directory. No attempt to open it in Microsoft Excel has been made (Excel is not supplied by the browser).

## Look after data — workbook return executed

Correction to the earlier export checkpoint: the first automated Download attempt used the wrong element role and did not save a file; that was an automation error, not a guide defect. Reopened the export through Jobs, followed its Download link and saved `stops-export.xlsx`. Export job `aaf89a9f-c7f1-4449-8b96-9cfdf23e98ea`: 2,443 Stops, 2,076 Served by mode, 2,443 Operated by, 575 KB, change-set version 11.

Completed **manual import of an untouched exported workbook**: Workspace actions → Import → **Import without the assistant…**, File, Profile None, Only if unchanged since the export, Preview. Import job `48392372-3c09-435d-9834-96eb13f1f72f` read the saved layout automatically; preview: 6,962 unchanged, zero creations/updates/refusals. Load the file finished **Completed**, 6,962 unchanged, zero refusals/unprocessed. This checks actual parsing and execution, not only the preview. No AI task started. The assistant bypass is clearly explained and worked.

Not run: editing cells in Microsoft Excel, columns-per-parent workbook creation, a supplier profile's next-version/rename/delete-missing branches, and stale-version refusals. These are coverage gaps, not successful end-to-end paths. Additional Look after data paths pending: multi-record move/delete, mapping-grid replacement, cross-workspace transfer, retired/unavailable and appearance/phone navigation.

## Change with approval — direct publication/history group

Read the journey and its linked preparation, review, publication, live-work, earlier-publication and next-model guides. Graubünden has **No publications yet**; its C11 exercises validated and the Publish confirmation could be opened and cancelled, without publication. An additional empty Graubünden proposal **C11 reader publication**, ID `b29924fc-395d-427c-aff8-68e88b8bc3f5`, was inadvertently created while recovering an automation workspace-switch race; it contains no edits and must be discarded during cleanup. No Live Operator was created in Graubünden by that attempt.

In `reader`, created Operator **Reader publish operator** (`0c1c1eb3-4090-4686-972f-3733add8aa61`, SBOID `ch:1:sboid:C11-reader-publish`), then proposal **C11 reader publication** (`83464356-edda-4269-bbf1-4c7ff76c4899`). Renamed it inside the set to **Reader published operator**, reviewed its Name change, validated (**Change set validation passed**), confirmed publication and opened **Publication 1**. Its read-only banner and saved model were present. Publication ID `3b785633-dea6-4a2b-a278-3f34ee0b0ae4`. Opened its Operator snapshot. Withdrew it through More actions and confirmation: notice says Live and publications remain, no Current mark, row says Withdrawn. Started **C11 reader from history** from that snapshot, checked the source/model warning, then discarded the empty history proposal.

Completed direct **prepare/review/validate/publish**, **browse publication**, **withdraw publication**, **start from publication** and **discard unfinished work** branches in `reader`. Not yet run: two-person submission/send-back/resubmission, concurrent Live conflict, next-model conversion, migration+publication, retained-publication comparison. Publication/withdrawal in Graubünden is excluded by the wave.

### 2. Supplied contributor cannot sign in — setup, fixed

Page `/docs/guide/use/propose-a-change/`, prerequisite Contributor sign-in. Opened a separate browser context and submitted the contributor username/password provided by `guide/reference/.env` (neither printed). Sign-in returned **The username or password is not right. Check both and try again.** No Contributor session was established. The administrator's People list had no contributor among its five active people after creating C11 Reader. This is an execution/setup blocker, not evidence that the prose's proposal steps are wrong. No repeated password guessing.

The supplied Approver credentials also returned the same wrong-credentials message on one attempt. To continue without altering those accounts, used the guide's documented account/password/grant flow for the already created `reader-c11`: made a replacement one-use link, opened it privately, set a generated password held only in browser-controller memory, and signed in successfully. Direct grant: **Contributor**, workspace **reader**, writes narrowed to **Operator**; reading remains workspace-wide. The table shows `reader / Contributor / Operator / Directly`. This supplies an isolated alternative for the proposal path; it does not repair or verify the supplied role accounts.

## Change with approval — two-person branch recovered and executed

Using the new isolated Contributor account in `reader`, completed Propose a change → name **C11 reader approval** → Start and edit (this also opened the ordinary whole-record form), changed the Operator name to **Reader approved operator**, saved and submitted with a comment. Proposal ID `38b04861-fe3a-467f-8277-8a987fd96f82`. Waiting banner froze editing. As Guide Admin, found Home → Waiting for your approval → Review. Decision showed the submitted version/person/comment. Send back with no comment was refused with **Say what needs to change.** Added the reason and sent back; Contributor saw the reason and Submit for publication again. Resubmitted with the source explanation; Guide Admin reviewed the new request and chose Approve and publish in `reader`.

Historical checkpoint (superseded by the resumed run below): the supplied-account blocker remained; it was bypassed with the documented person/password/grant workflow, not by changing the supplied accounts or installation policy. The second-person-required self-approval refusal and concurrent publication conflicts remain unverified. Contributor's grant was intentionally narrow and only Operator writes were exercised.

## Shape a model — new model started

Created empty draft **C11 reader model**, ID `94af7b42-317b-48bf-af86-ebe36a6b8ddb`, using Settings → Model → New draft → Empty model. It opened Valid, version 1, no definitions. Application action created **Stops reader**; version 2 showed one issue until a type/view is added, matching the guide's warning that an empty draft needs these. It has not been installed or applied to any workspace. All future work stays in this draft or `reader`; no Graubünden release is activated.

## Shape a model — definitions and empty preview group

In the C11 draft added top-level **Stop** and **Operator** types. Stop generated a table and record page, as documented. Added shared Text attribute **Stop code**, Required and Unique on Stop; attached the same attribute to Operator without Required. Added optional many-to-one **Operated by / Operates**, Stop → Operator; direction and cardinality controls matched. Draft reached Valid, version 7. Preview correctly said `Empty record: Stop is new, no records yet` and explained that `reader` runs another model, so none of its records is read. Empty page showed the field and generated relationship panel; no records were written.

The preview offers a read-only example even when it cannot show a populated record from another model. Populated draft preview, numeric bounds, candidate criteria and relationship-carried fields remain unverified in this group.

## Shape a model — page/table layout group

Completed empty-record **edit a record page** and **choose table columns/filters/sort** branches: Preview → Edit layout; created Main field group **Stop identification** moving Stop code into it, set the line under the title to Stop code, selected Table, added Operated by to Columns and Filters, and changed Default sort to Stop code. Every Apply saved a draft step; version 12 remained Valid. Returning from the layout editor went directly to the type definition (no extra Back to definition was needed). Generated page was already declared by type creation, so Declare its page was not required.

Not yet run: related-field/ancestor columns, multi-panel reorder/hide/remove, phone menus, populated preview and absence/refusal states. No guide mismatch was observed on the completed layout steps.

## Shape a model — views/navigation/release group

Added **Reference lists** navigation group and placed Stop in it through Move to group; added optional-relation mapping grid **Stops to operators**; Undo removed that last step and Redo restored it. Valid at version 17. Opened Install and activate, reviewed key/version/name and its explicit list of unchanged workspaces, then installed isolated model **c11-reader-model@1.0.0** into a new empty owned workspace **reader model** (key `reader-model`). Chose a separate workspace so this new model did not replace the already published `reader` definitions or any reference workspace. Success explicitly says installed and active; the editor now marks definitions **Released** and keys **Key fixed: released**. Draft continues from the release.

Created: model release `c11-reader-model@1.0.0`; workspace `reader-model`; application Stops reader with Stop/Operator types, shared Stop code, Operated by, two generated tables and one mapping grid. No data created in it yet. No activation or model installation in Graubünden. Scope limitations: tree and relation-matrix view creation, incompatible activation, separate install-only and already-installed activation branches are not covered by this release.

### 3. Supplied consumer credentials cannot obtain access — setup, fixed

Page `/docs/guide/integrate/get-a-token/`, “Make the exchange”. Exchanged the supplied `GUIDE_CONSUMER_CLIENT_ID` and `GUIDE_CONSUMER_CLIENT_SECRET` using client_secret_basic, grant_type=client_credentials and scope=consumer against the supplied HTTP instance. HTTP **401**, `{"error":"invalid_client","error_description":"The client is unknown, inactive or its secret is wrong"}`, Cache-Control `no-store`. Both credential variables exist; neither value was printed. This prevents continuing the exact supplied-client consumer sequence. The guide's diagnostic explanation matches the response. No retry loop or credential guessing.

## Manage access / Integrate a system — isolated client and consumer read group

Created **C11 reader client**, ID `75289c91-564f-4f25-b7cb-3c751fe7b3fe`, through the documented New client/one-time-secret flow. Secret retained only in controller memory. Granted **Stops API in Graubünden**; no management access initially. Exact same OAuth exchange succeeded HTTP 200, consumer audience, expires_in 3600. This recovers the reader exercise without repairing the supplied credential pair.

Completed consumer discovery/index/OpenAPI, direct object read for the guide's exact Tschamut-Selva UUID, first list page, all **13** `operator=MGB-fo` results one page of one at a time to the final null cursor, and conditional GET **304** with its prior ETag. Actual request/response evidence (no bearer tokens) is in `api-evidence.json`. The guide's counts and shape match. Dated list `asOf=2026-11-02` returned 200 and `asOfApplied: [Stop]`. Crosswalk `8505173` → Wikidata returned `Q33467326`. Two-row resolve returned found/score 900 for row-1 and not_found/NO_MATCH for T-9999, counts 1/1. Fictional T-0300 with expect=one returned **409 AMBIGUOUS_MATCH**, count 2 and top score 90, as described.

These are actual network requests from the controller using Fetch equivalent to the printed HTTP requests, with supplied instance origin substituted. A complete filtered live read is verified; a consistent full-snapshot extract and durable external mirror are not yet verified. New client also granted Stops API in `reader` for isolated publication/event checks.

## Consumer snapshot/events and access boundary

Confirmed publication resulting from approval: `58efc7e6-bcae-4670-91a4-99ff7bf5215e`, active in `reader`, eventSequence 10. Earlier withdrawn snapshot has sequence 7. Read the contract's Operators list pinned to the active publication: one record. All-stops pinned there is correctly empty. Events after 7 returned no watched Stop events, caughtUp true at head 10; continuing with its cursor (no after) returned 200 caughtUp true. This matches the contract, which watches Stops, not the changed Operator. No populated watched-event/delivery has yet been demonstrated.

Failure checks: invalid `asOf=yesterday` → HTTP 400 `INVALID_AS_OF` with the precise calendar-date message; version 99 → HTTP 404 `CONTRACT_VERSION_NOT_FOUND` with served versions. These match the guide. Granted the new client Data owner only in owned `reader` and `reader-model` for separate management API exercises.

## Appearance/phone unit

Completed Appearance choices: Website purple, Dark, Compact, palette A, Always faintly. At 390 × 844 every named control and its help stayed readable (`03-appearance-phone.png`, visually inspected). Settings: Appearance opened the phone navigation drawer. Restored Normal/System/Comfortable/palette B/hover and 1280 × 900 afterwards. These are this test browser's preferences; no installation setting changed.

## Integrate a system — management discovery and bounded batch

Read the live public OpenAPI document reached by the guide's API reference (no repository source). Obtained a separate management-audience token for the new client after granting Data owner in **reader** and **reader model**. Caller, capabilities, own model and Stop collection all returned 200. Model release `685fd41c-3e9b-4f72-939b-e446938dd7ba` identifies the installed C11 model. Submitted an atomic inline two-item create batch in `reader-model`; both applied, each version 1, job **db20407e-4844-4547-950a-3f8db6f831ae**. Exact body and idempotency key retained in `batch-request.json` without credentials.

Created API Stops: **Reader API stop 1**, `84db6234-619b-4799-bc61-c2d545d11ddd`, Stop code `C11-API-1`; **Reader API stop 2**, `d09e08fa-07fc-4f1c-a29a-1ee39c05b3c0`, Stop code `C11-API-2`. Earlier form-created Stop **Chur reader example**, `0a249609-67b2-448d-b1cc-92781c06386d`, code `C11-CHUR`.

Replayed exact request/key: 200 and the **same job ID**, no duplicated work. Changed policy under that key: **422 IDEMPOTENCY_KEY_REUSED**, message says nothing was run. Guide correctly says a changed request is refused (it does not promise 409). Full token-free responses remain in `api-evidence.json`.

## Background preview/cancellation unit

Submitted a two-item background atomic preview in `reader-model` (job `d6389950-ca4e-458f-a08e-87c5d984d693`). 202, then Awaiting confirmation; complete coverage 2/2, two would create, zero refusals. Opened the job in the browser and read all two outcomes. Chose **Cancel preview** → **Discard the preview**. Settled at **Cancelled**, retaining the readable preview and having written neither background Stop. No worker restart, crash or cancellation after committed chunks was attempted.

### 4. Job-cancellation guide omits the waiting batch button's label — small

Page `/docs/guide/use/follow-and-cancel-a-job/`, step 3. It names **Cancel job** and **Cancel import**, but the batch preview page offers **Cancel preview**. Guessed that control; the following **Discard the preview** confirmation matches the guide and cancellation worked. This is a small label gap, not a failure to cancel. Exact job and state above.

## Production checklist — external probes and screens

Actual origin is the assigned **http://localhost:8480**, not a public HTTPS deployment. Terminal curl: `/health/live` 200 `{"status":"ok"}`; `/health` 200 same; `/` HEAD 200 HTML; public `/metrics` 404. Application response has the documented HSTS max-age 31536000, nosniff, same-origin referrer policy, frame-ancestors none and DENY. HTTP 200 here is not evidence of production HTTPS/redirection. TLS certificate trust/renewal, DNS, firewall and balancer trust are not run (host / no supplied public HTTPS origin).

Deployment: model/workspace administration, jobs and webhook subscriptions On; migration revision `20261123_01`, PUBLIC_URL/CORS use the assigned HTTP origin, cursor/sealing keys show Set, persistent job path is shown. No settings changed. Operations: engine **0.16.0**, one live ready process; all eight listed background threads Running; **17 of 18** workspaces served, `c10-language-pictures` unavailable because schema 0.9 is outside this engine's window. Guide correctly warns readiness 200 does not prove every workspace usable. **No backup has been rehearsed**. These are reference-environment limits, not guide defects or a production acceptance.

Not run (host): Compose state/ports, PostgreSQL version/collation/extensions, private metrics/log correlation/alerts, secrets custody, filesystem persistence after restart, restart/takeover, backup/restore rehearsal, upgrade/cutover and host move. No installation or host command was executed. Not run (AI): enabling, assistant tasks, proposals or explanations.

## Resumed run — supplied consumer client recovered

Both supplied role accounts now sign in successfully (Contributor: Guide Contributor; Approver: Rita Approver). Findings 2 and 3 are reference setup issues, fixed before this continuation, not open guide defects.

With the supplied consumer client, completed token exchange (200, token kept only in memory), consumer index and generated OpenAPI (200), Tschamut-Selva object read (200), conditional GET (304), all 13 one-record MGB-fo list pages to null nextCursor, crosswalk to Q33467326, two-row resolution (one found / one not found), and T-0300 ambiguity (409). Dated read and publication catalogue results follow in the next checkpoint. Evidence: `recovery-api-evidence.json`, with no credentials. No client was created for this continuation.

## Change with approval — supplied-role branch recovered

As Guide Contributor in Graubünden: opened Chur Wiesental → Propose a change → named **C11 supplied contributor review**, edited Abbreviation CHWI → C11SUP, reviewed and submitted. Change set `518005aa-b4d3-4ec6-979b-ccbc8a13c3c0`, version 2. As Rita Approver: Home showed the request, Review opened the named submitted version/comment and record difference. Blank Send back refused with **Say what needs to change.** Supplied a rehearsal reason and sent back; Contributor saw Rita’s reason, could edit again, then resubmitted with a new comment. Rita’s refreshed Decision showed the new request/comment. Left waiting, never approved or published in Graubünden. Screenshot: `04-supplied-contributor-waiting.png`. Role account prerequisites now work.

Dated supplied-client read returned `asOfApplied: [Stop]`; Graubünden publication catalogue returned 200 with no items. A fixed consumer baseline there is unavailable without arranging publication, which this wave forbids in Graubünden. Earlier owned-workspace publication evidence remains separate.

## Change with approval — second-person refusal executed

In owned `reader`, followed `set-an-approval-policy`: saved approval required plus second-person required (both were off before this unit). Created **C11 second person refusal**, `f978267d-f6eb-4f02-a0ed-30cdf7f10aef`, submitted its empty version 1 as Guide Admin, opened Review and decide. The review displayed **A second person must decide this request.** and no Decision panel. Screenshot `05-second-person-refusal.png`. Withdrew the request; **Request withdrawn.** confirmed that it remains editable. No publication occurred. Policy restoration and discard are recorded below once completed.

## Receive notices — settings and following executed

Read the complete journey, Mail and linked setup/email/follow/inbox guides. Notification email correctly says **Your account has no email address, so there is nothing to choose here.** Email choices are absent (`06-notification-email-unavailable.png`). Mail has saved settings and an empty message list (Waiting/Sent/Failed all zero); no settings changed and no test mail sent because no intended mailbox is supplied. Followed owned `reader` from Home, checked Following, opened Notification email and saw reader with following date, then Stop following removed it. Inbox approval/send-back notices worked during the supplied-account unit. This completes follow/unfollow and unavailable-email paths; delivery, digests and publication follower notice are not yet verified. SMTP save/replacement/removal excluded as installation settings; mailbox delivery unrun for lack of a recipient and mailbox.

Restored `reader` approval policy to its original two unchecked settings; saved successfully and checked both values. Empty second-person test set remains open after withdrawal for cleanup.

## Manage access — local group and inherited grant executed

Created **C11 reader2 group** (local), added Rita Approver by Search and tick, granted Data owner only in owned `reader` after removing the dialog’s initially selected C10 history pictures workspace. Rita’s People table explicitly shows `reader / Data owner / Group C11 reader2 group`. Her next Home request offers reader without a new sign-in; opening its Network application and change-set list succeeds. No grant was made in C10 or other workspaces. Group remains temporarily for the publication-notice test, then is removed below. An unrelated existing **C11 reader group checked** was observed and left untouched.

## Run the service — reading and existing external evidence

Read the journey and linked built pages for database, configuration, health/startup checks, monitoring, troubleshooting, several processes, backups/restores, upgrades, model releases/rollback, HTTPS, secrets/keys, sign-in/mail, background jobs, webhook delivery, security/production checklists, licence/source and developer setup. Commands distinguish initial refusal (repair/restart) from a running database outage (restore connectivity), and preserve keys, database/file pairing and the automatic-HTTPS overlay during upgrade/recovery. No additional actionable prose blocker identified in these readings. No host command was executed.

Completed external probes and Deployment/Operations screens are recorded above; these are reused rather than repeated. Not run (host): clean installation, intentional startup failures/outage, PostgreSQL inspection, multi-process startup/takeover, TLS/DNS/firewall, renewal, setting changes, storage/secret replacement, backup/restore/rehearsal, upgrade/cutover/rollback, host migration and developer setup. Source-offer link destination/content is not verified against a source revision. Not run (AI): optional AI setup and tasks. The existing HTTP reference installation is partially available (unsupported-schema workspace) and has no recorded restore rehearsal; it is not evidence of production readiness.

## Receive notices — publication follower path executed

As Guide Admin, followed owned reader again. Rita, temporarily holding Data owner through C11 reader2 group, opened the withdrawn empty second-person test set, validated it, then published it with confirmation. Success: **Published as Publication 3. Reviewed changes are now live.** This publishes no authored record changes and only affects owned reader. Guide Admin’s bell received **Published: ‘C11 second person refusal’ / By Rita Approver**; this verifies a different publisher generates the follower notice. The set is consumed and Publication 3 is retained. Opening the notice and removing follow/group are the next cleanup checkpoint. No Graubünden publication.

### 5. Active publication follower notice does not open its publication — costs time

Pages `/docs/guide/use/follow-a-workspace/` step 3 and `/docs/use/inbox-and-approvals/` opening notices. Guide Admin follows reader; Rita publishes its empty test proposal as Publication 3. Clicked its **Published: ‘C11 second person refusal’** entry first in the bell and then on Notifications. Both mark the notice read but leave the person in the inbox (URL `/notifications` on the full-page attempt), with no explanation. Independently, Rita’s Publications screen shows Publication 3 **Current**, ID `6e9047e1-56b3-4179-8191-3c065033fdd8`. Guide Admin retains whole-instance Browse. This is outside the guide’s stated unavailable-publication/access exception. Evidence: `07-follower-notice-stays-in-inbox.png`, visually inspected. Workaround: navigate to the workspace’s Publications list. No source was opened to diagnose the cause.

Cleanup completed: stopped following reader and deleted C11 reader2 group with confirmation, removing its Rita membership and Data owner grant; Rita’s original Graubünden grant remains. Publication 3 is retained, and the second-person test set is consumed.

Webhook sample: extracted the built page’s Copy-to-clipboard code, ran its Python verification with the public demonstration key and sample clock. The original sample verifies, one extra body byte fails, and timestamp +301 seconds fails (`webhook-sample-check.json`). No receiver, real signing secret, subscription or delivery was created for this check; live delivery/retry/rotation/reset remains unrun for lack of a prepared receiver.

## Manage access — custom role creation/editing executed

Created **C11 reader2 scoped reader** from Reader using Start from. The matrix showed Browse checked and all other action groups unchecked. Saved its explanatory description. Reopened Edit and selected Delete role while it was ungranted; named confirmation is checked in the next unit. This verifies clone/edit controls and keeps the original Reader untouched. No broad instance grant, policy or shared signing key changed. Provider provisioning/linking, installation-wide factor policy and ordinary-local-sign-in switch were read but not changed (installation-setting exclusion). No provider registration, authenticator device or passkey was supplied for their complete sign-in/recovery branches.

## Integrate a system — supplied-client populated event read

The exact documented `after=63&event=stops-changed&pageSize=1&payload=full` request succeeds: first event is creation of Selva, via Alpsu spv., position 207, with full current object and `caughtUp: false`; the response carries a lasting cursor. The event is real historical reference data, not a newly published test change. Its composition/head position differs from the guide’s earlier capture, as the page permits. Identity traversal/resume is recorded in the next checkpoint.

## Integrate a system — complete identity event traversal/resume

With the supplied client, read `stops-changed` identity events from after=0 in pages of 1,000: three pages, **2,443 events**, finishing `caughtUp: true`, head 8927. Continued once from that response’s cursor, without after: 200, caughtUp true. No new live stop mutation was required. Evidence contains the exact pages and cursor scopes in `recovery-api-evidence.json`. This exercises complete retained event enumeration and caught-up polling; it does not establish a durable external mirror, event-expiry recovery or pushed delivery.

Isolated client rotation: generated one replacement with default 24-hour overlap, then a second with 1-hour overlap. Fresh OAuth exchanges with both replacement secrets return 200 during overlap. Secrets stay in controller memory. Explicit old-secret ending/deactivation checks follow; the supplied consumer client was untouched.

## Manage access — client handover checked

Both replacement secrets authenticated during overlap. Chose End now on the older replacement (matched its suffix) for the isolated C11 reader client. The next checkpoint records its refusal and surviving secret. Custom role deletion was confirmed and the role is removed. No new client was created in this continuation; two replacement secret records were added to the earlier client’s activity.

## Integrate a system — management baseline, paging and raw feed executed

With the isolated C11 client’s existing Data owner grants, paged all three reader-model Stops at pageSize=1 to null nextCursor; changing search with the saved cursor returned INVALID_CURSOR. Read a per-type Stop code equality filter and got the intended API Stop. Read owned reader’s active Publication 3 catalogue: feedPosition 11. Loaded its complete one-record object collection by explicit publication ID, saved that generation and checkpoint together in `baseline-generation.json`, then raw feed after=11 returned empty with nextAfter=headPosition=11. This is a complete small fixed-publication baseline and caught-up continuation.

Separately paged reader-model’s populated raw feed from 0: first two entries, then after=2 returned its remaining entry with nextAfter=headPosition=3. An ahead-of-head checkpoint returns 409 FEED_POSITION_AHEAD and tells the reader to rebuild from a baseline. A cross-type asOf read returns AS_OF_NOT_SUPPORTED naming the per-type/query route, matching the guide. These are HTTP-level sequence checks and a notes-file mirror, not a deployed integration or restore trial.

Client old-secret ending verified: old replacement exchange returns 401; new replacement returns 200. The original earlier-run secret was not available to this continuation and was not printed or guessed.

## Manage access — isolated client deactivation executed

Confirmed Deactivate C11 reader client. Both its already issued management bearer token and a fresh exchange using the surviving replacement secret now return **401**. Restore is offered. Left this test client deactivated, preserving its name, grants, activity and secret records for owner cleanup. This is the client created by the earlier run, never the supplied Stops reader client. Its exact ID is in the earlier ledger.

A model-aware query in reader-model also passed: Stop code equality, explicit name/code selection, one result and total 1. API evidence is token-free.

## Build check

`GUIDE_OUT=_build/C11-READER2 npm run build` in guide completed successfully: 253 pages, 22.42 s, exit 0. Warnings: `caddyfile` highlighting falls back to text (twice), and `/404` route conflict resolves to the higher-priority 404 page. No guide source was edited to address these warnings. Build was isolated from other waves.

## Manage access — test-person password recovery executed

Made a fresh one-use password link for the earlier-run **C11 Reader** (`reader-c11`), copied it privately, opened it in a separate browser, set a generated 32-character password held only in memory, and saw **Your password is set. You were signed out everywhere.** Sign in opened the password form; signing in reached its single reader workspace. Account shows This browser and the Operator-only Contributor proposal allowance, with no Live/Publish/Approve permission. The original “No password set” ledger entry is superseded. No reset link or password is recorded. Authenticator enrolment continues below.

## Manage access — authenticator enrolment

On C11 Reader’s Account, Set up an authenticator app shows the key and code form inline. Supplied a valid TOTP generated from that private key in memory; confirmation showed ten recovery codes. Held them only in memory and chose I have kept them. Signed out and signed in again with password: **Enter your code** correctly required the second step. The recovery-code sign-in/removal outcome is recorded next. No installation-wide factor requirement was changed and no key/code screenshot was taken.

## Manage access — recovery-code sign-in executed

At the second-step screen, chose Use a recovery code instead, supplied one of the ten held-in-memory codes, and signed in successfully. Account offered New recovery codes… and Remove… afterwards. This verifies the saved recovery-code route in a real browser, not a simulated assertion. Admin removal of the test factor follows; it has not yet been reported as removed.

## Manage access — lost-factor administration executed

Refreshed C11 Reader’s People page: **Second factor: authenticator app**, setup time, **9 of 10 recovery codes left** matched the single recovery sign-in. Followed Remove second factor… → named confirmation → Remove second factor; success says **C11 Reader’s second factor was removed.** Then opened Sign out everywhere and its named confirmation. No factor on another person was touched. Password-only sign-in after that confirmation is the final check below.

## Manage access — factor recovery completed

Confirmed the administrator’s Sign out everywhere for C11 Reader, reloaded that person’s browser, and signed in with its password alone. Home/Account became available without a factor challenge, proving the removal and recovery at the real sign-in boundary. The temporary authenticator and all ten recovery codes are now invalid. No secret was written. The account remains active with its earlier Operator-only Contributor grant and unrelated pre-existing group membership unchanged.

## Look after data — two-record refusal and deletion executed

In owned reader-model, selected Reader API stop 1 and 2. Change values → Stop code → Set to C11-CHUR → Change none → Preview reported **0 would change, 2 would be refused** and **Attribute 'Stop code' must be unique** on both. The value belongs to Chur reader example. Closed the preview with Escape (nothing applied). This tests an actual two-record unique-value refusal.

With the same selection, Delete → Delete none → Preview: **2 would be deleted**, no dependants or relationships. Confirmed Delete 2 records; result **2 deleted, 0 refused, 0 not reached**. Both API test Stop IDs from the earlier ledger are now deleted, only in owned reader-model. The result keeps per-item outcomes. This is bulk deletion without dependent cascades, not evidence for cascaded or partially refused deletion. New preview/execution jobs remain in Jobs.

## Current coverage limits to carry into final report

The earlier-run units are preserved, not rerun. This continuation adds repaired-account approval/refusal paths, complete consumer event reads, management baseline/feed/paging/query, groups/custom-role lifecycle, isolated-client rotation/deactivation, personal password/factor recovery, publication-follow notices, and two-record bulk refusal/deletion. It does not turn earlier explicitly unrun branches into passes. In particular: advanced model authoring/migrations/contract version changes, workbook onboarding/supplier-layout evolution, dependent cascades, concurrent editing/publication races and cross-workspace transfer remain outside completed end-to-end evidence so far. Host and AI exclusions remain as assigned; missing receiver/mailbox/provider/device branches remain separately identified.

## Look after data — mapping-grid save and conflict recovery

Created Operator **C11 reader mapping operator**, ID `66b4422c-705b-434f-9d30-a1a52cdd75e4`, Stop code C11-MAP-OP in owned reader-model. Opened Stops to operators; Chur reader example was Unmapped. Map → selected the Operator → Save mapping made it Mapped; reopening showed that target under Currently. A rapid reopen/remove after the save met **Mapping conflict**, with the current operator named and **Continue with my selection**, exactly the guide’s recovery controls. Followed that recovery; removal outcome follows next. No existing reference-world connection was changed.

Security checklist boundary: unauthenticated `GET /api/v1/workspaces` at the assigned origin returned HTTP 401 JSON `AUTHENTICATION_REQUIRED`, with the stated access-token guidance. Public docs/health are not workspace access. Request ID `40859b82cda54dbca56e714fc7b4244b`; no internal logs accessed.

## Look after data / Shape a model — retirement browser path

Mapping recovery completed: Continue with my selection, then Remove mapping succeeded; grid returned Chur reader example to Unmapped and kept both records.

In owned reader, workspace management explicitly says deletion is unavailable because it has publications. Retire… → Retire workspace retained its data and opened the application with **Retired · read only** and **Read-only workspace / changes are disabled**; Add Stop was absent. Record/publication browsing and reactivation continue below. No default or reference workspace retired.

### 6. Retired workspace still says edits apply immediately — small

Page `/docs/guide/use/open-a-retired-or-unavailable-workspace/`, steps 1–2; `/docs/guide/model/retire-or-delete-a-workspace/`, step 2. Opened retired owned reader as instructed. Alongside its correct read-only marks, the Live context band still says **Edits apply immediately in this workspace.** The controls respect read-only in the observed empty Stop collection, so this is contradictory screen wording rather than an observed write bypass. Screenshot `08-retired-live-banner.png`, visually inspected.

## Retirement — retained browsing verified

While reader was retired, opened Publication 3, then its Operators collection and Reader approved operator record; the named record heading rendered. Publication’s pinned-model and read-only banners remained. The workspace’s data was not deleted; its published-state deletion explanation matches the guide. Reactivation is the next checkpoint. No retired-workspace write was forced through an API; the observed write controls were absent.

## Final checkpoint and consolidated report

Reader reactivated successfully; original approval policy and not-followed state retained. C11 Reader was deactivated with confirmation; its next browser reload returned to Sign in, matching the leaver/session rule. No remaining test factor. About reports engine 0.16.0, management v1, model language 0.10 and the corresponding source-tag URL; source contents unverified.

See `report.md` for ranked findings, the consolidated journey table, explicit unrun paths and final artifact ledger. Exact continuation refusal/deletion job IDs are in `job-ledger.txt`. No test secret value was found in stored text. Build remains passing; only wave notes/progress changed after it.

## Continuation: concurrent editor conflict completed

/docs/guide/use/correct-a-record/ — Guide Admin and Rita opened the same reader-model Stop in separate contexts. Admin saved v2 first; Rita’s v1 save was refused with The value was not saved / Object version has changed. Her proposed name remained in the input, and Current saved value showed Admin’s v2. After reviewing it, Rita saved again successfully. Screenshot 09-editor-conflict.png. Temporary direct Data owner grants to Rita in reader and reader-model were added for these paths; no reference write.

## Continuation: live-versus-proposal publication conflict completed

/docs/guide/use/continue-live-work-while-a-change-set-is-open/: proposal C11 reader live conflict a2ec407f-600a-4178-93de-46d15a1ecfb3 changed the Stop name, while Rita changed its Stop code in Live. Validation passed; publication refused with Change set conflicts with the live active data and the exact record ID. Proposal and Live values remain distinct; nothing was partially published. Screenshot 10-publication-live-conflict.png. Recovery uses a fresh current-Live proposal next.

## Continuation: publication race and reconciliation completed

/docs/guide/use/continue-live-work-while-a-change-set-is-open/: fresh set C11 reader reconciled 54c73fff-1569-4ff0-9b1e-040a0d35b6ed re-applied the intended name over current Live and published, preserving Rita’s newer Stop code. Then Admin validated empty race A df883df3-c8aa-4175-8b39-e851572a25b7 and kept its publication confirmation open. Rita published race B 3de28eb0-aae5-4a4d-a299-4daf048a70c8 first. Confirming A refused Active publication has changed; A was preserved. Both races used separate people and browser contexts, only reader-model.

## Continuation: owned hierarchy and matrix preparation

Followed /docs/guide/integrate/submit-a-bulk-change/ to discover reader’s served model and submit an eight-item parent-first atomic batch. It created one Canton, District, two Municipalities, two Stops, an English Language and one owned Name. All eight applied, no refusals, job b810fc92-1cc9-43ea-b6cb-9d6d9d4b5257. Exact request and IDs are fixture-batch-request.json / fixture-ids.json. This is documented API preparation for the browser journeys, not evidence that finding 1’s missing first-root browser action is repaired. Restored/rotated the isolated C11 client for this continuation; secret in memory only.

## Continuation: multi-record hierarchy move completed

/docs/guide/use/move-several-records-together/: expanded Geography, selected Stop A/B with Ctrl+Space, Shift+F10 → Move to…, reviewed 2 records, chose Arosa reader and Move to Arosa reader. Both public IDs now have the Arosa parent (public per-type read), retaining identity. Live in owned reader.

## Continuation: insert/remove hierarchy level completed

/docs/guide/use/reshape-a-hierarchy/: in C11 reader restructure 5af85536-31ff-41d0-b029-994f897cdc64 inserted a Municipality above the childless Chur municipality. Preview required new FSO 9999 and Designation; showed original Municipality → Stop. Applied, then removed the inserted level: preview showed Stop → Municipality, retained public identity, FSO 3901 and Designation kept in history. Reviewed and published the round trip in reader. Created inserted record was removed within the same proposal; no Graubünden changes.

## Continuation: manual workbook draft created

/docs/guide/model/start-a-draft-from-a-workbook/: selected the downloadable Haltestellen_Busbetrieb_Nord.xlsx, Nothing: I will map it by hand, comparison reader-model, and c11-reader-model@1.0.0 as Base release. Created C11 reader manual workbook, draft 0758ce86-c841-48d7-8447-7129309b428c. No AI request; model starts unchanged, profiling reads the source. The submit button correctly changes to Create draft for manual choice (guide says Create and propose generically).

## Continuation: manual workbook binding, dry run and load completed

/docs/guide/model/map-a-column/ and load-a-workbook-into-a-change-set/: manually bound Haltestelle to Stop Name, UIC-Nr to unique Stop code with row key. Other columns and sheets were intentionally left unmapped; no proposed model accepted and no AI used. Resolved a profile-key collision using the offered haltestellen-busbetrieb-nord-2 key. Dry run: all 51 mapped rows checked, 51 creates, no refusals. Load kept the active model, saved that profile, loaded C11 reader manual workbook load into reader-model, 51 created/0 updated/0 unchanged. Reviewed and published the proposal. Draft 0758ce86-c841-48d7-8447-7129309b428c remains; the controller captured the editor URL before review navigation settled; the loaded proposal is identified by name and workspace here, not that stale URL.

## 7. Recurring profile saves use the wrong model workspace — blocks the reader

/docs/guide/use/load-the-next-version-of-a-workbook/, steps 2–4: uploaded the supplied _next workbook to the new haltestellen-busbetrieb-nord-2 profile and explicitly chose reader model for comparison. The 51-row check resolves every binding and has zero refused rows. Accept on UIC-Nr → UIC number fails: The profile was not saved / profile is written for c11-reader-model, and the workspace runs guide-reference-swiss. The profile header simultaneously says Needs a fix and the detail says Valid. No installation or default-workspace changes made. Screenshot 11-profile-wrong-workspace.png. Rename, ignore-new-column and deleting-load browser variants are blocked at this save boundary; trying an explicit owned-workspace address next.

## Supplier profile: explicit-workspace API counterpart

The documented API accepted the same rename and ignored extra column when workspaceKey reader-model was supplied explicitly: saved profile haltestellen-busbetrieb-nord-2 version 2. Check job 821508a0-b3a5-4474-a70d-c2e8b20a86a9 completed with 51 unchanged, 0 rejected, 1 missing. This does not complete the blocked browser Accept path (finding 7). Manual workbook load set was 75c92694-9dcc-412d-a18f-fd909fed3004, published in reader-model.

## Supplier deleting-load API path completed

/docs/guide/integrate/exchange-a-supplier-file/ plus load-the-next-version-of-a-workbook: accepted rename and ignored Capture note via API with explicit workspace after UI finding 7. Import 9ad94504-b7bf-4545-be7d-a474675f6c06 executed 51 unchanged. Set profile missing=delete (version 3), preview job b32a6e42-7c4b-4473-bddf-83edb96044ab: complete coverage 52 items, 51 unchanged, one deleted, no refusal. Executed into own set e90a9638-bb64-4cce-8e7b-12b6a971185d, reviewed Removed Chur reader reconciled in browser, validated and published. Browser recurring Accept/Ignore/load remains blocked by finding 7; API counterpart passes.

## Collection-wide selection and exclusion checked

/docs/use/changing-many-records/ and change-relationships-of-many-records: header selection and Cmd+A selected all 51 stops although only about 20 rows were drawn. Set Operated by to C11 reader mapping operator, preview/apply 51 successful. Cmd+A then unticked Trimmis Cholplatzweg; 50 selected, Clear relationship preview/apply 50 successful. Excluded Stop retains its connection. Bar says count selected, not All matching; explicit server selection mode not yet demonstrated.

## 8. Deletion Preview again retains the stale object version — costs time

/docs/guide/use/delete-many-records/ step 5 and changing-many-records: after 1 deletion / 1 concurrent-edit refusal, Preview again narrowed to refused record but still refused Object version has changed and offered Delete 0 records. It did not refresh the request version as the guide implies. Recovering requires closing, reloading/reselecting the current record, and starting a new preview. Original partial result is correct; screenshot 12-partial-delete.png.

## Partial deletion completed, fresh-selection recovery completed

Guide Admin previewed two reader-model Stops with Delete the rest. Rita saved a new name for one in her own context. Confirming deleted Ardisla and refused La Val, preserving Rita value. Preview again retained a stale version (finding 8). Closed, reloaded and selected La Val Rita afresh; new one-record preview and deletion succeeded. Screenshot 12 inspected.

## Cross-workspace model-mapped move completed

/docs/guide/model/move-records-to-another-model/ and /docs/guide/use/copy-or-move-records/: created saved mapping c11-reader-stops-transfer v6 from guide-reference-swiss 1.0.0 (reader) to c11-reader-model 1.0.0 (reader-model). Rules-based proposal, no AI. Manually mapped Stop number (integer) to Stop code (text); deliberately left duplicate Designation behind after inspecting ATTRIBUTE_NOT_MAPPED report. Selected subtree Chur reader A only. Dry run 1 create, 0 refused, no other relationships. Started move job 788cbc51-4705-4022-b221-4f6a66d20f31, reviewed and published target set 6c155814-47de-4f25-aa93-69c6d9442112 first, then reviewed/published source deletion set 5817da09-cdce-48be-8835-cb9c98a6fcaf. One source removed, zero kept. Mapping, target counterpart and both publications remain.

## Matrix Inactive and History only completed

/docs/guide/use/fill-in-a-relation-matrix/: reader Chur/en cell One → Active unchecked → Inactive, inspected retained content, Active checked → One. Deleted owned Chur reader English via preview, matrix became History only with content from publication 5, explicitly read-only. Create from this prefilled Name, Translated name and Active; reviewed English reader container and created. Cell returned One with a new identity, not undo of deletion. Original Name dd8c435d-7624-48e3-9d84-2460b065b3b3 remains only historical.

## Several matrix state completed

/docs/guide/use/fill-in-a-relation-matrix/: created own System C11 reader municipality codes, key wikidata-municipalities, and codes C11-MATRIX-1/2 mapped to own Chur municipality using documented batch. Initial arbitrary system key was refused by served candidate rule; atomic rollback left no records, then corrected the key. IDs a25248e3-723b-46d8-b5d7-cfdfdea47402, 02b86fa6-5f1a-4a62-bf39-c5d07042c292, ca0bb9fb-5013-4223-a210-e08d03fc59e5. Cell Several(2), inspected both, edited description of first, confirmed Unlink second. Cell One; unlinked code remains.

## Conflict matrix state: supported-write refusal verified

/docs/use/relation-matrices/ and fill-in-a-relation-matrix: tried creating a second counting Active name under the same own English reader column for Chur. Public atomic batch refused DUPLICATE_RELATION_SCOPE; no duplicate record created. Current installed model enforces one counting record per owner/language, so its Conflict display cannot be produced through the documented valid writes. Conflict-cell inspection/resolution remains uncompleted: needs an already-inconsistent historical/imported fixture or a model/rule transition that permits it; I did not bypass validation or alter another workspace. Other exceptional Inactive/History only/Several paths completed.

## Dependent deletion completed

/docs/guide/use/delete-many-records/: in own reader selected Chur and Arosa municipalities. Preview explicitly counted 4 records: 2 selected municipalities, 1 child Stop B, 1 owned restored Name; 6 relationships removed, 4 to retained records. Confirmed Delete 4 records; actual 2 selected deleted with 2 dependants, no refusal. Language, System and independent System codes are retained. Source Stop A had already moved through separate published proposals; target copy is unaffected.

## Draft split completed

/docs/guide/model/split-merge-and-move-types/: new own draft 1560c91a-32e9-49fc-b4b0-5e5d3ac117cc C11 reader contracts and refactoring based on own release 1.0.0. Added unserved Reader refactor type with Reader detail/Reader retained attributes, Split moved Reader detail to Reader detail type with Has reader detail / Detail of reader many-to-one relation. Version 5 valid; inspected both types and relation, no Live change.

## Draft merge and keyboard move completed

/docs/guide/model/split-merge-and-move-types/: merged new Reader detail type into Reader refactor; both attributes and the relation joined the surviving definition, valid at version 6. Move to… → Find a target Operator, ArrowDown/Enter moved Reader refactor under Operator using new Contains Reader refactor / In Operator containment. Inspected nested type and valid draft. Undo and Redo exercised. These are definition changes in an unserved draft, not movement of live data.

## Two-person draft collaboration completed

/docs/guide/model/work-on-a-draft-with-others/: temporary whole-instance Model administrator granted to Rita. Separate Admin/Rita contexts opened same draft v9 and edited Reader refactor name. Admin save v10 succeeded; Rita stale save showed Another change came first and newer model without overwriting it. Applied mine again after review saved Reader refactor Rita at v11; History and no Issues inspected. Screenshot 13-draft-conflict.png inspected. Notice mislabels earlier rename as Renamed Reader refactor Admin to Reader refactor Admin (minor history wording defect, finding 9 to follow).

## 9. Draft conflict summary repeats the new name — small

/docs/guide/model/work-on-a-draft-with-others/ step 1: the intervening rename from Reader refactor to Reader refactor Admin was summarized as Renamed Reader refactor Admin to Reader refactor Admin. The current model and stale-write refusal are correct; the before name is misleading in the review summary. Screenshot 13-draft-conflict.png.

## Temporary model grant removed

Removed Rita temporary Model administrator in every workspace after completed draft collaboration. Existing supplied Graubünden Data owner and wave temporary reader/reader-model Data owner remain for later checks/cleanup.

## Consumer API authored in draft

/docs/guide/model/define-a-consumer-api/: created c11-reader-stops-api v1 exposing Stop, ID/name/stopCode fields, default stops list and Get by ID. Added operator related block through outgoing Operated by, name output; XREF exact Stop code weight 900 (Contains blank), Resolve and standard Events per type, kind By type filter. Refused Contains=0 with precise >=1 diagnostic, corrected blank. A rapid second operation save met optimistic concurrency; inspected current operation states and applied Events afresh. Draft valid, unpublished.

## Consumer v1 released in own workspace

Reviewed generated schema and Message example (Stop with ID/name/stopCode and single operator object), no Issues, compatible consumer result. /docs/guide/model/install-and-activate-a-release/: reviewed full comparison and reader model destination, compatible with stored data. Installed c11-reader-model 1.0.1 and activated only in reader-model. Draft continues from newly served v1 contract; other workspaces untouched.

## Consumer contract raised with earlier version retained

/docs/guide/model/raise-a-contract-version/: renamed public stopCode to code; editor correctly required contract version 2 and identified removed output field. Raise to version 2 retained the released v1 definition. Set its Sunset day 2026-12-31; inspected both fields and compatible checks, installed/activated own c11-reader-model 1.0.2 in reader-model. Current v2 and retained v1 read same workspace data in their own shapes. API readback to follow, not yet claimed.

## Consumer earlier-version retirement completed

/docs/guide/model/stop-serving-an-earlier-contract-version/: retained v1/v2 list reads both 200; v1 stopCode and v2 code shapes plus v1 Sunset/Deprecation checked, evidence contract-reads.jsonl. Explicit Stop serving v1 confirmation then own release 1.0.3 activation comparison warned 404 CONTRACT_VERSION_NOT_FOUND. Activated only reader-model: v1 list now 404 CONTRACT_VERSION_NOT_FOUND with servedContractVersions [2]; v2 200 still serves same live record. No webhooks owned for this API, so no receiver suspension check applicable. Granted own C11 reader client c11-reader-stops-api in reader-model; grant remains until cleanup.

## Incompatible activation correctly refused

/docs/guide/model/install-and-activate-a-release/: specialist JSON edit changed shared Stop code text to integer, raised own consumer contract to 3 without retaining 2, validated and compiled. Visual editor had refused this released-field edit as migration planned for 1.0 (screenshot 14 inspected), so this is explicitly the documented specialist path. Install review warned Activation needs a migration; installed own c11-reader-model 1.0.4, activation refused, Installed not active, no workspace changed. reader-model remains 1.0.3; proceeding to installed-release migration preview.

## Workspace migration completed

/docs/guide/model/migrate-a-workspace/: own reader-model preview ff75c764-9489-43c4-8416-bbb43decbb69 checked all records: 50 Converted, 0 Type changed, 1 Removed, 0 Must be fixed. Inspected before/after numeric Stop codes and Removed Operator Stop code C11-MAP-OP / VALUE_NOT_CONVERTIBLE. Explicitly accepted that optional value loss, confirmed Migrate reader model to 1.0.4. Success: 50 converted, 1 removed, workspace now 1.0.4, no record identities changed. Consumer v3 returns numeric code (200). Open conflict/race sets remain pinned to 1.0.0; history retains removed value. No automatic reverse assumed.

## Language raising: owned setup blocked by supported-version check

/docs/guide/model/raise-a-model-language-version/: attempted guide-owned setup rather than altering C10 language pictures. New workspace Another installed release / Show older versions excludes the only 0.9 release. Created own Import JSON draft C11 reader older language attempt dce95f0b-70ec-475e-ab75-9f34286e4a29, key c11-reader-language, from own model copy with schemaVersion 0.9 and no consumers. Authoritative validation: Schema version 0.9 is unsupported; supported versions [0.10], /schemaVersion; cannot install it as an old release or make an affected own workspace. Raise and reopen therefore remains uncompleted: recovery needs a pre-existing older-language release/workspace, cannot be created on this running version through guide UI. Only existing affected workspace is C10 language pictures, not ours; raising its shared release would mutate another owner’s workspace. No such mutation, host downgrade or validation bypass attempted. Invalid draft retained as evidence, not installed.

## People workbook export downloaded

/docs/guide/use/edit-in-excel-and-import-back/ step 1 and export-records: For people, reviewed Advanced Name/Stop code columns and optional relationship sheets. Started three equivalent export jobs while locating completion/download through Jobs; saved completed 986d7510-9e81-467c-ad99-95f1e4b17af2 people-stops-current.xlsx, 50 Stops, live feed position 225, 6.4 KB. Desktop Excel unavailable through provided tools: visible-cell editing below is programmatic, preserves hidden IDs/versions/layout and is not claimed as desktop Excel coverage.

## Edited people-workbook guarded import completed

/docs/guide/use/edit-in-excel-and-import-back/: programmatically changed two visible Name cells of people-stops-current.xlsx, preserving all hidden identity/version and layout parts, saved people-stops-edited.xlsx. Rita independently renamed Chur Albula to Chur Albula Rita after export. Manual Import without the assistant, Profile None, Only if unchanged, Load rows that can load. Preview job 606f9eef-0dd0-495f-8818-ef2be22c29c0 recognized Read as exported from Stops; 50 rows: 1 update, 48 unchanged, 1 refused Object version has changed. Load the file confirmed same partial result; Rita name retained, other edited name applied. Desktop Excel UI unrun, workbook/import semantics exercised.

## Edited workbook deliberate overwrite attempted, refused

/docs/guide/use/edit-in-excel-and-import-back/: after explicit review of Rita’s newer own-workspace name, reimported the same edited file with Profile None and Update them anyway. Actual preview and execution instead refused the stale row: 0 updated, 49 unchanged, 1 Object version has changed; job 1b2fdf4e-56b5-460c-bd1f-afa17cd09fcf. Public job parameters confirm onExisting=overwrite, while the UI says Records the file finds: Updated. Rita name remains. The deliberate-overwrite variant is blocked (finding 10); guarded import passed. Desktop Excel editing remains unrun; names were edited in XLSX XML with metadata intact.

## 10. Update them anyway still refuses exported stale rows — blocks this variant

/docs/guide/use/edit-in-excel-and-import-back/ step 5: after reviewing Rita’s current name, reimported edited people workbook, Profile None, explicitly selected Update them anyway. Job 1b2fdf4e-56b5-460c-bd1f-afa17cd09fcf records onExisting=overwrite and UI Records the file finds: Updated, yet preview and execution both refuse row 2 Object version has changed. 49 unchanged, 0 updated, 1 rejected; Rita value preserved. This contradicts the documented deliberate overwrite option. Earlier continuation note was corrected from its premature success wording after reading actual result. Fresh-export reconciliation is next.

## Fresh-export reconciliation completed

/docs/guide/use/edit-in-excel-and-import-back/ refusal recovery: exported fresh For people workbook from current reader-model (job 964a5478-95fa-4fbd-9a15-9b4c7cf48704). Changed visible Chur Albula Rita to Chur Albula reconciled in people-stops-reconciled.xlsx, preserved fresh IDs/versions. Profile None, Only if unchanged: full preview 1 updated/49 unchanged/0 rejected, then Load the file completed those counts; import f268305d-dcda-4400-94d1-431337e3763d. Safe edit/reconcile/guarded import round trip completed. Deliberate overwrite remains blocked by finding 10; desktop Excel itself not available.

## All-matching keyboard selection and exclusion completed

/docs/use/changing-many-records/: prepared 151 additional own Stops via public atomic batch, IDs/request all-matching-fixture.json; all created. Collection now 201 records, 5 pages, about 23 drawn rows. Header initially selected 150 and briefly offered Select all 201 matching; subsequent full-selection shortcut Cmd+A (documented alternative) selected 201. Unticked C11 bulk selection 001, count 200. Changed Operated by to C11 reader mapping operator: complete preview 199 changes/1 already as asked/0 refused; applied 199 and kept the unchanged connection. Excluded first Stop remains without connection. True whole-result selection via documented shortcut completed; bar renders 200 selected after resolving IDs, not All matching except. Explicit transient link was not clicked.

## All-matching exclusion verified on record

Opened C11 bulk selection 001 after bulk completion: Operated by panel says No relationships yet, confirming exclusion; 199 applied additions include records outside the drawn rows.

## Supplier upload and profile deletion completed

/docs/guide/use/load-the-next-version-of-a-workbook/ Remove a file: owned haltestellen-busbetrieb-nord-2 page, Delete the file… confirmed stored Haltestellen_Busbetrieb_Nord_next.xlsx deletion. Profile/last load remained; no next version uploaded. Then Delete the profile… confirmed deletion of that owned profile. Earlier imported records remain in reader-model; original other-owner haltestellen-busbetrieb-nord profile untouched. File/profile deletion does not reverse the published deleting-load result. Original manual workbook draft still retains its own source upload.

## Old change-set model move completed

/docs/guide/model/migrate-a-workspace/ change-set branch: opened retained own race-A df883df3-c8aa-4175-8b39-e851572a25b7, pinned 1.0.0 while live reader-model runs 1.0.4. Move this change set to active release preview ad991ed5-f224-4d4d-a32b-293924c09790: 0 conversions/removals/blockers, explicitly no live change. Confirmed Move change set, reopened and reviewed no authored changes, validated and published normally against current 201 Stops. Original live-conflict proposal remains pinned for inspection.

## Temporary Rita grants removed

Removed the continuation’s direct Data owner grants in reader and reader-model after all two-person checks. Whole-instance Model administrator grant had already been removed. Supplied original Graubünden Data owner grant remains untouched; Rita’s accounts/settings unchanged.

## Continuation client cleanup and final readback completed

Own C11 reader client deactivated after final ledger read. Existing management and consumer tokens now return 401 TOKEN_INVALID (details.reason=revoked) on next request. Grants/secrets remain for attribution, no secret value stored. final-state.json verifies own active reader on reference model 1.0.0 (7 live records; Publication 5 current) and reader-model on own model 1.0.4 (202 live records: 201 Stops + Operator; Publication 6 current). Only reader-model live-conflict set remains open; race-A moved/published. No reference workspace mutation in this continuation.

## Final continuation report and created-artifact ledger — 2026-11-08T16:51:09.548024+00:00

Consolidated report.md replaces its stale Remaining coverage gaps and final-state sections. New numbered findings 7–10; screenshots 11–16 saved and visually inspected. Final isolated build passed: GUIDE_OUT=_build/C11-READER2 npm run build, 253 pages, 4.46 s, exit 0, existing /404 route-priority warning. No steer file existed before the final unit. Secret scan: 21 text files, zero matches against actual passwords/client secret/tokens held in memory.

Created/retained in this continuation: manual workbook draft 0758ce86-c841-48d7-8447-7129309b428c, refactoring/consumer draft 1560c91a-32e9-49fc-b4b0-5e5d3ac117cc, invalid uninstalled older-language draft dce95f0b-70ec-475e-ab75-9f34286e4a29; own model releases 1.0.1–1.0.4; c11-reader-stops-transfer mapping v6; 51 workbook Stops, target moved Stop A, 151 bulk fixture Stops; System and two System codes; historical Name recreation (later deleted); owned supplier profile/upload (both later deleted); load/move/migration/import/export/bulk jobs and resulting publications. Earlier fixture requests and final-state.json identify exact records and publications. Final live counts: reader 7; reader-model 202 (201 Stops + Operator). Own client deactivated; temporary Rita grants removed. Existing original draft/release/person/proposals from earlier runs remain as listed in report.md.

Incomplete requested paths: supplier browser evolution/deleting-load save (wrong-workspace finding 7; API counterpart passes); deliberate stale workbook overwrite (finding 10; fresh-export recovery passes); desktop Excel operation (not available in supplied browser tools); Conflict matrix cell (valid writes refuse duplicate scope, no owned inconsistent fixture); Raise and reopen (current version cannot create/install an owned old-language release, only existing old fixture belongs to another owner). Other requested categories were exercised; no broad claim that every conditional subvariant passed.

Final closure 2026-11-08T16:51:40.900Z: signed out Admin and Rita sessions, closing the two wave contexts (three pages) and disconnecting Chromium. Report, progress and evidence saved. No service/database process was started.
