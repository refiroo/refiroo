import json
from pathlib import Path

from ...config import model_path
from ...models.schema import EngineModel
from .compiler import SCHEMA_VERSIONS, SUPPORTED_SCHEMA_VERSIONS, parse_model


def load_model(path: Path) -> EngineModel:
    """Load a model document from disk, rejecting one of a schema outside the window and one whose
    references do not resolve."""
    with path.open(encoding="utf-8") as model_file:
        source = json.load(model_file)
    schema = source.get("schemaVersion") if isinstance(source, dict) else None
    if schema is not None and schema not in SUPPORTED_SCHEMA_VERSIONS:
        raise RuntimeError(
            f"RDM_MODEL_PATH names {path}, a model of schema {schema}, but this version supports"
            f" schema {', '.join(SCHEMA_VERSIONS)}. Point RDM_MODEL_PATH at a model of a"
            " supported schema, such as model/rdm-starter.json, or run the RDM Engine version the"
            " model was written for, then start again. Releases already installed in the database"
            " are not affected."
        )
    return parse_model(source)


def load_bootstrap_model() -> EngineModel:
    return load_model(model_path())
