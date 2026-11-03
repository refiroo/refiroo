---
title: Set up AI
description: Enable the assistant and AI provider in Docker Compose, supply credentials, and check that each works.
reader: operator
---

Use these steps for an existing Docker Compose installation. Claude Code is already installed in
the engine image. You do not need `docker exec`, an installation command inside the container, or
an interactive sign-in there.

First decide what data may leave the instance and which features you need. [About AI in
refiroo](/docs/run/ai/) explains the separate switches, permissions, session guards and retention.

## 1. Open the installation's environment file

Run the commands below from the repository root, where `compose.yml` lives.

- For the normal Compose installation, edit `.env`. If you use a different environment file,
  edit that file and use your existing Compose invocation; `RDM_ENV_FILE` must name the file
  passed to the engine.
- For the documentation's reference instance, edit `guide/reference/.env`. It is generated on the
  first `guide/reference/reference.sh up`. If the instance has not been created, run that command
  first. Do not replace the generated database, encryption or sign-in settings.

Compose passes this file's settings to the engine, including Claude Code's credential variables.
Editing an example file does not configure a running instance.

**`ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN` and `AI_API_KEY` are secrets. Never commit them or a
filled environment file.** The examples below contain placeholders: replace them only in your
private environment file. Do not paste credentials into the assistant's instructions or a support
report.

## 2. Enable the assistant

Add or update these lines in that environment file:

```dotenv
AI_AGENT_COMMAND="claude --model sonnet --permission-mode bypassPermissions"
AI_AGENT_SANDBOX=container
AI_SEND_LEVEL=values
```

The command selects Claude Code and its model. refiroo adds its own session restrictions and
replaces the command's permission-mode option with the mode it enforces. The example does not
remove those guards. `container` selects the shipped image's separate assistant user; do not leave
it unset in this installation. `values` allows the assistant to read the workbook and records
needed by the task. Lower levels make the assistant unavailable.

Choose **one** of the following credential methods for Claude Code.

### Use an Anthropic API key

Put your API key in the same environment file:

```dotenv
ANTHROPIC_API_KEY=replace-with-your-anthropic-api-key
```

This is Claude Code's variable. `AI_API_KEY` alone does not authenticate the assistant. Leave
`CLAUDE_CODE_OAUTH_TOKEN` unset for this method.

### Use a Claude subscription token

On a computer with Claude Code installed and access to your Claude subscription, run:

```bash
claude setup-token
```

Follow Claude Code's browser authorisation and copy the token it prints. Put it in the engine's
environment file:

```dotenv
CLAUDE_CODE_OAUTH_TOKEN=replace-with-the-token-from-claude-setup-token
```

Leave `ANTHROPIC_API_KEY` unset in that file when using the subscription token. Claude Code reads
these variables itself; refiroo forwards `ANTHROPIC_*` and `CLAUDE_*` environment names to its
session. Creating the token on your computer does not automatically transfer it to the engine.
See [Claude Code's authentication documentation](https://code.claude.com/docs/en/authentication#generate-a-long-lived-token)
for its token requirements and lifecycle.

Keep the image's `CLAUDE_CONFIG_DIR=/data/assistant-claude` unless you also arrange the required
directory permissions. The image already gives the engine and assistant users access there.

## 3. Enable the provider if needed

For mapping targets, questions in words and summaries through the Claude API, add:

```dotenv
AI_PROVIDER=claude
AI_API_KEY=replace-with-your-anthropic-api-key
```

This key is separate from the assistant's credential setting. A subscription token is not a
replacement for `AI_API_KEY`. If you use API-key authentication for both, put the API key in both
`ANTHROPIC_API_KEY` and `AI_API_KEY`. If you only need the assistant, leave `AI_PROVIDER` unset.

You can set `AI_MODEL` to choose the provider's model and `AI_BASE_URL` to use a gateway. Leaving
both empty uses refiroo's default Claude model and Anthropic's API. The assistant's `--model sonnet`
does not select the provider model.

For an endpoint using the chat-completions protocol, set `AI_PROVIDER=openai-compatible`,
`AI_BASE_URL` and `AI_MODEL`; set `AI_API_KEY` if that endpoint requires one. A provider on another
container or host needs an address reachable from the engine container: `localhost` inside the
container refers to that container.

Keep `AI_SEND_LEVEL=values` for mapping targets. If you enable only features that need less data,
choose `structure` or `samples` instead. `AI_SAMPLE_VALUES=20` controls sampling at `samples`,
not the amount read by the assistant at `values`.

## 4. Enable external agent access if needed

To let external MCP assistants connect, add:

```dotenv
MCP_ENABLED=true
```

This is optional and does not enable or authenticate the built-in assistant. The shipped web image
already forwards `/mcp` and `/.well-known/`; another reverse proxy must forward them too. After
restart, a security administrator can open **Settings › Security › Agent access** to register and
manage assistants and agent clients. Their grants determine the data they can reach.

## 5. Apply the settings

For the normal Compose installation, run:

```bash
docker compose up -d
docker compose ps
```

For the documentation's reference instance, use its own command instead:

```bash
guide/reference/reference.sh up
guide/reference/reference.sh status
```

The reference command builds and starts its dedicated Compose project and reruns its reference-data
loader. It uses `guide/reference/.env`, rather than the repository-root `.env`. Open
`http://localhost:8480` and sign in with the reference administrator's credentials from that file.

Changing the environment requires the engine container to be recreated; `up -d` applies those
changes. A plain `docker compose restart` does not load an edited environment file. Applying
changes can remove unfinished assistant sessions' files because the shipped Compose file does not
persist their working directories. Finish or discard active tasks first.

## 6. Check the provider and assistant separately

1. With **Operations** access, open **Settings › Administration › AI**. Under **What is switched on**,
   check **Assistant** and **Provider** against what you enabled. **Assistant: On** means the command
   is set; it does not prove a session can authenticate. Check **What may be sent** too.
2. If a provider is configured, select **Send a test request**. Success shows **The AI provider
   answered** and a new **Calls** entry. The request contains none of your reference data. With
   only the assistant enabled, this button is absent.
3. To test the assistant independently, use an active workspace and a person with **Use AI proposals**,
   **Work in change sets**, **Bulk and import**, and permission to create jobs there. The model-change
   test also needs **Model authoring** and **Model release** access. Open the workspace's
   **⋯** menu and choose **Change this model…**. Enter a small proposed change in **What should
   change?**, then select **Ask the assistant**. Read the proposed result without applying it.
   This exercises a real session and sends the instructions, model and any records it needs.
4. Return to **Settings › Administration › AI**. The session's turn should appear in **Calls** with
   its outcome, tokens and any reported cost. Review or discard the test task when finished.

## If startup or a request fails

| What you see | What to check and do |
| --- | --- |
| The engine refuses to start and names `AI_API_KEY`. | `AI_PROVIDER=claude` needs that setting even if the assistant has credentials. Add the API key, or unset `AI_PROVIDER` if you only want the assistant, then apply the settings again. |
| Startup names `AI_BASE_URL`, `AI_MODEL` or a provider factory. | Supply the required endpoint and model for `openai-compatible`, or correct the factory named in the message. Apply the settings again. |
| Startup names `INFERENCE_ASSISTANT` or `INFERENCE_ASSISTANT_ROWS`. | Remove these retired settings. Use `AI_PROVIDER` and `AI_SAMPLE_VALUES` for the corresponding configuration. |
| The provider test says the key was refused. | Replace `AI_API_KEY` with a valid provider key, apply the settings, and test again. Changing the assistant's token does not fix this test. |
| The provider cannot be reached or returns an answer in the wrong shape. | Check the displayed endpoint, outbound connectivity and gateway settings. A compatible endpoint must support JSON-schema answers. The failed call remains visible; ordinary work can continue without the proposal. |
| The assistant action is missing. | Check `AI_AGENT_COMMAND`, `AI_SEND_LEVEL=values` and the person's grants. The provider switch and MCP switch do not make it appear. |
| A task reports `AI_AGENT_COMMAND could not start`. | Check the command and the image being used. With the shipped image, use `claude` and `AI_AGENT_SANDBOX=container`; its executable and separate user are already installed. |
| A turn fails or says `The session ended without an answer.` | Check the task's warnings and its failed call. Verify the assistant's credential variable, token validity, network access and container sandbox setting. Inspect the task's session log if the message is insufficient; it is beside its folder under `/data/assistant`. Treat logs as sensitive. Correct the configuration, apply it, then continue or start the task again. |
| A turn says `The session took too long.` | It exceeded the 30-minute session limit. Check service availability and reduce the task before trying again. `AI_TIMEOUT_SECONDS` controls provider calls, not this session limit. |
| The task reports `AI_ASSISTANT_ROLE_CHANGED`. | An assistant role no longer has the required action groups. Follow the message to restore them or have an administrator delete that role so refiroo can recreate it, then try again. |

For startup diagnostics on the normal installation, use a bounded log read:

```bash
docker compose logs --tail=100 engine
```

For the reference instance, select its project and environment explicitly:

```bash
docker compose -p refiroo-guide-ref -f compose.yml \
  -f guide/reference/compose.override.yml \
  --env-file guide/reference/.env logs --tail=100 engine
```

## Other installations

On a host installation, install Claude Code where the worker can run it. Set the same credentials
in the worker's environment, leave `AI_AGENT_SANDBOX` unset to use the operating-system sandbox,
and restart the engine and worker through your service manager. The session refuses to run if the
sandbox is unavailable. For the repository's developer installation, settings live in
`.dev/settings.env` rather than Compose's `.env`.

`AI_AGENT_API_URL` defaults to `PUBLIC_URL`. Set it only when the assistant must use a different,
reachable address for this engine's API. Provider credentials still use their own settings; an
internal API address does not change the AI provider's endpoint.
