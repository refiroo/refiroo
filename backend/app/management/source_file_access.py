"""The one rule for using a stored source file by its ID, shared by the source file routes and
``POST /imports`` naming ``sourceFileId``."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..engine.authorization.visibility import may_use_source_file
from ..engine.sources.store import load_source_file
from ..errors import api_error
from ..models.database import ModelDraft, SourceFile
from .access import CurrentPermissions, forbidden, own_draft_only
from .dependencies import CurrentPrincipal


def usable_source_file(
    session: Session,
    source_file_id: str,
    permissions: CurrentPermissions,
    principal: CurrentPrincipal,
) -> SourceFile:
    """A source file the caller may use: a profile's by its uploader and by holders of Bulk and
    import in its workspace, or at the instance for one naming none (0.12 Z2, D248, D295); a
    draft's by the session that owns the draft, and by any other caller as before (R172-F24)."""
    source = load_source_file(session, source_file_id)
    if source.task_id is not None:
        # An assistant task's workbook is read through its task (0.16 AP6a).
        raise api_error(404, "SOURCE_FILE_NOT_FOUND", f"Source file '{source_file_id}' not found")
    if source.draft_id is not None:
        own_draft_only(
            session,
            principal,
            session.scalar(select(ModelDraft.public_id).where(ModelDraft.id == source.draft_id)),
        )
    if source.profile_key is not None and not may_use_source_file(
        permissions, principal.kind, principal.row_id, source
    ):
        raise forbidden("source-files.manage", ("bulk",), source.workspace_key)
    return source
