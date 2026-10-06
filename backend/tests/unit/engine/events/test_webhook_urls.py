"""Which URLs a webhook subscription may name (Base 0.9 C11, C-D101)."""

import pytest

from app.engine.events.webhook_urls import check_webhook_url, host_allowed

ALLOWED = ("hooks.example.test", "*.partner.test", "localhost", "10.0.0.5")


@pytest.mark.parametrize(
    ("host", "allowed"),
    [
        ("hooks.example.test", True),
        ("HOOKS.Example.Test", True),
        ("other.example.test", False),
        ("a.partner.test", True),
        ("deep.a.partner.test", True),
        ("partner.test", False),
        ("evilpartner.test", False),
        ("10.0.0.5", True),
        ("10.0.0.6", False),
        ("localhost", True),
    ],
)
def test_a_host_is_allowed_exactly_or_below_a_wildcard_domain(host, allowed):
    assert host_allowed(host, ALLOWED) is allowed


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("https://hooks.example.test/rdm?x=1", None),
        ("https://hooks.example.test:8443/rdm", None),
        ("https://a.partner.test/rdm", None),
        ("http://localhost:9000/hook", None),
        ("http://hooks.example.test/rdm", "INVALID_WEBHOOK_URL"),
        ("http://10.0.0.5/rdm", "INVALID_WEBHOOK_URL"),
        ("https://user:pw@hooks.example.test/rdm", "INVALID_WEBHOOK_URL"),
        ("https://hooks.example.test/rdm#part", "INVALID_WEBHOOK_URL"),
        ("ftp://hooks.example.test/rdm", "INVALID_WEBHOOK_URL"),
        ("/relative/path", "INVALID_WEBHOOK_URL"),
        ("https://hooks.example.test:port/rdm", "INVALID_WEBHOOK_URL"),
        ("https://hooks.example.test/" + "a" * 2048, "INVALID_WEBHOOK_URL"),
        ("https://elsewhere.test/rdm", "WEBHOOK_HOST_NOT_ALLOWED"),
        ("http://127.0.0.1/hook", "WEBHOOK_HOST_NOT_ALLOWED"),
    ],
)
def test_a_url_is_absolute_https_on_an_allowed_host_or_http_to_a_listed_loopback(url, code):
    refusal = check_webhook_url(url, ALLOWED)
    assert (refusal.code if refusal else None) == code
    if refusal is not None:
        assert refusal.details["pointer"] == "/url"


def test_an_empty_allowlist_allows_nothing_and_names_the_setting():
    refusal = check_webhook_url("https://hooks.example.test/rdm", ())
    assert refusal.code == "WEBHOOK_HOST_NOT_ALLOWED"
    assert refusal.details["setting"] == "CONSUMER_WEBHOOK_ALLOWED_HOSTS"
    assert refusal.details["allowedHosts"] == []
