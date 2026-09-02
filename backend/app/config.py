import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def model_path() -> Path:
    configured = os.getenv("RDM_MODEL_PATH")
    return Path(configured) if configured else PROJECT_ROOT / "model" / "rdm-starter.json"


def database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./rdm-engine.db")
