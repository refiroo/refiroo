"""The mail settings and the outbox (Product 0.12 M1, D418–D422, API.md § Mail).

Mail decides where one-time links go, so it needs Security administration at the instance (D423).
"""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, File, Form, Query, Request, Response, UploadFile

from ...engine.identity.settings import IdentitySettings
from ...engine.identity.users import load_user
from ...engine.mail import mail_template, outbox, settings, smtp, templates, transport
from ...engine.notifications import mailing
from ...errors import api_error
from ...models.commands import (
    MailSettingsUpdate,
    MailTemplatePreview,
    MailTemplateUpdate,
    MailTest,
)
from ..access import INSTANCE, SIGNED_IN, AuthorizedRoute, requires
from ..dependencies import CurrentPrincipal, DbSession
from ..paging import PageQuery
from ..projections import mail as present
from ..schemas.mail import (
    MailMessagePage,
    MailMessageResponse,
    MailSettingsResponse,
    MailTemplatePreviewResponse,
    MailTemplateResponse,
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
    """How mail is sent (`smtp` or `microsoft365`), the address its links point to and how many
    messages wait, were sent or failed. Never a password, client secret or certificate; a
    certificate is answered by its thumbprint and expiry (0.12 M1, 0.13 MS)."""
    return present.settings_response(session, _identity(request), settings.load(session))


@router.put("/mail-settings", response_model=MailSettingsResponse)
@requires("security.manage", at=INSTANCE)
def put_mail_settings(
    payload: MailSettingsUpdate, request: Request, session: DbSession
) -> MailSettingsResponse:
    """Save the settings, replacing what was saved; the first save omits ``expectedVersion``.
    ``method`` is `smtp` (the default) or `microsoft365`; saving one method clears the other's
    saved fields. Microsoft 365 takes a client secret, a certificate or a managed identity
    (`identityMode` `direct` or `federated`, no secret stored). ``password``, ``clientSecret`` and ``certificate`` are sealed and never answered;
    omitted, they keep the saved one (not for another host, port, tenant, application or token
    address: ``422 MAIL_PASSWORD_REQUIRED``, ``422 MAIL_CREDENTIAL_REQUIRED``). A certificate that
    cannot be used is ``422 MAIL_CERTIFICATE_INVALID``. A login is refused over an unencrypted
    connection (``422 MAIL_INSECURE_LOGIN``). Nothing is sent: try the settings with
    ``POST /mail-settings/test``."""
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
    `sender` or `rejected`), with either method. The message shows the address links will point to."""
    identity = _identity(request)
    row = settings.require(session)
    connection = settings.connection(identity, row)
    rendered = mail_template.apply(
        session,
        identity,
        templates.test_message(templates.product(session), settings.application_url(identity, row)),
        None,
    )
    logo = mail_template.logo_of(session)
    session.rollback()
    try:
        transport.deliver(
            connection,
            smtp.build(
                connection, payload.to, rendered.subject, rendered.body, rendered.html, logo
            ),
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


SAMPLE_NAME = "Alex Example"


@router.get("/mail-template", response_model=MailTemplateResponse)
@requires("mail-template.manage", at=INSTANCE)
def get_mail_template(session: DbSession) -> MailTemplateResponse:
    """The e-mail template: Markdown with placeholders and the logo. Without a saved template the
    default Markdown is answered (`saved` false) and the engine's own layout is used."""
    return present.template_response(mail_template.load(session))


@router.put("/mail-template", response_model=MailTemplateResponse)
@requires("mail-template.manage", at=INSTANCE)
def put_mail_template(payload: MailTemplateUpdate, session: DbSession) -> MailTemplateResponse:
    """Save the template's Markdown, replacing what was saved; the first save omits
    ``expectedVersion``. The logo stays. ``{{content}}`` is required exactly once
    (``422 MAIL_TEMPLATE_CONTENT_REQUIRED``) and only the listed placeholders are known
    (``422 MAIL_TEMPLATE_UNKNOWN_PLACEHOLDER``). Nothing is sent: look at it with
    ``POST /mail-template/preview``."""
    return present.template_response(
        mail_template.save(session, payload.markdown, payload.expectedVersion)
    )


@router.delete("/mail-template", status_code=204)
@requires("mail-template.manage", at=INSTANCE)
def delete_mail_template(session: DbSession) -> Response:
    """Back to the default: the saved Markdown and logo are deleted and the engine's own layout is
    used. Repeats harmlessly."""
    mail_template.remove(session)
    return Response(status_code=204)


@router.put("/mail-template/logo", response_model=MailTemplateResponse)
@requires("mail-template.manage", at=INSTANCE)
def put_mail_template_logo(
    session: DbSession,
    file: Annotated[UploadFile, File(description="A PNG, JPEG or SVG image of at most 512 KB")],
    expectedVersion: Annotated[
        int | None,
        Form(ge=1, description="The template's `version`; omitted before the first save"),
    ] = None,
) -> MailTemplateResponse:
    """Upload the logo that `{{logo}}` shows, sent inline in each mail. Without a saved template
    the default Markdown is saved with it. ``413 MAIL_LOGO_TOO_LARGE``, ``422 MAIL_LOGO_UNSUPPORTED``
    (not a PNG, JPEG or SVG), ``422 MAIL_LOGO_UNSAFE`` (an SVG with script)."""
    data = file.file.read(mail_template.MAX_LOGO_BYTES + 1)
    return present.template_response(
        mail_template.set_logo(session, data, file.content_type or "", expectedVersion)
    )


@router.delete("/mail-template/logo", response_model=MailTemplateResponse)
@requires("mail-template.manage", at=INSTANCE)
def delete_mail_template_logo(
    session: DbSession,
    expected_version: int | None = Query(default=None, ge=1, alias="expectedVersion"),
) -> MailTemplateResponse:
    """Remove the uploaded logo: `{{logo}}` shows the refiroo mark again. ``409
    MAIL_TEMPLATE_NOT_SAVED`` when no template is saved."""
    return present.template_response(mail_template.clear_logo(session, expected_version))


@router.post("/mail-template/preview", response_model=MailTemplatePreviewResponse)
@requires("mail-template.manage", at=INSTANCE)
def post_mail_template_preview(
    payload: MailTemplatePreview, request: Request, session: DbSession
) -> MailTemplatePreviewResponse:
    """Render a draft Markdown around a sample message with sample values and answer the HTML (the
    logo inline as a data URL) and the plain text. Nothing is saved or sent; the draft is checked
    like a save."""
    identity = _identity(request)
    product = templates.product(session)
    url = settings.application_url(identity, settings.load(session))
    rendered = mail_template.render_draft(
        session,
        payload.markdown,
        mail_template.Values(product, url, SAMPLE_NAME),
        templates.template_test(product, url),
    )
    return MailTemplatePreviewResponse(html=rendered.html, text=rendered.body)


@router.post("/mail-template/test", response_model=MailTestResponse)
@requires("mail-template.manage", at=INSTANCE)
def post_mail_template_test(
    request: Request, principal: CurrentPrincipal, session: DbSession
) -> MailTestResponse:
    """Send the saved template, around a sample message, to the caller's own address through the
    saved mail settings now. A client has no address (`403 NOT_A_PERSON`), nor may a person without
    one (`409 NO_EMAIL`); `409 MAIL_NOT_SET_UP`; `422 MAIL_SEND_FAILED` as `POST /mail-settings/test`."""
    if principal.kind != "user":
        raise api_error(403, "NOT_A_PERSON", "Only a signed-in person has an address to send to")
    user = load_user(session, principal.id)
    if not user.email:
        raise api_error(
            409, "NO_EMAIL", f"{user.name} has no e-mail address; add one to the person first"
        )
    identity = _identity(request)
    row = settings.require(session)
    connection = settings.connection(identity, row)
    product = templates.product(session)
    rendered = mail_template.apply(
        session,
        identity,
        templates.template_test(product, settings.application_url(identity, row)),
        user.name,
    )
    logo = mail_template.logo_of(session)
    address = user.email
    session.rollback()
    try:
        transport.deliver(
            connection,
            smtp.build(connection, address, rendered.subject, rendered.body, rendered.html, logo),
        )
    except smtp.MailError as error:
        raise api_error(
            422, "MAIL_SEND_FAILED", str(error), {"kind": error.kind, "reason": str(error)}
        ) from None
    return MailTestResponse(sentTo=address)
