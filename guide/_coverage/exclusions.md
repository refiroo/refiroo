# Coverage exclusions

> One line per entry the guide does not document, as `kind key — reason`. The kind and key are those in `_coverage/inventory/<kind>.json`.

model-feature applications[].settings — a free map the engine does not read; nothing in refiroo changes with it, so there is nothing to document
model-feature applications[].state — no part of the engine or the browser reads an application's state (draft, active, retired), so the editor does not offer it and there is nothing to document (0.13 ED)
model-feature applications[].color — no screen draws an application's colour, so the editor does not offer it and there is nothing to document (0.13 ED)

screen route:list — internal browser route discriminator in frontend/src/types/ui.ts, not a screen label; collection use is documented in use/lists-and-filters and guide/use/find-records
screen route:detail — internal browser route discriminator in frontend/src/types/ui.ts; record pages and opening records are documented in use/records and guide/use/correct-a-record
screen route:changeSetChanges — internal browser route discriminator in frontend/src/types/ui.ts; the Records and Relationships review is documented in use/change-sets and guide/use/review-what-a-change-set-changes
screen route:group — internal browser route discriminator in frontend/src/types/ui.ts; group pages and Find a collection are documented in use/applications
screen settings:ai-tasks — internal browser route discriminator; frontend/src/app/SettingsArea.tsx selects Jobs navigation for this task detail, documented in use/loading-with-the-assistant and guide/use/continue-an-assistant-task
screen confirm:DeleteAction.tsx:dialog — reusable confirmation component, with no fixed screen title; its import-file and import-profile confirmations are documented in use/importing-and-exporting, and model mappings are documented in model/model-mappings
