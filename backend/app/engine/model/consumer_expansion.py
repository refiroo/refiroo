"""A schema 0.9 consumer API definition expanded into the engine's internal form (Base 0.9 C18).

The internal form is ``ConsumerApiDefinition``, which every reader works on. Expanding writes out
every default (C-D136): public names in PascalCase, the per-type events, ``matchOn`` of ``under`` and
``linkedTo`` filters, a list's ``within.types``, ``code`` as one rule per source of the ``code``
field (C-D135). The checks of the syntax itself are made here, at the author's pointers; the
reference rules then run on the expanded form, and :class:`PointerMap` takes each of their pointers
back to the node the author wrote (C-D141).
"""

import re
from collections.abc import Sequence
from typing import Any, NoReturn

from pydantic import ValidationError

from ...common.json_pointer import pointer_segment as seg
from ...models.schema import (
    ConsumerApiDefinition,
    ConsumerApiDocument,
    EngineModel,
    FieldSpec,
    FilterSpec,
    FrozenDict,
    ParentSpec,
    freeze_model_graph,
)
from .diagnostics import ModelReferenceError

PER_TYPE_CHANGES = ("created", "updated", "deleted")
FILTER_VERBS = ("byType", "under", "linkedTo", "onRelated")
# A ``linkedTo`` filter's routes, and the internal names they stand for.
THROUGH_ITSELF = "itself"
THROUGH_SHARED = "sharedWith:"
VIA_SELF = "self"
VIA_SHARED = "sharedProjection:"
# What each verb may be given beside it.
_VERB_PARTS = {
    "byType": frozenset({"description"}),
    "under": frozenset({"matchOn", "description"}),
    "linkedTo": frozenset({"through", "matchOn", "description"}),
    "onRelated": frozenset({"matchOn", "keepOnlyMatching", "scoreOnlyMatching", "crosswalk", "description"}),
}


def public_name(type_key: str) -> str:
    """The default public name of a type: its key in PascalCase (``timetable-type`` →
    ``TimetableType``)."""
    return "".join(part[:1].upper() + part[1:] for part in re.split(r"[^0-9A-Za-z]+", type_key) if part)


class PointerMap:
    """Internal pointers within a definition to the authored ones. A pointer below a mapped one keeps
    its rest unless the mapped node absorbs it (a node the author wrote in one piece)."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[str, bool]] = {}

    def add(self, internal: str, authored: str, *, absorb: bool = False) -> None:
        self._entries[internal] = (authored, absorb)

    def authored(self, path: str) -> str:
        parts = path.split("/")
        for length in range(len(parts), 0, -1):
            found = self._entries.get("/".join(parts[:length]))
            if found is not None:
                authored, absorb = found
                rest = "/".join(parts[length:])
                return authored if absorb or not rest else f"{authored}/{rest}"
        return path


IDENTITY = PointerMap()


def expand(model: EngineModel, document: ConsumerApiDocument) -> tuple[ConsumerApiDefinition, PointerMap]:
    """The internal form of ``document`` and the map of its pointers, or a refusal at the authored
    pointer of a part the syntax does not allow."""
    return _Expansion(model, document).run()


class _Expansion:
    def __init__(self, model: EngineModel, document: ConsumerApiDocument) -> None:
        self.model = model
        self.document = document
        self.base = f"/consumerApis/{seg(document.key)}"
        self.pointers = PointerMap()
        self.descriptions: dict[str, str] = {}
        # Each role's output name, and the sources of the ``code`` role.
        self.roles: dict[str, str] = {}
        self.code_sources: tuple[str, ...] = ()

    def fail(self, path: str, message: str, code: str = "INVALID_MODEL") -> NoReturn:
        raise ModelReferenceError(code, f"{self.base}{path}", f"Consumer API '{self.document.key}': {message}")

    def describe(self, part: str, description: str | None) -> None:
        if description:
            self.descriptions[part] = description

    def run(self) -> tuple[ConsumerApiDefinition, PointerMap]:
        document = self.document
        operations = document.operations
        source: dict[str, Any] = {
            "key": document.key,
            "name": document.name,
            "contractVersion": document.contractVersion,
            "objectTypes": self._types(),
            "object": self._object(),
            "projections": self._related(),
            "parameters": self._filters(),
            "lists": self._lists(),
            "events": self._events(),
        }
        if document.description is not None:
            source["description"] = document.description
        match = self._match()
        if match is not None:
            source["match"] = match
        offered = {name for name in ("objects", "xref", "resolve", "lists", "events") if getattr(operations, name) is not None}
        if operations.resolve is not None and (operations.objects is None or operations.xref is None):
            self.fail("/operations/resolve", "batch resolve answers as get by ID and XREF do, so it needs 'objects' and 'xref'")
        for name in offered - {"lists"}:
            self.describe(f"operation:{name}", getattr(operations, name).description)
        try:
            definition = ConsumerApiDefinition.model_validate(source)
        except ValidationError as exc:
            error = exc.errors()[0]
            internal = "".join(f"/{seg(item)}" for item in error["loc"])
            self.fail(self.pointers.authored(internal), str(error["msg"]))
        freeze_model_graph(definition)
        definition._operations = frozenset(offered - {"lists", "events"})
        definition._descriptions = FrozenDict(self.descriptions)
        return definition, self.pointers

    # --- what is exposed --------------------------------------------------------------------------

    def _types(self) -> dict[str, Any]:
        document = self.document
        types: dict[str, Any] = {}
        self.pointers.add("/objectTypes", "/exposes", absorb=True)
        for index, key in enumerate(document.exposes):
            if key in types:
                self.fail(f"/exposes/{index}", f"exposes '{key}' twice", "DUPLICATE_KEY")
            types[key] = {"publicName": document.publicNames.get(key) or public_name(key)}
            self.pointers.add(f"/objectTypes/{seg(key)}", f"/exposes/{index}", absorb=True)
            if key in document.publicNames:
                self.pointers.add(f"/objectTypes/{seg(key)}/publicName", f"/publicNames/{seg(key)}", absorb=True)
        for key in document.publicNames:
            if key not in types:
                self.fail(f"/publicNames/{seg(key)}", f"names type '{key}', which is not exposed", "INVALID_REFERENCE")
        return types

    # --- the object -------------------------------------------------------------------------------

    def _object(self) -> dict[str, Any]:
        shape = self.document.object
        result: dict[str, Any] = {}
        attributes: dict[str, Any] = {}
        for output, spec in shape.fields.items():
            path = f"/object/fields/{seg(output)}"
            role, sources, default, from_path = self._field(output, spec, path)
            if role is None:
                internal = f"/object/attributes/{seg(output)}"
                entry: dict[str, Any] = {"source": sources}
                attributes[output] = entry
            else:
                if role in self.roles:
                    self.fail(f"{path}/role", f"role '{role}' is given to '{self.roles[role]}' too", "DUPLICATE_KEY")
                self.roles[role] = output
                internal = f"/object/{role}"
                entry = {"output": output, "source": sources}
                result[role] = entry
                if role == "code":
                    self.code_sources = sources
            if default is not None:
                entry["default"] = default
            self.pointers.add(internal, path, absorb=True)
            self.pointers.add(f"{internal}/default", f"{path}/default" if isinstance(spec, FieldSpec) else path, absorb=True)
            self.pointers.add(f"{internal}/source", from_path(None), absorb=True)
            for index in range(len(sources)):
                self.pointers.add(f"{internal}/source/{index}", from_path(index), absorb=True)
        if "id" not in self.roles:
            self.fail("/object/fields", "a field with role 'id' is needed: the object ID consumers read it by")
        # Role fields may stand anywhere in ``fields``: the internal form keeps them by role, so they
        # are output first, in role order, and written order orders the other fields (C-D140).
        result["attributes"] = attributes
        if isinstance(shape.parent, ParentSpec):
            result["parent"] = {"output": shape.parent.output, "fields": list(shape.parent.fields)}
        elif shape.parent is not None:
            result["parent"] = {"output": "parent", "fields": list(shape.parent)}
            self.pointers.add("/object/parent", "/object/parent", absorb=True)
        for part in ("path", "hierarchy"):
            value = getattr(shape, part)
            if value is True:
                result[part] = part
            elif isinstance(value, str):
                result[part] = value
        return result

    def _field(self, output: str, spec: Any, path: str) -> tuple[str | None, tuple[str, ...], Any, Any]:
        """A field's role, sources, default and the authored pointer of its sources."""
        if isinstance(spec, str):
            return None, (spec,), None, lambda _index: path
        if isinstance(spec, tuple):
            if not spec:
                self.fail(path, f"field '{output}' names no source")
            return None, spec, None, lambda index: path if index is None else f"{path}/{index}"
        self.describe(f"field:{output}", spec.description)
        sources = spec.from_
        if sources is None:
            if spec.role != "id":
                self.fail(path, f"field '{output}' needs 'from', the sources it reads")
            return spec.role, ("id",), spec.default, lambda _index: path
        if isinstance(sources, str):
            return spec.role, (sources,), spec.default, lambda _index: f"{path}/from"
        if not sources:
            self.fail(f"{path}/from", f"field '{output}' names no source")
        return spec.role, sources, spec.default, lambda index: f"{path}/from" if index is None else f"{path}/from/{index}"

    def _related(self) -> dict[str, Any]:
        projections: dict[str, Any] = {}
        for name, spec in self.document.object.related.items():
            path = f"/object/related/{seg(name)}"
            route = self._route(spec.via)
            if route is None:
                self.fail(
                    f"{path}/via",
                    f"'{spec.via}' is neither a relation type's key (outgoing) nor its reverseKey (incoming)",
                    "INVALID_REFERENCE",
                )
            projections[name] = {"from": route, "fields": dict(spec.fields)}
            internal = f"/projections/{seg(name)}"
            self.pointers.add(internal, f"/object/related/{seg(name)}")
            self.pointers.add(f"{internal}/from", f"{path}/via", absorb=True)
            self.describe(f"related:{name}", spec.description)
        self.pointers.add("/projections", "/object/related", absorb=True)
        return projections

    def _route(self, via: str) -> dict[str, str] | None:
        """A relation's ``key`` is the outgoing route and its ``reverseKey`` the incoming one; the two
        share one namespace (``DUPLICATE_KEY``), so ``via`` names one route at most."""
        for relation in self.model.relationTypes:
            if relation.key == via:
                return {"relation": relation.key, "direction": "outgoing"}
            if relation.reverseKey == via:
                return {"relation": relation.key, "direction": "incoming"}
        return None

    # --- how it is found --------------------------------------------------------------------------

    def _match(self) -> dict[str, Any] | None:
        xref = self.document.operations.xref
        if xref is None or (xref.matchOn is None and not xref.alsoMatchThrough):
            return None
        own: list[dict[str, Any]] = []
        for index, rule in enumerate(xref.matchOn or ()):
            path = f"/operations/xref/matchOn/{index}"
            weights = rule.model_dump(mode="json", exclude={"field"})
            if rule.field == "code":
                for source in self._code(f"{path}/field"):
                    self.pointers.add(f"/match/own/{len(own)}", path)
                    own.append({"field": source, **weights})
            else:
                self.pointers.add(f"/match/own/{len(own)}", path)
                own.append(rule.model_dump(mode="json"))
        promoted = []
        for index, item in enumerate(xref.alsoMatchThrough):
            internal, path = f"/match/promoted/{index}", f"/operations/xref/alsoMatchThrough/{index}"
            self.pointers.add(internal, path)
            self.pointers.add(f"{internal}/projection", f"{path}/related", absorb=True)
            self.pointers.add(f"{internal}/firstMatch", f"{path}/firstOf")
            self.pointers.add(f"{internal}/preferTargetTypes", f"{path}/preferTypes")
            promoted.append(
                {
                    "projection": item.related,
                    "firstMatch": [rule.model_dump(mode="json") for rule in item.firstOf],
                    "preferTargetTypes": list(item.preferTypes),
                }
            )
        self.pointers.add("/match", "/operations/xref", absorb=True)
        self.pointers.add("/match/own", "/operations/xref/matchOn")
        self.pointers.add("/match/promoted", "/operations/xref/alsoMatchThrough")
        return {"own": own, "promoted": promoted}

    def _code(self, path: str) -> tuple[str, ...]:
        if "code" not in self.roles:
            self.fail(path, "'code' stands for the sources of the field with role 'code', and no field has that role")
        return self.code_sources

    # --- how it is filtered -----------------------------------------------------------------------

    def _filters(self) -> dict[str, Any]:
        parameters: dict[str, Any] = {}
        for name, spec in self.document.filters.items():
            path = f"/filters/{seg(name)}"
            internal = f"/parameters/{seg(name)}"
            verbs = [verb for verb in FILTER_VERBS if getattr(spec, verb) not in (None, False)]
            if len(verbs) != 1:
                given = f"; it has {', '.join(verbs)}" if verbs else ""
                self.fail(path, f"filter '{name}' needs exactly one of {', '.join(FILTER_VERBS)}{given}")
            verb = verbs[0]
            for part in sorted(spec.model_fields_set - _VERB_PARTS[verb] - {verb}):
                self.fail(f"{path}/{part}", f"'{part}' does not apply to a '{verb}' filter")
            self.pointers.add(internal, path, absorb=True)
            self.describe(f"filter:{name}", spec.description)
            parameters[name] = self._filter(spec, verb, path, internal)
        self.pointers.add("/parameters", "/filters", absorb=True)
        return parameters

    def _filter(self, spec: FilterSpec, verb: str, path: str, internal: str) -> dict[str, Any]:
        if verb == "byType":
            return {"kind": "objectType"}
        if verb == "onRelated":
            if spec.matchOn is None:
                self.fail(path, "an 'onRelated' filter needs 'matchOn': the fields of the related records it matches")
            self.pointers.add(f"{internal}/projection", f"{path}/onRelated", absorb=True)
            self.pointers.add(f"{internal}/matchFields", f"{path}/matchOn")
            self.pointers.add(f"{internal}/requireMatch", f"{path}/keepOnlyMatching", absorb=True)
            self.pointers.add(f"{internal}/scoresFrom", f"{path}/scoreOnlyMatching", absorb=True)
            self.pointers.add(f"{internal}/targetable", f"{path}/crosswalk", absorb=True)
            return {
                "kind": "projection",
                "projection": spec.onRelated,
                "matchFields": list(spec.matchOn),
                "requireMatch": spec.keepOnlyMatching,
                "scoresFrom": spec.scoreOnlyMatching,
                "targetable": spec.crosswalk,
            }
        types: tuple[str, ...] = getattr(spec, verb)
        self.pointers.add(f"{internal}/objectTypes", f"{path}/{verb}")
        result: dict[str, Any] = {
            "kind": "ancestor" if verb == "under" else "related",
            "objectTypes": list(types),
            "matchFields": self._filter_match(spec.matchOn, types, path, internal),
        }
        if verb == "linkedTo":
            if not spec.through:
                self.fail(path, "a 'linkedTo' filter needs 'through': itself, a related name or sharedWith:<related>")
            result["via"] = [_via(item) for item in spec.through]
            self.pointers.add(f"{internal}/via", f"{path}/through")
        return result

    def _filter_match(
        self, match_on: Sequence[str] | None, types: Sequence[str], path: str, internal: str
    ) -> list[str]:
        """``matchOn`` with ``code`` as the code sources the filter's types bind (C-D135); by default
        ``id``, those sources and ``name`` (C-D136)."""
        bound = [source for source in self.code_sources if self._bound(types, source)]
        if match_on is None:
            self.pointers.add(f"{internal}/matchFields", path, absorb=True)
            return ["id", *bound, "name"]
        fields: list[str] = []
        for index, field in enumerate(match_on):
            expanded = bound if field == "code" else [field]
            if field == "code":
                self._code(f"{path}/matchOn/{index}")
            for item in expanded:
                self.pointers.add(f"{internal}/matchFields/{len(fields)}", f"{path}/matchOn/{index}", absorb=True)
                fields.append(item)
        if not fields:
            self.fail(f"{path}/matchOn", "the filter's types bind none of the code field's sources, so it matches nothing")
        return fields

    def _bound(self, types: Sequence[str], attribute: str) -> bool:
        return any(
            binding.attributeTypeKey == attribute
            for key in types
            if (item := self.model.object_type(key)) is not None
            for binding in item.attributes
        )

    # --- lists and events -------------------------------------------------------------------------

    def _lists(self) -> list[dict[str, Any]]:
        lists: list[dict[str, Any]] = []
        self.pointers.add("/lists", "/operations/lists", absorb=True)
        for key, spec in (self.document.operations.lists or {}).items():
            path = f"/operations/lists/{seg(key)}"
            internal = f"/lists/{seg(key)}"
            self.pointers.add(internal, path)
            self.pointers.add(f"{internal}/key", path, absorb=True)
            self.pointers.add(f"{internal}/objectType", f"{path}/of", absorb=True)
            self.describe(f"list:{key}", spec.description)
            item: dict[str, Any] = {"key": key, "objectType": spec.of}
            if spec.sortBy is not None:
                item["sortBy"] = spec.sortBy
            within = spec.within
            if within is not None:
                types = within.types
                self.pointers.add(f"{internal}/parentParameter", f"{path}/within", absorb=True)
                self.pointers.add(f"{internal}/parentParameter/name", f"{path}/within/filter", absorb=True)
                if types is None:
                    named = self.document.filters.get(within.filter)
                    if named is None or named.under is None:
                        self.fail(
                            f"{path}/within",
                            f"'{within.filter}' is not an 'under' filter, so 'within' needs 'types': the types"
                            " whose records the list is within",
                        )
                    types = named.under
                    self.pointers.add(f"{internal}/parentParameter/objectTypes", f"{path}/within/filter", absorb=True)
                else:
                    self.pointers.add(f"{internal}/parentParameter/objectTypes", f"{path}/within/types")
                item["parentParameter"] = {"name": within.filter, "objectTypes": list(types)}
            lists.append(item)
        return lists

    def _events(self) -> list[dict[str, Any]]:
        declared = self.document.operations.events
        self.pointers.add("/events", "/operations/events", absorb=True)
        if declared is None:
            return []
        if not declared.perType and not declared.custom:
            self.fail("/operations/events", "declares no event: give 'perType' or 'custom', or leave 'events' out")
        events: list[dict[str, Any]] = []
        if declared.perType:
            for key in self.document.exposes:
                event = f"{key}-changed"
                self.pointers.add(f"/events/{seg(event)}", "/operations/events/perType", absorb=True)
                events.append({"key": event, "objectTypes": [key], "changes": list(PER_TYPE_CHANGES)})
        for index, event in enumerate(declared.custom):
            path = f"/operations/events/custom/{index}"
            self.pointers.add(f"/events/{seg(event.key)}", path)
            self.pointers.add(f"/events/{seg(event.key)}/watch/projections", f"{path}/watch/related")
            item: dict[str, Any] = {"key": event.key, "objectTypes": list(event.objectTypes), "changes": list(event.changes)}
            if event.watch is not None:
                item["watch"] = {"fields": list(event.watch.fields), "projections": list(event.watch.related)}
            events.append(item)
        return events


def authored_through(via: str) -> str:
    """An internal ``linkedTo`` route as the author writes it."""
    if via == VIA_SELF:
        return THROUGH_ITSELF
    if via.startswith(VIA_SHARED):
        return THROUGH_SHARED + via.removeprefix(VIA_SHARED)
    return via


def _via(through: str) -> str:
    if through == THROUGH_ITSELF:
        return VIA_SELF
    if through.startswith(THROUGH_SHARED):
        return VIA_SHARED + through.removeprefix(THROUGH_SHARED)
    return through
