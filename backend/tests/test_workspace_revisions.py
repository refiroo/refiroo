from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.database import (
    Base,
    Workspace,
    WorkspaceDraft,
    WorkspaceDraftObject,
    WorkspaceDraftRelation,
    WorkspaceRevision,
    WorkspaceRevisionObject,
    WorkspaceRevisionRelation,
)
from app.services.workspace_revisions import effective_draft_membership


def test_workspace_draft_membership_is_copy_on_write_with_tombstones():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    revision_id = str(uuid4())
    draft_id = str(uuid4())
    with Session(engine) as session:
        session.add(Workspace(key="default", label="Default", active_revision_id=revision_id))
        session.add(
            WorkspaceRevision(
                id=revision_id,
                workspace_key="default",
                model_release_id=1,
                revision_number=1,
                status="active",
            )
        )
        session.add(
            WorkspaceDraft(
                id=draft_id,
                workspace_key="default",
                model_release_id=1,
                derived_from_revision_id=revision_id,
                version=1,
            )
        )
        session.add_all(
            [
                WorkspaceRevisionObject(
                    revision_id=revision_id,
                    object_id="base-kept",
                    application_key="app",
                    object_type_key="type",
                    name="Kept",
                    parent_object_id=None,
                    attributes={},
                    version=1,
                ),
                WorkspaceRevisionObject(
                    revision_id=revision_id,
                    object_id="base-changed",
                    application_key="app",
                    object_type_key="type",
                    name="Before",
                    parent_object_id=None,
                    attributes={},
                    version=1,
                ),
                WorkspaceRevisionRelation(
                    revision_id=revision_id,
                    relation_id="removed-relation",
                    relation_type_key="links",
                    from_object_id="base-kept",
                    to_object_id="base-changed",
                    attributes={},
                    version=1,
                ),
                WorkspaceDraftObject(
                    draft_id=draft_id,
                    object_id="base-changed",
                    application_key="app",
                    object_type_key="type",
                    name="After",
                    parent_object_id=None,
                    attributes={},
                    version=2,
                ),
                WorkspaceDraftObject(
                    draft_id=draft_id,
                    object_id="new-object",
                    application_key="app",
                    object_type_key="type",
                    name="New",
                    parent_object_id=None,
                    attributes={},
                    version=1,
                ),
                WorkspaceDraftRelation(
                    draft_id=draft_id,
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
        effective = effective_draft_membership(session, draft_id)
        assert [(item.object_id, item.name) for item in effective.objects] == [
            ("base-changed", "After"),
            ("base-kept", "Kept"),
            ("new-object", "New"),
        ]
        assert effective.relations == ()
    engine.dispose()
