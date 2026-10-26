"""The mail settings and the outbox (Product 0.12 M1, D418–D422, API.md § Mail).

Mail decides where one-time links go, so it needs Security administration at the instance (D423).
"""

from typing import Literal

from fastapi import APIRouter, Query, Request, Response

from ...engine.identity.settings import IdentitySettings
from ...engine.mail import outbox, settings, smtp, templates
from ...errors import api_error
from ...models.commands import MailSettingsUpdate, MailTest
from ..access import INSTANCE, AuthorizedRoute, requires
from ..dependencies import DbSession
from ..paging import PageQuery
from ..projections import mail as present
from ..schemas.mail import MailMessagePage, MailSettingsResponse, MailTestResponse

router = APIRouter(route_class=AuthorizedRoute, prefix="/api/v1", tags=["mail"])


def _identity(request: Request) -> IdentitySettings:
    return request.app.state.identity_settings


@router.get("/mail-settings", response_model=MailSettingsResponse)
@requires("security.manage", at=INSTANCE)
def get_mail_settings(request: Request, session: DbSession) -> MailSettingsResponse:
    """The SMTP connection mail is sent through, the address its links point to and how many
    messages wait, were sent or failed. Never the password (0.12 M1)."""
    return present.settings_response(session, _identity(request), settings.load(session))


@router.put("/mail-settings", response_model=MailSettingsResponse)
@requires("security.manage", at=INSTANCE)
def put_mail_settings(
    payload: MailSettingsUpdate, request: Request, session: DbSession
) -> MailSettingsResponse:
    """Save the settings, replacing what was saved; the first save omits ``expectedVersion``.
    ``password`` is sealed and never answered; omitted, it keeps the saved one. A login is refused
    over an unencrypted connection (``422 MAIL_INSECURE_LOGIN``). Nothing is sent: try the settings
    with ``POST /mail-settings/test``."""
    row = settings.save(session, _identity(request), payload)
    return present.settings_response(session, _identity(request), row)


@router.delete("/mail-settings", status_code=204)
@requires("security.manage", at=INSTANCE)
def delete_mail_settings(session: DbSession) -> Response:
    """Remove the settings: no mail is sent (``409 MAIL_NOT_SET_UP`` for anything that needs it).
    Messages already waiting stay in the outbox and fail after 24 hours."""
    settings.remove(session)
    return Response(status_code=204)


@router.post("/mail-settings/test", response_model=MailTestResponse)
@requires("security.manage", at=INSTANCE)
def post_mail_test(payload: MailTest, request: Request, session: DbSession) -> MailTestResponse:
    """Send a test message through the saved settings now, and answer what failed if it cannot be
    sent (``422 MAIL_SEND_FAILED``, ``details.kind``: `connection`, `tls`, `login`, `recipient`,
    `sender` or `rejected`). The message shows the address links will point to."""
    identity = _identity(request)
    row = settings.require(session)
    connection = settings.connection(identity, row)
    rendered = templates.test_message(
        templates.product(session), settings.application_url(identity, row)
    )
    session.rollback()
    try:
        smtp.deliver(
            connection, smtp.build(connection, payload.to, rendered.subject, rendered.body)
        )
    except smtp.MailError as error:
        raise api_error(
            422, "MAIL_SEND_FAILED", str(error), {"kind": error.kind, "reason": str(error)}
        ) from None
    return MailTestResponse(sentTo=payload.to)


@router.get("/mail-outbox", response_model=MailMessagePage)
@requires("security.manage", at=INSTANCE)
def list_mail_outbox(
    session: DbSession,
    paging: PageQuery,
    status: Literal["pending", "sent", "failed"] | None = None,
    page_size: int = Query(default=50, ge=1, le=500, alias="pageSize"),
) -> MailMessagePage:
    """The messages waiting, sent or given up on, newest first; a failed one says why. The text of
    a message is never answered."""
    return present.message_page(
        outbox.message_page(session, status=status, page=paging, page_size=page_size)
    )
