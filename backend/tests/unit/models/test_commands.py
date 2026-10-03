"""``models/commands.py``: the write inputs the engine accepts.

A batch request names its policy and run, holds at least one item of a known operation, and an
item's ``ref`` is 1–200 characters; anything else is refused before the engine reads it (the API
answers ``422 request_validation_error``).
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.models.commands import BatchRequest

DELETE = {"op": "delete", "target": {"id": str(uuid4())}, "expectedVersion": 1}
VALID = {"workspaceKey": "default", "policy": "atomic", "run": "inline", "items": [DELETE]}


@pytest.mark.parametrize(
    "change",
    [
        {"policy": None},
        {"run": None},
        {"items": []},
        {"items": [{"op": "rename"}]},
        {"items": [{**DELETE, "ref": ""}]},
        {"items": [{**DELETE, "ref": "r" * 201}]},
        {"expectedChangeSetVersion": 0},
        {"unknown": True},
    ],
    ids=[
        "no-policy",
        "no-run",
        "no-items",
        "unknown-op",
        "empty-ref",
        "long-ref",
        "version-0",
        "extra",
    ],
)
def test_a_malformed_batch_request_is_refused(change):
    body = {key: value for key, value in {**VALID, **change}.items() if value is not None}
    with pytest.raises(ValidationError):
        BatchRequest.model_validate(body)


def test_a_well_formed_batch_request_is_accepted():
    request = BatchRequest.model_validate({**VALID, "items": [{**DELETE, "ref": "r" * 200}]})
    assert (request.onExisting, request.items[0].ref) == ("reject", "r" * 200)
