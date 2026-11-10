"""A proposal provider that answers through the Claude Code CLI (``claude -p``), ``AI_PROVIDER=claude-code``.

Each request runs one headless Claude Code call with no tools, no MCP servers, no project settings and
no saved session, in an empty temporary directory, so the model sees only refiroo's instructions and
context. The answer is held to the request's JSON schema (``--json-schema``); refiroo checks it again,
as for any provider. It needs no ``AI_API_KEY``: it authenticates as Claude Code does
(``CLAUDE_CODE_OAUTH_TOKEN`` or ``ANTHROPIC_API_KEY`` in the environment, or the host's sign-in) and
uses that account's limits. ``AI_MODEL`` is any model name ``claude --model`` takes; empty is Claude
Code's default. The input tokens and the CLI's ``total_cost_usd`` (the API-price equivalent of the
call, whatever the sign-in) come back on the answer, so ``ai_calls`` records them.
"""

import json
import logging
import shutil
import subprocess
import tempfile
from typing import Any

from .provider import ProposalRequest, ProviderAnswer, ProviderError, answer_schema

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
        # plain input, and ``ai_calls`` keeps only their sum.
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
        cost = reply.get("total_cost_usd")
        return ProviderAnswer(
            data,
            self.model or "claude-code",
            tokens_in,
            tokens_out,
            cost_usd=float(cost) if isinstance(cost, int | float) else None,
        )
