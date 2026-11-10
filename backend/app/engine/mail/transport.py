"""The sending method in use: one message through SMTP or Microsoft Graph (Product 0.13 MS)."""

from email.message import EmailMessage

from . import graph, smtp

Transport = smtp.Connection | graph.GraphConnection


def deliver(connection: Transport, message: EmailMessage, *, timeout: float | None = None) -> None:
    """Send ``message`` through ``connection``; raises ``smtp.MailError``."""
    kwargs = {} if timeout is None else {"timeout": timeout}
    if isinstance(connection, graph.GraphConnection):
        graph.deliver(connection, message, **kwargs)
    else:
        smtp.deliver(connection, message, **kwargs)
