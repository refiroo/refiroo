# Source review

Read guide/AGENTS.md and _waves/COMPLETE-COMMON.md fully; assignment, run sidebar, existing run pages (AI pages excluded), outline section 5 and run coverage. Read operations runtime, database, startup, monitoring, jobs, events, deployment, maintenance and backup sections; config settings/defaults and catalogue; compose and engine Dockerfile. Large combined reads were truncated; subsequent targeted reads supply the page-specific evidence. Top-level agent guidance is excluded by the assignment.

Confirmed documentation defect: old /model and /data paths differ from Dockerfile and Compose. Corrected to /opt/refiroo/rdm-engine.

Product concern: backend/Dockerfile guide stage copies astro.config.mjs but not sidebar/, although config imports eight sidebar modules. Image build was not executed. Outside allowed edits.

Further sources read: all nine executable app/cli modules; operations authentication/key rotation and mail sections, compatibility commitment; model compiler/schema version constants; main capability route registration; jobs worker/export lease comments and BatchRequest; mail settings boundary; AboutPage, DeploymentPage, OperationsPage, WebhookDeliveries, WebhooksPage, MailPage; dev helper settings/network paths; nginx mode validation; journey J12 and J24.8; targeted behaviour rules and AI release/plan evidence for classification. No application processes, migrations, deployment builds or operational commands were executed.

Checked unchanged pages: https (compose, acme overlay, nginx entrypoint), secrets-and-keys (reseal CLI and operations), licence-and-source (config and AboutPage), production-checklist (the referenced procedures). Sidebar already lists every run page in the required groups, so left unchanged.

Out-of-scope source concern: excluded run/ai.md still names /data/assistant and /data/assistant-claude; run/set-up-ai.md also names /data/assistant. The current Dockerfile uses /opt/refiroo/rdm-engine/data/... . These two files were not edited.

Coverage classification: 58 previously deferred AI rows retained; 10 additional explicitly AI screen/summary/assistant/provenance rows marked after 0.16 after checking their cited source; C2747 is provider-test strategy, excluded from reader documentation. Resolution JSON retains reasons and all changed destinations. Shared-reader rows link to the other wave's existing pages without editing them.
