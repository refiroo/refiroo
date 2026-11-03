# Steering for C13-AI-MODEL

## 2026-11-03: the provider and webhooks are now on in the reference instance

`GET /api/v1/ai/status` now answers `configured: true`, `assistant: true`, `provider: "claude-code"` (the
development provider, see `_waves/steer/C13-AI-RUN.md`), model `sonnet`, send level `values`; the
provider's features (mapping targets, a question in words, explanations) are available there too. Webhook
subscriptions are switched on (`CONSUMER_SUBSCRIPTIONS_ENABLED`). So the screens of these features can now
be taken: add every AI screen your pages need to your screens-wanted file (the screen, its state, what must
be visible), and reference them on the pages as usual; they are captured after your wave.
