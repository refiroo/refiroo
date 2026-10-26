"""``management/access.py``: where the route check runs among the other request checks (0.12 E1).

The sweep of J47.1 calls every operation with a body that cannot be valid and relies on the check
refusing before the body is read as a model; this probes that order, once, for one operation of each
declared scope kind (``x-action-scope``). A caller holding nothing is called with the real change set,
publication, job and subscription a scope resolves, so the lookup that precedes the check finds its
record; the call carries a body no operation accepts (JSON ``[]``), and then an unknown query
parameter. The first order is what the sweep needs; the second is what the API document promises
(``401`` before anything is read, ``403`` for an action not allowed).
"""

import pytest
from configurations import all_configurations
from scenario import world_for
from test_j30_subscriptions import SUBSCRIPTIONS
from test_j40_authorization import _client
from test_j47_security_sweep import _fixtures, operations, probe

from app.engine.authorization.catalogue import ACTIONS


@pytest.fixture(scope="module")
def probed():
    """One application on the Ledger configuration, a caller holding nothing, one operation of each
    scope kind that names a group, and the identifiers their scopes resolve."""
    configuration = all_configurations()["generated-a"]
    with world_for(configuration, SUBSCRIPTIONS) as world:
        declared, _ = operations(world.api.client.app)
        sample: dict[str, object] = {}
        # Prefer an operation that reads a body, then the first by path, for each scope kind.
        for operation in sorted(declared, key=lambda op: (op.body is None, op.path, op.method)):
            if ACTIONS[operation.action].groups and operation.scope not in sample:
                sample[operation.scope] = operation
        _, nobody = _client(world, "Nobody")
        yield world, nobody, _fixtures(world), sample


def _anonymous(world):
    from harness_identity import TestClient

    return TestClient(world.api.client.app, authenticated=False)


def _differences(probed, extra, expected_status, expected_code, caller=None) -> list[str]:
    _, nobody, ids, sample = probed
    problems = []
    for scope, operation in sample.items():
        client = nobody.api.client if caller is None else caller
        response = probe(client, operation, ids, "default", real=True, extra=extra)
        body = response.json() if response.content else {}
        error = body.get("error", {}) if isinstance(body, dict) else {}
        code = error.get("code") if isinstance(error, dict) else None
        if (response.status_code, code) != (expected_status, expected_code):
            problems.append(
                f"{scope}: {operation.method.upper()} {operation.path} answered "
                f"{response.status_code} {code}"
            )
    return problems


def test_the_scope_kinds_sampled_are_those_the_document_declares(probed):
    world, _, _, sample = probed
    declared, _ = operations(world.api.client.app)
    named = {op.scope for op in declared if ACTIONS[op.action].groups}
    assert set(sample) == named
    assert len(sample) >= 15


def test_authorization_refuses_before_the_body_is_validated(probed):
    """A caller holding nothing, a body no operation accepts: `403 FORBIDDEN`, never `422`."""
    assert _differences(probed, {}, 403, "FORBIDDEN") == []


def test_authentication_refuses_before_the_body_is_validated(probed):
    """No token, a body no operation accepts: `401 AUTHENTICATION_REQUIRED`, never `422`."""
    world = probed[0]
    anonymous = _anonymous(world)
    assert _differences(probed, {}, 401, "AUTHENTICATION_REQUIRED", anonymous) == []


def test_authorization_refuses_before_an_unknown_parameter_is_refused(probed):
    """A caller holding nothing, a parameter no operation declares: `403 FORBIDDEN`, not `422
    UNKNOWN_PARAMETER` (the refusal of an unknown parameter is an application-wide dependency)."""
    assert _differences(probed, {"probeUnknown": "1"}, 403, "FORBIDDEN") == []


def test_authentication_refuses_before_an_unknown_parameter_is_refused(probed):
    """No token, a parameter no operation declares: `401 AUTHENTICATION_REQUIRED`."""
    anonymous = _anonymous(probed[0])
    assert (
        _differences(probed, {"probeUnknown": "1"}, 401, "AUTHENTICATION_REQUIRED", anonymous) == []
    )
