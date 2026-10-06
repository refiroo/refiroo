"""What a subscription asks of a definition, and what suspends it (Base 0.9 C11, C-D98, C-D99).

A subscription is checked against the active release's definition when it is created, edited or
resumed, and against a release being activated, in the activation's transaction: a consumer API, an
event or a filter parameter the release no longer declares suspends it ``MODEL_CHANGED`` with each
finding; otherwise a raised contract version suspends it ``CONTRACT_VERSION_CHANGED``, since one
version is served (C-D3) and the ``full`` object's shape would change without the receiver agreeing.
A parameter whose kind changes reaches it the second way: the contract check requires the version
raised. Retiring a workspace suspends its subscriptions ``WORKSPACE_RETIRED`` in the same
transaction. Subscriptions are configuration, few: they are decided in Python and written with one
statement.

This module reads only the model and the subscription table, so the activation and the workspace
catalogue can call it without importing the reads.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import bindparam, select, update
from sqlalchemy.orm import Session

from ...errors import ApiError, api_error
from ...models.database import ConsumerSubscription
from ...models.schema import ConsumerApiDefinition, EngineModel, ProjectionParameter
from ..model.validation.consumer_api_rules import RESERVED_PARAMETERS

ACTIVE, SUSPENDED = "active", "suspended"
SUSPENDED_BY_USER = "SUSPENDED_BY_USER"
MODEL_CHANGED = "MODEL_CHANGED"
CONTRACT_VERSION_CHANGED = "CONTRACT_VERSION_CHANGED"
WORKSPACE_RETIRED = "WORKSPACE_RETIRED"
# Set by the dispatcher (C12, C-D98, C-D109, C-D110).
DELIVERY_FAILED = "DELIVERY_FAILED"
FILTER_MATCHES_NOTHING = "FILTER_MATCHES_NOTHING"
HOST_NOT_ALLOWED = "HOST_NOT_ALLOWED"
EVENTS_EXPIRED = "EVENTS_EXPIRED"

TARGET_PREFIX = "to."


@dataclass(frozen=True)
class Asked:
    """What a subscription names of a definition: the API, its events and its filters."""

    consumer_api: str
    event_keys: Sequence[str]
    filters: Mapping[str, Sequence[str]]


def definition_of(model: EngineModel, consumer_api: str) -> ConsumerApiDefinition | None:
    return next((item for item in model.consumerApis or () if item.key == consumer_api), None)


def definition_findings(model: EngineModel, asked: Asked) -> list[ApiError]:
    """Each way ``model`` cannot serve what ``asked`` names, at its body pointer: the consumer API,
    its events, each named event, each filter's name. An empty list when it can."""
    definition = definition_of(model, asked.consumer_api)
    if definition is None:
        return [
            api_error(
                400,
                "CONSUMER_API_NOT_FOUND",
                f"Consumer API '{asked.consumer_api}' not found in the active release",
                {"pointer": "/consumerApi"},
            )
        ]
    if not definition.events:
        return [
            api_error(
                400,
                "EVENTS_NOT_DECLARED",
                f"Consumer API '{definition.key}' declares no events at contract version "
                f"{definition.contractVersion}",
                {"pointer": "/consumerApi"},
            )
        ]
    findings: list[ApiError] = []
    declared = [event.key for event in definition.events]
    for index, key in enumerate(asked.event_keys):
        if key not in declared:
            findings.append(
                api_error(
                    400,
                    "UNKNOWN_EVENT",
                    f"Consumer API '{definition.key}' declares no event '{key}'; it declares "
                    f"{', '.join(sorted(declared))}",
                    {"events": [key], "pointer": f"/events/{index}"},
                )
            )
    findings += filter_name_findings(definition, asked.filters)
    return findings


def filter_name_findings(
    definition: ConsumerApiDefinition, filters: Mapping[str, Sequence[str]]
) -> list[ApiError]:
    """A filter names a definition parameter (C-D90): a name the API does not know is
    ``UNKNOWN_PARAMETER``; one it knows that is not a parameter (a read's own name such as
    ``workspace`` or ``asOf``, a crosswalk target, a list's parent) is ``PARAMETER_NOT_SUPPORTED``."""
    targets = {
        f"{TARGET_PREFIX}{name}"
        for name, parameter in definition.parameters.items()
        if isinstance(parameter, ProjectionParameter) and parameter.targetable
    }
    parents = {item.parentParameter.name for item in definition.lists if item.parentParameter is not None}
    known = RESERVED_PARAMETERS | set(definition.parameters) | targets | parents
    filtering = sorted(definition.parameters)
    findings = []
    for name in filters:
        if name in definition.parameters:
            continue
        if name not in known:
            findings.append(
                api_error(
                    400,
                    "UNKNOWN_PARAMETER",
                    f"Unknown parameter '{name}'; consumer API '{definition.key}' filters by "
                    f"{', '.join(filtering) or 'no parameter'}",
                    {"parameters": [name], "pointer": f"/filters/{name}"},
                )
            )
        else:
            findings.append(
                api_error(
                    400,
                    "PARAMETER_NOT_SUPPORTED",
                    f"Parameter '{name}' is not a filter: a subscription filters by the definition's "
                    "parameters",
                    {"parameters": [name], "pointer": f"/filters/{name}"},
                )
            )
    return findings


def finding_body(error: ApiError) -> dict[str, Any]:
    """A finding as a suspension or a refusal lists it: its code, message and pointer."""
    return {"code": error.code, "message": error.message, "pointer": (error.details or {}).get("pointer")}


def suspend_left_behind(session: Session, model: EngineModel) -> None:
    """Suspend each active subscription the release being activated cannot serve (C-D99), in the
    activation's transaction. A suspended one keeps its reason; its resume checks again."""
    now = datetime.now(UTC)
    rows = []
    for subscription in session.scalars(
        select(ConsumerSubscription).where(ConsumerSubscription.status == ACTIVE).with_for_update()
    ):
        asked = Asked(subscription.consumer_api, subscription.event_keys, subscription.filters)
        findings = definition_findings(model, asked)
        if findings:
            rows.append(
                {
                    "row": subscription.sequence_id,
                    "reason": MODEL_CHANGED,
                    "message": "The active model release no longer declares what this subscription "
                    "names; edit it, then resume it",
                    "details": {"errors": [finding_body(error) for error in findings]},
                }
            )
            continue
        definition = definition_of(model, subscription.consumer_api)
        assert definition is not None
        if definition.contractVersion != subscription.contract_version:
            rows.append(
                {
                    "row": subscription.sequence_id,
                    "reason": CONTRACT_VERSION_CHANGED,
                    "message": f"Consumer API '{definition.key}' is served at contract version "
                    f"{definition.contractVersion} now; resuming accepts it",
                    "details": {
                        "contractVersion": subscription.contract_version,
                        "servedContractVersion": definition.contractVersion,
                    },
                }
            )
    if not rows:
        return
    table = ConsumerSubscription.__table__
    session.execute(
        update(table)
        .where(table.c.sequence_id == bindparam("row"))
        .values(
            status=SUSPENDED,
            suspension_reason=bindparam("reason"),
            suspension_message=bindparam("message"),
            suspension_details=bindparam("details"),
            suspended_at=now,
            version=table.c.version + 1,
            updated_at=now,
        ),
        rows,
    )


def suspend_for_retired_workspace(session: Session, workspace_key: str) -> None:
    """Suspend the workspace's active subscriptions as it is retired (C-D99); undelivered events
    stay until retention, so a resume after reactivation continues from them."""
    now = datetime.now(UTC)
    session.execute(
        update(ConsumerSubscription)
        .where(ConsumerSubscription.workspace_key == workspace_key, ConsumerSubscription.status == ACTIVE)
        .values(
            status=SUSPENDED,
            suspension_reason=WORKSPACE_RETIRED,
            suspension_message=f"Workspace '{workspace_key}' was retired; reactivate it, then resume",
            suspension_details={"workspaceKey": workspace_key},
            suspended_at=now,
            version=ConsumerSubscription.version + 1,
            updated_at=now,
        )
        .execution_options(synchronize_session=False)
    )


def has_subscriptions(session: Session, workspace_key: str) -> bool:
    return (
        session.scalar(
            select(ConsumerSubscription.sequence_id)
            .where(ConsumerSubscription.workspace_key == workspace_key)
            .limit(1)
        )
        is not None
    )
