"""Base 0.9 B1: batches keep the stored relation matrix states derived (ADR-033).

A batch releases one savepoint per item, and the cell states its items touch are recomputed once
when the outer savepoint is released (``matrix_states.deferred``). Items applied, items refused
after writing a row, and an atomic batch rolled back all leave the stored states equal to states
rebuilt from records, live and in a change set, on the starter's translation matrix.
"""

from test_batches import (
    WORKSPACE,
    _ok,
    batch,
    change_set,
    claimed,
    outcomes,
    read,
    without_workspace,
)
from test_matrix_states import check, client, languages, stored_only  # noqa: F401 - fixtures
from test_relation_matrix import TRANSLATIONS
from test_relation_matrix_writes import TRANSLATION_LINK


def _translation(name: str, group: dict, master: dict, *, active: bool = True) -> dict:
    return {
        "op": "create",
        "applicationKey": "rdm-translations",
        "objectTypeKey": "translation",
        "name": name,
        "parent": {"id": group["id"]},
        "attributes": [
            {"attributeTypeKey": "translated-name", "value": f"{name} text"},
            {"attributeTypeKey": "active", "value": active},
        ],
        "initialRelations": [
            {"relationTypeKey": TRANSLATION_LINK, "direction": "incoming", "object": {"id": master["id"]}}
        ],
    }


def test_batches_keep_stored_matrix_states_derived(client, languages, stored_only):  # noqa: F811
    """Items applied, items refused after writing a row, and an atomic batch rolled back leave the
    stored cell states equal to states rebuilt from records, live and in a change set."""
    columns, groups, masters = languages["columns"], languages["groups"], languages["masters"]
    staged = change_set(client)
    for context in ({"workspaceKey": WORKSPACE}, {"changeSetId": staged["id"]}):
        nested = _ok(read(client, lambda key: key, "translation-group", groups["nested"]["id"], **without_workspace(context)))
        items = [
            _translation("M1 cs", groups["cs"], masters["M1"]),
            # M1 already has an active EN translation: refused by the scope rule after the
            # record row is written.
            _translation("M1 en again", groups["en"], masters["M1"]),
            # The nested container moves to DE with its cells.
            {
                "op": "update",
                "target": {"id": groups["nested"]["id"]},
                "expectedVersion": nested["version"],
                "parent": {"id": languages["language"]["de"]["id"]},
            },
            _translation("M2 cs", groups["cs"], masters["M2"], active=False),
        ]
        body = _ok(batch(client, items, policy="independent", **claimed(client, context)))
        assert outcomes(body) == [
            ("applied", "created"),
            ("rejected", "duplicate_relation_scope"),
            ("applied", "updated"),
            ("applied", "created"),
        ]
        check(client, TRANSLATIONS, columns, without_workspace(context))
        rolled_back = _ok(
            batch(
                client,
                [_translation("M2 de", groups["en"], masters["M2"], active=False), _translation("M1 cs again", groups["cs"], masters["M1"])],
                policy="atomic",
                **claimed(client, context),
            )
        )
        assert outcomes(rolled_back) == [("unprocessed", "batch_rolled_back"), ("rejected", "duplicate_relation_scope")]
        check(client, TRANSLATIONS, columns, without_workspace(context))
