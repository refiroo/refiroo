# Fourth-capture corrections and retake

This supersedes the earlier fourth-round preparation handoff. Eleven images were inspected: the ten attachments plus the saved mapping result. Per-image comparison: fourth-capture-image-review.md. No external capture or instance request ran here.

## What changed

- AI settings captions now describe status rows. Calls caption says answered provider calls and unreported costs; no failure/assistant turn is claimed.
- Ask clicks the visible label, because Choice radio inputs have pointer-events:none (styles/layout.css). AI result waits now have timeout:300000 instead of fixed sleeps plus 15-second waits.
- Workspace Activity uses /settings/workspaces/graubuenden/activity, as routing/routes.ts defines; ?tab=activity opened Overview.
- Mail Messages no longer depends on Mail is not set up or an empty Waiting filter. Existing rows are allowed; no send/stop occurs.
- Agent access uses the sidebar link from the working AI settings page. Labels already match AgentAccessPage.tsx. The log does not establish whether MCP is off, the route failed or the status read failed. Five enabled-page captures still require How to connect. If Agent access is off or an error appears, report it; do not enable MCP or create access fixtures. Client/registration dialogs still cancel without saving.
- Notification email also uses the sidebar link. The image now shows saved settings or the no-address/unconfigured explanation. No sent-digest browser view exists: MailPage explicitly excludes message text and NoticeMailPanel only configures delivery. The page directs readers to their mailbox for a sent message. No mail is generated.
- Mapping result is accepted: 0 proposed, 1 unmatched, 0 changed meanwhile. Show proposed is correctly absent. Corrected caption and conditional steps; keep the existing image and do not repeat its charged request. The grid recipe reads the retained named change set, Codes to stops lens and Proposed filter (both buttons), capturing the honest empty state. It claims no confidence/reason rows.
- Task cancellation is asynchronous. Recover the existing task from Jobs → newest Graubünden Assistant: reading a workbook → Open the load, then wait for its stopped/failed state. No duplicate upload/task is started. Continue once using the actual Go on as it was or Try again as it was action. All six task captures are now contiguous to preserve their shared page. If another assistant task has since run, use the recorded original task URL instead of the newest-job lookup. If the task is already checked/loaded, report/reuse that state rather than force another Stop or resume.

## Retake only

Keep all ten accepted attachments and the zero-proposal result. Run only these 17 entries in manifest order; five Agent access entries remain deployment-dependent. Provider continuations incur cost. Do not rerun use-mapping-proposal-result.

```sh
node guide/tools/screens.mjs --file C10.screens.json --only admin-mail-messages,admin-agent-access-enabled,integrate-agent-access-connect,admin-agent-new-client,admin-agent-register,use-ask-filters,use-ask-partial,use-history-explained,use-mapping-proposed,use-assistant-stopped,use-assistant-proposal,model-assistant-workbook-proposal,use-assistant-loaded,model-assistant-workbook-loaded,use-assistant-reload,notification-email-digest,admin-agent-calls
```

## Data and limits

C10.data-changes.md records four answered provider operations and one workbook task created/asked to stop. IDs and eventual task state were not supplied. No continuation, acceptance or load is evidenced by this run's log. No grant/client/registration/mail/activation/publication/deletion was confirmed by these recipes. Existing seven deferred fixtures remain unchanged. Missing MCP controls and task-stop timing are unresolved observations, not diagnosed product defects. No application code changed.

## Validation

All 60 recipes passed name/action/upload/timeout checks and the contiguous existing-task-chain check. Guide build result is appended after completion; no live retake ran here.

`GUIDE_OUT=_build/C10-SCREENS npm run build` passed: 247 pages in 7.26 seconds. Log: build-fourth-corrections.log.
