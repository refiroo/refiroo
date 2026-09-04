import json
from pathlib import Path

from ..config import model_path
from ..models.schema import EngineModel


def load_model(path: Path) -> EngineModel:
    with path.open(encoding="utf-8") as model_file:
        return EngineModel.model_validate(json.load(model_file))


def load_bootstrap_model() -> EngineModel:
    return load_model(model_path())
