"""The AI provider for operators (Product 0.16 AP1, AP-D4): its status, its call records and a test.

There is no generic "ask the model" route: a proposal is made through its feature's own route,
which builds the context within the send level (AP-D3). The provider is set in the environment and
read at start; nothing here changes it, and the key is never answered.
"""

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from ...config import get_settings
from ...engine.proposals import calls
from ...engine.proposals.provider import ProposalRequest
from ...errors import api_error
from ...models.database import AiCall
from ..access import INSTANCE, AuthorizedRoute, requires
from ..ai import configuration
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..projections import ai as present
from ..schemas.ai import AiCallPage, AiCallResponse, AiStatusResponse

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["ai"])

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
