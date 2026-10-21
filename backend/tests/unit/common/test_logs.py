"""The JSON log line and the request ID (Product 0.11 O1, D195, D196)."""

import json
import logging
import re
import sys

import pytest

from app.common.logs import JsonFormatter, RequestContext, begin_request, request_id_from


def _record(message, *args, exc_info=None, **fields):
    record = logging.LogRecord("app.x", logging.ERROR, __file__, 1, message, args, exc_info)
    if fields:
        record.fields = fields
    return record


@pytest.fixture
def no_request():
    begin_request(None)
    yield
    begin_request(None)


def test_a_line_outside_a_request(no_request):
    entry = json.loads(JsonFormatter().format(_record("Zoë %s", "ünïcode")))
    assert entry["message"] == "Zoë ünïcode" and entry["level"] == "ERROR"
    assert entry["logger"] == "app.x" and isinstance(entry["process"], int)
    assert "requestId" not in entry and "exception" not in entry


def test_a_line_within_a_request_with_a_traceback(no_request):
    begin_request(RequestContext("abc", "GET", "/api/v1/x/1", "/api/v1/x/{id}"))
    try:
        raise ValueError("boom")
    except ValueError:
        line = JsonFormatter().format(_record("failed", exc_info=sys.exc_info(), status=500))
    assert "\n" not in line
    entry = json.loads(line)
    assert entry["requestId"] == "abc" and entry["route"] == "/api/v1/x/{id}"
    assert entry["method"] == "GET" and entry["status"] == 500
    assert "ValueError: boom" in entry["exception"]


@pytest.mark.parametrize(
    ("sent", "kept"),
    [
        ("proxy-1.a_B", True),
        ("x" * 64, True),
        ("x" * 65, False),
        ("", False),
        ("two words", False),
        ("line\nbreak", False),
        (None, False),
    ],
)
def test_the_request_id_is_kept_only_when_well_formed(sent, kept):
    made = request_id_from(sent)
    assert made == sent if kept else re.fullmatch(r"[0-9a-f]{32}", made)
