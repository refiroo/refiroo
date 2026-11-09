"""A model's consumer API definitions in the engine's internal form, expanded once (Base 0.9 C18).

Every reader of a definition goes through :func:`consumer_apis` or :func:`consumer_api`: the
definitions are expanded from what the author wrote (``consumer_expansion``) into
``ConsumerApiDefinition``.
"""

from dataclasses import dataclass, field

from ...common.json_pointer import pointer_segment
from ...models.schema import ConsumerApiDefinition, EngineModel
from .consumer_expansion import IDENTITY, PointerMap, expand


@dataclass(frozen=True)
class ServedVersion:
    """A contract version a consumer API serves: the current one, or an earlier one the model keeps
    (0.13 DF3). ``index`` is the earlier version's place in ``earlierVersions``; the current one has
    none."""

    definition: ConsumerApiDefinition
    index: int | None = None
    deprecated: str | None = None
    sunset: str | None = None

    @property
    def is_current(self) -> bool:
        return self.index is None

    @property
    def base(self) -> str:
        """The pointer of the node the author wrote."""
        root = f"/consumerApis/{pointer_segment(self.definition.key)}"
        return root if self.index is None else f"{root}/earlierVersions/{self.index}"


@dataclass(frozen=True)
class CompiledConsumerApis:
    definitions: tuple[ConsumerApiDefinition, ...]
    # Each definition's map from internal pointers to the authored ones, by key.
    pointers: dict[str, PointerMap] = field(default_factory=dict)
    # The earlier versions each definition keeps, by key, newest first, with their pointer maps.
    earlier: dict[str, tuple[ServedVersion, ...]] = field(default_factory=dict)
    earlier_pointers: dict[tuple[str, int], PointerMap] = field(default_factory=dict)


def compiled_consumer_apis(model: EngineModel) -> CompiledConsumerApis:
    """The model's definitions, expanded on first use and kept on the model. Raises
    ``ModelReferenceError`` at the authored pointer of a part the 0.9 syntax refuses; compilation asks
    first, so a model that compiled never does."""
    compiled = model._consumer_apis
    if compiled is None:
        definitions: list[ConsumerApiDefinition] = []
        pointers: dict[str, PointerMap] = {}
        earlier: dict[str, tuple[ServedVersion, ...]] = {}
        earlier_pointers: dict[tuple[str, int], PointerMap] = {}
        for item in model.consumerApis or ():
            definition, mapped = expand(model, item)
            pointers.setdefault(item.key, mapped)
            definitions.append(definition)
            kept: list[ServedVersion] = []
            for index, version in enumerate(item.earlierVersions):
                # A frozen copy is a definition of its own: the API's key and name, its body.
                copy = item.model_copy(
                    update={
                        "contractVersion": version.contractVersion,
                        "description": version.description,
                        "exposes": version.exposes,
                        "publicNames": version.publicNames,
                        "object": version.object,
                        "operations": version.operations,
                        "filters": version.filters,
                        "earlierVersions": (),
                    }
                )
                base = f"/consumerApis/{pointer_segment(item.key)}/earlierVersions/{index}"
                old, old_mapped = expand(model, copy, base)
                earlier_pointers.setdefault((item.key, index), old_mapped)
                kept.append(ServedVersion(old, index, version.deprecated, version.sunset))
            if kept:
                earlier.setdefault(item.key, tuple(kept))
        compiled = CompiledConsumerApis(tuple(definitions), pointers, earlier, earlier_pointers)
        model._consumer_apis = compiled
    return compiled


def consumer_apis(model: EngineModel) -> tuple[ConsumerApiDefinition, ...]:
    return compiled_consumer_apis(model).definitions


def consumer_api(model: EngineModel, key: str) -> ConsumerApiDefinition | None:
    return next((item for item in consumer_apis(model) if item.key == key), None)


def served_versions(model: EngineModel, key: str) -> tuple[ServedVersion, ...]:
    """Every contract version of API ``key`` the model serves, the current one first and then the
    kept ones, newest first; empty when the model declares no such API (0.13 DF3)."""
    current = consumer_api(model, key)
    if current is None:
        return ()
    return (ServedVersion(current), *compiled_consumer_apis(model).earlier.get(key, ()))


def served_version(model: EngineModel, key: str, contract_version: int) -> ServedVersion | None:
    """The version of API ``key`` the model serves at ``contract_version``, if it serves it."""
    return next(
        (
            item
            for item in served_versions(model, key)
            if item.definition.contractVersion == contract_version
        ),
        None,
    )


def authored_pointer(model: EngineModel, key: str, path: str, earlier: int | None = None) -> str:
    """``path`` within definition ``key`` (``/consumerApis/<key>…``) as the pointer of the node the
    author wrote. For the kept earlier version ``earlier`` (DF3), ``path`` starts at
    ``/consumerApis/<key>/earlierVersions/<earlier>``."""
    prefix = f"/consumerApis/{pointer_segment(key)}"
    if earlier is not None:
        prefix = f"{prefix}/earlierVersions/{earlier}"
    if path != prefix and not path.startswith(f"{prefix}/"):
        return path
    compiled = compiled_consumer_apis(model)
    mapped = (
        compiled.pointers.get(key, IDENTITY)
        if earlier is None
        else compiled.earlier_pointers.get((key, earlier), IDENTITY)
    )
    return prefix + mapped.authored(path.removeprefix(prefix))


def kept_store_key(definition: ConsumerApiDefinition) -> str:
    """What an earlier version's derived events are stored under as ``consumer_api`` (DF3); no model key
    can hold the ``@``."""
    return f"{definition.key}@v{definition.contractVersion}"
