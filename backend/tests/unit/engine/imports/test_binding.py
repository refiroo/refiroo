"""The binding report (``engine/imports/binding.py``, 0.9 J3, D86).

J27.11 checks a converted column and a parent column through the API. Here are the counts of every
other binding kind in one file: a name, an attribute through a value map, a split relation column
and two flag columns, matched against records the same file creates; a match finding none or
several, and a row refused by one column still counted in the others.
"""

import io

from openpyxl import Workbook
from scenario import W1
from sqlalchemy import event

from app.db import SessionLocal
from app.engine.imports.binding import ImportLimits, bind_import
from app.engine.jobs.store import start_job
from app.engine.model.registry import resolve_model_snapshot


def _workbook(path, sheets):
    book = Workbook()
    book.remove(book.active)
    for title, rows in sheets.items():
        sheet = book.create_sheet(title)
        for row in rows:
            sheet.append(list(row))
    buffer = io.BytesIO()
    book.save(buffer)
    path.write_bytes(buffer.getvalue())


def _bind(path, profile, listen=None):
    """Bind ``path`` through ``profile`` as an import's preview in W1, writing nothing;
    ``listen(connection, statement)`` sees each statement before it runs."""
    with SessionLocal() as session:
        snapshot = resolve_model_snapshot(session)
        job = start_job(
            session,
            kind="import",
            workspace_key=W1,
            change_set_id=None,
            model_release_id=snapshot.release_db_id,
            parameters={
                "policy": "independent",
                "stage": "preview",
                "file": {"format": "xlsx"},
                "profile": {"definition": profile},
            },
            total=None,
            retention_days=7,
            queued=True,
        )
        connection = session.connection()
        if listen is not None:
            event.listen(connection, "before_cursor_execute", listen)
        try:
            return bind_import(
                session, job, path, snapshot.model, lambda: None, ImportLimits(10_000, 1_000_000)
            )
        finally:
            if listen is not None:
                event.remove(connection, "before_cursor_execute", listen)
            session.rollback()


def test_the_report_counts_each_binding_kind_per_column(seeded, tmp_path):
    k = seeded.key
    profile = {
        "sources": [
            {
                "sheet": "Tokens",
                "applicationKey": seeded.app("K"),
                "objectTypeKey": k("K"),
                "columns": [
                    {"column": "Code", "attributeTypeKey": k("K.code")},
                    {"column": "Name", "field": "name"},
                ],
            },
            {
                "sheet": "Branches",
                "applicationKey": seeded.app("H"),
                "objectTypeKey": k("H"),
                "columns": [
                    {"column": "Code", "attributeTypeKey": k("H.code")},
                    {"column": "Name", "field": "name"},
                    {"column": "Rank", "attributeTypeKey": k("H.rank"), "valueMap": "none"},
                    {
                        "column": "Tokens",
                        "relation": {
                            "relationTypeKey": k("Bnn"),
                            "objectTypeKey": k("K"),
                            "matchBy": {"attributeTypeKey": k("K.code")},
                            "split": ";",
                        },
                    },
                    {
                        "columns": ["Web", "Phone"],
                        "relationFlags": {
                            "relationTypeKey": k("Bnn"),
                            "objectTypeKey": k("K"),
                            "matchBy": {"field": "name"},
                            "targets": {"Web": "Unit token one", "Phone": "Unit twin"},
                            "trueValues": ["x"],
                        },
                    },
                ],
            },
        ],
        "valueMaps": {"none": {"-": None}},
    }
    path = tmp_path / "file.source"
    _workbook(
        path,
        {
            "Tokens": [
                ("Code", "Name"),
                ("UTK1", "Unit token one"),
                ("UTK2", "Unit twin"),
                ("UTK3", "Unit twin"),
            ],
            "Branches": [
                ("Code", "Name", "Rank", "Tokens", "Web", "Phone"),
                ("UB1", "One", 5, "UTK1;UTK2", "x", None),
                ("UB2", "Two", "-", "UTK9", None, "x"),
                ("UB3", "Three", "many", None, None, None),
                ("UB4", None, None, None, None, None),
            ],
        },
    )
    bound = _bind(path, profile)

    tokens, branches = bound.report
    assert (tokens["sheet"], tokens["rows"], tokens["rejectedRows"]) == ("Tokens", 3, 0)
    assert (branches["sheet"], branches["rows"], branches["rejectedRows"]) == ("Branches", 4, 3)
    columns = {c["column"]: c for c in branches["columns"]}
    assert columns["Name"] == {
        "column": "Name",
        "binding": "field",
        "target": "name",
        "cells": 4,
        "empty": 1,
        "converted": 3,
        "valueMapped": 0,
        "refused": 0,
    }
    rank = columns["Rank"]
    assert (rank["converted"], rank["valueMapped"], rank["refused"], rank["empty"]) == (1, 1, 1, 1)
    tokens_column = columns["Tokens"]
    assert tokens_column["binding"] == "relation" and tokens_column["target"] == k("Bnn")
    assert (tokens_column["cells"], tokens_column["empty"]) == (4, 2)
    assert (
        tokens_column["resolved"],
        tokens_column["notFound"],
        tokens_column["ambiguous"],
    ) == (2, 1, 0)
    web, phone = columns["Web"], columns["Phone"]
    assert web["binding"] == phone["binding"] == "relationFlags"
    assert (web["empty"], web["resolved"], web["ambiguous"]) == (3, 1, 0)
    assert (phone["empty"], phone["resolved"], phone["ambiguous"]) == (3, 0, 1)


def _subplan_reads(node, table, inside=False):
    """Whether a plan node reads ``table`` inside a subplan run once per outer row."""
    inside = inside or node.get("Parent Relationship") == "SubPlan"
    if inside and node.get("Relation Name") == table:
        return True
    return any(_subplan_reads(child, table, inside) for child in node.get("Plans", []))


def test_record_items_collect_relationship_links_once_not_per_row(seeded, tmp_path):
    """0.10 A3 (found measuring the dry run): building the record items looked up each row's
    required links in a subquery run per row, scanning every link each time, so binding a file
    with a relationship column grew with rows times links (8 s of a 10,000-row file's 9 s). The
    statement's plan reads ``import_links`` once, not in a per-row subplan."""
    k = seeded.key
    profile = {
        "sources": [
            {
                "sheet": "Tokens",
                "applicationKey": seeded.app("K"),
                "objectTypeKey": k("K"),
                "columns": [
                    {"column": "Code", "attributeTypeKey": k("K.code")},
                    {"column": "Name", "field": "name"},
                ],
            },
            {
                "sheet": "Branches",
                "applicationKey": seeded.app("H"),
                "objectTypeKey": k("H"),
                "columns": [
                    {"column": "Name", "field": "name"},
                    {
                        "column": "Tokens",
                        "relation": {
                            "relationTypeKey": k("Bnn"),
                            "objectTypeKey": k("K"),
                            "matchBy": {"attributeTypeKey": k("K.code")},
                        },
                    },
                ],
            },
        ]
    }
    path = tmp_path / "file.source"
    _workbook(
        path,
        {
            "Tokens": [("Code", "Name"), ("LTK1", "Link one"), ("LTK2", "Link two")],
            "Branches": [("Name", "Tokens"), ("Linked one", "LTK1"), ("Linked two", "LTK2")],
        },
    )
    plans = []

    def explain(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("INSERT INTO import_items") and "SELECT 1," in statement:
            cursor.execute("EXPLAIN (FORMAT JSON) " + statement, parameters)
            plans.append(cursor.fetchone()[0][0]["Plan"])

    _bind(path, profile, explain)
    (plan,) = plans
    assert not _subplan_reads(plan, "import_links"), plan
