import json
from functools import lru_cache
from pathlib import Path

from .config import model_path
from .model_schema import EngineModel


def load_model(path: Path) -> EngineModel:
    with path.open(encoding="utf-8") as model_file:
        return EngineModel.model_validate(json.load(model_file))


@lru_cache(maxsize=1)
def current_model() -> EngineModel:
    return load_model(model_path())
