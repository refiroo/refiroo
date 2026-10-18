"""Model mappings: what each element of a source model becomes in a target model (0.11 X1, D18,
D104–D112).

A mapping is stored once for the instance under its ``key``, named by its two models' release keys
and checked against two releases, which its definition names (``sourceReleaseId``,
``targetReleaseId``) so that re-pointing it is a step like any other (D104). It is created between
two workspaces (the releases they run) or two releases, and changes only through operations
(``mapping_kinds``) with history, undo and redo, the same history a model draft has
(``authoring/history``, D105). Every read reports its problems and coverage against its releases,
or against the releases two named workspaces run (``mapping_check``, D110).
"""

import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import ColumnElement, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...common.pagination import Page, PageRequest, paginate_statement, text_key
from ...errors import api_error
from ...models.database import ModelMapping, ModelMappingOperation, ModelRelease, WorkspaceModel
from ..model.authoring import history
from ..model.authoring.document import Document, Refusal
from ..model.authoring.history import Outcome, StepResult
from ..model.authoring.kinds import Applied
from ..model.diagnostics import ModelDiagnostic
from ..model.registry import resolve_pinned_release
from ..workspaces.catalogue import resolve_workspace
from . import mapping_kinds
from .mapping_check import coverage, problems
from .mapping_kinds import IDENTITIES, MappingContext
from .sides import Side

_KEYS = (text_key("key", ModelMapping.key, "key"),)


@dataclass(frozen=True)
class ReadMapping:
    """A mapping as read: its row, its releases' public IDs, and its problems and coverage against
    the releases it was read under."""

    mapping: ModelMapping
    problems: list[dict[str, Any]]
    coverage: dict[str, list[Any]]


# --- releases and sides ----------------------------------------------------------------------------


class Releases:
    """Releases by public ID, each read once per request as a mapping's side."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._sides: dict[str, Side | None] = {}

    def side(self, release_id: str) -> Side | None:
        if release_id not in self._sides:
            row = self.session.scalar(
                select(ModelRelease.id).where(ModelRelease.public_id == release_id)
            )
            self._sides[release_id] = (
                Side(
                    resolve_pinned_release(self.session, row, require_ready=False).model, release_id
                )
                if row
                else None
            )
        return self._sides[release_id]

    def by_db_id(self, db_id: int) -> Side:
        public_id = self.session.scalar(
            select(ModelRelease.public_id).where(ModelRelease.id == db_id)
        )
        side = self.side(public_id)
        assert side is not None
        return side

    def of_workspace(self, workspace_key: str, *, require_active: bool = False) -> Side:
        """The release ``workspace_key`` runs, without binding the session's commits to it: a
        mapping is configuration, not a write into the workspace."""
        workspace = resolve_workspace(self.session, workspace_key)
        if require_active and workspace.status == "retired":
            raise api_error(409, "WORKSPACE_RETIRED", f"Workspace '{workspace.key}' is retired")
        db_id = self.session.scalar(
            select(WorkspaceModel.model_release_id).where(
                WorkspaceModel.workspace_key == workspace.key
            )
        )
        return self.by_db_id(db_id)


# --- the history owner (D105) ----------------------------------------------------------------------


class _Mappings:
    label = "Model mapping"
    version_field = "mappingVersion"
    version_column = "mapping_version"
    internal_kinds = mapping_kinds.INTERNAL_KINDS
    rows = ModelMappingOperation

    def lock(self, session: Session, public_id: str) -> ModelMapping:
        return load_mapping(session, public_id, for_update=True)

    def public_id(self, subject: ModelMapping) -> str:
        return subject.key

    def owned(self, subject: ModelMapping) -> ColumnElement[bool]:
        return ModelMappingOperation.mapping_id == subject.id

    def row_version(self, row: ModelMappingOperation) -> int:
        return row.mapping_version

    def new_row(self, subject: ModelMapping, **fields: Any) -> ModelMappingOperation:
        return ModelMappingOperation(
            mapping_id=subject.id, mapping_version=subject.version, **fields
        )

    def apply(
        self,
        session: Session,
        mapping: ModelMapping,
        operations: list[dict[str, Any]],
        pointer: str,
    ) -> Outcome:
        document = Document(copy.deepcopy(mapping.definition), identities=IDENTITIES)
        context = MappingContext(
            document, (mapping.source_model_key, mapping.target_model_key), Releases(session).side
        )
        applied: list[Applied] = []
        for index, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise history.invalid(
                    index,
                    Refusal("", "invalidValue", "An operation is an object with a kind"),
                    pointer,
                )
            try:
                applied.append(mapping_kinds.apply_operation(context, operation))
            except Refusal as refusal:
                raise history.invalid(index, refusal, pointer) from refusal
        return applied, document.data

    def commit(
        self, session: Session, mapping: ModelMapping, expected_version: int, state: Any
    ) -> tuple[ModelMapping, bool, tuple[ModelDiagnostic, ...]]:
        releases = {
            row.public_id: row.id
            for row in session.execute(
                select(ModelRelease.public_id, ModelRelease.id).where(
                    ModelRelease.public_id.in_({state["sourceReleaseId"], state["targetReleaseId"]})
                )
            )
        }
        mapping.definition = state
        mapping.source_release_id = releases[state["sourceReleaseId"]]
        mapping.target_release_id = releases[state["targetReleaseId"]]
        mapping.version += 1
        mapping.updated_at = datetime.now(UTC)
        session.flush()
        return mapping, True, ()


MAPPINGS: history.Owner = _Mappings()


# --- the resource ----------------------------------------------------------------------------------


def create_mapping(
    session: Session,
    *,
    key: str,
    name: str,
    source_workspace_key: str | None,
    target_workspace_key: str | None,
    source_release_id: str | None,
    target_release_id: str | None,
) -> ReadMapping:
    """A mapping between the releases two workspaces run, or two releases named by ID; commits."""
    releases = Releases(session)
    sides = []
    for name_, workspace, release in (
        ("source", source_workspace_key, source_release_id),
        ("target", target_workspace_key, target_release_id),
    ):
        if (workspace is None) == (release is None):
            raise api_error(
                422,
                "INVALID_MODEL_MAPPING",
                f"Name the {name_} by a workspace or by a release, not both",
                {"pointer": f"/{name_}WorkspaceKey"},
            )
        if workspace is not None:
            sides.append(releases.of_workspace(workspace, require_active=True))
        else:
            side = releases.side(release)
            if side is None:
                raise api_error(
                    404, "MODEL_RELEASE_NOT_FOUND", f"Model release '{release}' not found"
                )
            sides.append(side)
    source, target = sides
    now = datetime.now(UTC)
    mapping = ModelMapping(
        key=key,
        name=name,
        source_model_key=source.model_key,
        target_model_key=target.model_key,
        source_release_id=session.scalar(
            select(ModelRelease.id).where(ModelRelease.public_id == source.release_id)
        ),
        target_release_id=session.scalar(
            select(ModelRelease.id).where(ModelRelease.public_id == target.release_id)
        ),
        version=1,
        definition={
            "sourceReleaseId": source.release_id,
            "targetReleaseId": target.release_id,
            "types": [],
            "valueMaps": {},
        },
        created_at=now,
        updated_at=now,
    )
    session.add(mapping)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise api_error(
            409, "MODEL_MAPPING_EXISTS", f"A model mapping '{key}' already exists"
        ) from None
    session.commit()
    return _read(mapping, source, target)


def load_mapping(session: Session, key: str, *, for_update: bool = False) -> ModelMapping:
    statement = select(ModelMapping).where(ModelMapping.key == key)
    if for_update:
        statement = statement.with_for_update()
    mapping = session.scalar(statement)
    if mapping is None:
        raise api_error(404, "MODEL_MAPPING_NOT_FOUND", f"Model mapping '{key}' not found")
    return mapping


def read_mapping(
    session: Session,
    mapping: ModelMapping,
    *,
    source_workspace_key: str | None = None,
    target_workspace_key: str | None = None,
) -> ReadMapping:
    """The mapping with its problems and coverage against its releases, or, for a side whose
    workspace is named, against the release that workspace runs (D110)."""
    releases = Releases(session)
    source = (
        releases.of_workspace(source_workspace_key)
        if source_workspace_key is not None
        else releases.side(mapping.definition["sourceReleaseId"])
    )
    target = (
        releases.of_workspace(target_workspace_key)
        if target_workspace_key is not None
        else releases.side(mapping.definition["targetReleaseId"])
    )
    assert source is not None and target is not None
    for side, model_key, workspace in (
        (source, mapping.source_model_key, source_workspace_key),
        (target, mapping.target_model_key, target_workspace_key),
    ):
        if side.model_key != model_key:
            raise mismatch(mapping, source.model_key, target.model_key, workspace)
    return _read(mapping, source, target)


def mismatch(
    mapping: ModelMapping, source_key: str, target_key: str, workspace: str | None = None
) -> Exception:
    return api_error(
        422,
        "MODEL_MAPPING_MODEL_MISMATCH",
        f"Model mapping '{mapping.key}' maps '{mapping.source_model_key}' to '{mapping.target_model_key}'",
        {
            "mappingSourceModelKey": mapping.source_model_key,
            "mappingTargetModelKey": mapping.target_model_key,
            "sourceModelKey": source_key,
            "targetModelKey": target_key,
            "workspaceKey": workspace,
        },
    )


def _read(mapping: ModelMapping, source: Side, target: Side) -> ReadMapping:
    return ReadMapping(
        mapping,
        problems(mapping.definition, source, target),
        coverage(mapping.definition, source, target),
    )


def mapping_page(
    session: Session,
    page: PageRequest,
    page_size: int,
    *,
    source_model_key: str | None = None,
    target_model_key: str | None = None,
) -> Page[ModelMapping]:
    """Mappings in key order, of one source and one target model when given."""
    statement = select(ModelMapping)
    if source_model_key is not None:
        statement = statement.where(ModelMapping.source_model_key == source_model_key)
    if target_model_key is not None:
        statement = statement.where(ModelMapping.target_model_key == target_model_key)
    return paginate_statement(
        session,
        statement,
        keys=_KEYS,
        scope="model-mappings",
        filters={"sourceModelKey": source_model_key, "targetModelKey": target_model_key},
        page=page,
        page_size=page_size,
        message="Model mapping list cursor is invalid",
    )


def delete_mapping(session: Session, key: str, expected_version: int) -> None:
    """The mapping with its history and proposals (D112); commits."""
    mapping = load_mapping(session, key, for_update=True)
    if mapping.version != expected_version:
        raise history.conflict(session, mapping, expected_version, MAPPINGS)
    session.execute(delete(ModelMapping).where(ModelMapping.id == mapping.id))
    session.commit()


def apply_request(
    session: Session,
    key: str,
    expected_version: int,
    operations: list[dict[str, Any]],
    max_items: int,
) -> StepResult:
    return history.apply_request(session, key, expected_version, operations, max_items, MAPPINGS)


def undo(
    session: Session, key: str, expected_version: int, step: int | None, steps: list[int] | None
) -> StepResult:
    return history.undo(session, key, expected_version, step, steps, MAPPINGS)


def redo(session: Session, key: str, expected_version: int) -> StepResult:
    return history.redo(session, key, expected_version, MAPPINGS)
