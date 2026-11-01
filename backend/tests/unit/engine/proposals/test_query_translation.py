"""``engine/proposals/query_translation.py``: what the provider is sent (0.16 AG4, AG-D35).

The request holds the question, today's date and the list's fields, conditions and relationships
with their labels and the type names they sit under, and nothing a record holds: not a name, not a
value, not an ID; the names of short lists are added only by ``with_names`` at samples or values
(J54.9). The same on both generated models, live and in a change set.
"""

import json
from datetime import date

import pytest
from configurations import all_configurations

from app.engine.model.compiler import parse_model
from app.engine.proposals.context import FEATURE_LEVELS
from app.engine.proposals.query_translation import list_fields, prepare, table_view

TODAY = date(2026, 11, 1)


def _hold(configuration, model):
    """The application and view of R's table list, wherever the configuration places R."""
    key = configuration.key("R")
    for application in model.applications:
        for view in application.views:
            if view.key == f"{key}--list":
                return application.key, view.key
    raise AssertionError("R has no list")


@pytest.mark.parametrize("configuration", ["generated-a", "generated-b"])
def test_the_request_holds_the_question_and_the_lists_structure_and_no_record_value(configuration):
    configuration = all_configurations()[configuration]
    model = parse_model(configuration.model)
    application, view = _hold(configuration, model)
    question = "records changed last month without a webshop mapping"
    prepared = prepare(model, application, view, question, live=True, today=TODAY)
    sent = prepared.request
    assert (sent.purpose, FEATURE_LEVELS["queryTranslation"]) == ("queryTranslation", "structure")
    assert sent.context["question"] == question and sent.context["today"] == "2026-11-01"
    fields = {item["field"]: item for item in sent.context["fields"]}
    related = fields[f"related:{configuration.key('Bassoc')}"]
    assert related["kind"] == "relationship"
    assert set(related["conditions"]) == {"eq", "isNull", "under", "notUnder"}
    # The names of the types a related record can sit under: labels of the model, not of records.
    ancestors = {configuration.key("G")}
    assert {
        item.key for item in model.objectTypes if item.name in related["canSitUnder"]
    } >= ancestors
    assert {"createdAt", "updatedAt"} <= set(fields)
    assert set(fields["updatedAt"]["conditions"]) >= {"gte", "lt", "isNull"}
    # Nothing but the question, the date and structure: every key and string value is the model's
    # (a label, a key, a condition, a kind, a type name) or the question itself.
    words = json.dumps({**sent.context, "question": ""})
    assert "Webshop" not in words and "webshop" not in words
    assert set(sent.context) == {"question", "today", "list", "fields"}


def test_a_change_set_offers_no_timestamp_and_a_view_that_is_not_a_table_is_refused():
    configuration = all_configurations()["generated-a"]
    model = parse_model(configuration.model)
    application, view = _hold(configuration, model)
    live = prepare(model, application, view, "q", live=True, today=TODAY)
    staged = prepare(model, application, view, "q", live=False, today=TODAY)
    offered = {item["field"] for item in staged.request.context["fields"]}
    assert {"createdAt", "updatedAt"} & offered == set()
    assert {item["field"] for item in live.request.context["fields"]} - offered == {
        "createdAt",
        "updatedAt",
    }
    assert list_fields(model, table_view(model, application, view), live=False).keys() == offered
    matrix = next((a.key, v.key) for a in model.applications for v in a.views if v.type != "table")
    with pytest.raises(Exception) as refused:
        table_view(model, *matrix)
    assert getattr(refused.value, "code", None) == "QUERY_TRANSLATION_VIEW_UNSUPPORTED"


@pytest.mark.parametrize("configuration", ["generated-a", "generated-b"])
def test_every_relationship_of_the_listed_type_is_a_field_declared_or_not(configuration):
    configuration = all_configurations()[configuration]
    model = parse_model(configuration.model)
    application, view = _hold(configuration, model)
    definition = table_view(model, application, view)
    fields = list_fields(model, definition, live=True)
    undeclared = f"related:{configuration.key('Bown')}"
    assert undeclared not in definition.config.filterFields
    assert fields[undeclared].kind == "relationship"
    assert {"eq", "isNull"} <= set(fields[undeclared].conditions)
    # The request still holds no record name: names are added only by ``with_names``.
    shown = prepare(model, application, view, "q", live=True, today=TODAY).request.context["fields"]
    assert all("recordNames" not in item and "ancestorNames" not in item for item in shown)
