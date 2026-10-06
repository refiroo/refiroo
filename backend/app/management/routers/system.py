"""``GET /api/v1/system`` (0.9 U3): what the deployment runs and how it is configured. Read-only and
behind no capability, like ``/capabilities``; for administrators once roles exist (0.12)."""

from dataclasses import asdict

from fastapi import APIRouter, Request

from ...common.time import as_utc
from ...config import ENGINE_VERSION
from ...engine.model.compiler import SUPPORTED_SCHEMA_VERSIONS
from ...engine.reads.system import read_system_state
from ..dependencies import DbSession
from ..schemas.system import (
    ActiveModelRelease,
    DatabaseInfo,
    EngineInfo,
    SystemResponse,
    SystemSetting,
)

router = APIRouter(prefix="/api/v1", tags=["system"])


@router.get("/system", response_model=SystemResponse)
def get_system(request: Request, session: DbSession) -> SystemResponse:
    state = read_system_state(session)
    release = state.active_release
    return SystemResponse(
        engine=EngineInfo(version=ENGINE_VERSION, managementApi="v1"),
        schemaLanguages=sorted(SUPPORTED_SCHEMA_VERSIONS),
        activeModelRelease=ActiveModelRelease(
            id=release.public_id,
            key=release.release_key,
            name=release.release_name,
            version=release.release_version,
            schemaVersion=release.schema_version,
            activatedAt=as_utc(state.activated_at),
        ),
        database=DatabaseInfo(revision=state.revision),
        settings=[
            SystemSetting(**asdict(setting)) for setting in request.app.state.settings_report
        ],
    )
