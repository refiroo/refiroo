"""A development-only proposal provider that answers through the Claude Code CLI (`claude -p`).

Not part of the engine and never deployed: it lives outside ``app/``, nothing imports it, and it is
loaded only when the developer names it in ``.dev/settings.env``:

    AI_PROVIDER=devtools.claude_code_provider:provider
    AI_MODEL=sonnet            # any model name `claude --model` takes; empty: Claude Code's default

Remove it by deleting ``backend/devtools/`` and that line. Each request runs one headless Claude Code
call with no tools, no MCP servers, no project settings and no saved session, in an empty temporary
directory, so the model sees only refiroo's instructions and context. The answer is held to the
request's JSON schema (``--json-schema``); refiroo checks it again, as for any provider. Usage and
cost are logged and the tokens returned, so ``ai_calls`` records them. It uses the developer's Claude
Code sign-in and its limits.

Each call also appends one line to ``usage.jsonl`` beside this file (the purpose, prompt version,
model, the input tokens by kind, the output tokens, ``total_cost_usd`` and the time), so a try's usage
can be reported at API prices (0.16 plan, "AI usage log"). Delete the file to start over.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

USAGE_LOG = Path(__file__).with_name("usage.jsonl")

from app.engine.proposals.provider import (
    ProposalRequest,
    ProviderAnswer,
    ProviderError,
    answer_schema,
)

logger = logging.getLogger(__name__)


class ClaudeCodeProvider:
    name = "claude-code"

    def __init__(self, model: str, timeout: int) -> None:
        self.model = model
        self.timeout = timeout
        self.binary = shutil.which("claude") or "claude"

    def propose(self, request: ProposalRequest) -> ProviderAnswer:
        command = [
            self.binary,
            "-p",
            json.dumps(request.context, ensure_ascii=False),
            "--output-format",
            "json",
            "--system-prompt",
            request.instructions,
            "--json-schema",
            json.dumps(answer_schema(request.answer)),
            "--tools",
            "",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--no-session-persistence",
        ]
        if self.model:
            command += ["--model", self.model]
        with tempfile.TemporaryDirectory(prefix="refiroo-claude-code-") as empty:
            try:
                done = subprocess.run(
                    command,
                    cwd=empty,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ProviderError(
                    "unreachable", "Claude Code did not answer in time (AI_TIMEOUT_SECONDS)"
                ) from exc
            except OSError as exc:
                raise ProviderError("unreachable", "The claude command could not be run") from exc
        try:
            reply: dict[str, Any] = json.loads(done.stdout)
        except ValueError as exc:
            raise ProviderError(
                "failed", f"Claude Code answered no JSON (exit {done.returncode})"
            ) from exc
        usage = reply.get("usage") or {}
        tokens_in = sum(
            int(usage.get(key) or 0)
            for key in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
        )
        tokens_out = int(usage.get("output_tokens") or 0)
        # The input kinds apart: the API prices a cache write and a cache read differently from
        # plain input, and ``ai_calls`` keeps only their sum. ``total_cost_usd`` is Claude Code's
        # API-price equivalent of the call, whatever the sign-in.
        logger.info(
            "Claude Code (%s): %s tokens in (%s plain, %s cache write, %s cache read), %s out, "
            "%s USD reported, %s ms",
            self.model or "default",
            tokens_in,
            int(usage.get("input_tokens") or 0),
            int(usage.get("cache_creation_input_tokens") or 0),
            int(usage.get("cache_read_input_tokens") or 0),
            tokens_out,
            reply.get("total_cost_usd"),
            reply.get("duration_ms"),
        )
        try:
            with USAGE_LOG.open("a", encoding="utf-8") as log:
                log.write(
                    json.dumps(
                        {
                            "at": datetime.now(UTC).isoformat(),
                            "purpose": request.purpose,
                            "promptVersion": request.prompt_version,
                            "model": self.model or "default",
                            "plain": int(usage.get("input_tokens") or 0),
                            "cacheWrite": int(usage.get("cache_creation_input_tokens") or 0),
                            "cacheRead": int(usage.get("cache_read_input_tokens") or 0),
                            "out": tokens_out,
                            "costUsd": reply.get("total_cost_usd"),
                            "ms": reply.get("duration_ms"),
                            "error": bool(done.returncode != 0 or reply.get("is_error")),
                        }
                    )
                    + "\n"
                )
        except OSError:
            logger.warning("Could not append to %s", USAGE_LOG)
        if done.returncode != 0 or reply.get("is_error"):
            raise ProviderError(
                "failed",
                f"Claude Code failed ({reply.get('subtype') or done.returncode}): "
                f"{str(reply.get('result') or done.stderr or '')[:200]}",
            )
        data = reply.get("structured_output")
        if data is None:
            try:
                data = json.loads(reply.get("result") or "")
            except ValueError as exc:
                raise ProviderError(
                    "malformed", "Claude Code's answer is not JSON in the expected place"
                ) from exc
        return ProviderAnswer(data, self.model or "claude-code", tokens_in, tokens_out)


def provider() -> ClaudeCodeProvider:
    return ClaudeCodeProvider(
        os.environ.get("AI_MODEL", "").strip(),
        int(os.environ.get("AI_TIMEOUT_SECONDS", "") or 300),
    )
