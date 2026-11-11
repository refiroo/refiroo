"""A minimal SMTP server for the mail journeys (Product 0.12 M1): on ``127.0.0.1``, in a thread.

It speaks enough SMTP for ``smtplib``: EHLO, STARTTLS, AUTH PLAIN and LOGIN (when given a login),
MAIL, RCPT, DATA and QUIT. TLS uses a certificate made for the run (``certificate_file``): the
engine verifies it as it would any server's, so a test that wants it trusted sets ``SSL_CERT_FILE``
to that file. ``implicit_tls`` wraps the connection from its first byte. A test scripts the rest:
``login`` is the user name and password it accepts, ``refuse`` maps a recipient to the answer it
gives, ``reject_data`` is an answer to refuse every message with, ``down`` makes it answer ``421``
and hang up, and each accepted message is recorded in ``messages`` (parsed). ``stop`` closes the
port, so the next connection is refused.
"""

import base64
import datetime
import ipaddress
import socketserver
import ssl
import tempfile
import threading
from email import message_from_bytes, policy
from email.message import EmailMessage
from pathlib import Path
from typing import Self

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


def _certificate(directory: Path) -> tuple[Path, Path]:
    """A self-signed certificate for 127.0.0.1 and localhost, and its key."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "fake smtp")])
    now = datetime.datetime.now(datetime.UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(hours=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    certificate_file, key_file = directory / "certificate.pem", directory / "key.pem"
    certificate_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    return certificate_file, key_file


class FakeSmtp:
    def __init__(self, *, login: tuple[str, str] | None = None, implicit_tls: bool = False) -> None:
        self.login = login
        self.down = False
        self._directory = tempfile.TemporaryDirectory(prefix="fake-smtp-")
        self.certificate_file, key_file = _certificate(Path(self._directory.name))
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(self.certificate_file, key_file)
        self.refuse: dict[str, tuple[int, str]] = {}
        self.reject_data: tuple[int, str] | None = None
        self.messages: list[EmailMessage] = []
        self.connections = 0
        self._lock = threading.Lock()
        fake = self

        class Handler(socketserver.StreamRequestHandler):
            def handle(self) -> None:
                try:
                    self.session()
                except OSError:
                    pass  # the client hung up
                finally:
                    # After STARTTLS or implicit TLS the request is the wrapping socket, which the
                    # server does not know to close.
                    self.request.close()

            def wrap(self) -> None:
                self.request = tls.wrap_socket(self.request, server_side=True)
                self.rfile = self.request.makefile("rb")
                self.wfile = self.request.makefile("wb")

            def session(self) -> None:
                with fake._lock:
                    fake.connections += 1
                if fake.down:
                    self.send("421 service not available")
                    return
                secured = implicit_tls
                if implicit_tls:
                    try:
                        self.wrap()
                    except ssl.SSLError:
                        return
                self.send("220 fake.test ready")
                recipients: list[str] = []
                authenticated = fake.login is None
                while line := self.rfile.readline():
                    text = line.decode(errors="replace").strip()
                    verb = text.split(" ", 1)[0].upper()
                    if verb in ("EHLO", "HELO"):
                        extras = ["250-fake.test"]
                        if not secured:
                            extras.append("250-STARTTLS")
                        if fake.login is not None:
                            extras.append("250-AUTH PLAIN LOGIN")
                        self.send("\r\n".join([*extras, "250 8BITMIME"]))
                    elif verb == "STARTTLS":
                        self.send("220 go ahead")
                        try:
                            self.wrap()
                        except ssl.SSLError:
                            return
                        secured = True
                    elif verb == "AUTH":
                        authenticated = self.authenticate(text)
                    elif verb == "MAIL":
                        recipients = []
                        self.send("250 ok" if authenticated else "530 authentication required")
                    elif verb == "RCPT":
                        address = text.split("<", 1)[1].split(">", 1)[0]
                        if address in fake.refuse:
                            code, answer = fake.refuse[address]
                            self.send(f"{code} {answer}")
                        else:
                            recipients.append(address)
                            self.send("250 ok")
                    elif verb == "DATA":
                        if fake.reject_data is not None and recipients:
                            code, answer = fake.reject_data
                            self.send("354 go ahead")
                            self.read_data()
                            self.send(f"{code} {answer}")
                            continue
                        self.send("354 go ahead")
                        raw = self.read_data()
                        with fake._lock:
                            fake.messages.append(message_from_bytes(raw, policy=policy.default))
                        self.send("250 queued")
                    elif verb == "RSET":
                        self.send("250 ok")
                    elif verb == "QUIT":
                        self.send("221 bye")
                        return
                    else:
                        self.send("500 unknown command")

            def send(self, text: str) -> None:
                self.wfile.write(text.encode() + b"\r\n")
                self.wfile.flush()

            def read_data(self) -> bytes:
                lines = []
                while (line := self.rfile.readline()) not in (b".\r\n", b""):
                    lines.append(line[1:] if line.startswith(b"..") else line)
                return b"".join(lines)

            def authenticate(self, text: str) -> bool:
                parts = text.split(" ")
                if parts[1].upper() == "PLAIN":
                    if len(parts) > 2:
                        blob = parts[2]
                    else:
                        self.send("334 ")
                        blob = self.rfile.readline().decode().strip()
                    _, user, password = base64.b64decode(blob).decode().split("\0")
                else:
                    self.send("334 " + base64.b64encode(b"Username:").decode())
                    user = base64.b64decode(self.rfile.readline().strip()).decode()
                    self.send("334 " + base64.b64encode(b"Password:").decode())
                    password = base64.b64decode(self.rfile.readline().strip()).decode()
                if (user, password) == fake.login:
                    self.send("235 authenticated")
                    return True
                self.send("535 5.7.8 authentication failed")
                return False

        class Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        self.server = Server(("127.0.0.1", 0), Handler)
        self.port: int = self.server.server_address[1]
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self._directory.cleanup()

    def __enter__(self) -> Self:
        self._thread.start()
        return self

    def __exit__(self, *_exc) -> None:
        if self._thread.is_alive():
            self.stop()
