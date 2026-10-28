"""Whether this version can serve the model release a workspace runs (0.12 UW1)."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.orm import Session

from ...models.database import ModelRelease
from .raising import hashes_taken, plan_release, schema_side
from .registry import model_registry

Reason = Literal["schemaLeftWindow", "schemaAfterWindow", "invalidRelease"]


@dataclass(frozen=True)
class Unavailable:
    reason: Reason
    release_id: str
    schema_version: str
    # Raising the release would give a valid document that equals no other release.
    raisable: bool


def unavailability(session: Session, releases: Iterable[ModelRelease]) -> dict[int, Unavailable]:
    """The releases (by database id) the registry cannot serve, read once for a page of workspaces;
    a release it can serve is left out. Nothing is raised."""
    found: dict[int, Unavailable] = {}
    # Every stored release by hash, read once for the page: planning a raising checks the raised
    # document against it, and each plan works on its own copy (0.12 R).
    taken: dict[str, ModelRelease] | None = None
    for release in releases:
        if release.id in found or model_registry.unavailability(release) is None:
            continue
        side = schema_side(release.schema_version)
        reason: Reason = (
            "schemaAfterWindow"
            if side == "after"
            else "schemaLeftWindow"
            if side in ("left", "unreadable")
            else "invalidRelease"
        )
        raisable = False
        if reason == "schemaLeftWindow":
            if taken is None:
                taken = hashes_taken(session)
            raisable = plan_release(release, dict(taken)).skipped is None
        found[release.id] = Unavailable(
            reason, release.public_id, release.schema_version, raisable=raisable
        )
    return found
