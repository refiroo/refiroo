"""Atomically transition an offline database from a selected schema 0.4 model to 0.5."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import update

from ..db import SessionLocal, create_database
from ..models.database import AuditEvent, ModelRelease, ModelRuntimeState
from ..services.model.compatibility import analyze_compatibility
from ..services.model.legacy import parse_schema_04_for_transition
from ..services.model.loader import load_model
from ..services.model.releases import ReleaseIdentityConflict, install_model_release
from ..services.model.runtime import require_runtime_state


def transition(model_path: Path) -> str:
    candidate = load_model(model_path)
    if candidate.schemaVersion != "0.5":
        raise RuntimeError("The transition candidate must use schema version 0.5")
    create_database()
    with SessionLocal() as session:
        runtime_state, active_release = require_runtime_state(session)
        active_model = parse_schema_04_for_transition(active_release.model_json)
        try:
            candidate_release, _created = install_model_release(session, candidate)
        except ReleaseIdentityConflict as exc:
            raise RuntimeError(
                f"Release '{exc.release_key}@{exc.release_version}' already has different content"
            ) from exc
        compatibility = analyze_compatibility(
            session, active_model, candidate, active_release.public_id
        )
        if compatibility.classification != "compatible":
            diagnostics = [asdict(item) for item in compatibility.diagnostics]
            raise RuntimeError(
                "Schema transition requires runtime-data migration: "
                + json.dumps(diagnostics, sort_keys=True)
            )
        result = session.execute(
            update(ModelRuntimeState)
            .where(
                ModelRuntimeState.id == runtime_state.id,
                ModelRuntimeState.version == runtime_state.version,
                ModelRuntimeState.active_model_release_id == active_release.id,
            )
            .values(
                active_model_release_id=candidate_release.id,
                version=runtime_state.version + 1,
            )
        )
        if result.rowcount != 1:
            raise RuntimeError("Model runtime state changed during the offline transition")
        session.execute(update(ModelRelease).values(is_active=False))
        session.execute(
            update(ModelRelease)
            .where(ModelRelease.id == candidate_release.id)
            .values(is_active=True)
        )
        session.add(
            AuditEvent(
                aggregate_type="model_runtime_state",
                aggregate_id=candidate_release.public_id,
                action="schema_upgraded",
                version=runtime_state.version + 1,
                changes={
                    "oldReleaseId": active_release.public_id,
                    "newReleaseId": candidate_release.public_id,
                    "oldSchemaVersion": active_release.schema_version,
                    "newSchemaVersion": candidate_release.schema_version,
                },
            )
        )
        session.commit()
        return candidate_release.public_id


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Atomically select a compatible schema 0.5 model in an offline database"
    )
    parser.add_argument("--model", required=True, type=Path)
    args = parser.parse_args()
    release_id = transition(args.model)
    print(f"Selected schema 0.5 model release {release_id}")


if __name__ == "__main__":
    main()
