import json
from pathlib import Path

from ...config import model_path
from ...models.schema import EngineModel
from .compiler import parse_model


def load_model(path: Path) -> EngineModel:
    """Load a model document from disk, rejecting one whose references do not resolve."""
    with path.open(encoding="utf-8") as model_file:
        return parse_model(json.load(model_file))


def load_bootstrap_model() -> EngineModel:
    return load_model(model_path())
