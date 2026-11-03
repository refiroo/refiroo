# Steering for C10, fourth round (2026-11-03)

The reference instance now has AI (assistant and provider, `GET /api/v1/ai/status`: configured, provider
`claude-code`), mail (Settings › Mail) and webhook subscriptions (`CONSUMER_SUBSCRIPTIONS_ENABLED`) switched on.

- Take every image the pages still miss: the AI waves' requests (`_waves/screens-wanted/C13-AI-*.md`), and
  the entries of `C10-LATER.md` that needed mail, AI or webhooks. Put each image reference back on its page
  and take its entry out of C10-LATER.
- AI screens need real AI work: a recipe may ask for proposals (mapping targets, a question in words, an
  explanation) and run one assistant task on the example data, waiting for its result (allow minutes; use
  the runner's `waitFor` with a long timeout). Keep it to what the pictures need: each AI request costs. Never
  accept a proposal into live data or publish; leave a proposal or task in the state the picture shows, then
  discard it where the screen offers that. Record every AI request and task in `C10.data-changes.md`.
- Mail: the instance may send real mail; only to the reference accounts' own addresses, and only what a
  picture needs (a digest, a test message). Record it.
- Webhooks: read the subscription host rules in `backend/app/` before choosing a receiver address; use only
  an address the rules allow that belongs to this instance (no outside service, no server started for it). If
  no allowed address can receive, take the screens a subscription shows without deliveries (new, rotate,
  paused with its reason) and leave the delivery screens in C10-LATER with the reason.
