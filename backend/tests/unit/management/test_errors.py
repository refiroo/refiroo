"""The last line of error handling (``management/errors.py``, ``UnexpectedErrors``): an exception
no handler answered is answered 500 with a reference and never escapes to the server, which would
log it as an unhandled "Exception in ASGI application" (found on a real instance, 2026-10-28)."""

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from app.management.errors import UnexpectedErrors


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(UnexpectedErrors)

    @app.get("/fails")
    def fails() -> None:
        raise RuntimeError("boom")

    @app.get("/stream-fails")
    def stream_fails() -> StreamingResponse:
        def body():
            yield "first"
            raise RuntimeError("late")

        return StreamingResponse(body())

    return app


def test_an_unexpected_error_is_answered_500_with_a_reference_and_does_not_escape():
    answer = TestClient(_app(), raise_server_exceptions=True).get("/fails")
    error = answer.json()["error"]
    assert answer.status_code == 500 and error["code"] == "INTERNAL_ERROR"
    assert error["details"]["correlationId"] in error["message"] and "boom" not in answer.text


def test_a_stream_failing_after_it_began_is_logged_and_does_not_escape(caplog):
    answer = TestClient(_app(), raise_server_exceptions=True).get("/stream-fails")
    assert answer.status_code == 200
    assert any("failed after it began" in r.getMessage() for r in caplog.records)
