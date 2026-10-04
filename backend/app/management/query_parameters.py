"""Unknown query parameters are refused, naming them (H4c, decided D-3, journey J21.8).

A misspelt parameter (``pagesize``) used to be ignored, so the client silently got another answer
than it asked for. Every route now accepts only the query parameters it declares, and the routes
marked with :func:`accepts_field_filters` also accept the ``filter.<field>.<operator>`` family they
read themselves.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from ..errors import api_error

FIELD_FILTER_PREFIX = "filter."
_KNOWN: dict[int, tuple[frozenset[str], bool]] = {}


def accepts_field_filters[F: Callable[..., Any]](endpoint: F) -> F:
    """Mark a route that reads ``filter.<field>.<operator>`` parameters from the request."""
    endpoint.accepts_field_filters = True  # type: ignore[attr-defined]
    return endpoint


def refuse_unknown_parameters(request: Request) -> None:
    route = request.scope.get("route")
    if not isinstance(route, APIRoute):
        return
    known, filters = _parameters(route)
    unknown = sorted(
        {
            name
            for name in request.query_params
            if name not in known and not (filters and name.startswith(FIELD_FILTER_PREFIX))
        }
    )
    if unknown:
        raise api_error(
            422,
            "UNKNOWN_PARAMETER",
            f"Unknown query parameter '{unknown[0]}'",
            {"parameters": unknown, "path": f"/query/{unknown[0]}"},
        )


def _parameters(route: APIRoute) -> tuple[frozenset[str], bool]:
    key = id(route)
    if key not in _KNOWN:
        _KNOWN[key] = (
            frozenset(_query_names(route.dependant)),
            getattr(route.endpoint, "accepts_field_filters", False),
        )
    return _KNOWN[key]


def _query_names(dependant: Dependant) -> set[str]:
    names = {field.alias for field in dependant.query_params}
    for dependency in dependant.dependencies:
        names |= _query_names(dependency)
    return names
