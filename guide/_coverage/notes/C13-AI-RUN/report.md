# Working report

Authoritative guide instructions and common/wave/steering files were read from disk first. The top-level AGENTS instructions were not used. Existing AI pages were present, but no earlier C13 progress or reconciliation files existed. No memory files, credentials or live instance were read. Work stayed in the wave allowlist.

Source discrepancies:
- frontend/src/features/settings/aiText.ts sendLevelText(values) says up to sampleValues per column; backend proposals/context.py does not cap values. Documented code behavior, left UI code untouched.
- CURRENT_FUNCTIONALITY F29 and OPERATIONS have older wording about provider features arriving later, and OPERATIONS' question-context paragraph says never record names. Current context policy and J54 allow short relationship lists at samples/values; documented this.
- Original plan AO-D8 suggests interface-language explanations. F29/current explanation contract says English only; documented current capability, excluded superseded row.
- Historical inference AI naming and old read/match/fix tasks were removed before release. Do not treat their earlier CHANGELOG Added headings as current.
- Existing AI guide paths abbreviated /data/assistant; shipped image uses /opt/refiroo/rdm-engine/data/assistant and assistant-claude. Corrected in allowed pages.

Not exercised: Docker/start/recreation, subscription token generation, live provider or assistant calls, MCP connectivity, provider bills, screenshot appearance. Setup facts verified in local source, not a deployment rehearsal. Provider screenshots remain wanted. No servers or background services started by this wave.

Validation: GUIDE_OUT=_build/C13-AI-RUN npm run verify in guide/: build PASS (246 pages), terms/brand PASS; links FAIL (33 missing screenshot files only; two owned by this wave, 31 outside scope). No page-link/anchor failures. Required image placeholders retained and listed as wanted rather than creating fabricated images or editing other waves. Build warnings: caddyfile highlighting fallback and duplicate 404 route. Source cross-check: all 22 AI/MCP catalogue names documented; 254 coverage rows, 214 destinations / 40 explicit exclusions. Initial invocation from repository root failed before building; corrected working directory. This is documentation-only evidence.
