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

## Choose the features and credentials

Both switches are needed for all AI features. Set `AI_SEND_LEVEL=values` for the assistant and
mapping targets. The two switches can use different credentials.

| Features | Switch | With a Claude subscription | With an Anthropic API key |
| --- | --- | --- | --- |
| Load a workbook or change records with the assistant; **Change this model…** | `AI_AGENT_COMMAND="claude --model sonnet --permission-mode bypassPermissions"` | `CLAUDE_CODE_OAUTH_TOKEN` from `claude setup-token` | `ANTHROPIC_API_KEY` |
| Proposed mapping targets, asking a list in words, explanations of model changes and what changed | `AI_PROVIDER` | Development and reference instance only: `AI_PROVIDER=devtools.claude_code_provider:provider`, `AI_MODEL=sonnet`; uses Claude Code's sign-in or `CLAUDE_CODE_OAUTH_TOKEN` | `AI_PROVIDER=claude`, `AI_API_KEY`; optional `AI_MODEL` |

For a production provider, use the Claude API with an API key, or `openai-compatible` with a
chat-completions endpoint, including a model hosted inside your organisation. `AI_PROVIDER=claude`
cannot use a Claude subscription token. The development subscription option is explained below.

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
remove those guards. `AI_AGENT_SANDBOX=container` runs the session without Claude Code's permission
prompts so it can execute the shell commands needed for a task. The shipped image's separate
`assistant` user is its boundary: it cannot read the engine's secrets or job files. Do not leave
this setting unset in this installation. The container does not restrict outbound network access;
apply any required restrictions in your deployment. `values` allows the assistant to read the
workbook and records needed by the task. Lower levels make the assistant unavailable.

`AI_AGENT_API_URL` is the address the assistant's session uses to reach this engine's API.
Compose sets it to `http://127.0.0.1:8000` unless you override it in the environment file, so no
extra setting is needed for the shipped installation. The session runs inside the engine container:
`localhost` there names that container, so a public address such as `http://localhost:8480` would
send it to the wrong port. Keep `PUBLIC_URL` as the address people open in their browsers.

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

Keep the image's `CLAUDE_CONFIG_DIR=/opt/refiroo/rdm-engine/data/assistant-claude` unless you also arrange the required
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

### Use the subscription for provider features in development

The repository supplies a development-only provider in `backend/devtools/claude_code_provider.py`.
It answers through Claude Code using the developer's sign-in and limits. It is absent from the
engine image. It works on a [developer instance](/docs/run/developer-instance/) and on the guide's
reference instance, whose Compose override mounts `backend/devtools` into the engine.

For a developer instance, put these settings in `.dev/settings.env`; install and authenticate
Claude Code on the host. For the reference instance, put them in `guide/reference/.env` beside the
assistant settings and subscription token from step 2:

```dotenv
AI_PROVIDER=devtools.claude_code_provider:provider
AI_MODEL=sonnet
```

Leave `AI_API_KEY` unset for this provider. Each request runs a separate Claude Code call with no
tools, MCP servers or saved session. It still sends the feature's context to Claude. Usage is
recorded in **Calls** and appended to `backend/devtools/usage.jsonl`; reported dollar amounts are
usage at API prices, not a subscription invoice. This option is for development and trying the
features. A production installation uses `claude` with `AI_API_KEY` or `openai-compatible`.

A custom provider can also be named as `AI_PROVIDER=package.module:function`. The module must be
installed in the engine's Python environment; the factory takes no arguments and returns an object
with `propose(request)`. A missing module or unsuitable result refuses startup.

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

:::caution[Automatic HTTPS needs both Compose files]
With [automatic HTTPS](/docs/run/install-with-compose/#5-start-with-automatic-https), run `docker compose up -d` with
`compose.acme.yml` too: keep `COMPOSE_FILE=compose.yml:compose.acme.yml` set in the shell, or add
`-f compose.yml -f compose.acme.yml` to each command. Without it, web is recreated without Caddy
in front and the site stops answering until you run the command again with both files.
:::

For the normal Compose installation, run:

```bash
docker compose up -d
docker compose ps
```

For the documentation's reference instance, use its own command instead:

```bash
guide/reference/reference.sh start
guide/reference/reference.sh status
```

The reference `start` command starts or recreates its dedicated Compose project's containers without
rebuilding the images or rerunning the data loader. Use `up` for the initial build and data load. It uses `guide/reference/.env`, rather than the repository-root `.env`. Open
`http://localhost:8480` and sign in with the reference administrator's credentials from that file.

Changing the environment requires the engine container to be recreated; `up -d` applies those
changes without rebuilding the image. A plain `docker compose restart` does not load an edited environment file.
The shipped Compose file keeps task folders in `assistant` and Claude Code configuration and
session logs in `assistant-claude`. Recreating the container, including during upgrades, keeps
these named volumes, so open tasks retain the files they need to continue.

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
   change?**, then select **Ask the assistant**. Wait until the task presents its proposal, then
   read it without applying it. Reaching the proposal checks that the assistant can reach the
   engine's API as well as authenticate with Claude Code. This exercises a real session and sends
   the instructions, model and any records it needs.
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
| A task stops at once with an internal error. | Check `AI_AGENT_API_URL`: an unreachable engine API address can cause this failure. With the shipped Compose installation, remove an incorrect override so Compose supplies `http://127.0.0.1:8000`. On a host installation, use an address reachable from the engine's machine. Apply the settings, start another task and check that it reaches its proposal. |
| A turn fails or says `The session ended without an answer.` | Check the task's warnings and its failed call. Verify the assistant's credential variable, token validity, network access and container sandbox setting. Inspect the task's session log if the message is insufficient; it is beside its folder under `/opt/refiroo/rdm-engine/data/assistant`. Treat logs as sensitive. Correct the configuration, apply it, then continue or start the task again. |
| A task's note says the session took longer than the limit | The turn exceeded `AI_AGENT_TIMEOUT_SECONDS` (default 1800) and was stopped; the task is back at its last point. Check service availability, reduce the task or raise the limit, then continue or try again. `AI_TIMEOUT_SECONDS` controls provider calls, not this session limit. |
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

Outside Compose, an unset or empty `AI_AGENT_API_URL` uses `PUBLIC_URL`. Set it yourself when the
engine's machine cannot reach that public address, for example behind a proxy that only answers
outside callers. Use an address for this engine's API that the session can reach from that machine,
then run the assistant check in step 6. Provider credentials still use their own settings; an
internal API address does not change the AI provider's endpoint.
