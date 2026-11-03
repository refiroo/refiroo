"""The mail settings and the outbox (Product 0.12 M1, D418–D422, API.md § Mail).

Mail decides where one-time links go, so it needs Security administration at the instance (D423).
"""

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Query, Request, Response

from ...engine.identity.settings import IdentitySettings
from ...engine.identity.users import load_user
from ...engine.mail import outbox, settings, smtp, templates
from ...engine.notifications import mailing
from ...errors import api_error
from ...models.commands import MailSettingsUpdate, MailTest
from ..access import INSTANCE, SIGNED_IN, AuthorizedRoute, requires
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..projections import mail as present
from ..schemas.mail import (
    MailMessagePage,
    MailMessageResponse,
    MailSettingsResponse,
    MailTestResponse,
    NoticeMailResponse,
    NoticeMailUpdate,
)

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
            connection,
            smtp.build(connection, payload.to, rendered.subject, rendered.body, rendered.html),
        )
    except smtp.MailError as error:
        raise api_error(
            422, "MAIL_SEND_FAILED", str(error), {"kind": error.kind, "reason": str(error)}
        ) from None
    return MailTestResponse(sentTo=payload.to)


@router.post("/mail-outbox/{message_id}/stop", response_model=MailMessageResponse)
@requires("security.manage", at=INSTANCE)
def post_stop_mail_message(message_id: str, session: DbSession) -> MailMessageResponse:
    """Stop sending a message that is still waiting for its next try: it fails at once with
    "Stopped by an administrator" and its text is erased. `404 NOT_FOUND`, `409
    MESSAGE_NOT_WAITING` (sent or failed already), `409 MESSAGE_BEING_SENT` (a sender holds it:
    try again)."""
    return present.message_response(outbox.stop(session, message_id))


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


@router.get("/me/notification-mail", response_model=NoticeMailResponse)
@requires("signed-in", at=SIGNED_IN)
def get_my_notification_mail(principal: CurrentPrincipal, session: DbSession) -> NoticeMailResponse:
    """Whether the caller is mailed when something arrives in their inbox, and whether they can be
    (`available`, else `reason`). A client has no mail: `available` is false."""
    user = load_user(session, principal.id) if principal.kind == "user" else None
    return present.notice_mail_response(mailing.state(session, user))


@router.put("/me/notification-mail", response_model=NoticeMailResponse)
@requires("signed-in", at=SIGNED_IN)
def put_my_notification_mail(
    payload: NoticeMailUpdate, principal: CurrentPrincipal, session: DbSession
) -> NoticeMailResponse:
    """Switch mail for the caller's inbox on or off (`enabled`), choose how often the digest comes
    and in which time zone (`digest`: `every` daily or weekly, `timeZone`; 07:00 there, Mondays for
    weekly) and how each kind of notice is mailed (`kinds`, kind -> `now`, `digest` or `off`; the
    kinds not named stay as they are). Switching on needs mail set up (`409 MAIL_NOT_SET_UP`) and an
    address on the person (`409 NO_EMAIL`); a client is refused (`403 NOT_A_PERSON`). An unknown kind
    is `422 UNKNOWN_NOTICE_KIND`, an unknown time zone `422 UNKNOWN_TIME_ZONE`, a kind put in the
    digest with no digest set `422 DIGEST_NOT_SET`; a body with none of the fields is `422`, and
    nothing changes when any part is refused. Choices may be made while mail is off or not set up.
    Only notices made after switching on are mailed. Switching off always works and repeats
    harmlessly. Only the mail changes for a kind in the digest or off: the inbox keeps the notice.
    None of it is a security event."""
    if principal.kind != "user":
        raise api_error(403, "NOT_A_PERSON", "Only a signed-in person can be sent mail")
    user = load_user(session, principal.id, for_update=True)
    now = datetime.now(UTC)
    if payload.digest is not None:
        mailing.set_digest(user, payload.digest.every, payload.digest.timeZone, now)
    if payload.kinds is not None:
        mailing.choose_kinds(session, user, payload.kinds)
    if payload.enabled is None:
        session.commit()
        return present.notice_mail_response(mailing.state(session, user))
    return present.notice_mail_response(mailing.switch(session, user, payload.enabled, now))
