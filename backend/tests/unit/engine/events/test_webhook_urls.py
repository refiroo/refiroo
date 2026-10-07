"""Which URLs a webhook subscription may name (Base 0.9 C11, C-D101 revised)."""

import pytest

from app.engine.events.webhook_urls import check_webhook_url


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("https://hooks.example.test/rdm?x=1", None),
        ("https://hooks.example.test:8443/rdm", None),
        ("https://anywhere.else.test/rdm", None),
        ("http://localhost:9000/hook", None),
        ("http://127.0.0.1/hook", None),
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
    refusal = check_webhook_url(url)
    assert (refusal.code if refusal else None) == code
    if refusal is not None:
        assert refusal.details["pointer"] == "/url"
