"""Unknown query parameters are refused, naming them (H4c, decided D-3, journey J21.8).

A misspelt parameter (``pagesize``) used to be ignored, so the client silently got another answer
than it asked for. Every route now accepts only the query parameters it declares, and the routes
marked with :func:`accepts_field_filters` also accept the ``filter.<field>.<operator>`` family they
read themselves. A consumer API route checks its parameters against its definition itself (marked
``reads_own_parameters`` by the consumer tier) and is left alone here.
"""

from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from ..errors import api_error

FIELD_FILTER_PREFIX = "filter."
# Accepted on every route: a write to a submitted change set withdraws its submission (A1, D426);
# ``access.authorized`` reads it.
UNIVERSAL_PARAMETERS = frozenset({"withdrawSubmission"})


def accepts_field_filters[F: Callable[..., Any]](endpoint: F) -> F:
    """Mark a route that reads ``filter.<field>.<operator>`` parameters from the request."""
    endpoint.accepts_field_filters = True  # type: ignore[attr-defined]
    return endpoint


def field_filters(request: Request) -> list[tuple[str, str, str]]:
    """Every ``filter.<field>.<operator>=<value>`` of the request, in order."""
    result: list[tuple[str, str, str]] = []
    for key, value in request.query_params.multi_items():
        if not key.startswith("filter."):
            continue
        field_operator = key.removeprefix("filter.")
        if "." not in field_operator:
            raise api_error(
                422,
                "INVALID_FILTER",
                f"Invalid filter parameter '{key}'",
                {"path": f"/query/{key}"},
            )
        field, operator = field_operator.rsplit(".", 1)
        if not field or not operator:
            raise api_error(
                422,
                "INVALID_FILTER",
                f"Invalid filter parameter '{key}'",
                {"path": f"/query/{key}"},
            )
        result.append((field, operator, value))
    return result


def refuse_unknown_parameters(request: Request) -> None:
    """The application-wide dependency: refuse a query parameter the route does not declare. A
    route that needs a token (it declares an action) is left to :func:`refuse_after_authorization`,
    which ``authorized`` calls once the caller is known, so ``401`` and ``403`` come before ``422
    UNKNOWN_PARAMETER`` (0.12 E1, F1); the other routes are checked here, first."""
    route = request.scope.get("route")
    if isinstance(route, APIRoute) and getattr(route.endpoint, "requirement", None) is not None:
        return
    refuse_after_authorization(request)


def refuse_after_authorization(request: Request) -> None:
    route = request.scope.get("route")
    if not isinstance(route, APIRoute) or getattr(route.endpoint, "reads_own_parameters", False):
        return
    known, filters = _parameters(route)
    unknown = sorted(
        {
            name
            for name in request.query_params
            if name not in known
            and name not in UNIVERSAL_PARAMETERS
            and not (filters and name.startswith(FIELD_FILTER_PREFIX))
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
    """The route's declared query names and whether it reads field filters, worked out once and kept
    on the route itself, so it lives and goes with it (an ``id`` is reused once a route is gone)."""
    known: tuple[frozenset[str], bool] | None = getattr(route, "known_query_parameters", None)
    if known is None:
        known = (
            frozenset(_query_names(route.dependant)),
            getattr(route.endpoint, "accepts_field_filters", False),
        )
        route.known_query_parameters = known  # type: ignore[attr-defined]
    return known


def _query_names(dependant: Dependant) -> set[str]:
    names = {field.alias for field in dependant.query_params}
    for dependency in dependant.dependencies:
        names |= _query_names(dependency)
    return names
