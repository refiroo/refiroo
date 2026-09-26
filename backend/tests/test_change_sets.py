from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.database import (
    Base,
    ChangeSet,
    ChangeSetObject,
    ChangeSetRelation,
    Publication,
    PublicationObject,
    PublicationRelation,
    Workspace,
)
from app.services.change_sets import effective_change_set_membership


def test_change_set_membership_is_copy_on_write_with_tombstones():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    publication_id = str(uuid4())
    change_set_id = str(uuid4())
    with Session(engine) as session:
        session.add(Workspace(key="default", label="Default", active_publication_id=publication_id))
        session.add(
            Publication(
                id=publication_id,
                workspace_key="default",
                model_release_id=1,
                publication_number=1,
                status="active",
            )
        )
        session.add(
            ChangeSet(
                id=change_set_id,
                workspace_key="default",
                model_release_id=1,
                derived_from_publication_id=publication_id,
                version=1,
            )
        )
        session.add_all(
            [
                PublicationObject(
                    publication_id=publication_id,
                    object_id="base-kept",
                    application_key="app",
                    object_type_key="type",
                    name="Kept",
                    parent_object_id=None,
                    attributes={},
                    version=1,
                ),
                PublicationObject(
                    publication_id=publication_id,
                    object_id="base-changed",
                    application_key="app",
                    object_type_key="type",
                    name="Before",
                    parent_object_id=None,
                    attributes={},
                    version=1,
                ),
                PublicationRelation(
                    publication_id=publication_id,
                    relation_id="removed-relation",
                    relation_type_key="links",
                    from_object_id="base-kept",
                    to_object_id="base-changed",
                    attributes={},
                    version=1,
                ),
                ChangeSetObject(
                    change_set_id=change_set_id,
                    object_id="base-changed",
                    application_key="app",
                    object_type_key="type",
                    name="After",
                    parent_object_id=None,
                    attributes={},
                    version=2,
                ),
                ChangeSetObject(
                    change_set_id=change_set_id,
                    object_id="new-object",
                    application_key="app",
                    object_type_key="type",
                    name="New",
                    parent_object_id=None,
                    attributes={},
                    version=1,
                ),
                ChangeSetRelation(
                    change_set_id=change_set_id,
                    relation_id="removed-relation",
                    relation_type_key="links",
                    from_object_id="base-kept",
                    to_object_id="base-changed",
                    attributes={},
                    version=2,
                    is_deleted=True,
                ),
            ]
        )
        session.flush()
        effective = effective_change_set_membership(session, change_set_id)
        assert [(item.object_id, item.name) for item in effective.objects] == [
            ("base-changed", "After"),
            ("base-kept", "Kept"),
            ("new-object", "New"),
        ]
        assert effective.relations == ()
    engine.dispose()
