"""A model's consumer API definitions in the engine's internal form, expanded once (Base 0.9 C18).

Every reader of a definition goes through :func:`consumer_apis` or :func:`consumer_api`: a schema 0.9
model's definitions are expanded from what the author wrote (``consumer_expansion``), a schema 0.8
model's are read as stored (``consumer_legacy``). Both give ``ConsumerApiDefinition``.
"""

from dataclasses import dataclass, field

from ...common.json_pointer import pointer_segment
from ...models.schema import ConsumerApiDefinition, ConsumerApiDocument, EngineModel
from .consumer_expansion import IDENTITY, PointerMap, expand


@dataclass(frozen=True)
class CompiledConsumerApis:
    definitions: tuple[ConsumerApiDefinition, ...]
    # Each definition's map from internal pointers to the authored ones, by key.
    pointers: dict[str, PointerMap] = field(default_factory=dict)


def compiled_consumer_apis(model: EngineModel) -> CompiledConsumerApis:
    """The model's definitions, expanded on first use and kept on the model. Raises
    ``ModelReferenceError`` at the authored pointer of a part the 0.9 syntax refuses; compilation asks
    first, so a model that compiled never does."""
    compiled = model._consumer_apis
    if compiled is None:
        definitions: list[ConsumerApiDefinition] = []
        pointers: dict[str, PointerMap] = {}
        for item in model.consumerApis or ():
            if isinstance(item, ConsumerApiDocument):
                definition, mapped = expand(model, item)
                pointers.setdefault(item.key, mapped)
            else:
                definition = item
            definitions.append(definition)
        compiled = CompiledConsumerApis(tuple(definitions), pointers)
        model._consumer_apis = compiled
    return compiled


def consumer_apis(model: EngineModel) -> tuple[ConsumerApiDefinition, ...]:
    return compiled_consumer_apis(model).definitions


def consumer_api(model: EngineModel, key: str) -> ConsumerApiDefinition | None:
    return next((item for item in consumer_apis(model) if item.key == key), None)


def authored_pointer(model: EngineModel, key: str, path: str) -> str:
    """``path`` within definition ``key`` (``/consumerApis/<key>…``) as the pointer of the node the
    author wrote: itself for a schema 0.8 definition."""
    prefix = f"/consumerApis/{pointer_segment(key)}"
    if path != prefix and not path.startswith(f"{prefix}/"):
        return path
    mapped = compiled_consumer_apis(model).pointers.get(key, IDENTITY)
    return prefix + mapped.authored(path.removeprefix(prefix))

