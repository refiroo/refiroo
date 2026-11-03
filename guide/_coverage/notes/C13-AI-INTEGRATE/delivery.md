# Delivery record

New pages:
- integrate/assistants-and-agents.md
- integrate/assistant-tasks.md
- guide/integrate/connect-an-assistant.md

Updated pages:
- integrate/overview.md
- integrate/signing-in-and-tokens.md
- integrate/security-model-for-integrators.md
- integrate/files-imports-and-exports.md
- integrate/jobs.md
- integrate/writing-in-bulk.md
- integrate/reading-records.md
- integrate/model-and-release-operations.md
- integrate/following-changes.md
- integrate/changes-approvals-and-publication.md

Coverage: 719 rows = 689 covered + 30 not for readers. All 57 fully deferred rows and the mixed deployment-settings row reconciled. Zero open.

Screenshot wanted: integrate-agent-access-connect.png, enabled Agent access / How to connect / Address / person and system instructions / command / Agent clients headings. The existing admin-agent-access.png was visually inspected and is the disabled state.

Validation: scoped build passed. Full verify blocked by an out-of-scope capitalized product name in use/history.md. Standalone links check blocked by missing screenshot assets; the only Integrate finding is the requested enabled-state screenshot. Logs in this folder. No runtime assistant/provider calls made.

Source disagreements: some early API/task and release prose ends sessions at loaded, whereas current agent.end_session and design_job sync retain them for correction until publication, discard, migration or expiry. Historical AP6a planner/loop is superseded. MCP reads are retained as call records, not separate read audit events. Current button is New agent client. No confirmed application defect found.
