"""Batch resolve: many lookups in one read (Base 0.9 C14, C-D47–C-D53).

Each item is resolved exactly as the single read it stands for: by ``query`` as XREF's
``expect=one``, by ``id`` as get by ID, with the definition's parameters (its own over the
request's ``defaults``). Its outcome is that read's answer: ``found`` with the object, or
``not_found``, ``ambiguous`` or ``rejected`` with the read's error, a rejection pointing into the
item (C-D48).

The items are grouped by their parameters, since the parameters make one filter, and each group is
resolved in a fixed number of statements whatever its size, each distinct lookup once: one for every
lookup's exact matches,
one more for the lookups they leave unsettled (``consumer_xref.resolve_lookups``, C-D52), and one
composition of every object the group found (C-D51). Nothing resolves item by item.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from ...errors import ApiError
from ...models.schema import ConsumerApiDefinition, EngineModel
from .consumer_objects import ConsumerObjects, object_not_found, one_target
from .consumer_parameters import Target, consumer_filter
from .consumer_source import ConsumerSource
from .consumer_xref import Found, resolve_lookups

_STATUS = {404: "not_found", 409: "ambiguous"}
_COUNTS = {"found": "found", "not_found": "notFound", "ambiguous": "ambiguous", "rejected": "rejected"}


@dataclass(frozen=True)
class ResolveItem:
    """One item of a batch, checked: a lookup's ``terms`` or an ``object_id``, the parameters that
    apply to it and, by name, where each was given (``/defaults/…`` or ``/items/i/…``); or the
    refusal its own content earned."""

    index: int
    ref: str | None
    terms: list[str] | None = None
    object_id: str | None = None
    parameters: dict[str, list[str]] = field(default_factory=dict)
    pointers: dict[str, str] = field(default_factory=dict)
    refused: ApiError | None = None

    def pointer(self, path: str | None) -> str:
        """Where in the request an error's ``/query/<name>`` path points for this item."""
        name = path.removeprefix("/query/") if path and path.startswith("/query/") else None
        if name is None:
            return f"/items/{self.index}"
        return self.pointers.get(name, f"/items/{self.index}/{name}")


def item_error(error: ApiError, pointer: str) -> ApiError:
    """``error`` for an item: its details with ``pointer`` in place of the single read's ``path``."""
    details = {key: value for key, value in (error.details or {}).items() if key != "path"}
    return ApiError(error.status, error.code, error.message, {**details, "pointer": pointer})


def read_resolve(
    session: Session,
    model: EngineModel,
    definition: ConsumerApiDefinition,
    source: ConsumerSource,
    items: Sequence[ResolveItem],
) -> dict[str, Any]:
    """Every item's outcome, in item order, with the workspace and publication read and the outcomes
    counted."""
    outcomes: dict[int, dict[str, Any]] = {}
    groups: dict[tuple[tuple[str, tuple[str, ...]], ...], list[ResolveItem]] = {}
    for item in items:
        if item.refused is not None:
            outcomes[item.index] = _failed(item, item.refused)
            continue
        key = tuple(sorted((name, tuple(values)) for name, values in item.parameters.items()))
        groups.setdefault(key, []).append(item)
    composer = ConsumerObjects(model, definition)
    for members in groups.values():
        try:
            narrowed = consumer_filter(session, model, definition, source, members[0].parameters)
        except ApiError as error:
            for item in members:
                outcomes[item.index] = _failed(item, item_error(error, item.pointer((error.details or {}).get("path"))))
            continue
        # Items sending the same terms in one group are one lookup, resolved once (C14a): a file of
        # codes repeats its values.
        distinct = list(dict.fromkeys(_lookup(item) for item in members if item.terms is not None))
        answers = dict(
            zip(
                distinct,
                resolve_lookups(session, model, definition, source, [list(key) for key in distinct], narrowed),
                strict=True,
            )
        )
        found = {item.index: answers[_lookup(item)] for item in members if item.terms is not None}
        wanted = [answer.id for answer in found.values() if isinstance(answer, Found)]
        wanted += [item.object_id for item in members if item.object_id is not None]
        composed = composer.compose(session, source, list(dict.fromkeys(wanted)), narrowed)
        for item in members:
            if item.object_id is not None:
                body = composed.get(item.object_id)
                outcomes[item.index] = (
                    _targeted(item, body, item.object_id, narrowed.target)
                    if body is not None
                    else _failed(item, object_not_found(item.object_id))
                )
                continue
            answer = found[item.index]
            if isinstance(answer, Found):
                outcomes[item.index] = _targeted(item, composed[answer.id], answer.id, narrowed.target, answer.score)
            elif answer.status in _STATUS:
                outcomes[item.index] = _failed(item, answer)
            else:
                outcomes[item.index] = _failed(item, item_error(answer, item.pointer((answer.details or {}).get("path"))))
    ordered = [outcomes[item.index] for item in items]
    counts = dict.fromkeys(_COUNTS.values(), 0)
    for outcome in ordered:
        counts[_COUNTS[outcome["status"]]] += 1
    return {
        "items": ordered,
        "workspace": source.workspace_key,
        "publication": source.publication_id,
        "counts": counts,
    }


def _lookup(item: ResolveItem) -> tuple[str, ...]:
    """What a lookup is: its terms, whatever their order or repeats, since an object's score is its
    best over the terms."""
    return tuple(sorted(set(item.terms or [])))


def _targeted(
    item: ResolveItem, body: dict[str, Any], object_id: str, target: Target | None, score: int | None = None
) -> dict[str, Any]:
    """A found object's outcome: ``found``, or with a crosswalk target that is missing or not
    unique, ``not_found`` or ``ambiguous`` pointing at where the ``to.`` name was given (C-D55)."""
    try:
        answered = one_target(body, object_id, target)
    except ApiError as error:
        return _failed(item, item_error(error, item.pointer((error.details or {}).get("path"))))
    return _found(item, answered if score is None else {**answered, "matchScore": score})


def _found(item: ResolveItem, body: dict[str, Any]) -> dict[str, Any]:
    return {"index": item.index, "ref": item.ref, "status": "found", "object": body}


def _failed(item: ResolveItem, error: ApiError) -> dict[str, Any]:
    """A ``not_found``, ``ambiguous`` or ``rejected`` outcome carrying the error as the API renders
    it."""
    rendered = {
        "code": error.code,
        "message": error.message,
        **({"details": error.details} if error.details is not None else {}),
    }
    return {"index": item.index, "ref": item.ref, "status": _STATUS.get(error.status, "rejected"), "error": rendered}
