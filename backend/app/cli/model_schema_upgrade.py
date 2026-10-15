"""Atomically transition an offline database from a selected schema 0.4 model to a supported schema.

The workspaces running the default workspace's release, which must be of schema 0.4, move to the
candidate together (0.11 M1); a workspace on another release is left as it is.
"""

import argparse
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import update

from ..db import SessionLocal, create_database
from ..engine.model.compatibility import analyze_compatibility
from ..engine.model.compiler import SCHEMA_VERSIONS, SUPPORTED_SCHEMA_VERSIONS
from ..engine.model.diagnostics import ModelValidationError
from ..engine.model.legacy import parse_schema_04_for_transition
from ..engine.model.loader import load_model
from ..engine.model.releases import ReleaseIdentityConflict, install_model_release
from ..engine.model.workspace_models import default_assignment, workspaces_running
from ..models.database import AuditEvent, WorkspaceModel


def transition(model_path: Path) -> str:
    candidate = load_model(model_path)
    if candidate.schemaVersion not in SUPPORTED_SCHEMA_VERSIONS:
        raise RuntimeError(
            "The transition candidate must use schema version "
            + ", ".join(SCHEMA_VERSIONS)
        )
    create_database()
    with SessionLocal() as session:
        _assignment, active_release = default_assignment(session)
        if active_release.schema_version != "0.4":
            raise RuntimeError(
                "The offline schema transition requires a selected schema 0.4 release; "
                f"found schema {active_release.schema_version}"
            )
        active_model = parse_schema_04_for_transition(active_release.model_json)
        try:
            candidate_release, _created = install_model_release(session, candidate)
        except ReleaseIdentityConflict as exc:
            raise RuntimeError(
                f"Release '{exc.release_key}@{exc.release_version}' already has different content"
            ) from exc
        workspaces = workspaces_running(session, active_release.id)
        compatibility = analyze_compatibility(
            session, active_model, candidate, active_release.public_id, workspaces
        )
        if compatibility.classification != "compatible":
            diagnostics = [asdict(item) for item in compatibility.diagnostics]
            raise RuntimeError(
                "Schema transition requires runtime-data migration: "
                + json.dumps(diagnostics, sort_keys=True)
            )
        result = session.execute(
            update(WorkspaceModel)
            .where(
                WorkspaceModel.workspace_key.in_(workspaces),
                WorkspaceModel.model_release_id == active_release.id,
            )
            .values(
                model_release_id=candidate_release.id,
                version=WorkspaceModel.version + 1,
                updated_at=datetime.now(UTC),
            )
        )
        if result.rowcount != len(workspaces):
            raise RuntimeError("A workspace's model changed during the offline transition")
        for workspace_key in workspaces:
            session.add(
                AuditEvent(
                    aggregate_type="workspace_model",
                    aggregate_id=candidate_release.public_id,
                    action="schema_upgraded",
                    version=session.get(WorkspaceModel, workspace_key).version,
                    changes={
                        "workspaceKey": workspace_key,
                        "oldReleaseId": active_release.public_id,
                        "newReleaseId": candidate_release.public_id,
                        "oldSchemaVersion": active_release.schema_version,
                        "newSchemaVersion": candidate_release.schema_version,
                    },
                )
            )
        session.commit()
        return candidate_release.public_id


_SCHEMAS = ", ".join(SCHEMA_VERSIONS)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            f"Atomically select a compatible schema {_SCHEMAS} model in an offline database"
        )
    )
    parser.add_argument(
        "--model",
        required=True,
        type=Path,
        help=f"Path to the schema {_SCHEMAS} model JSON to validate, install and select",
    )
    args = parser.parse_args()
    try:
        release_id = transition(args.model)
    except (RuntimeError, ModelValidationError, OSError) as exc:
        print(
            f"Schema transition refused: {exc}. The selected release is unchanged. "
            "Correct the candidate or resolve the reported incompatibility, then retry "
            "with traffic stopped. Restart the API only after the transition succeeds.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    print(f"Selected supported model release {release_id}")


if __name__ == "__main__":
    main()
