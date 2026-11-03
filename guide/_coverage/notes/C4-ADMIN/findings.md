# Findings

- WebhooksPage.tsx disabled-state text asks for CONSUMER_WEBHOOK_KEY_ENCRYPTION_KEY. docs/OPERATIONS.md and startup use SECRETS_ENCRYPTION_KEY; the old name is refused. No application code edited.
- Validation is documentation build/static/link evidence, not live browser acceptance or mail/webhook delivery proof.
