"""One message handed to Microsoft 365 through Microsoft Graph (Product 0.13 MS).

The engine is an application of the organisation's tenant: it takes a token with the client-credentials
grant (a client secret, a signed assertion of a certificate, or the assertion of a managed identity's
token) or, with a managed identity in the organisation's own tenant, straight from the Azure host's
token endpoint (0.13 MS-D5), and sends with ``POST
/users/<mailbox>/sendMail``, the message being the MIME ``smtp.build`` makes, base64-encoded. Plain
``httpx``; no Microsoft library (MS-D3). The MIME route has no ``saveToSentItems``: Microsoft saves
the message in the mailbox's Sent Items.

A failure is a ``MailError`` in the kinds the sender knows (``smtp.py``): a refused token, missing
consent or a mailbox the app may not use is ``login`` (every message would fail the same); Graph out
of reach, throttled or failing is ``connection``, with the wait Graph asked for; a mailbox that does
not exist is ``sender``; any other refusal is ``rejected``. Each carries a sentence an administrator
can act on, never the secret, the token or Graph's own text. A ``202`` means Graph accepted the
message; a bad address comes back later as a bounce to the mailbox, which the engine does not read
(MS-D2).
"""

import base64
import hashlib
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlsplit

import httpx
import jwt
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ...models.commands import DEFAULT_AUTHORITY_URL, DEFAULT_GRAPH_URL
from .smtp import CONNECTION, LOGIN, REJECTED, SENDER, MailError

__all__ = ["DEFAULT_AUTHORITY_URL", "DEFAULT_GRAPH_URL", "GraphConnection", "deliver"]

TIMEOUT_SECONDS = 15.0
# A token is renewed this long before it expires.
RENEW_BEFORE_SECONDS = 120.0
LONGEST_RETRY_AFTER = 24 * 3600.0
ASSERTION = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
# The Azure host's token endpoint of a virtual machine (instance metadata); App Service and Container
# Apps give theirs in IDENTITY_ENDPOINT with IDENTITY_HEADER. A constant tests point at a stand-in.
IMDS_URL = "http://169.254.169.254/metadata/identity/oauth2/token"
# The host is on the same machine or network: it answers at once or not at all.
HOST_CONNECT_TIMEOUT = 2.0
NO_IDENTITY_HOST = (
    "refiroo is not running with a managed identity on an Azure host: the host's identity endpoint "
    "(IDENTITY_ENDPOINT, or the instance metadata service) did not answer. Use a client secret or "
    "a certificate instead, or run refiroo on Azure (App Service, Container Apps or a virtual "
    "machine) with a managed identity"
)


@dataclass(frozen=True)
class GraphConnection:
    tenant_id: str | None
    client_id: str | None
    authority_url: str
    graph_url: str
    from_address: str
    client_secret: str | None = field(default=None, repr=False)
    certificate_pem: str | None = field(default=None, repr=False)
    # Managed identity: ``direct`` or ``federated``; the user-assigned identity's client ID.
    identity_mode: str | None = None
    identity_client_id: str | None = None

    def describe(self) -> str:
        return urlsplit(self.graph_url).netloc or "Microsoft Graph"

    def credential_fingerprint(self) -> str:
        credential = (
            self.client_secret
            or self.certificate_pem
            or f"identity:{self.identity_mode}:{self.identity_client_id or ''}"
        )
        return hashlib.sha256(credential.encode()).hexdigest()


# --- the certificate ----------------------------------------------------------------------------


@dataclass(frozen=True)
class CertificateInfo:
    pem: bytes
    thumbprint: str
    expires_at: datetime


def read_certificate(text: str) -> CertificateInfo:
    """The private key and certificate in ``text`` (PEM), as one normalised PEM and the certificate's
    SHA-1 thumbprint (as the Entra portal shows it) and expiry; ``ValueError`` says what is wrong."""
    data = text.encode()
    blocks = re.findall(rb"-----BEGIN ([A-Z ]+)-----.*?-----END \1-----", data, flags=re.DOTALL)
    if b"ENCRYPTED PRIVATE KEY" in blocks:
        raise ValueError("the private key must not be encrypted with a password")
    try:
        key = serialization.load_pem_private_key(data, password=None)
    except (ValueError, TypeError) as exc:
        raise ValueError("holds no private key in PEM form") from exc
    if not isinstance(key, rsa.RSAPrivateKey):
        raise ValueError("the private key must be an RSA key")  # noqa: TRY004
    try:
        certificates = x509.load_pem_x509_certificates(data)
    except ValueError as exc:
        raise ValueError("holds no certificate in PEM form") from exc
    public = key.public_key().public_numbers()
    for certificate in certificates:
        candidate = certificate.public_key()
        if isinstance(candidate, rsa.RSAPublicKey) and candidate.public_numbers() == public:
            break
    else:
        raise ValueError("holds no certificate that belongs to the private key")
    expires = certificate.not_valid_after_utc
    if expires <= datetime.now(UTC):
        raise ValueError("the certificate has expired")
    pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ) + certificate.public_bytes(serialization.Encoding.PEM)
    return CertificateInfo(pem, certificate.fingerprint(hashes.SHA1()).hex().upper(), expires)


def _assertion(connection: GraphConnection, endpoint: str) -> str:
    """The signed JWT that proves the certificate's key to the token endpoint."""
    pem = (connection.certificate_pem or "").encode()
    certificate = x509.load_pem_x509_certificates(pem)[0]
    now = int(time.time())
    return jwt.encode(
        {
            "aud": endpoint,
            "iss": connection.client_id,
            "sub": connection.client_id,
            "jti": str(uuid.uuid4()),
            "nbf": now,
            "exp": now + 600,
        },
        serialization.load_pem_private_key(pem, password=None),  # type: ignore[arg-type]
        algorithm="RS256",
        headers={
            "x5t": _b64url(certificate.fingerprint(hashes.SHA1())),
            "x5t#S256": _b64url(certificate.fingerprint(hashes.SHA256())),
        },
    )


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


# --- the token ----------------------------------------------------------------------------------

_tokens: dict[tuple[str, ...], tuple[str, float]] = {}
_tokens_lock = threading.Lock()


def _cache_key(connection: GraphConnection) -> tuple[str, ...]:
    return (
        connection.authority_url,
        connection.graph_url,
        connection.tenant_id or "",
        connection.client_id or "",
        connection.credential_fingerprint(),
    )


def forget_tokens() -> None:
    """Drop every cached token (tests; a token refused with 401)."""
    with _tokens_lock:
        _tokens.clear()


def _token(connection: GraphConnection, client: httpx.Client) -> str:
    key = _cache_key(connection)
    cached = _cached(key)
    if cached is not None:
        return cached
    if connection.identity_mode == "direct":
        # The Azure host gives the Graph token itself: no tenant token request.
        token, lifetime = _host_token(client, connection.graph_url, connection.identity_client_id)
        _remember(key, token, lifetime)
        return token
    endpoint = (
        f"{connection.authority_url}/{quote(connection.tenant_id or '', safe='')}/oauth2/v2.0/token"
    )
    form = {
        "grant_type": "client_credentials",
        "client_id": connection.client_id or "",
        "scope": f"{connection.graph_url}/.default",
    }
    if connection.client_secret is not None:
        form["client_secret"] = connection.client_secret
    elif connection.identity_mode == "federated":
        form["client_assertion_type"] = ASSERTION
        form["client_assertion"] = _identity_token(connection, client)
    else:
        form["client_assertion_type"] = ASSERTION
        form["client_assertion"] = _assertion(connection, endpoint)
    where = urlsplit(connection.authority_url).netloc
    response = _post(client, endpoint, where, data=form)
    if response.status_code != 200:
        raise _token_failure(response, where)
    try:
        body = response.json()
        token, lifetime = str(body["access_token"]), float(body.get("expires_in", 3600))
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise MailError(
            CONNECTION, f"{where} answered with a token response that cannot be read"
        ) from exc
    _remember(key, token, lifetime)
    return token


def _cached(key: tuple[str, ...]) -> str | None:
    with _tokens_lock:
        cached = _tokens.get(key)
    if cached is not None and cached[1] - RENEW_BEFORE_SECONDS > time.monotonic():
        return cached[0]
    return None


def _remember(key: tuple[str, ...], token: str, lifetime: float) -> None:
    with _tokens_lock:
        _tokens[key] = (token, time.monotonic() + lifetime)


def exchange_audience(authority_url: str) -> str:
    """The audience of a managed identity's token that an app registration trusts, by cloud."""
    host = (urlsplit(authority_url).hostname or "").lower()
    if host.endswith("microsoftonline.us"):
        return "api://AzureADTokenExchangeUSGov"
    if host.endswith("microsoftonline.cn"):
        return "api://AzureADTokenExchangeChina"
    return "api://AzureADTokenExchange"


def _identity_token(connection: GraphConnection, client: httpx.Client) -> str:
    """A federated managed identity's token, which stands in for the certificate's signed
    assertion in the client-credentials grant."""
    audience = exchange_audience(connection.authority_url)
    key = ("identity", audience, connection.identity_client_id or "")
    cached = _cached(key)
    if cached is not None:
        return cached
    token, lifetime = _host_token(client, audience, connection.identity_client_id)
    _remember(key, token, lifetime)
    return token


def _host_token(
    client: httpx.Client, resource: str, identity_client_id: str | None
) -> tuple[str, float]:
    """A token for ``resource`` from the Azure host's token endpoint (App Service, Container Apps:
    ``IDENTITY_ENDPOINT`` with ``IDENTITY_HEADER``; else a virtual machine's metadata service)."""
    endpoint, header = os.environ.get("IDENTITY_ENDPOINT"), os.environ.get("IDENTITY_HEADER")
    params = {"resource": resource}
    if endpoint and header:
        url, headers = endpoint, {"X-IDENTITY-HEADER": header}
        params["api-version"] = "2019-08-01"
    else:
        url, headers = IMDS_URL, {"Metadata": "true"}
        params["api-version"] = "2018-02-01"
    if identity_client_id:
        params["client_id"] = identity_client_id
    try:
        response = client.get(
            url,
            params=params,
            headers=headers,
            timeout=httpx.Timeout(TIMEOUT_SECONDS, connect=HOST_CONNECT_TIMEOUT),
        )
    except httpx.HTTPError as exc:
        raise MailError(LOGIN, NO_IDENTITY_HOST) from exc
    if response.status_code == 429 or response.status_code >= 500:
        return _raise(_busy(response, "The Azure host's identity endpoint"))
    who = (
        f"the managed identity {identity_client_id}"
        if identity_client_id
        else "the host's system-assigned managed identity"
    )
    if response.status_code != 200:
        raise MailError(
            LOGIN,
            f"The Azure host did not issue a token for {who}: check the identity's client ID and "
            f"that the identity is assigned to this host (HTTP {response.status_code})",
        )
    try:
        body = response.json()
        token = str(body["access_token"])
        lifetime = _lifetime(body)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise MailError(
            LOGIN, f"The Azure host's answer for {who} holds no token that can be read"
        ) from exc
    return token, lifetime


def _raise(error: MailError) -> tuple[str, float]:
    raise error


def _lifetime(body: dict) -> float:
    """Seconds a host token lives: ``expires_in``, else ``expires_on`` (epoch seconds), else 5 minutes."""
    for name, relative in (("expires_in", True), ("expires_on", False)):
        try:
            value = float(body[name])
        except KeyError, TypeError, ValueError:
            continue
        return value if relative else value - time.time()
    return 300.0


# What an administrator can do about the codes Microsoft Entra answers a token request with.
_AADSTS = {
    "7000215": "the client secret is wrong: use the secret's Value (not its ID) from the app registration",
    "7000222": "the client secret has expired: create a new one on the app registration",
    "700016": "the application (client) ID is not known in this tenant",
    "90002": "the tenant ID is not known to Microsoft",
    "900023": "the tenant ID is not a valid tenant ID or domain name",
    "700027": "the certificate is not registered on the app registration, or its signature is wrong",
    "700024": "the certificate's signed assertion is not valid now: check the engine's clock",
    "7000112": "the application is disabled in this tenant",
    "7000114": "the application is not allowed to use this tenant",
    "50034": "the user or application is not found in the tenant",
    "70025": "the app registration has no federated credential for a managed identity",
    "700213": "no federated credential on the app registration matches the managed identity "
    "(its issuer, subject and audience), or the app is not consented in this tenant",
}


def _token_failure(response: httpx.Response, where: str) -> MailError:
    if response.status_code == 429 or response.status_code >= 500:
        return _busy(response, where)
    code = _aadsts(response)
    meaning = _AADSTS.get(code or "")
    if meaning is not None:
        detail = f"{meaning} (AADSTS{code})"
    elif code is not None:
        detail = f"check the tenant ID, the application ID and the credential (AADSTS{code})"
    else:
        detail = f"check the tenant ID, the application ID and the credential (HTTP {response.status_code})"
    return MailError(LOGIN, f"Microsoft did not issue a token: {detail}")


def _aadsts(response: httpx.Response) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    codes = body.get("error_codes")
    if isinstance(codes, list) and codes and isinstance(codes[0], int):
        return str(codes[0])
    found = re.search(r"AADSTS(\d{1,8})", str(body.get("error_description", "")))
    return found.group(1) if found else None


# --- sending ------------------------------------------------------------------------------------


def deliver(
    connection: GraphConnection, message: EmailMessage, *, timeout: float = TIMEOUT_SECONDS
) -> None:
    """Send ``message`` as the mailbox of ``connection``; raises ``MailError``."""
    where = connection.describe()
    mailbox = connection.from_address
    url = f"{connection.graph_url}/v1.0/users/{quote(mailbox, safe='@')}/sendMail"
    body = base64.b64encode(message.as_bytes())
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        for attempt in (1, 2):
            token = _token(connection, client)
            response = _post(
                client,
                url,
                where,
                content=body,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "text/plain"},
            )
            if response.status_code == 401 and attempt == 1:
                # The token was not accepted (revoked or stale): ask for a new one once.
                with _tokens_lock:
                    _tokens.pop(_cache_key(connection), None)
                continue
            break
    if response.status_code == 202:
        return
    if response.status_code == 401:
        with _tokens_lock:
            _tokens.pop(_cache_key(connection), None)
    raise _send_failure(response, where, mailbox)


def _post(client: httpx.Client, url: str, where: str, **kwargs) -> httpx.Response:
    try:
        return client.post(url, **kwargs)
    except httpx.TimeoutException as exc:
        raise MailError(CONNECTION, f"{where} did not answer in time") from exc
    except httpx.HTTPError as exc:
        raise MailError(CONNECTION, f"Could not reach {where}: {_reason(exc)}") from exc


def _reason(exc: Exception) -> str:
    cause = exc.__cause__ or exc.__context__
    if isinstance(cause, OSError) and cause.strerror:
        return cause.strerror.lower()[:100]
    return "the connection failed"


def _send_failure(response: httpx.Response, where: str, mailbox: str) -> MailError:
    status = response.status_code
    suffix = _detail(response)
    if status == 429 or status >= 500 or status == 408:
        return _busy(response, where)
    if status == 401:
        return MailError(
            LOGIN,
            f"{where} did not accept the app's token: check that the app has the Mail.Send "
            f"application permission with admin consent{suffix}",
        )
    if status == 403:
        return MailError(
            LOGIN,
            f"{where} refused to send as {mailbox}: the app needs the Mail.Send application "
            "permission with admin consent, and its application access policy must allow this "
            f"mailbox{suffix}",
        )
    if status == 404:
        return MailError(
            SENDER,
            f"Microsoft 365 has no mailbox {mailbox} that can send: the from address must be a "
            f"licensed user or a shared mailbox of this tenant{suffix}",
        )
    return MailError(
        REJECTED, f"{where} did not accept the message{suffix}", permanent=status != 409
    )


def _busy(response: httpx.Response, where: str) -> MailError:
    suffix = _detail(response)
    wait = _retry_after(response)
    what = (
        "is busy and asked the engine to wait"
        if response.status_code == 429
        else "is not available"
    )
    return MailError(CONNECTION, f"{where} {what}{suffix}", retry_after=wait)


def _detail(response: httpx.Response) -> str:
    """`` (HTTP 403, ErrorAccessDenied)``: the status and Graph's short error name."""
    code = _graph_code(response)
    return f" (HTTP {response.status_code}, {code})" if code else f" (HTTP {response.status_code})"


def _graph_code(response: httpx.Response) -> str | None:
    """Graph's short error name (``ErrorAccessDenied``), the one part of its answer worth showing."""
    try:
        error = response.json().get("error")
        code = error.get("code") if isinstance(error, dict) else error
    except ValueError, AttributeError:
        return None
    return code if isinstance(code, str) and re.fullmatch(r"[A-Za-z0-9_.]{1,80}", code) else None


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        except TypeError, ValueError:
            return None
    return min(max(seconds, 0.0), LONGEST_RETRY_AFTER)
