"""Which URLs a webhook subscription may name (Base 0.9 C11, C-D101 revised)."""

import pytest

from app.config import reload_settings
from app.engine.events.webhook_urls import address_refusal, check_webhook_url


@pytest.fixture
def private_allowed(monkeypatch):
    monkeypatch.setenv("WEBHOOK_PRIVATE_ADDRESSES_ALLOWED", "true")
    reload_settings()
    yield
    monkeypatch.delenv("WEBHOOK_PRIVATE_ADDRESSES_ALLOWED")
    reload_settings()


def _no_resolution(*_args, **_kwargs):
    raise OSError("not resolvable")


def _resolving(*addresses):
    return lambda host, port, **_kwargs: [(2, 1, 6, "", (a, port)) for a in addresses]


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("https://hooks.example.test/rdm?x=1", None),
        ("https://hooks.example.test:8443/rdm", None),
        ("https://anywhere.else.test/rdm", None),
        ("http://hooks.example.test/rdm", "INVALID_WEBHOOK_URL"),
        ("http://10.0.0.5/rdm", "INVALID_WEBHOOK_URL"),
        ("https://user:pw@hooks.example.test/rdm", "INVALID_WEBHOOK_URL"),
        ("https://hooks.example.test/rdm#part", "INVALID_WEBHOOK_URL"),
        ("ftp://hooks.example.test/rdm", "INVALID_WEBHOOK_URL"),
        ("/relative/path", "INVALID_WEBHOOK_URL"),
        ("https://hooks.example.test:port/rdm", "INVALID_WEBHOOK_URL"),
        ("https://hooks.example.test/" + "a" * 2048, "INVALID_WEBHOOK_URL"),
    ],
)
def test_a_url_is_absolute_https_on_any_host_or_http_to_a_loopback_host(url, code):
    refusal = check_webhook_url(url, resolve=_no_resolution)
    assert (refusal.code if refusal else None) == code
    if refusal is not None:
        assert refusal.details["pointer"] == "/url"


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1",
        "10.0.0.5",
        "172.16.4.1",
        "192.168.1.1",
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "240.0.0.1",
        "::1",
        "::",
        "fd00::1",
        "ff02::1",
        "::ffff:10.0.0.5",
        "::ffff:127.0.0.1",
    ],
)
def test_a_non_public_address_is_refused_unless_the_setting_allows_it(address):
    assert address_refusal(address, private_allowed=False) is not None
    assert address_refusal(address, private_allowed=True) is None


@pytest.mark.parametrize(
    "address",
    ["169.254.169.254", "169.254.1.1", "fe80::1", "fe80::1%en0", "::ffff:169.254.169.254"],
)
def test_link_local_is_refused_whatever_the_setting_says(address):
    assert address_refusal(address, private_allowed=False) is not None
    assert address_refusal(address, private_allowed=True) is not None


@pytest.mark.parametrize("address", ["8.8.8.8", "1.1.1.1", "2606:4700::1111", "::ffff:8.8.8.8"])
def test_a_public_address_is_accepted(address):
    assert address_refusal(address, private_allowed=False) is None


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:9000/hook",
        "http://127.0.0.1/hook",
        "https://10.0.0.5/hook",
        "https://[fd00::1]/hook",
        "https://100.64.0.9/hook",
        "https://169.254.169.254/latest",
    ],
)
def test_a_literal_non_public_address_is_refused_by_default(url):
    refusal = check_webhook_url(url, resolve=_resolving("127.0.0.1"))
    assert refusal.code == "INVALID_WEBHOOK_URL" and refusal.details["pointer"] == "/url"
    assert (
        "private addresses are refused on this instance" in refusal.message
        or "link-local" in refusal.message
    )


def test_a_name_resolving_to_any_non_public_address_is_refused():
    refusal = check_webhook_url(
        "https://hooks.corp.test/hook", resolve=_resolving("8.8.8.8", "10.1.1.1")
    )
    assert refusal.code == "INVALID_WEBHOOK_URL" and "resolves to an address" in refusal.message
    assert check_webhook_url("https://hooks.corp.test/hook", resolve=_resolving("8.8.8.8")) is None


def test_private_addresses_are_accepted_with_the_setting_on_but_link_local_is_not(private_allowed):
    assert check_webhook_url("http://localhost:9000/hook", resolve=_resolving("127.0.0.1")) is None
    assert check_webhook_url("https://hooks.corp.test/hook", resolve=_resolving("10.1.1.1")) is None
    assert check_webhook_url("https://169.254.169.254/x", resolve=_no_resolution) is not None
    assert (
        check_webhook_url("https://hooks.corp.test/x", resolve=_resolving("169.254.1.1"))
        is not None
    )


@pytest.mark.parametrize(
    "address",
    ["64:ff9b::a00:5", "64:ff9b::7f00:1", "64:ff9b::c0a8:101", "64:ff9b:1::1", "64:ff9b:1:abcd::1"],
)
def test_a_nat64_address_of_a_non_public_address_is_refused_unless_the_setting_allows_it(address):
    """NAT64 reaches the IPv4 address in its last 32 bits; the local-use range never is public."""
    assert address_refusal(address, private_allowed=False) is not None
    assert address_refusal(address, private_allowed=True) is None


def test_a_nat64_address_of_a_public_or_link_local_address_follows_the_ipv4_rule():
    assert address_refusal("64:ff9b::808:808", private_allowed=False) is None
    assert address_refusal("64:ff9b::a9fe:a9fe", private_allowed=True) is not None


def test_the_refusal_for_an_author_does_not_name_the_address_a_host_resolves_to():
    refusal = check_webhook_url(
        "https://internal.example.test/rdm", resolve=_resolving("172.18.0.3")
    )
    assert refusal is not None and refusal.code == "INVALID_WEBHOOK_URL"
    assert "172.18.0.3" not in refusal.message and "internal.example.test" in refusal.message
