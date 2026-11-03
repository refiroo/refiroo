---
title: Secrets and keys
description: Keep sealing keys recoverable and change them without losing stored secrets.
reader: operator
---

Keep secrets in the installation's private environment or secret store. Never commit filled `.env`
files, credential-bearing database URLs, encryption or cursor keys, provider or SMTP credentials,
client secrets, webhook keys, AI credentials or TLS private keys. Backups contain sensitive data too.
Keep their keys securely outside the database and associate each backup with the key it needs.

## Which key does what

| Key | Default | Purpose and change rule |
| --- | --- | --- |
| `SECRETS_ENCRYPTION_KEY` | Required | 32 URL-safe-base64-encoded bytes. Opens stored token/webhook keys, provider secrets and session ID tokens, authenticator secrets, SMTP passwords and queued message text. Reseal before replacing it. |
| `RDM_CURSOR_SIGNING_KEY` | Ephemeral per process | Signs pagination cursors. Set one stable secret across processes; replacing it invalidates existing cursors. |
| Token signing keys | Engine-generated | Sign access tokens; stored sealed in PostgreSQL. Automatically rotate after `TOKEN_SIGNING_KEY_DAYS`, default 30, when another token is issued. |
| Webhook signing keys | Generated for subscriptions | Let receivers verify deliveries. Rotate independently of the sealing key. |

Generate a sealing key with `python -m app.cli.generate_key` in the configured backend environment,
or use the OpenSSL command from [installation](/docs/run/install-with-compose/). Never generate a
replacement merely because an existing installation cannot open a stored secret: find its original key.

## Change the sealing key

Arrange downtime and take a [backup](/docs/run/backup-and-restore/) first. Tell people with recovery
codes that they must create new ones afterwards: those codes are keyed directly with the old key
and cannot be resealed. Their authenticator app continues working after resealing.

For Compose, from the repository root:

1. Stop every engine process. In the single-instance reference:

   ```bash
   docker compose stop engine
   docker compose run --rm engine python -m app.cli.reseal_secrets --check
   ```

   The check opens every sealed value with the current key without changing it, and reports how
   many people have unused recovery codes. Stop if any value cannot be opened.
2. Generate a new key and supply it as `NEW_SECRETS_ENCRYPTION_KEY` through a secure environment
   injection. Keep the old key in `SECRETS_ENCRYPTION_KEY`. Do not put either value in command
   arguments or shell history. With the new variable exported in your shell, run:

   ```bash
   docker compose run --rm -e NEW_SECRETS_ENCRYPTION_KEY engine \
     python -m app.cli.reseal_secrets
   ```

3. The command reseals all values in one transaction. If a value fails, it names its kind and
   identity without printing its contents and changes nothing. An absent, malformed or identical
   new key is refused. Fix the cause before retrying.
4. On success, replace `SECRETS_ENCRYPTION_KEY` in every instance's private environment with the
   new value, remove the temporary variable, and recreate the engine:

   ```bash
   unset NEW_SECRETS_ENCRYPTION_KEY
   docker compose up -d engine
   ```

5. Check readiness and sign-in. Ask affected people to make new recovery codes on
   **Account › Second factor**. An administrator must help anyone who also lost their authenticator.

Keep the old key for backups made before resealing, and the new key for later backups. Resealing
preserves the underlying signing secrets, so it does not itself invalidate access tokens or require
receiver reconfiguration. To respond to a signing-key leak, also rotate the affected key:
[Signing keys](/docs/administer/signing-keys/) and [Webhook delivery](/docs/run/webhook-delivery/).

## Supply the temporary new key without a literal secret in history

Before starting, have the old key available in the installation's private settings, a rehearsed
backup, downtime for every engine and a protected place to keep both key versions. The reference
image can generate key material without starting the database or engine server. One shell sequence
for the **new** key is:

```bash
NEW_SECRETS_ENCRYPTION_KEY="$(docker compose run --rm --no-deps -T engine python -m app.cli.generate_key)"
export NEW_SECRETS_ENCRYPTION_KEY
```

Check that generation succeeded before resealing; store the generated value securely without
printing it into logs. The command text in shell history contains no literal key. The shell's
export makes `docker compose run -e NEW_SECRETS_ENCRYPTION_KEY` pass the variable through. An
environment export alone does not replace Compose's configured `SECRETS_ENCRYPTION_KEY`.
Do not close that shell or discard the new key until you have stored it and changed the private
configuration after successful resealing.

A successful check begins `Every sealed value opens with the current key` and reports counts by
kind. A successful write begins `Re-sealed` and prints
`Set SECRETS_ENCRYPTION_KEY to the new key before starting the engine.` It also reports either how
many people lose unused recovery codes or
`No one has an unused recovery code, so no recovery code is lost with a new key.`
The detailed command status reference is [Command-line tools](/docs/run/command-line/).

## If checking or resealing fails

| Message fragment | State and action |
| --- | --- |
| `Not re-sealed: SECRETS_ENCRYPTION_KEY is not set.` | No resealing occurred. Restore the current installation key. |
| `Not re-sealed: NEW_SECRETS_ENCRYPTION_KEY is not set; generate one with` | No resealing occurred. Export the new key and explicitly pass it into the one-shot container. |
| `Not re-sealed: NEW_SECRETS_ENCRYPTION_KEY is the current key.` | No change. Supply a different generated key if rotation is intended. |
| `Not re-sealed:` followed by sealed-item identities | Some values could not be opened; none were replaced. Recover the correct old key or investigate damaged/mixed-key data before retrying. |

Before a successful reseal, the old key remains correct. After success, start engines only with the
new key. A safe undo of the whole operation is restoring the matching pre-change database and
file backup with the old configuration. Do not merely switch the environment back to the old key
after resealing: the database now contains ciphertext sealed under the new one.

After recreation, require readiness 200, sign in, and exercise the configured services that open
stored secrets: a mail test and provider sign-in where used, and webhook delivery with its receiver.
Existing TOTP apps should still work. Ask people with recovery codes to regenerate them; do not
invalidate an authenticator app just because its recovery codes need replacing. Keep both key
versions under separate backup-version labels until no retained backup needs the old one.

## Cursor keys and signing-key rotations

Changing `RDM_CURSOR_SIGNING_KEY` does not require resealing database values. It makes existing
pagination cursors invalid; arrange for clients to restart lists and deploy the same new value to
all processes together. To undo, restore the previous shared value and recreate the processes;
cursors issued under the temporary value then fail. This setting is unrelated to token signatures.

Token signing-key rotation and client/webhook secret rotation are administrator operations, with
their own overlap and retirement rules. Use [Signing keys](/docs/administer/signing-keys/),
[Clients](/docs/administer/clients/) and [Webhook delivery](/docs/run/webhook-delivery/).
Resealing is storage-key maintenance and does not rotate those underlying credentials.
