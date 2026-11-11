"""The operation kinds the OpenAPI document describes agree with the kinds the engine applies.

The registries own what a kind allows (``engine/model/authoring/kinds.py`` with
``consumer.py`` and ``mapping.py`` for a model draft, ``engine/moves/mapping_kinds.py`` for a model
mapping); the tables in ``management/schemas`` only describe it. These tests hold the two together,
for every kind of both registries: the same kinds, every parameter described and typed and none
extra, a plain summary from the docstring, and the required flags as the code refuses them (an
operation without parameters is refused at a parameter the table calls needed). The document the
application builds holds both unions, without the kinds only the server writes.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from app.engine.model.authoring import (  # noqa: F401  (register their kinds)
    consumer,
    kinds,
    mapping,
)
from app.engine.model.authoring.document import Document, Refusal
from app.engine.moves import mapping_kinds
from app.main import create_app
from app.management.schemas.mapping_operation_parameters import PARAMETERS as MAPPING_TABLE
from app.management.schemas.model_mapping_operations import (
    MAPPING_OPERATION_SCHEMAS,
    mapping_operation_schema_name,
)
from app.management.schemas.model_operation_parameters import PARAMETERS as DRAFT_TABLE
from app.management.schemas.model_operations import OPERATION_SCHEMAS, operation_schema_name
from app.management.schemas.operation_description import Param


@dataclass(frozen=True)
class Registry:
    name: str
    kinds: dict[str, Any]
    parameters: dict[str, tuple[str, ...]]
    internal: set[str] | frozenset[str]
    table: dict[str, dict[str, Param]]
    schemas: dict[str, Any]
    schema_name: Callable[[str], str]
    request: str
    apply: Callable[[dict[str, Any]], Any]

    @property
    def public(self) -> list[str]:
        return sorted(set(self.kinds) - set(self.internal))


def _draft(operation: dict[str, Any]) -> Any:
    return kinds.apply_operation(kinds.Context(Document({}), lambda _atom: False), operation)


def _mapping(operation: dict[str, Any]) -> Any:
    document = Document({}, identities=mapping_kinds.IDENTITIES)
    context = mapping_kinds.MappingContext(document, ("a", "b"), lambda _release: None)
    return mapping_kinds.apply_operation(context, operation)


DRAFT = Registry(
    "draft",
    kinds.KINDS,
    kinds.PARAMETERS,
    kinds.INTERNAL_KINDS,
    DRAFT_TABLE,
    OPERATION_SCHEMAS,
    operation_schema_name,
    "ModelDraftOperationsRequest",
    _draft,
)
MAPPING = Registry(
    "mapping",
    mapping_kinds.KINDS,
    mapping_kinds.PARAMETERS,
    mapping_kinds.INTERNAL_KINDS,
    MAPPING_TABLE,
    MAPPING_OPERATION_SCHEMAS,
    mapping_operation_schema_name,
    "ModelMappingOperationsRequest",
    _mapping,
)
BOTH = pytest.mark.parametrize("registry", [DRAFT, MAPPING], ids=lambda registry: registry.name)

# Kinds whose first check is the lookup or the type of a key the table calls required, so an
# operation without parameters is refused with that reason at that parameter, not as
# ``missingParameter``. Every other kind refuses ``missingParameter`` at a needed parameter.
FIRST_CHECK = {
    "addSource": ("unknownElement", "sheet"),
    "addValuesToList": ("invalidValue", "source"),
    "ignoreColumn": ("invalidValue", "source"),
    "ignoreSheet": ("unknownElement", "sheet"),
    "insertConsumerApiPart": ("invalidValue", "consumerApi"),
    "mapColumn": ("invalidValue", "source"),
    "moveConsumerApiPart": ("invalidValue", "consumerApi"),
    "raiseConsumerApiVersion": ("invalidValue", "consumerApi"),
    "removeConsumerApi": ("invalidValue", "consumerApi"),
    "removeConsumerApiPart": ("invalidValue", "consumerApi"),
    "removeConsumerApiVersion": ("invalidValue", "consumerApi"),
    "removeDetailPage": ("invalidValue", "applicationKey"),
    "removeNavigationGroup": ("invalidValue", "applicationKey"),
    "removeSource": ("invalidValue", "source"),
    "removeView": ("invalidValue", "applicationKey"),
    "setColumnReading": ("invalidValue", "source"),
    "setConsumerApiPart": ("invalidValue", "consumerApi"),
    "setConsumerApiSunset": ("invalidValue", "consumerApi"),
    "setKey": ("invalidValue", "element"),
    "setLabel": ("invalidValue", "element"),
    "setMissing": ("invalidValue", "source"),
    "setNavigationGroup": ("invalidValue", "applicationKey"),
    "setSource": ("invalidValue", "source"),
    "splitColumn": ("invalidValue", "source"),
    "unmapColumn": ("invalidValue", "source"),
}
# A package or decision identifier has no place in what an integrator reads.
IDENTIFIER = re.compile(r"\b[DI]\d{1,3}\b|\b0\.\d{1,2} [A-Z]{1,3}\d*\b|\bADR-\d+|\bDF-?D?\d")


def test_the_registries_count_what_the_document_describes():
    assert (len(DRAFT.public), len(MAPPING.public)) == (66, 12)


@BOTH
def test_the_tables_and_the_unions_hold_every_public_kind(registry):
    assert set(registry.parameters) == set(registry.kinds)
    assert sorted(registry.table) == registry.public
    assert sorted(registry.schemas) == registry.public
    assert not set(registry.internal) & set(registry.table)


@BOTH
def test_every_registry_parameter_is_described_and_typed_and_none_is_extra(registry):
    for kind in registry.public:
        table = registry.table[kind]
        assert set(table) == set(registry.parameters[kind]), kind
        for name, parameter in table.items():
            where = f"{kind}.{name}"
            assert len(parameter.description) > 8, where
            assert parameter.description.rstrip().endswith((".", "`")), where
            assert not IDENTIFIER.search(parameter.description), where
            if not parameter.schema:
                # A value whose shape depends on another parameter is left untyped, and says so.
                assert name in {"item", "value"}, where
        assert not any(p.required and p.when for p in table.values()), kind


@BOTH
def test_every_public_kind_has_a_plain_summary_from_its_docstring(registry):
    for kind in registry.public:
        summary = " ".join((registry.kinds[kind].__doc__ or "").split())
        assert summary, f"{kind} has no docstring"
        assert not IDENTIFIER.search(summary), f"{kind}: an identifier in the summary"
        assert len(re.split(r"(?<=[.])\s+(?=[A-Z`])", summary)) <= 3, kind
        assert registry.schemas[kind].__doc__ == summary, kind


@BOTH
def test_a_kind_refuses_an_operation_without_parameters_at_a_parameter_it_needs(registry):
    for kind in registry.public:
        needed = {name for name, parameter in registry.table[kind].items() if parameter.needed}
        assert needed, f"{kind} needs no parameter"
        with pytest.raises(Refusal) as refused:
            registry.apply({"kind": kind})
        reason, field = refused.value.reason, refused.value.field
        assert field in needed, f"{kind} refuses {field!r}; the table needs {sorted(needed)}"
        if registry is MAPPING:
            assert reason == "missingParameter", kind
        else:
            assert (reason, field) == FIRST_CHECK.get(kind, ("missingParameter", field)), kind


@BOTH
def test_an_unknown_parameter_is_refused_at_its_name_before_a_kind_runs(registry):
    for kind in registry.public:
        with pytest.raises(Refusal) as refused:
            registry.apply({"kind": kind, "zzUnknown": 1})
        assert (refused.value.field, refused.value.reason) == ("zzUnknown", "unknownParameter")


def test_the_document_holds_both_unions_and_not_the_kinds_the_server_writes(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("INTEGRATION_JOBS_ENABLED", "true")
    schemas = create_app().openapi()["components"]["schemas"]
    for registry in (DRAFT, MAPPING):
        items = schemas[registry.request]["properties"]["operations"]["items"]
        assert items["discriminator"]["propertyName"] == "kind"
        assert sorted(items["discriminator"]["mapping"]) == registry.public, registry.name
        for kind in registry.internal:
            assert kind not in items["discriminator"]["mapping"]
            assert registry.schema_name(kind) not in schemas
        for kind in registry.public:
            schema = schemas[registry.schema_name(kind)]
            assert schema["properties"]["kind"]["const"] == kind
            assert schema["additionalProperties"] is False
            assert schema["description"], kind
            assert set(schema["properties"]) == {"kind", *registry.parameters[kind]}, kind
            required = [name for name, p in registry.table[kind].items() if p.required]
            assert schema["required"] == ["kind", *required], kind
            for name, member in schema["properties"].items():
                assert member.get("description"), f"{kind}.{name} is not described"


def test_the_history_entries_say_the_server_writes_its_own_kinds(monkeypatch):
    monkeypatch.setenv("MODEL_ADMIN_MUTATIONS_ENABLED", "true")
    monkeypatch.setenv("INTEGRATION_JOBS_ENABLED", "true")
    schemas = create_app().openapi()["components"]["schemas"]
    for name, written in (
        ("ModelDraftOperationEntry", ("replaceModel", "restoreElements")),
        ("ModelMappingOperationEntry", ("restoreElements",)),
    ):
        for field in ("kind", "parameters", "inverse"):
            assert schemas[name]["properties"][field].get("description"), f"{name}.{field}"
        for kind in written:
            assert kind in schemas[name]["properties"]["kind"]["description"], (name, kind)
