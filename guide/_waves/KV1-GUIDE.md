# KV1 guide: keep a contract version through a breaking change

Read `guide/AGENTS.md`. Readers: model administrators (the guide pages under Model your data) and, in one sentence,
integrators. Write plain prose; no package or decision numbers.

## Why

A consumer API has a `contractVersion`. Until now, a release that changed what the current version's readers get
(removing or retyping an output field, a related block's shape, and so on) could only be activated by raising the
version. Now the person who activates the release may instead **keep** the current version: its readers then get the
new shape under the same number. The code wins over this text wherever they differ:
- the dialogs' section: `frontend/src/ui/ActivationParts.tsx` (`ConsumerContracts`, `useKeptContracts`), used by
  `frontend/src/features/model-editor/InstallDialog.tsx` and `ApplyDialog.tsx`;
- the engine: `backend/app/engine/model/consumer_contract.py` (`contract_refusals`), `releases.py`
  (`activate_model_release`), `migrations.py` (`submit_migration`);
- the documents: `docs/CONSUMER_API.md` ("Each definition has its own `contractVersion`…"), `docs/API.md` (the
  paragraph after the `classification` description), `docs/COMPATIBILITY.md` (DF-D2), CHANGELOG, Unreleased.

## What the product does now (check each point in the code)

- In **Install and activate** and in **Apply to this workspace**, the **Consumer APIs** section lists each consumer
  API with its version. A row whose change breaks what its readers get says **Needs version {n+1}:** and the change,
  and offers **Raise to v{n+1}** (a step in the draft, as before) and, new, a red **Keep v{n}, break its readers**.
- **Keep** is a choice in the dialog only: the draft is not changed and nothing is saved. After it the row shows a red
  box, **Stays v{n}, changed in place**: "Once applied, every reader of /api/consumer/{api}/v{n} gets the new shape:"
  with the breaking changes exactly as the engine reports them, and, when the person may read webhooks and some are
  bound to that version, a line **Webhooks bound to v{n}:** with their names (left out when there are none or the person
  cannot read them). The row's button becomes **Raise to v{n+1} instead**, which takes the choice back and raises.
- The dialog's main action (**Install … and activate in …**, **Apply to …**) is disabled while any breaking row is
  neither raised nor kept; the closing sentence says "Activation is refused while a consumer API needs a higher contract
  version, unless you keep its version." Once every row is decided the main action is enabled; it activates, or
  starts the migration preview, with the keep choices.
- **Keep** is shown only to people who hold the Model release group (the people who may install a release), and never
  to anyone else (the closing sentence then has no "unless…"). It is not offered on a row that also changes an earlier
  version still served beside the current one, or that lowers the version: those stay refused, and the row says why.
  Say that an earlier version's frozen copy is never changed by keeping.
- What keeping means for others: consumers and webhooks of that version get the new shape at once, with no
  `Deprecation` header and no second version to move to; nothing is retained of the old shape. Say plainly that raising
  is the way to let readers move on their own time, and keeping is for a change that should never have been a break
  (a field set up by mistake, then put back).
- The activation records what was kept: the release's activation history (and the audit trail) names each API, the
  version and the breaking changes accepted, with who did it.
- The assistant never keeps: its own activations stay refused for a break.
- For integrators: `POST /workspaces/{key}/model/activation` and `POST /workspaces/{key}/model/migrations` take
  `keepContractVersions` (default false); the activation answers `keptContractVersions`. One sentence on the pages
  that name these, linking `/docs/api`; do not repeat the reference.

## What to do

Extend the three pages that own the topic; no new pages. Neutral wording; examples use the reference data (the Stops API:
a field removed from it without a higher version).
- `src/content/docs/guide/model/define-a-consumer-api.md`, section "Refine a released API safely": when raising is the
  right choice and when keeping is, and where the choice is made (the Install and activate and Apply dialogs).
- `src/content/docs/guide/model/install-and-activate-a-release.md`: the steps of the Consumer APIs section in both
  dialogs (Install from the editor; Apply from a workspace), the two pictures of each, what each button does, the
  disabled main action, who sees Keep. Where the page says activation is refused until the contract version is
  raised, add "or kept". The result table row "A consumer API needs a higher contract version" gets the second way.
- `src/content/docs/model/consumer-apis.md`: the concept, in "Contracts, access and limits" and "When the retained
  version prevents activation": a contract version can be kept through a break; what it means for readers; that an
  earlier version still served is never covered; where it is recorded.

## Pictures (taken, in `guide/public/screens/`; look at them, then reference them as `![…](/docs/screens/<name>.png)`)

- `model-install-contracts-break`: the Install and activate dialog, Consumer APIs: the break, Raise to v2 and Keep v1.
- `model-install-contracts-kept`: the same after Keep: the red box and Raise to v2 instead; the main action enabled.
- `model-apply-contracts-break`, `model-apply-contracts-kept`: the same two states in Apply to Graubünden.
Use them where the steps describe those states, each with a caption that says what to look at. Where the pages already show
the older dialog pictures (`model-install-dialog`, `model-workspace-apply-dialog`, `model-apply-migration`), keep them.

## Files you may edit
- `src/content/docs/guide/model/define-a-consumer-api.md`
- `src/content/docs/guide/model/install-and-activate-a-release.md`
- `src/content/docs/model/consumer-apis.md`
