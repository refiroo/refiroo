"""The binding report (``engine/imports/binding.py``, 0.9 J3, D86).

J27.11 checks a converted column and a parent column through the API. Here are the counts of every
other binding kind in one file: a name, an attribute through a value map, a split relation column
and two flag columns, matched against records the same file creates; a match finding none or
several, and a row refused by one column still counted in the others.
"""

import io

from openpyxl import Workbook
from scenario import W1

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
        bound = bind_import(
            session, job, path, snapshot.model, lambda: None, ImportLimits(10_000, 1_000_000)
        )
        session.rollback()

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
