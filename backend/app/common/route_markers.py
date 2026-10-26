"""Markers a route declares about itself, read by the checks that run around it.

They live in ``common`` because both the management and the consumer tier mark routes, and the
consumer tier never imports ``management`` (``tests/test_boundaries.py``).
"""


def reads_own_parameters[F](endpoint: F) -> F:
    """Mark a route that checks its query parameters itself (a consumer route against its
    definition, the provider callback against what it needs): the app-wide unknown-parameter check
    (``management/query_parameters``) leaves it alone."""
    endpoint.reads_own_parameters = True  # type: ignore[attr-defined]
    return endpoint
