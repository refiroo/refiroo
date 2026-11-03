
## 2026-11-03T22:49:17+01:00 — MCP connection and tools

Finished `integrate/assistants-and-agents.md` and `guide/integrate/connect-an-assistant.md`, and added them to the sidebar. Covers authentication, readable data, owned change sets, human approval, provenance, paging, limits and external data handling. No steer file was present. Existing Agent access screenshot shows the disabled state, so an enabled-state capture is requested.

## 2026-11-03T22:50:57+01:00 — Task API and related pages

Finished `integrate/assistant-tasks.md`; linked it from file exchange and jobs, and added assistant authentication to `integrate/signing-in-and-tokens.md`. Covers checked proposals, human acceptance, saved profiles, migrations without change sets, retry/stop/discard and session cleanup. No steer file was present. Source prose ending a session at loaded conflicts with the current cleanup code; the page follows code and the later continuation contract.

## 2026-11-03T22:52:14+01:00 — Provider features and approval links

Finished the AI sections in `integrate/writing-in-bulk.md`, `reading-records.md`, `model-and-release-operations.md` and `following-changes.md`, with links from overview, approval and security pages. Covers target proposals and their result counts, partial question translations, fact-based explanations and provider failures, with permissions and data/cost/retention links on each affected surface. No steer file was present. These are source-and-code documentation; provider behavior was not exercised against the reference instance.

## 2026-11-03T22:54:40+01:00 — Coverage reconciliation

Finished `_waves/coverage/integrate.md` and the source-heading ledger. All 57 deferred rows and the partially deferred deployment-settings row have current page references: 689 covered, 30 not for readers, 0 open, 719 total. No steering corrections were present. The ledger records source disagreements about session lifetime, the removed planner, read-call auditing and current button labels.

## 2026-11-03T22:55:31+01:00 — Final validation and delivery

Finished all 13 written/updated pages, sidebar, coverage, source reconciliation and screenshot request. `GUIDE_OUT=_build/C13-AI-INTEGRATE npm run build` passed (242 pages, 4.76 s); `npm run verify` reaches a passing build but stops at the out-of-scope capitalization error in `use/history.md`. Standalone link checking reports pending screenshot assets across concurrent waves; this wave has only `integrate-agent-access-connect.png` missing, already requested. No page links or anchors in Integrate were reported broken. No steer file was present. Runtime/provider requests were not exercised; no code defect is claimed.
