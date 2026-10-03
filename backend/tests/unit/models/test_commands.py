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


def test_a_relationship_item_survives_the_background_job_s_stored_form():
    """A background job stores each item as JSON and parses it back at its chunk (D27). A
    relationship item's ``from`` end, a Python keyword held under another field name, keeps its
    JSON name both ways; a set replacement's targets keep omitted values omitted."""
    from pydantic import TypeAdapter

    from app.models.commands import BatchItem

    ends = {"from": {"id": str(uuid4())}, "to": {"id": str(uuid4())}}
    items = [
        {"op": "createRelation", "relationTypeKey": "t", **ends, "attributes": {"a": 1}},
        {"op": "ensureRelation", "relationTypeKey": "t", **ends},
        {
            "op": "replaceRelationSet",
            "relationTypeKey": "t",
            "fromObjectTypeKey": "a",
            "toObjectTypeKey": "b",
            "direction": "incoming",
            "anchor": {"id": str(uuid4())},
            "targets": [{"object": {"id": str(uuid4())}}],
        },
    ]
    request = BatchRequest.model_validate({**VALID, "items": items})
    adapter = TypeAdapter(BatchItem)
    for item, given in zip(request.items, items, strict=True):
        stored = item.model_dump(mode="json", exclude_unset=True)
        assert stored == given
        assert adapter.validate_python(stored) == item
    python_name = {key: value for key, value in items[0].items() if key != "from"}
    with pytest.raises(ValidationError):
        BatchRequest.model_validate({**VALID, "items": [{**python_name, "from_": ends["from"]}]})
