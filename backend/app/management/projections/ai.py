"""The AI provider's status and call records as the API answers them (0.16 AP1)."""

from sqlalchemy.orm import Session

from ...common.pagination import Page
from ...common.time import as_utc
from ...config import Settings
from ...engine.identity.principals import named, ref
from ...engine.proposals import calls
from ...engine.proposals.context import FEATURE_LEVELS
from ...engine.proposals.registry import AiConfiguration, model_label, provider_label
from ...engine.tasks import agent
from ...models.database import AiCall
from ..schemas.ai import (
    AiCallPage,
    AiCallResponse,
    AiFeature,
    AiStatusResponse,
    AiSystemInfo,
    AiTotals,
)

FEATURE_NAMES = {
    "mappingTarget": "Targets for the unmapped values of a mapping view",
}


def call_response(session: Session, row: AiCall) -> AiCallResponse:
    return AiCallResponse(
        id=row.public_id,
        purpose=row.purpose,  # type: ignore[arg-type]
        provider=row.provider,
        model=row.model,
        sendLevel=row.send_level,  # type: ignore[arg-type]
        promptVersion=row.prompt_version,
        requestedBy=named(session, ref(row.requested_by_user_id, row.requested_by_client_id)),  # type: ignore[arg-type]
        jobId=row.job_id,
        startedAt=as_utc(row.started_at),
        durationMs=row.duration_ms,
        bytesIn=row.bytes_in,
        bytesOut=row.bytes_out,
        tokensIn=row.tokens_in,
        tokensOut=row.tokens_out,
        costUsd=float(row.cost_usd) if row.cost_usd is not None else None,
        taskId=row.task_id,
        outcome=row.outcome,  # type: ignore[arg-type]
        failureKind=row.failure_kind,  # type: ignore[arg-type]
        failure=row.failure,
        content=row.content,
    )


def call_page(session: Session, page: Page[AiCall]) -> AiCallPage:
    return AiCallPage(items=[call_response(session, row) for row in page.items], **page.links())


def status(session: Session, ai: AiConfiguration, settings: Settings) -> AiStatusResponse:
    provider = ai.provider
    last = calls.last_call(session)
    found = calls.totals(session)
    return AiStatusResponse(
        configured=provider is not None,
        assistant=agent.enabled(),
        provider=provider_label(provider) if provider else None,
        model=model_label(provider) if provider else None,
        endpoint=settings.ai_base_url or None,
        keySet=bool(settings.ai_api_key),
        sendLevel=ai.policy.level,
        sampleValues=ai.policy.samples,
        minConfidence=ai.min_confidence,
        logContent=ai.log_content,
        logContentDays=ai.log_content_days,
        timeoutSeconds=settings.ai_timeout_seconds,
        features=[
            AiFeature(
                purpose=purpose,
                name=FEATURE_NAMES[purpose],
                needs=needs,
                available=ai.offers(purpose),
            )  # type: ignore[arg-type]
            for purpose, needs in FEATURE_LEVELS.items()
            if purpose in FEATURE_NAMES
        ],
        lastCall=call_response(session, last) if last else None,
        totals=AiTotals(
            days=found.days,
            calls=found.calls,
            failed=found.failed,
            tokensIn=found.tokens_in,
            tokensOut=found.tokens_out,
            bytesIn=found.bytes_in,
            bytesOut=found.bytes_out,
            costUsd=found.cost_usd,
        ),
    )


def system_info(ai: AiConfiguration) -> AiSystemInfo:
    return AiSystemInfo(
        configured=ai.configured,
        provider=provider_label(ai.provider) if ai.provider else None,
        model=model_label(ai.provider) if ai.provider else None,
        sendLevel=ai.policy.level,
        assistant=agent.enabled(),
    )
