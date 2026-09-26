from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.database import (
    AttributeValue,
    Base,
    ObjectRelation,
    Publication,
    PublicationObject,
    RdmObject,
    Workspace,
)
from app.models.schema import EngineModel
from app.services.model.compatibility import analyze_compatibility


def _source() -> dict:
    return {
        "schemaVersion": "0.5",
        "release": {"key": "compat", "name": "Compatibility", "version": "1"},
        "product": {"name": "Compatibility test"},
        "attributeTypes": [
            {"key": "value", "name": "Value"},
            {"key": "relation-note", "name": "Relation note"},
            {"key": "relation-score", "name": "Relation score", "valueType": "integer"},
        ],
        "objectTypes": [
            {
                "key": "source",
                "name": "Source",
                "pluralName": "Sources",
                "attributes": [{"attributeTypeKey": "value"}],
                "features": {"rootCreatable": True},
            },
            {
                "key": "target",
                "name": "Target",
                "pluralName": "Targets",
                "attributes": [{"attributeTypeKey": "value"}],
                "features": {"rootCreatable": True},
                "behavior": {"parentRelationTypeKeys": ["contains"]},
            },
        ],
        "relationTypes": [
            {
                "key": "links",
                "reverseKey": "linked-by",
                "name": "Links",
                "reverseName": "Linked by",
            },
            {
                "key": "contains",
                "reverseKey": "belongs-to",
                "name": "Contains",
                "reverseName": "Belongs to",
                "features": {"parentOf": True},
            },
        ],
        "objectTypeRelations": [
            {
                "relationTypeKey": "links",
                "fromObjectTypeKey": "source",
                "toObjectTypeKey": "target",
                "cardinality": "many-to-many",
                "attributeTypeKeys": ["relation-note", "relation-score"],
            },
            {
                "relationTypeKey": "contains",
                "fromObjectTypeKey": "source",
                "toObjectTypeKey": "target",
                "cardinality": "one-to-many",
            },
        ],
        "applications": [
            {
                "key": "app",
                "name": "Application",
                "objectTypeKeys": ["source", "target"],
                "defaultView": "sources",
                "views": [
                    {
                        "key": "sources",
                        "name": "Sources",
                        "type": "table",
                        "objectTypeKey": "source",
                        "config": {
                            "columns": ["name"],
                            "filterFields": ["name"],
                            "sortFields": ["name"],
                            "defaultSort": "name",
                            "pageSize": 20,
                        },
                    }
                ],
            }
        ],
    }


def _model(source: dict | None = None) -> EngineModel:
    return EngineModel.model_validate(source or _source())


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as value:
        publication_id = str(uuid4())
        value.add(
            Workspace(
                key="default",
                label="Default",
                status="active",
                active_publication_id=publication_id,
            )
        )
        value.add(
            Publication(
                id=publication_id,
                workspace_key="default",
                model_release_id=1,
                publication_number=1,
                status="active",
            )
        )
        value.flush()
        yield value
    engine.dispose()


def _object(session: Session, object_type: str, *, parent: RdmObject | None = None) -> RdmObject:
    item = RdmObject(
        application_key="app",
        object_type_key=object_type,
        workspace_key="default",
        name=object_type,
        parent_object_id=parent.id if parent else None,
    )
    session.add(item)
    session.flush()
    publication_id = session.scalar(
        select(Workspace.active_publication_id).where(Workspace.key == "default")
    )
    session.add(
        PublicationObject(
            publication_id=publication_id,
            object_id=item.id,
            application_key=item.application_key,
            object_type_key=item.object_type_key,
            name=item.name,
            parent_object_id=item.parent_object_id,
            attributes={},
            version=item.version,
        )
    )
    session.flush()
    return item


def _compatibility(session: Session, candidate_source: dict):
    return analyze_compatibility(session, _model(), _model(candidate_source), "active-release")


def test_presentation_change_and_unused_addition_are_compatible(session: Session):
    _object(session, "source")
    candidate = deepcopy(_source())
    candidate["applications"][0]["views"][0]["name"] = "Renamed sources"
    candidate["attributeTypes"].append({"key": "unused", "name": "Unused"})

    result = _compatibility(session, candidate)

    assert result.classification == "compatible"
    assert result.diagnostics == ()


@pytest.mark.parametrize(
    ("mutate", "seed", "code"),
    [
        (
            lambda source: source.update({"applications": []}),
            lambda session: _object(session, "source"),
            "application_in_use",
        ),
        (
            lambda source: (
                source["objectTypes"].pop(1),
                source["applications"][0].update({"objectTypeKeys": ["source"]}),
                source.update({"objectTypeRelations": []}),
            ),
            lambda session: _object(session, "target"),
            "object_type_in_use",
        ),
        (
            lambda source: (
                source["attributeTypes"].pop(0),
                source["objectTypes"][0].update({"attributes": []}),
                source["objectTypes"][1].update({"attributes": []}),
            ),
            lambda session: _seed_attribute(session),
            "attribute_type_in_use",
        ),
        (
            lambda source: source["attributeTypes"][0].update({"valueType": "integer"}),
            lambda session: _seed_attribute(session),
            "attribute_value_type_changed",
        ),
        (
            lambda source: source["objectTypes"][0].update({"attributes": []}),
            lambda session: _seed_attribute(session),
            "attribute_binding_in_use",
        ),
        (
            lambda source: source["objectTypeRelations"].pop(0),
            lambda session: _seed_link(session),
            "relation_pair_in_use",
        ),
        (
            lambda source: source["objectTypeRelations"][0].update(
                {"attributeTypeKeys": []}
            ),
            lambda session: _seed_link(session, attributes={"relation-note": "used"}),
            "relation_attribute_in_use",
        ),
        (
            lambda source: source["attributeTypes"][1].update({"valueType": "integer"}),
            lambda session: _seed_link(session, attributes={"relation-note": "used"}),
            "relation_attribute_value_type_changed",
        ),
        (
            lambda source: source["objectTypes"][1].update({"behavior": {}}),
            lambda session: _seed_parent(session),
            "parent_relation_semantics_changed",
        ),
        (
            lambda source: source["objectTypes"][0]["attributes"][0].update(
                {"required": True}
            ),
            lambda session: _object(session, "source"),
            "required_attribute_missing",
        ),
        (
            lambda source: source["objectTypeRelations"][0].update({"required": True}),
            lambda session: _object(session, "target"),
            "required_relation_missing",
        ),
        (
            lambda source: source["attributeTypes"][0].update(
                {"features": {"unique": True}}
            ),
            lambda session: _seed_duplicate_attributes(session),
            "attribute_uniqueness_violated",
        ),
        (
            lambda source: source["objectTypeRelations"][0].update(
                {"cardinality": "one-to-many"}
            ),
            lambda session: _seed_duplicate_target_relations(session),
            "relation_cardinality_violated",
        ),
    ],
)
def test_runtime_data_blocking_classes_are_reported(session, mutate, seed, code):
    seed(session)
    candidate = deepcopy(_source())
    mutate(candidate)

    result = _compatibility(session, candidate)

    assert result.classification == "migration_required"
    diagnostic = next(item for item in result.diagnostics if item.code == code)
    assert diagnostic.count is not None and diagnostic.count > 0
    assert diagnostic.path.startswith("/")


def test_scoped_relation_uniqueness_is_checked_against_containment_ancestors(session):
    parent = _object(session, "source")
    for _ in range(2):
        target = _object(session, "target", parent=parent)
        session.add_all(
            [
                ObjectRelation(
                    relation_type_key="contains",
                    from_object_id=parent.id,
                    to_object_id=target.id,
                    attributes={},
                ),
                ObjectRelation(
                    relation_type_key="links",
                    from_object_id=parent.id,
                    to_object_id=target.id,
                    attributes={},
                ),
            ]
        )
    session.flush()
    candidate = deepcopy(_source())
    candidate["objectTypeRelations"][0]["features"] = {
        "uniqueToAncestorTypeKey": "source"
    }

    result = _compatibility(session, candidate)

    diagnostic = next(
        item for item in result.diagnostics if item.code == "relation_uniqueness_violated"
    )
    assert diagnostic.count == 1


def test_numeric_bounds_are_checked_for_stored_relation_attributes(session):
    _seed_link(session, attributes={"relation-score": 5})
    candidate = deepcopy(_source())
    candidate["attributeTypes"][2]["validation"] = {"minimum": 10}

    result = _compatibility(session, candidate)

    diagnostic = next(
        item for item in result.diagnostics if item.code == "attribute_validation_violated"
    )
    assert diagnostic.count == 1
    assert diagnostic.path == "/attributeTypes/relation-score/validation/minimum"


def test_cardinality_is_checked_across_all_pairs_sharing_a_relation_type(session):
    active_source = deepcopy(_source())
    active_source["objectTypes"].append(
        {
            "key": "second-source",
            "name": "Second source",
            "pluralName": "Second sources",
            "features": {"rootCreatable": True},
        }
    )
    active_source["applications"][0]["objectTypeKeys"].append("second-source")
    active_source["objectTypeRelations"].append(
        {
            "relationTypeKey": "links",
            "fromObjectTypeKey": "second-source",
            "toObjectTypeKey": "target",
            "cardinality": "many-to-many",
        }
    )
    first_source = _object(session, "source")
    second_source = _object(session, "second-source")
    target = _object(session, "target")
    session.add_all(
        [
            ObjectRelation(
                relation_type_key="links",
                from_object_id=first_source.id,
                to_object_id=target.id,
                attributes={},
            ),
            ObjectRelation(
                relation_type_key="links",
                from_object_id=second_source.id,
                to_object_id=target.id,
                attributes={},
            ),
        ]
    )
    session.flush()
    candidate_source = deepcopy(active_source)
    for pair in candidate_source["objectTypeRelations"]:
        if pair["relationTypeKey"] == "links":
            pair["cardinality"] = "one-to-many"

    result = analyze_compatibility(
        session,
        _model(active_source),
        _model(candidate_source),
        "active-release",
    )

    assert result.classification == "migration_required"
    diagnostic = next(
        item for item in result.diagnostics if item.code == "relation_cardinality_violated"
    )
    assert diagnostic.count == 1


def test_one_to_one_cardinality_checks_shared_sources_across_target_pairs(session):
    active_source = deepcopy(_source())
    active_source["objectTypes"].append(
        {
            "key": "second-target",
            "name": "Second target",
            "pluralName": "Second targets",
            "features": {"rootCreatable": True},
        }
    )
    active_source["applications"][0]["objectTypeKeys"].append("second-target")
    active_source["objectTypeRelations"].append(
        {
            "relationTypeKey": "links",
            "fromObjectTypeKey": "source",
            "toObjectTypeKey": "second-target",
            "cardinality": "many-to-many",
        }
    )
    source = _object(session, "source")
    first_target = _object(session, "target")
    second_target = _object(session, "second-target")
    session.add_all(
        [
            ObjectRelation(
                relation_type_key="links",
                from_object_id=source.id,
                to_object_id=target.id,
                attributes={},
            )
            for target in (first_target, second_target)
        ]
    )
    session.flush()
    candidate_source = deepcopy(active_source)
    for pair in candidate_source["objectTypeRelations"]:
        if pair["relationTypeKey"] == "links":
            pair["cardinality"] = "one-to-one"

    result = analyze_compatibility(
        session,
        _model(active_source),
        _model(candidate_source),
        "active-release",
    )

    assert result.classification == "migration_required"
    diagnostic = next(
        item for item in result.diagnostics if item.code == "relation_cardinality_violated"
    )
    assert diagnostic.count == 1


def _seed_attribute(session: Session) -> None:
    item = _object(session, "source")
    session.add(
        AttributeValue(
            object_id=item.id,
            attribute_type_key="value",
            value_type="text",
            text_value="stored",
        )
    )
    session.flush()


def _seed_link(session: Session, *, attributes: dict | None = None) -> None:
    source = _object(session, "source")
    target = _object(session, "target")
    session.add(
        ObjectRelation(
            relation_type_key="links",
            from_object_id=source.id,
            to_object_id=target.id,
            attributes=attributes or {},
        )
    )
    session.flush()


def _seed_parent(session: Session) -> None:
    parent = _object(session, "source")
    child = _object(session, "target", parent=parent)
    session.add(
        ObjectRelation(
            relation_type_key="contains",
            from_object_id=parent.id,
            to_object_id=child.id,
            attributes={},
        )
    )
    session.flush()


def _seed_duplicate_attributes(session: Session) -> None:
    for _ in range(2):
        item = _object(session, "source")
        session.add(
            AttributeValue(
                object_id=item.id,
                attribute_type_key="value",
                value_type="text",
                text_value="duplicate",
            )
        )
    session.flush()


def _seed_duplicate_target_relations(session: Session) -> None:
    target = _object(session, "target")
    for _ in range(2):
        source = _object(session, "source")
        session.add(
            ObjectRelation(
                relation_type_key="links",
                from_object_id=source.id,
                to_object_id=target.id,
                attributes={},
            )
        )
    session.flush()
