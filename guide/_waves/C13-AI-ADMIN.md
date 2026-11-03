# C13-AI-ADMIN: the AI features in "administer"

Read `guide/AGENTS.md` and `_waves/COMPLETE-COMMON.md`. 0.16 is released and the AI features are now
documented (DOC-D21). The reference instance has the assistant switched on (`AI_AGENT_COMMAND` with Claude
Code, `AI_AGENT_SANDBOX=container`, `AI_SEND_LEVEL` set); `AI_PROVIDER` is not set there, so the
provider's features (proposed mapping targets, asking a list in words, explanations) are documented from
the sources and the code, and their screenshots stay wanted.

**Your rows:** every row marked `after 0.16` in `_waves/coverage/administer.md`. Cover each now, then mark
it covered with its page, the same way as every other row.

**What to write:** Settings › AI (provider, send levels, the call list, Send a test request, costs), who may use AI (the action group and the roles that hold it), and agent access (`administer/agent-access.md`: /mcp, agent clients, tools, sessions, what an agent may and may not do).

**Sources:** `docs/BASE_0_16_IMPLEMENTATION_PLAN.md` (the delivered packages and decisions),
`CHANGELOG.md` [0.16.0], `docs/product-functionality/CURRENT_FUNCTIONALITY.md` F29 and F30,
`docs/product-functionality/USER_JOURNEYS.md` J49–J57, `docs/OPERATIONS.md` ("AI proposals", "Agent
access"), `docs/API.md` ("Agent access"), the screens in `frontend/src/` (labels exactly as shown) and
`backend/app/` (the code wins). Reconcile them heading by heading as the reconciliation waves did, with a
ledger row per source heading in `_waves/reconcile/C13-AI-ADMIN.md`, saved before the next heading.

Plain words about what leaves the instance, who may use AI, what it costs and what is kept: every reader
who meets an AI feature needs that, briefly, with a link to the page that explains it in full. AI proposals
are never applied on their own: say what the person reviews and accepts, as the screens show it.

## Files you may edit

- `src/content/docs/administer/*.md`
- `src/content/docs/guide/administer/*.md`
- `sidebar/administer.mjs`
- `_waves/coverage/administer.md`
- `_waves/reconcile/C13-AI-ADMIN.md`
- `_waves/screens-wanted/C13-AI-ADMIN.md`

## Report

As `COMPLETE-COMMON.md` says.
