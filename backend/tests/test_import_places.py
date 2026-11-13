"""Where an import puts a new cell record, worked out for every column record in whole-set
statements (``engine/imports/places.py``, release review R17-F15).

The containers under a column record that meet the candidate criteria are the ones the earlier
per-record Python walk found (``meets_criteria`` over each container's ancestor chain); the walk is
kept here as the reference. The statements do not grow with the number of column records.
"""

import json
import threading
from pathlib import Path

from sqlalchemy import event, select
from test_relation_matrix import attr, create
from test_relation_matrix_writes import client, languages, systems  # noqa: F401

from app.db import SessionLocal, get_engine
from app.engine.imports.places import PlaceRequest, _View, resolve_places
from app.engine.model.candidates import meets_criteria
from app.engine.model.compiler import parse_model
from app.engine.model.traversal import parent_type_keys
from app.engine.reads.context_sets import record_source
from app.models.schema import CandidateCriterion

MODEL = parse_model(
    json.loads((Path(__file__).resolve().parents[2] / "model/rdm-starter.json").read_text())
)
VIEW = {
    "column_type_key": "language",
    "cell_type_key": "translation",
    "relation_type_key": "object-has-translation",
    "direction": "outgoing",
    "row_type_key": "master-value",
}


def _criterion(field, op, value):
    return CandidateCriterion(field=field, op=op, value=value)


CRITERIA = {
    "none": (),
    "group name": (_criterion("ancestor:translation-group.name", "eq", "Group en"),),
    "nested group": (_criterion("ancestor:translation-group.name", "eq", "Nested"),),
    "group contains": (_criterion("ancestor:translation-group.name", "contains", "group"),),
    "language code": (
        _criterion("ancestor:language.language-code", "eq", "cs"),
        _criterion("ancestor:translation-group.name", "startsWith", "Group"),
    ),
    "no group matches": (_criterion("ancestor:translation-group.name", "eq", "Nowhere"),),
}


def _reference(session, column_id, criteria):
    """The containers under the column record that meet the criteria, by the earlier walk: every
    record read into Python, its ancestor chain built and the criteria run per record."""
    types = ["language", "translation-group"]
    source = record_source("default", None, types)
    rows = {
        row.object_id: row
        for row in session.execute(
            select(
                source.c.object_id,
                source.c.object_type_key,
                source.c.name,
                source.c.parent_object_id,
                source.c.attributes,
            )
        )
    }
    direct = parent_type_keys(MODEL, "translation")
    found = set()
    for row in rows.values():
        if row.object_type_key not in direct:
            continue
        chain, at = [], row.object_id
        for _ in range(64):
            item = rows.get(at)
            if item is None:
                break
            chain.append(item)
            at = item.parent_object_id
        if not any(item.object_id == column_id for item in chain):
            continue
        ancestors = [
            (item.object_type_key, item.name, lambda item=item: dict(item.attributes or {}))
            for item in chain
        ]
        if meets_criteria(MODEL, criteria, ("", dict), ancestors):
            found.add(row.object_id)
    return found


def _requests(columns, criteria):
    return [PlaceRequest(criteria=criteria, column_record_id=column, **VIEW) for column in columns]


def test_the_containers_found_in_sql_are_those_the_python_walk_found(client, languages):  # noqa: F811
    """Given a language with two nested groups, one with one group and one with none, and criteria
    that are met by both groups, one, none, or by the language's code. Then each column's found
    containers equal the earlier walk's."""
    with SessionLocal() as session:
        for name, criteria in CRITERIA.items():
            view = _View(
                session, MODEL, "default", None, _requests(languages["columns"], criteria), _reads()
            )
            for column in languages["columns"]:
                got = {row.object_id for row in view.found.get(column, [])}
                assert got == _reference(session, column, criteria), (name, column)
        # The cases are not all empty: both groups of EN, EN's second level alone, none.
        view = _View(session, MODEL, "default", None, _requests(languages["columns"], ()), _reads())
        en, cs, de = languages["columns"]
        assert len(view.found[en]) == 2 and len(view.found[cs]) == 1 and de not in view.found
        nested = _View(
            session,
            MODEL,
            "default",
            None,
            _requests(languages["columns"], CRITERIA["nested group"]),
            _reads(),
        )
        assert [row.name for row in nested.found[en]] == ["Nested"]


def test_the_place_follows_the_data_ambiguity_and_absence(client, languages):  # noqa: F811
    en, cs, de = languages["columns"]
    with SessionLocal() as session:
        places = resolve_places(session, MODEL, "default", None, _requests([en, cs, de], ()))
        # EN: the group that holds its translations; CS: a sole empty group is never the default;
        # DE: no group at all, and no place can be derived.
        assert places[0].container_id == languages["groups"]["en"]["id"]
        assert places[1].container_id is None or places[1].new is not None
        assert places[1].container_id != languages["groups"]["cs"]["id"]
        assert places[2].container_id is None or places[2].new is not None
        ambiguous = resolve_places(
            session, MODEL, "default", None, _requests([en], CRITERIA["group contains"])
        )[0]
        assert ambiguous.container_id == languages["groups"]["en"]["id"]


def _reads():
    from app.engine.imports.places import PlaceReads

    return PlaceReads()


def test_statements_do_not_grow_with_the_column_records(client, languages):  # noqa: F811
    """Given the three languages and five more without groups. When the places of the three and one
    without a group, then of all eight column records are worked out. Then both take the same number
    of statements. (The reads that propose or explain a place, one statement each for the whole view,
    are made as soon as one column record has no group, so both sets hold one such.)"""
    extra = [
        create(
            client,
            "rdm-translations",
            "language",
            f"Language x{number}",
            [attr("language-code", f"x{number}")],
        )["id"]
        for number in range(5)
    ]
    statements: list[str] = []

    caller = threading.get_ident()

    def count(connection, cursor, statement, *rest):
        # The caller's own statements: the application's background threads, which an earlier
        # module's application may have left running, are not the places' reads.
        if threading.get_ident() == caller:
            statements.append(statement)

    def measure(columns, criteria):
        statements.clear()
        with SessionLocal() as session:
            event.listen(get_engine(), "before_cursor_execute", count)
            try:
                resolve_places(session, MODEL, "default", None, _requests(columns, criteria))
            finally:
                event.remove(get_engine(), "before_cursor_execute", count)
        return len(statements)

    for criteria in (CRITERIA["none"], CRITERIA["group name"]):
        few = measure([*languages["columns"], extra[0]], criteria)
        many = measure([*languages["columns"], *extra], criteria)
        assert few == many and many <= 10, (few, many)
