"""A stand-in for Microsoft's token endpoint and Graph ``sendMail`` for the mail journeys (0.13 MS).

On ``127.0.0.1``, in a thread. ``POST /<tenant>/oauth2/v2.0/token`` checks the client credentials
(``secret``, or a signed assertion against ``certificate`` and answers like Entra: ``200`` with a
token, or ``400``/``401`` with an ``AADSTS`` code); ``POST /v1.0/users/<mailbox>/sendMail`` checks the
bearer token, decodes the base64 MIME into ``messages`` and answers ``202``. It is also the Azure
host's token endpoint of a managed identity: ``GET /identity`` (App Service and Container Apps, which
checks ``X-IDENTITY-HEADER`` against ``identity_header``) and ``GET /metadata/identity/oauth2/token``
(a virtual machine's metadata service, which checks ``Metadata: true``); both answer a token for the
``resource`` asked, ``identity-token-N`` for the federated audience and ``token-host-N`` for any other,
and record the query in ``host_requests``. With ``federated`` set the token endpoint accepts the
``client_assertion`` of an identity token instead of a secret. A test scripts the rest:
``token_refusal`` (status, AADSTS code) refuses every token request, ``send_answer`` (status, headers)
answers every send with that instead of accepting, ``expires_in`` is the token lifetime. Every request
is recorded in ``requests`` as (method, path, headers, form or body).
"""

import base64
import json
import threading
import time
from email import message_from_bytes, policy
from email.message import EmailMessage
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Self
from urllib.parse import parse_qs, urlsplit

import jwt
from cryptography import x509

ASSERTION = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


class FakeGraph:
    def __init__(
        self,
        *,
        secret: str | None = None,
        certificate: bytes | None = None,
        federated: bool = False,
        identity_header: str = "identity-header-1",
    ) -> None:
        self.secret = secret
        self.certificate = certificate
        self.federated = federated
        self.identity_header = identity_header
        self.host_requests: list[tuple[str, dict[str, str], dict[str, str]]] = []
        self.host_tokens = 0
        self.token_refusal: tuple[int, int] | None = None
        self.send_answer: tuple[int, dict[str, str]] | None = None
        self.expires_in = 3600
        self.messages: list[EmailMessage] = []
        self.mailboxes: list[str] = []
        self.requests: list[tuple[str, str, dict[str, str], object]] = []
        self.assertions: list[dict] = []
        self.tokens_issued = 0
        self._lock = threading.Lock()
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:  # silence
                pass

            def _answer(self, status: int, body: object = None, headers: dict | None = None):
                raw = b"" if body is None else json.dumps(body).encode()
                self.send_response(status)
                for name, value in (headers or {}).items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(raw)))
                if raw:
                    self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:
                url = urlsplit(self.path)
                query = {k: v[0] for k, v in parse_qs(url.query).items()}
                headers = {name.lower(): value for name, value in self.headers.items()}
                if url.path == "/identity":
                    allowed = headers.get("x-identity-header") == fake.identity_header
                elif url.path == "/metadata/identity/oauth2/token":
                    allowed = headers.get("metadata") == "true"
                else:
                    return self._answer(404, {"error": {"code": "NotFound"}})
                with fake._lock:
                    fake.host_requests.append((url.path, query, headers))
                    fake.host_tokens += 1
                    number = fake.host_tokens
                if not allowed or not query.get("resource"):
                    return self._answer(400, {"error": "invalid_request"})
                audience = query["resource"].startswith("api://AzureADTokenExchange")
                prefix = "identity-token" if audience else "token-host"
                self._answer(
                    200,
                    {
                        "access_token": f"{prefix}-{number}",
                        "expires_on": str(int(time.time()) + 3600),
                        "resource": query["resource"],
                        "token_type": "Bearer",
                    },
                )

            def do_POST(self) -> None:
                size = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(size)
                headers = {name.lower(): value for name, value in self.headers.items()}
                if self.path.endswith("/oauth2/v2.0/token"):
                    form = {k: v[0] for k, v in parse_qs(raw.decode()).items()}
                    with fake._lock:
                        fake.requests.append(("POST", self.path, headers, form))
                    status, body = fake._token(self.path, form)
                    return self._answer(status, body)
                if self.path.startswith("/v1.0/users/") and self.path.endswith("/sendMail"):
                    with fake._lock:
                        fake.requests.append(("POST", self.path, headers, raw))
                    status, body, extra = fake._send(self.path, headers, raw)
                    return self._answer(status, body, extra)
                self._answer(404, {"error": {"code": "NotFound"}})

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def _token(self, path: str, form: dict[str, str]) -> tuple[int, dict]:
        if self.token_refusal is not None:
            status, code = self.token_refusal
            return status, {
                "error": "invalid_client",
                "error_description": f"AADSTS{code}: refused. Trace ID: secret-trace",
                "error_codes": [code],
            }
        if self.secret is not None and form.get("client_secret") == self.secret:
            return self._issue()
        if (
            self.federated
            and form.get("client_assertion_type") == ASSERTION
            and form.get("client_assertion", "").startswith("identity-token-")
        ):
            return self._issue()
        if self.certificate is not None and form.get("client_assertion_type") == ASSERTION:
            assertion = form["client_assertion"]
            try:
                public = x509.load_pem_x509_certificate(self.certificate).public_key()
                header = jwt.get_unverified_header(assertion)
                claims = jwt.decode(
                    assertion,
                    public,  # type: ignore[arg-type]
                    algorithms=["RS256"],
                    audience=f"{self.url}{path}",
                    options={"verify_iss": False},
                )
            except jwt.PyJWTError:
                return 401, {"error": "invalid_client", "error_codes": [700027]}
            self.assertions.append({"header": header, "claims": claims})
            return self._issue()
        return 401, {"error": "invalid_client", "error_codes": [7000215]}

    def _issue(self) -> tuple[int, dict]:
        with self._lock:
            self.tokens_issued += 1
            number = self.tokens_issued
        return 200, {
            "token_type": "Bearer",
            "expires_in": self.expires_in,
            "access_token": f"token-{number}",
        }

    def _send(self, path: str, headers: dict, raw: bytes) -> tuple[int, object, dict]:
        if not headers.get("authorization", "").startswith("Bearer token-"):
            return 401, {"error": {"code": "InvalidAuthenticationToken"}}, {}
        if self.send_answer is not None:
            status, extra = self.send_answer
            return status, {"error": {"code": "Scripted", "message": "raw Graph text"}}, extra
        mailbox = path.split("/")[3]
        try:
            message = message_from_bytes(
                base64.b64decode(raw, validate=True), policy=policy.default
            )
        except ValueError:
            return 400, {"error": {"code": "ErrorMimeContentInvalidBase64String"}}, {}
        with self._lock:
            self.messages.append(message)  # type: ignore[arg-type]
            self.mailboxes.append(mailbox)
        return 202, None, {}

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self._server.shutdown()
        self._server.server_close()
