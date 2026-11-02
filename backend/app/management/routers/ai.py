"""The AI provider for operators (Product 0.16 AP1, AP-D4): its status, its call records and a test.

There is no generic "ask the model" route: a proposal is made through its feature's own route,
which builds the context within the send level (AP-D3). The provider is set in the environment and
read at start; nothing here changes it, and the key is never answered.
"""

from dataclasses import replace
from datetime import UTC, datetime

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from ...config import get_settings
from ...engine.model.registry import resolve_request_model
from ...engine.proposals import calls, impact_summary, query_translation
from ...engine.proposals.context import Policy
from ...engine.proposals.provider import ProposalRequest
from ...engine.reads.snapshot_reads import change_set_context, publication_context
from ...errors import api_error
from ...models.commands import (
    DraftImpactSummaryRequest,
    HistoryAccountRequest,
    ImpactSummaryRequest,
    QueryTranslationRequest,
)
from ...models.database import AiCall
from .. import history_account as history_inputs
from .. import impact_summary as impact_inputs
from ..access import (
    BODY,
    INSTANCE,
    QUERY_TRANSLATION,
    RECORD_READ,
    WORKSPACE_PATH,
    AuthorizedRoute,
    requires,
)
from ..ai import ai_requested, configuration
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..projections import ai as present
from ..schemas.ai import (
    AiCallPage,
    AiCallResponse,
    AiStatusResponse,
    HistoryAccountResponse,
    ImpactSummaryResponse,
    QueryTranslationFilter,
    QueryTranslationResponse,
    QueryTranslationUnexpressed,
)

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["ai"])
# The draft's account is part of model management: present when model drafts are (MODEL_ADMIN_MUTATIONS_ENABLED).
draft_router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["ai"])

TEST_PROMPT_VERSION = "connection-test/1"


class _TestAnswer(BaseModel):
    ready: bool


@router.get("/ai/status", response_model=AiStatusResponse)
@requires("operations.read", at=INSTANCE)
def get_ai_status(request: Request, session: DbSession) -> AiStatusResponse:
    """The provider as set at start (provider, model, endpoint, whether a key is set, the send level
    and the other ``AI_*`` settings), each feature and whether it is offered, the last call, and the
    totals of the last 30 days."""
    return present.status(session, configuration(request), get_settings())


@router.get("/ai/calls", response_model=AiCallPage)
@requires("operations.read", at=INSTANCE)
def list_ai_calls(
    session: DbSession,
    paging: PageQuery,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> AiCallPage:
    """Every call to the provider, newest first: who asked, for what, the provider and model, the
    sizes, the outcome and, while ``AI_LOG_CONTENT`` keeps it, the request and answer."""
    return present.call_page(session, calls.call_page(session, page=paging, page_size=page_size))


@router.post("/ai/test", response_model=AiCallResponse)
@requires("ai.test", at=INSTANCE)
def test_ai_provider(
    request: Request, principal: CurrentPrincipal, session: DbSession
) -> AiCallResponse:
    """Send the provider a fixed request that holds no data and answer the call it made: answered,
    or failed with what failed (the key refused, not reached, out of shape). Recorded like any
    call. ``409 AI_NOT_CONFIGURED`` without a provider."""
    ai = configuration(request)
    if not ai.configured:
        raise api_error(
            409, "AI_NOT_CONFIGURED", "No AI provider is set up on this instance (AI_PROVIDER)"
        )
    requester = calls.Requester(
        principal.row_id if principal.kind == "user" else None,
        principal.row_id if principal.kind == "client" else None,
    )
    recorded = []

    def record(row: AiCall) -> None:
        calls.record_in(session)(row)
        recorded.append(row)

    calls.ask(
        ai,
        ProposalRequest(
            purpose="connectionTest",
            instructions='This is a connection test. Answer {"ready": true}.',
            prompt_version=TEST_PROMPT_VERSION,
            context={"test": True},
            answer=_TestAnswer,
        ),
        record=record,
        requester=requester,
    )
    session.commit()
    return present.call_response(session, recorded[0])


@router.post(
    "/workspaces/{workspace_key}/query-translations", response_model=QueryTranslationResponse
)
@requires("records.read", at=QUERY_TRANSLATION)
def post_query_translation(
    workspace_key: str,
    body: QueryTranslationRequest,
    request: Request,
    principal: CurrentPrincipal,
    session: DbSession,
) -> QueryTranslationResponse:
    """Turn a question in words into the filters of a table view, answered directly (0.16 AG4).

    The provider is sent the question, today's date and the list's fields, conditions and
    relationships with their labels. At send level ``samples`` or ``values`` it is also sent the
    record names of a relationship's types when they hold at most 50 records in the context asked
    about, so it can choose records by meaning; at ``structure`` it is sent no record value. The answer is
    the list's own filters, a search text and the parts of the question the list cannot express; a
    record named in words is its ID, found in the database in the context asked about, or the part
    is not expressed. With any part not expressed ``applied`` is false: a client applies nothing.
    The fields it may use are every relationship the listed type has, the view's ``filterFields``,
    and on a live list ``createdAt`` and ``updatedAt``. Requires Browse and Use AI proposals in the workspace. Refused: ``403 FORBIDDEN``,
    ``409 AI_NOT_CONFIGURED``, ``409 AI_SEND_LEVEL_TOO_LOW``, ``404 VIEW_NOT_FOUND``, ``422
    QUERY_TRANSLATION_VIEW_UNSUPPORTED`` (not a table view), ``404 CHANGE_SET_NOT_FOUND``, ``404
    PUBLICATION_NOT_FOUND``. A provider that fails, answers out of shape, or answers with a field or
    condition the list does not take is a recorded failed call: ``502 QUERY_TRANSLATION_FAILED``
    (``details.callId``), with nothing applied."""
    ai_requested(
        request, "queryTranslation", True, workspace_key=workspace_key, send_level=body.sendLevel
    )
    change_set_id = str(body.changeSetId) if body.changeSetId else None
    publication_id = str(body.publicationId) if body.publicationId else None
    snapshot = resolve_request_model(session, workspace_key, change_set_id, publication_id)
    ai = configuration(request)
    if body.sendLevel is not None:
        ai = replace(ai, policy=Policy(body.sendLevel, ai.policy.samples))
    context = (
        change_set_context(session, change_set_id)
        if change_set_id
        else publication_context(session, publication_id)
        if publication_id
        else None
    )
    prepared = query_translation.prepare(
        snapshot.model,
        body.applicationKey,
        body.viewKey,
        body.question,
        live=not (change_set_id or publication_id),
        today=datetime.now(UTC).date(),
    )
    # At samples or values a short list's record names are read, in this transaction, in one
    # statement per type set; at structure none is.
    prepared = query_translation.with_names(
        session, prepared, ai.policy, workspace_key=snapshot.workspace_key, context=context
    )
    requester = calls.Requester(
        principal.row_id if principal.kind == "user" else None,
        principal.row_id if principal.kind == "client" else None,
    )
    # The provider can take seconds: no transaction is held while it answers (J48.8).
    session.commit()
    translation = query_translation.finish(
        session,
        ai,
        prepared,
        snapshot.model,
        workspace_key=snapshot.workspace_key,
        context=context,
        application_key=body.applicationKey,
        requester=requester,
    )
    session.commit()
    return QueryTranslationResponse(
        filters=[
            QueryTranslationFilter(field=item.field, operator=item.operator, value=item.value)
            for item in translation.filters
        ],
        search=translation.search,
        notExpressed=[
            QueryTranslationUnexpressed(part=item.part, reason=item.reason)
            for item in translation.not_expressed
        ],
        applied=translation.applied,
    )


def _summarise(
    request: Request,
    principal: CurrentPrincipal,
    session: DbSession,
    body: ImpactSummaryRequest,
    inputs: impact_inputs.Inputs,
) -> ImpactSummaryResponse:
    ai = impact_summary.with_level(configuration(request), body.sendLevel)
    facts = impact_inputs.facts_of(session, inputs)
    requester = calls.Requester(
        principal.row_id if principal.kind == "user" else None,
        principal.row_id if principal.kind == "client" else None,
    )
    summary = impact_summary.explain(
        session,
        ai,
        facts,
        language=body.language or impact_summary.DEFAULT_LANGUAGE,
        requester=requester,
    )
    session.commit()
    return impact_inputs.response(summary)


@router.post("/model-releases/{release_id}/impact-summary", response_model=ImpactSummaryResponse)
@requires("model.activate", at=BODY)
def post_release_impact_summary(
    release_id: str,
    body: ImpactSummaryRequest,
    request: Request,
    principal: CurrentPrincipal,
    session: DbSession,
) -> ImpactSummaryResponse:
    """Words for what activating a release in a workspace does (0.16 AO1), compared with the release
    the workspace runs. The engine writes the facts: each difference between the models, each rule
    the workspace's data would break with its count, what the consumer APIs would notice, whether
    activation is refused and the workspace's records per touched type, counted over the whole set.
    The provider is sent them (at most 40 of a kind, with each kind's true total) and no record; it
    words them, and a statement that cites no fact that exists is dropped and counted. The answer
    always carries every fact: a provider that fails or answers out of shape is a `200` with
    `failure` and no statements, recorded as a failed call. The same request within an hour is
    answered with no call (`cached`). Needs Activate model releases and Use AI proposals in
    `workspaceKey`. Refused: `403 FORBIDDEN`, `409 AI_NOT_CONFIGURED`, `409 AI_SEND_LEVEL_TOO_LOW`,
    `404 MODEL_RELEASE_NOT_FOUND`."""
    ai_requested(
        request, "impactSummary", True, workspace_key=body.workspaceKey, send_level=body.sendLevel
    )
    inputs = impact_inputs.release_inputs(session, release_id, body.workspaceKey)
    return _summarise(request, principal, session, body, inputs)


@draft_router.post("/model-drafts/{draft_id}/impact-summary", response_model=ImpactSummaryResponse)
@requires("model.activate", at=BODY)
def post_draft_impact_summary(
    draft_id: str,
    body: DraftImpactSummaryRequest,
    request: Request,
    principal: CurrentPrincipal,
    session: DbSession,
) -> ImpactSummaryResponse:
    """The same for a model draft, compared with the release it is based on (as its compilation is)
    and with `expectedVersion` claiming the draft's version. Refused as the release's route is, and
    `404 MODEL_DRAFT_NOT_FOUND`, `409 VERSION_CONFLICT`, `422 IMPACT_SUMMARY_DRAFT_INVALID` (an invalid
    draft has no change to describe)."""
    ai_requested(
        request, "impactSummary", True, workspace_key=body.workspaceKey, send_level=body.sendLevel
    )
    inputs = impact_inputs.draft_inputs(session, draft_id, body.expectedVersion, body.workspaceKey)
    return _summarise(request, principal, session, body, inputs)


def _requester(principal: CurrentPrincipal) -> calls.Requester:
    return calls.Requester(
        principal.row_id if principal.kind == "user" else None,
        principal.row_id if principal.kind == "client" else None,
    )


@router.post("/workspaces/{workspace_key}/history/account", response_model=HistoryAccountResponse)
@requires("records.read", at=WORKSPACE_PATH)
def post_workspace_history_account(
    workspace_key: str,
    body: HistoryAccountRequest,
    request: Request,
    principal: CurrentPrincipal,
    session: DbSession,
) -> HistoryAccountResponse:
    """Words for what changed in a workspace over a period (0.16 AO2). The engine counts, in the
    database, over every live change of ``[since, until)``: the records created, changed, moved and
    deleted per type, the fields changed per attribute, the relationships, where the changes came
    from (a job, a publication with the job and the people who prepared it and who published it, or
    made directly), who made them, what happened to change sets, withdrawn publications and model
    activations. Counts are of live data; work in an open change set appears only as that set's
    events. The provider is sent the counts and the model's labels (at most 40 facts of a kind, with
    each kind's true total) and, at send level `values` only, names as data; it words them, and a
    statement that cites no fact that exists is dropped and counted. The answer always carries every
    fact, each with where it leads; a provider that fails is a `200` with `failure` and no
    statements. A period with no change has no facts and makes no call; the same request within an
    hour is answered with no call (`cached`). Needs Browse and Use AI proposals in the workspace.
    Refused: `403 FORBIDDEN`, `409 AI_NOT_CONFIGURED`, `409 AI_SEND_LEVEL_TOO_LOW`, `404
    WORKSPACE_NOT_FOUND`, `422 HISTORY_PERIOD_INVALID` (an empty or reversed period, an unknown time
    zone)."""
    ai_requested(
        request, "historyAccount", True, workspace_key=workspace_key, send_level=body.sendLevel
    )
    period = history_inputs.period_of(body.since, body.until, body.timeZone)
    scope = history_inputs.workspace_scope(session, workspace_key)
    return history_inputs.account(
        session,
        configuration(request),
        scope,
        period,
        send_level=body.sendLevel,
        language=body.language,
        requester=_requester(principal),
    )


@router.post(
    "/objects/{object_type_key}/{object_id}/history/account",
    response_model=HistoryAccountResponse,
)
@requires("records.read", at=RECORD_READ)
def post_object_history_account(
    object_type_key: str,
    object_id: str,
    body: HistoryAccountRequest,
    request: Request,
    principal: CurrentPrincipal,
    session: DbSession,
) -> HistoryAccountResponse:
    """The same for one record's live changes, read through its history: its values, its
    relationships, its moves and where they came from, and no other record's. Needs Browse and Use
    AI proposals in the record's workspace; refused as the workspace's route is, and `404
    OBJECT_NOT_FOUND`."""
    scope = history_inputs.record_scope(session, object_type_key, object_id)
    ai_requested(
        request,
        "historyAccount",
        True,
        workspace_key=scope.workspace_key,
        send_level=body.sendLevel,
    )
    period = history_inputs.period_of(body.since, body.until, body.timeZone)
    return history_inputs.account(
        session,
        configuration(request),
        scope,
        period,
        send_level=body.sendLevel,
        language=body.language,
        requester=_requester(principal),
    )
