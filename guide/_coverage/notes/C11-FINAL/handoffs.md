# Reconciliation handoffs

This records the C11 disposition of the 26 handoff groups in `_waves/reconcile/R-FUNCTIONALITY.md`.
Source ledgers are outside the user's edit allowlist, so they remain untouched. Done means the
reader explanation has a current home; it does not mean the application was exercised again.
Paths below are relative to `src/content/docs/`. Detailed operation fields remain in the API
reference, with the required consumer-contract examples in the guide.

| Handoff | Disposition and homes |
| --- | --- |
| F02 | Done: `model/managing-workspaces`, `model/models`, `model/the-model-editor`, `run/configure`, `integrate/workspaces-contexts-and-models`. C11 added key/default/concurrency detail. |
| F03 | Done: `integrate/reading-records` — related criteria, columns and bounded expansion. |
| F09 | Done: `model/applications-and-views#relation-matrix-rules` — binding, ancestor, display fields and actions. |
| F11 | Done: `model/the-model-editor#history-undo-and-other-editors` and `integrate/security-model-for-integrators#trace-who-did-the-work` — authors, causes and actor-free consumer events. |
| F15 | Done: `model/models`, editor/layout/workbook/proposals/consumer/migration/mapping pages; `integrate/workspaces-contexts-and-models`, `integrate/model-and-release-operations`; `run/model-releases-and-rollback`, `run/upgrades`. The current serving language is 0.10; eligible older stored releases have raising, rather than a current 0.5–0.10 serving window. |
| F16 | Done: `integrate/overview`, `integrate/identifiers-paging-and-errors`, `integrate/signing-in-and-tokens`. |
| F17 | Done: `model/the-model-editor#history-undo-and-other-editors`, `guide/model/work-on-a-draft-with-others`, `guide/model/install-and-activate-a-release`, `model/managing-workspaces`. C11 added the concurrent default-switch outcome. |
| F19 | Done: `run/health-and-startup-checks`, `run/monitoring`, `run/backup-and-restore`, `run/upgrades`, `run/configure`, `run/troubleshooting`; `administer/deployment-pages` explains Operations permissions. |
| F20 | Done: `integrate/reading-records` — query, lookup, edge reads, expansion, contexts and paging. |
| F21 | Done: `integrate/business-dates`, `guide/integrate/read-as-of-a-date` — management/consumer periods, contexts and undated related records. |
| F22 | Done: `integrate/writing-in-bulk`, `integrate/files-imports-and-exports`, `integrate/jobs`; `run/configure`, `run/background-jobs` — policies, idempotency, limits and retention. |
| F23 | Done: integrator consumer reading/lookup/events pages, `model/consumer-apis`, `administer/webhooks` and guides — definitions, contracts, grants, limits, deliveries and signatures. |
| F24 | Done: `integrate/api-reference`, `run/configure` — Scalar, bundled/CDN script, signed-in console and active sources. |
| F25 | Done: `integrate/following-changes`, `guide/integrate/load-then-follow-changes`, `run/configure` — positions, retention and baseline recovery. |
| F26 | Done: `administer/sign-in`, `administer/people-and-groups`, `run/sign-in-and-mail-setup`, `integrate/signing-in-and-tokens`. C11 named WebAuthn and TOTP. |
| F27 | Done: administrator people/roles/clients/keys/audit pages and `integrate/security-model-for-integrators` — scope, current rights, grants, secrets and refusals. |
| F28 | Done: `administer/mail`, `guide/administer/set-up-mail`, `run/sign-in-and-mail-setup` — SMTP, test, retry, privacy, SPF/DKIM; digest/following pages remain current. C11 replaced the unavailable Messages image with text. |
| PRODUCT_GUIDE: Change what the application allows | Done: `model/releases`, `model/migrations` and activation guides — per-workspace activation, installation, data fit and migration. |
| GLOSSARY | Done: `integrate/identifiers-paging-and-errors`, `about/how-it-works`, capability pages. C11 added the object-type alias. Actual source is `docs/product-functionality/GLOSSARY.md`; `docs/GLOSSARY.md` is absent. Current code supersedes the older installation-wide activation and JSON-only draft wording. |
| PRODUCT: Start from home | Done: `integrate/workspaces-contexts-and-models` — caller's active browsable workspace cards, models, applications and open work. |
| PRODUCT: See what someone changed | Done: `administer/people-and-groups`, `administer/audit` — See changes and security activity. |
| PRODUCT: Check and set up the deployment | Done: `administer/deployment-pages`, `administer/api-reference-and-consumer-api-pages`, `administer/webhooks`, `run/configure` and integrator event pages. |
| PRODUCT: Manage workspaces | Done: `model/managing-workspaces`, its guides, `integrate/workspaces-contexts-and-models#deletion-and-reusing-a-workspace-key`. C11 added the retirement/write and deletion/feed consequences. |
| PRODUCT: Manage the application model | Done: `model/models`, `model/releases`, `model/the-model-editor`, `model/record-pages-and-tables`, `model/consumer-apis` and guides. |
| PRODUCT: Integrate other systems | Done: integrator read/bulk/feed/job/file/consumer pages; model workbook/proposals/mappings pages. |
| PRODUCT: Change rules | Done: `run/configure`, `run/health-and-startup-checks`, `model/releases` distinguish bootstrap content, installation and activation. |

R-MODEL's explicitly unowned example/consumer subjects already have homes in the example pages,
`model/consumer-apis` and integrator consumer pages. R-CONSUMER and R-OPS record completed
cross-section edits rather than additional uncompleted handoffs. Their historic shared link-check
failures were not reproduced by the isolated C11 verification.
