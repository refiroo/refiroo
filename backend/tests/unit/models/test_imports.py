"""The import profile models (``app/models/imports.py``): the forms of a source key."""

import pytest
from pydantic import ValidationError

from app.models.imports import SourceKey


def test_a_key_of_several_attributes_is_one_form_of_a_source_key():
    key = SourceKey(attributeTypeKeys=["a", "b"], versionColumn="Version")
    assert (key.attributeTypeKeys, key.versionColumn) == (["a", "b"], "Version")


@pytest.mark.parametrize(
    "form",
    [
        {"attributeTypeKeys": ["a"]},
        {"attributeTypeKeys": []},
        {"attributeTypeKeys": ["a", "a"]},
        {"attributeTypeKeys": ["a", "b"], "attributeTypeKey": "a"},
        {"attributeTypeKeys": ["a", "b"], "column": "ID"},
        {"attributeTypeKeys": ["a", "b"], "field": "name"},
        {"attributeTypeKeys": ["a", "b"], "nameColumn": "Name"},
    ],
)
def test_a_key_of_several_attributes_is_two_or_more_distinct_and_alone(form):
    with pytest.raises(ValidationError):
        SourceKey(**form)
