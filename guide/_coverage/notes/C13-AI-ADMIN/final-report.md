# C13-AI-ADMIN final report

## Pages

New: administer/ai; administer/agent-access; guide/administer/check-the-ai-provider; guide/administer/manage-agent-access.

Changed: administer/roles-and-grants; administer/approval-policies; administer/clients. Added the AI group and task links to the existing sidebar without moving existing groups.

## Coverage

All 42 deferred rows resolved: 41 reader-facing page destinations and one internal test-design exclusion (C2363). Total: 279 covered, 10 not for readers, no open/deferred rows. Cross-reader task details link to Use and Model; protocol and credential details link to Integrate.

## Screenshots

Nine requests in _waves/screens-wanted/C13-AI-ADMIN.md, each with filename, page, state and visible content. Existing admin-agent-access.png inspected and reused for the off state. Steering applied: provider and assistant are now on in the reference instance. Capture remains a later step.

## Checks

GUIDE_OUT=_build/C13-AI-ADMIN npm run verify: build passed, 247 pages; terms/brand passed; links failed solely on 36 missing-image references across parallel waves, including this wave's nine. No missing page/anchor reported. Output saved in verify.log here. Build warnings: caddyfile language fallback and conflicting 404 routes.

No live provider request, new browser exercise, client creation, registration or revocation performed. Screenshot appearance remains unverified except the existing off-state image. No commit or state-changing git command.

## Findings

Values send-level UI text claims a sample cap although Policy.values does not apply it. Guide describes actual behavior. Older source prose also contains superseded provider-only, no-follow-up and sandbox/network claims; these were reconciled with current code. Details in findings.md and the source ledger.
