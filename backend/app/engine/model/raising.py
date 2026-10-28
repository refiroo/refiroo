"""Raising a stored model release of a schema older than the window to the window's schema.

Before 1.0 the schema window is cleaned at every release and the running engine does not carry old
schemas forward (0.12 L2a, D439). A release of a schema that left the window is rewritten in place:
its schema version, canonical document and hash change; its identity (id, key, version) does not, so
workspaces, change sets and publications that refer to it follow. A document of schema 0.8 or
earlier also has its ``consumerApis`` rewritten from the old internal shape to the present syntax.
A raised document that is not valid, or whose hash another release already has, is not written.
The offline command (``app.cli.model_release_raise``) and the API (0.12 UW1) share this module.
"""

import copy
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ...db import lock_installation
from ...errors import api_error
from ...models.database import AuditEvent, ModelRelease
from ...models.schema import ConsumerApiDefinition, EngineModel
from .compiler import SCHEMA_VERSIONS, compile_model
from .consumer_rendering import expanded_definition
from .workspace_models import workspaces_running

TARGET = SCHEMA_VERSIONS[-1]
# Documents of these schemas write ``consumerApis`` in the engine's internal shape.
LEGACY_SCHEMA_VERSIONS = frozenset({"0.5", "0.6", "0.7", "0.8"})

SchemaSide = Literal["inside", "left", "after", "unreadable"]


class _LegacyEngineModel(EngineModel):
    """A model document of schema 0.8 or earlier, read only to rewrite its consumer APIs."""

    schemaVersion: Literal["0.5", "0.6", "0.7", "0.8"]  # type: ignore[assignment]
    consumerApis: tuple[ConsumerApiDefinition, ...] | None = Field(  # type: ignore[assignment]
        default=None, exclude_if=lambda value: value is None
    )


def _version(text: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in text.split("."))
    except ValueError:
        return None


def schema_side(schema: str) -> SchemaSide:
    """Where a schema version lies against the window: in it, before it (it left), after it (a
    later engine's), or not a version at all."""
    if schema in SCHEMA_VERSIONS:
        return "inside"
    parts, window = _version(schema), _version(TARGET)
    if parts is None or window is None:
        return "unreadable"
    return "after" if parts > window else "left"


@dataclass
class Outcome:
    release: ModelRelease
    old_schema: str
    new_json: dict[str, Any] | None = None
    new_hash: str | None = None
    # How many consumer API definitions were rewritten from the old internal shape.
    rewritten: int = 0
    skipped: str | None = None
    # With ``skipped``: the diagnostics of an invalid raised document, or the release it equals.
    diagnostics: tuple[dict[str, Any], ...] = ()
    collides_with: ModelRelease | None = None


def _raised(document: dict[str, Any]) -> tuple[dict[str, Any], int]:
    """The document in the window's schema, and how many consumer API definitions were rewritten."""
    raised = copy.deepcopy(document)
    rewritten = 0
    if raised.get("schemaVersion") in LEGACY_SCHEMA_VERSIONS and raised.get("consumerApis"):
        legacy = _LegacyEngineModel.model_validate(raised)
        raised["consumerApis"] = [
            expanded_definition(legacy, definition) for definition in legacy.consumerApis or ()
        ]
        rewritten = len(raised["consumerApis"])
    raised["schemaVersion"] = TARGET
    return raised, rewritten


def hashes_taken(session: Session) -> dict[str, ModelRelease]:
    """Every stored release by its hash."""
    return {
        release.model_hash: release
        for release in session.scalars(select(ModelRelease).order_by(ModelRelease.id))
    }


def plan_release(release: ModelRelease, taken: dict[str, ModelRelease]) -> Outcome:
    """What raising ``release`` comes to. ``taken`` holds the stored releases by hash; a release that
    can be raised moves its entry to the new hash, so the next one is checked against it."""
    schema = release.schema_version
    outcome = Outcome(release, schema)
    if _version(schema) is None:
        outcome.skipped = f"schema '{schema}' is not a version"
        return outcome
    try:
        document, outcome.rewritten = _raised(release.model_json)
        compiled = compile_model(document)
    except ValueError as exc:
        outcome.skipped = f"cannot be read: {exc}"
        return outcome
    if not compiled.valid:
        outcome.skipped = (
            "not valid in schema "
            + TARGET
            + ": "
            + "; ".join(f"{item.code} {item.path} {item.message}" for item in compiled.diagnostics)
        )
        outcome.diagnostics = tuple(item.__dict__ for item in compiled.diagnostics)
        return outcome
    other = taken.get(compiled.model_hash)
    if other is not None and other.id != release.id:
        outcome.skipped = (
            f"raised, it equals release {other.id} "
            f"({other.release_key}@{other.release_version}); not merged"
        )
        outcome.collides_with = other
        return outcome
    taken.pop(release.model_hash, None)
    taken[compiled.model_hash] = release
    outcome.new_json, outcome.new_hash = compiled.canonical_model, compiled.model_hash
    return outcome


def plan_one(session: Session, release: ModelRelease) -> Outcome:
    """What raising this one release comes to, against every stored release."""
    return plan_release(release, hashes_taken(session))


def apply_raising(outcome: Outcome) -> None:
    """Write a planned raising into its release (the caller commits)."""
    if outcome.new_json is None or outcome.new_hash is None:
        raise ValueError("a raising that was skipped cannot be applied")
    release = outcome.release
    release.schema_version = TARGET
    release.model_json = outcome.new_json
    release.model_hash = outcome.new_hash


@dataclass(frozen=True)
class Raising:
    """What raising one release came to (0.12 UW1): ``applied`` when it was written, otherwise the
    preview. ``model_hash`` is the release's hash now."""

    applied: bool
    release: ModelRelease
    schema_from: str
    schema_to: str
    rewritten: int
    model_hash: str
    workspaces: list[str]


def raise_release(
    session: Session, release_id: str, *, confirm: bool, expected_model_hash: str | None
) -> Raising:
    """Preview, or with ``confirm`` apply, raising one release (the caller commits).

    ``404 MODEL_RELEASE_NOT_FOUND``; ``422 RELEASE_NOT_RAISABLE`` for a schema in the window or
    after it; ``422 RELEASE_RAISE_REFUSED`` when the raised document is invalid or equals another
    release; ``409 MODEL_HASH_CHANGED`` when the release is no longer the one that was previewed.
    No process parses anything again: the registry keys what it parsed by the release's hash and
    reads its schema from the row on every request, so each serves the workspaces again from its
    next one. A process that started with no servable workspace is told once the caller has
    committed (``model_registry.refresh_servable``); the others find out at their next heartbeat or
    health probe, and then start the background threads that need a servable model (0.12 R, R-F9).
    """
    if confirm:
        lock_installation(session)
    release = session.scalar(
        select(ModelRelease).where(ModelRelease.public_id == release_id).with_for_update()
        if confirm
        else select(ModelRelease).where(ModelRelease.public_id == release_id)
    )
    if release is None:
        raise api_error(404, "MODEL_RELEASE_NOT_FOUND", f"Model release '{release_id}' not found")
    if confirm and release.model_hash != expected_model_hash:
        raise api_error(
            409,
            "MODEL_HASH_CHANGED",
            f"Release '{release_id}' changed after the preview you reviewed; nothing was raised. "
            "Preview the raising again",
            {
                "releaseId": release_id,
                "expectedModelHash": expected_model_hash,
                "currentModelHash": release.model_hash,
            },
        )
    schema = release.schema_version
    if schema_side(schema) in ("inside", "after"):
        raise api_error(
            422,
            "RELEASE_NOT_RAISABLE",
            f"Release '{release_id}' is of schema {schema}, "
            + (
                "which this version reads as it is"
                if schema_side(schema) == "inside"
                else "later than this version reads, and cannot be raised"
            ),
            {"schemaVersion": schema, "supportedSchemaVersions": list(SCHEMA_VERSIONS)},
        )
    outcome = plan_one(session, release)
    if outcome.skipped is not None:
        details: dict[str, Any] = {"releaseId": release_id, "reason": outcome.skipped}
        if outcome.diagnostics:
            details["diagnostics"] = list(outcome.diagnostics)
        if outcome.collides_with is not None:
            details["collidesWith"] = outcome.collides_with.public_id
        raise api_error(
            422,
            "RELEASE_RAISE_REFUSED",
            f"Release '{release_id}' cannot be raised to schema {TARGET}: {outcome.skipped}",
            details,
        )
    workspaces = workspaces_running(session, release.id)
    old_hash = release.model_hash
    if confirm:
        apply_raising(outcome)
        session.add(
            AuditEvent(
                aggregate_type="model_release",
                aggregate_id=release.public_id,
                action="schema_raised",
                version=1,
                changes={
                    "releaseKey": release.release_key,
                    "releaseVersion": release.release_version,
                    "oldSchemaVersion": schema,
                    "newSchemaVersion": TARGET,
                    "oldModelHash": old_hash,
                    "newModelHash": release.model_hash,
                    "consumerApisRewritten": outcome.rewritten,
                    "workspaces": workspaces,
                },
            )
        )
    return Raising(
        confirm, release, schema, TARGET, outcome.rewritten, release.model_hash, workspaces
    )
