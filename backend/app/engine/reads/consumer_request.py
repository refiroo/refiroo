"""A consumer read's parameters, checked against the names it serves (Base 0.9 C3).

The consumer routes pass what a request's query holds; an assistant's lookup tool (Product 0.16
AG-D21) passes its arguments, so both refuse the same names in the same words.
"""

import re
from dataclasses import dataclass
from datetime import date

from ...common.pagination import PageRequest
from ...errors import ApiError, api_error
from ...models.schema import ConsumerApiDefinition
from .consumer_lists import PAGE_SIZE
from .consumer_parameters import TARGET_PREFIX, target_names

# A business date: a calendar day, written YYYY-MM-DD and nothing else (C-D79).
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# The names that select a list's page (ADR-030, C-D30).
PAGING_NAMES = frozenset({"pageSize", "cursor", "position", "from", "seek", "includeTotal"})
# The names each route serves besides the definition's parameters. XREF pages by score, which no
# caller seeks, and always counts its total (C-D39); with expect=one it reads no page (C-D40).
OBJECT_NAMES = frozenset({"workspace", "publication", "asOf"})
LIST_NAMES = OBJECT_NAMES | PAGING_NAMES
XREF_ONE_NAMES = OBJECT_NAMES | {"query", "expect"}
XREF_NAMES = XREF_ONE_NAMES | (PAGING_NAMES - {"seek", "includeTotal"})
# The publications list reads live data in the order of publication, which no caller seeks (C-D66).
PUBLICATIONS_NAMES = frozenset({"workspace"}) | (PAGING_NAMES - {"seek"})
# The pull feed pages by position and cursor (C-D91) and chooses its payload (C-D7 revised).
EVENTS_NAMES = frozenset({"workspace", "event", "after", "cursor", "pageSize", "payload"})
# Every name a route of the API serves.
ROUTE_NAMES = LIST_NAMES | XREF_NAMES | EVENTS_NAMES
_MIN_PAGE_SIZE, _MAX_PAGE_SIZE, DEFAULT_PAGE_SIZE = PAGE_SIZE


def is_target(name: str) -> bool:
    return name.startswith(TARGET_PREFIX)


def targetable(name: str, targets: list[str]) -> str:
    """The end of an unknown ``to.`` name's message: the names this API can target (C-D57)."""
    if not is_target(name):
        return ""
    if not targets:
        return "; this API has no targetable parameter"
    return f"; this API targets {', '.join(targets)}"


def multiple_targets(names: list[str], key: str, at: str) -> ApiError | None:
    """``MULTIPLE_TARGETS`` when ``names`` hold more than one ``to.`` name: a read has one target
    (C-D56)."""
    given = [name for name in names if is_target(name)]
    if len(given) < 2:
        return None
    return api_error(
        400,
        "MULTIPLE_TARGETS",
        f"A read has one target, but {' and '.join(given)} are given",
        {"parameters": given, key: f"{at}/{given[1]}"},
    )


@dataclass(frozen=True)
class ReadParameters:
    """A request's query parameters, checked against the names its route serves."""

    raw: dict[str, list[str]]
    # Each name's values, split as OpenAPI's form style lists them (C-D32, C3b).
    listed: dict[str, list[str]]
    # The definition parameters the route applies, by name, with a ``to.`` target among them.
    definition: dict[str, list[str]]
    parents: list[str]
    # The business date of ``asOf``, on a route that serves it (C16).
    as_of: date | None = None

    @classmethod
    def check(
        cls,
        raw: dict[str, list[str]],
        listed: dict[str, list[str]],
        definition: ConsumerApiDefinition,
        *,
        serves: frozenset[str],
        parent: str | None = None,
        applies_definition: bool = True,
        crosswalk: bool = True,
    ) -> ReadParameters:
        """Refuse a name the API does not know (``UNKNOWN_PARAMETER``), then one it knows that this
        route does not apply (``PARAMETER_NOT_SUPPORTED``): one outside ``serves``, a list's parent
        parameter off its list, or a definition parameter on a route that takes them in its body
        (batch resolve's ``defaults``). A ``to.`` name is a definition parameter's crosswalk target,
        one per read (C-D56, C-D57); a read without ``crosswalk`` (the pull feed) applies none."""
        targets = target_names(definition)
        applied = set(serves) | (
            set(definition.parameters) | (set(targets) if crosswalk else set())
            if applies_definition
            else set()
        )
        if parent is not None:
            applied.add(parent)
        known = (
            applied
            | ROUTE_NAMES
            | set(definition.parameters)
            | set(targets)
            | {
                item.parentParameter.name
                for item in definition.lists
                if item.parentParameter is not None
            }
        )
        unknown = [name for name in raw if name not in known]
        if unknown:
            raise api_error(
                400,
                "UNKNOWN_PARAMETER",
                f"Unknown query parameter '{unknown[0]}'{targetable(unknown[0], targets)}",
                {"parameters": unknown, "path": f"/query/{unknown[0]}"},
            )
        unsupported = [name for name in raw if name not in applied]
        if unsupported:
            raise api_error(
                400,
                "PARAMETER_NOT_SUPPORTED",
                f"Parameter '{unsupported[0]}' is not supported on this read",
                {"parameters": unsupported, "path": f"/query/{unsupported[0]}"},
            )
        multiple = multiple_targets(list(raw), "path", "/query")
        if multiple is not None:
            raise multiple
        # On its list, a parent parameter sharing a definition parameter's name addresses the parent.
        return cls(
            raw=raw,
            listed=listed,
            definition={
                name: listed[name]
                for name in raw
                if name in applied
                and (name in definition.parameters or is_target(name))
                and name != parent
            },
            parents=list(dict.fromkeys(listed[parent])) if parent in raw else [],
            as_of=_as_of(raw.get("asOf"), listed.get("asOf")) if "asOf" in raw else None,
        )

    def single(self, name: str) -> str | None:
        values = self.raw.get(name)
        return values[-1] if values else None


def _as_of(raw: list[str] | None, listed: list[str] | None) -> date:
    """``asOf`` as a date: one calendar day, ``YYYY-MM-DD`` (C-D79). A time, a zone, an impossible
    day or several values are ``400 INVALID_AS_OF``: a read answers for one date."""
    values = listed or raw or []
    if len(values) == 1 and _DATE.match(values[0]):
        try:
            return date.fromisoformat(values[0])
        except ValueError:
            pass
    raise api_error(
        400,
        "INVALID_AS_OF",
        "asOf must be one calendar date, written YYYY-MM-DD",
        {"path": "/query/asOf"},
    )


def read_page(parameters: ReadParameters) -> tuple[int, PageRequest]:
    """The page size and the page a list read asks for (C-D30)."""
    raw_size = parameters.single("pageSize")
    try:
        page_size = DEFAULT_PAGE_SIZE if raw_size is None else int(raw_size)
    except ValueError:
        page_size = 0
    if not _MIN_PAGE_SIZE <= page_size <= _MAX_PAGE_SIZE:
        raise api_error(
            400,
            "INVALID_PAGE_SIZE",
            f"pageSize must be a whole number from 1 to {_MAX_PAGE_SIZE}",
            {"path": "/query/pageSize"},
        )
    raw_position = parameters.single("position")
    try:
        position = None if raw_position is None else int(raw_position)
    except ValueError:
        raise api_error(
            400, "INVALID_POSITION", "position must be a whole number", {"path": "/query/position"}
        ) from None
    start = _choice(parameters, "from", {"start": False, "end": True}, False)
    include_total = _choice(parameters, "includeTotal", {"false": False, "true": True}, False)
    try:
        page = PageRequest(
            cursor=parameters.single("cursor"),
            position=position,
            seek=parameters.single("seek"),
            from_end=start,
            include_total=include_total,
        )
    except ApiError as exc:
        exc.status = 400
        raise
    return page_size, page


def _choice(parameters: ReadParameters, name: str, choices: dict[str, bool], default: bool) -> bool:
    raw = parameters.single(name)
    if raw is None:
        return default
    if raw not in choices:
        raise api_error(
            400,
            "INVALID_PAGE_PARAMETER",
            f"{name} must be one of {', '.join(choices)}",
            {"path": f"/query/{name}"},
        )
    return choices[raw]
