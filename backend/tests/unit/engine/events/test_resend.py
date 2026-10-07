"""What a resend by hand sends (Base 0.9 U5a revision, C-D129; C17): the event alone, in the format
of the request it was sent in, which the stored body tells."""

import json

import pytest

from app.engine.events import delivery
from app.engine.events.resend import resend_body
from app.errors import ApiError
from app.models.database import ConsumerWebhookRequest

EVENT = {"eventId": "e1", "position": 3, "event": "ledger-changed", "change": "updated", "objectType": "Ledger", "id": "o1"}
OTHER = {**EVENT, "eventId": "e2", "position": 4}


def _cloudevent(event: dict) -> dict:
    return {"specversion": "1.0", "id": event["eventId"], "type": "rdm.ledger-changed.updated", "data": event}


def _request(body) -> ConsumerWebhookRequest:
    text = None if body is None else json.dumps(body)
    return ConsumerWebhookRequest(delivery_id="old", batch_id="old", request_body=text)


def test_an_rdm_json_request_is_resent_as_its_envelope_with_the_event_alone_under_the_new_id():
    stored = {"deliveryId": "old", "subscriptionId": "s", "events": [EVENT, OTHER]}
    body, content_type, event = resend_body(_request(stored), "e2", "new")
    assert body == {"deliveryId": "new", "subscriptionId": "s", "events": [OTHER]}
    assert (content_type, event) == (delivery.RDM_JSON, OTHER)


def test_a_cloudevent_is_resent_structured_and_a_batched_one_as_an_array_of_one():
    body, content_type, event = resend_body(_request(_cloudevent(EVENT)), "e1", "new")
    assert (body, content_type, event) == (_cloudevent(EVENT), delivery.CLOUDEVENT, EVENT)
    stored = [_cloudevent(EVENT), _cloudevent(OTHER)]
    body, content_type, event = resend_body(_request(stored), "e2", "new")
    assert (body, content_type, event) == ([_cloudevent(OTHER)], delivery.CLOUDEVENTS_BATCH, OTHER)


@pytest.mark.parametrize(
    "stored",
    [{"deliveryId": "old", "events": [EVENT]}, _cloudevent(EVENT), [_cloudevent(EVENT)]],
    ids=["rdm", "structured", "batched"],
)
def test_an_event_not_in_the_request_is_not_found(stored):
    with pytest.raises(ApiError) as raised:
        resend_body(_request(stored), "e9", "new")
    assert (raised.value.status, raised.value.code) == (404, "EVENT_NOT_IN_DELIVERY")


def test_a_request_never_sent_has_nothing_to_resend():
    with pytest.raises(ApiError) as raised:
        resend_body(_request(None), "e1", "new")
    assert (raised.value.status, raised.value.code) == (409, "DELIVERY_NOT_SENT")
