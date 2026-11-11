"""Which addresses a webhook request may go to (Base 0.9 C12, C-D107)."""

import socket

import pytest

from app.config import reload_settings
from app.engine.events.webhook_client import address_refusal, post


@pytest.fixture
def private_allowed(monkeypatch):
    """The instance setting that lets a webhook go to a private address, on."""
    monkeypatch.setenv("WEBHOOK_PRIVATE_ADDRESSES_ALLOWED", "true")
    reload_settings()
    yield
    monkeypatch.delenv("WEBHOOK_PRIVATE_ADDRESSES_ALLOWED")
    reload_settings()


@pytest.mark.parametrize(
    ("host", "address", "allowed"),
    [
        ("hooks.example.test", "203.0.113.7", True),
        ("hooks.example.test", "10.1.2.3", True),
        ("hooks.example.test", "192.168.0.10", True),
        ("hooks.example.test", "169.254.169.254", False),
        ("hooks.example.test", "fe80::1", False),
        ("hooks.example.test", "fe80::1%en0", False),
        ("hooks.example.test", "::ffff:169.254.169.254", False),
        ("hooks.example.test", "0.0.0.0", False),
        ("hooks.example.test", "127.0.0.1", False),
        ("hooks.example.test", "::1", False),
        ("localhost", "127.0.0.1", True),
        ("LOCALHOST", "::1", True),
        ("127.0.0.1", "127.0.0.1", True),
        ("localhost", "169.254.1.1", False),
    ],
)
def test_link_local_is_refused_and_loopback_only_for_a_loopback_host(host, address, allowed):
    assert (address_refusal(host, address) is None) is allowed


def _resolving(*addresses):
    def resolve(_host, port, **_kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port)) for address in addresses
        ]

    return resolve


def test_a_name_resolving_only_to_refused_addresses_is_not_connected_to():
    answer = post(
        "https://hooks.example.test/x", b"{}", {}, timeout=1, resolve=_resolving("169.254.169.254")
    )
    assert not answer.ok
    assert answer.error["kind"] == "address" and "169.254.169.254" in answer.error["message"]


def test_a_name_resolving_to_a_private_address_is_not_connected_to_by_default():
    answer = post(
        "https://hooks.example.test/x", b"{}", {}, timeout=1, resolve=_resolving("10.1.2.3")
    )
    assert answer.error["kind"] == "address"
    assert (
        "10.1.2.3" in answer.error["message"]
        and "refused on this instance" in answer.error["message"]
    )


def test_one_private_address_among_public_ones_refuses_the_delivery():
    answer = post(
        "https://hooks.example.test/x",
        b"{}",
        {},
        timeout=1,
        resolve=_resolving("8.8.8.8", "192.168.1.5"),
    )
    assert answer.error["kind"] == "address" and "192.168.1.5" in answer.error["message"]


def test_link_local_is_refused_even_with_the_setting_on(private_allowed):
    answer = post(
        "https://hooks.example.test/x",
        b"{}",
        {},
        timeout=1,
        resolve=_resolving("8.8.8.8", "169.254.169.254"),
    )
    assert answer.error["kind"] == "address" and "169.254.169.254" in answer.error["message"]


def test_a_name_that_does_not_resolve_is_a_connection_failure():
    def unresolvable(*_args, **_kwargs):
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    answer = post("https://nowhere.example.test/x", b"{}", {}, timeout=1, resolve=unresolvable)
    assert (
        answer.error["kind"] == "connection" and "could not be resolved" in answer.error["message"]
    )


def test_nothing_listening_is_a_connection_failure(private_allowed):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    answer = post(
        f"http://localhost:{port}/x", b"{}", {}, timeout=1, resolve=_resolving("127.0.0.1")
    )
    assert answer.error["kind"] == "connection" and len(answer.error["message"]) <= 200
