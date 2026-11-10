"""One message handed to the organisation's SMTP server (Product 0.12 M1, D419).

``deliver`` connects, secures the connection as configured, logs in when it has a user name and
sends. A failure is a ``MailError`` that names what failed (the connection, the TLS handshake, the
login, the recipient, the sender, the server's answer), whether trying again can help, and carries a
sentence an administrator can read; never the password and never a traceback (AGENTS.md, error
handling). The cause stays on ``__cause__`` for debug logs.
"""

import smtplib
import socket
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Protocol

from . import html as mailhtml

TIMEOUT_SECONDS = 15.0

TLS = "tls"
STARTTLS = "starttls"
NONE = "none"
SECURITIES = (TLS, STARTTLS, NONE)

# What failed. The first three are about the server as a whole: every message would fail the same.
CONNECTION = "connection"
TLS_FAILED = "tls"
LOGIN = "login"
RECIPIENT = "recipient"
SENDER = "sender"
REJECTED = "rejected"
SERVER_WIDE = (CONNECTION, TLS_FAILED, LOGIN)


@dataclass(frozen=True)
class Connection:
    host: str
    port: int
    security: str
    username: str | None
    password: str | None
    from_address: str

    def describe(self) -> str:
        return f"{self.host}:{self.port}"


class Sender(Protocol):
    """What ``build`` needs of a connection: the address the message is from."""

    @property
    def from_address(self) -> str: ...


class MailError(Exception):
    """A message that could not be sent: ``kind`` says what failed, ``permanent`` that trying again
    cannot help, and ``str(error)`` is the sentence shown to an administrator."""

    def __init__(
        self,
        kind: str,
        message: str,
        *,
        permanent: bool = False,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.permanent = permanent
        # Seconds the service asked the sender to wait before trying again (Graph's Retry-After).
        self.retry_after = retry_after


def build(
    connection: Sender, to_address: str, subject: str, body: str, html: str | None = None
) -> EmailMessage:
    """A message from the configured address: the plain text and, when there is HTML, the HTML
    after it with the brand images as inline ``cid:`` parts (multipart/alternative, the HTML part
    multipart/related). Clients that show text only get the text."""
    message = EmailMessage()
    message["From"] = connection.from_address
    message["To"] = to_address
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain=connection.from_address.rpartition("@")[2])
    # Tells auto-responders and mail loops that no person wrote this.
    message["Auto-Submitted"] = "auto-generated"
    message.set_content(body)
    if html is not None:
        message.add_alternative(html, subtype="html")
        part = message.get_payload()[-1]
        for cid, filename in mailhtml.IMAGES.items():
            data = (mailhtml.BRAND_DIR / filename).read_bytes()
            part.add_related(
                data, "image", "png", cid=f"<{cid}>", filename=filename, disposition="inline"
            )
    return message


def _open(connection: Connection, timeout: float) -> smtplib.SMTP:
    if connection.security == TLS:
        return smtplib.SMTP_SSL(
            connection.host,
            connection.port,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
    return smtplib.SMTP(connection.host, connection.port, timeout=timeout)


def deliver(
    connection: Connection, message: EmailMessage, *, timeout: float = TIMEOUT_SECONDS
) -> None:
    """Send ``message`` through ``connection``; raises ``MailError``."""
    where = connection.describe()
    try:
        server = _open(connection, timeout)
    except ssl.SSLError as exc:
        raise MailError(
            TLS_FAILED, f"The TLS handshake with {where} failed: {_reason(exc)}"
        ) from exc
    except (OSError, smtplib.SMTPException) as exc:
        raise MailError(CONNECTION, f"Could not connect to {where}: {_reason(exc)}") from exc
    try:
        with server:
            _secure_and_send(server, connection, message, where)
    except MailError:
        raise
    except smtplib.SMTPServerDisconnected as exc:
        raise MailError(CONNECTION, f"{where} closed the connection: {_reason(exc)}") from exc
    except (OSError, smtplib.SMTPException) as exc:
        raise MailError(REJECTED, f"{where} did not accept the message: {_reason(exc)}") from exc


def _secure_and_send(
    server: smtplib.SMTP, connection: Connection, message: EmailMessage, where: str
) -> None:
    try:
        server.ehlo()
        if connection.security == STARTTLS:
            if not server.has_extn("starttls"):
                raise MailError(TLS_FAILED, f"{where} does not offer STARTTLS")
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
    except ssl.SSLError as exc:
        raise MailError(
            TLS_FAILED, f"The TLS handshake with {where} failed: {_reason(exc)}"
        ) from exc
    except smtplib.SMTPServerDisconnected:
        raise
    except smtplib.SMTPException as exc:
        raise MailError(TLS_FAILED, f"{where} would not start TLS: {_reason(exc)}") from exc
    if connection.username:
        try:
            server.login(connection.username, connection.password or "")
        except smtplib.SMTPNotSupportedError as exc:
            raise MailError(LOGIN, f"{where} does not offer a login") from exc
        except smtplib.SMTPAuthenticationError as exc:
            raise MailError(
                LOGIN, f"{where} refused the login of {connection.username}: {_reason(exc)}"
            ) from exc
    try:
        server.send_message(message)
    except smtplib.SMTPRecipientsRefused as exc:
        codes = [code for code, _ in exc.recipients.values()]
        raise MailError(
            RECIPIENT,
            f"{where} refused the address: {_reason(exc)}",
            permanent=all(code >= 500 for code in codes),
        ) from exc
    except smtplib.SMTPSenderRefused as exc:
        # A settings problem the administrator can fix while the message waits.
        raise MailError(
            SENDER, f"{where} refused the from address {connection.from_address}: {_reason(exc)}"
        ) from exc
    except smtplib.SMTPResponseException as exc:
        raise MailError(
            REJECTED,
            f"{where} did not accept the message: {_reason(exc)}",
            permanent=exc.smtp_code >= 500,
        ) from exc


def _reason(exc: BaseException) -> str:
    """The cause in a sentence's length: the server's answer or the system's reason."""
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        answers = [f"{code} {_text(text)}" for code, text in exc.recipients.values()]
        return "; ".join(answers)
    if isinstance(exc, smtplib.SMTPResponseException):
        return f"{exc.smtp_code} {_text(exc.smtp_error)}"
    if isinstance(exc, socket.gaierror):
        return "the host name was not found"
    if isinstance(exc, TimeoutError):
        return "it did not answer in time"
    if isinstance(exc, ConnectionRefusedError):
        return "the connection was refused"
    if isinstance(exc, ssl.SSLCertVerificationError):
        return f"the certificate was not accepted ({exc.verify_message})"
    if isinstance(exc, ssl.SSLError):
        return (exc.reason or str(exc)).lower().replace("_", " ")
    return (_text(exc.args[0]) if exc.args else type(exc).__name__)[:300]


def _text(value: object) -> str:
    text = value.decode(errors="replace") if isinstance(value, bytes) else str(value)
    return " ".join(text.split())[:300]
