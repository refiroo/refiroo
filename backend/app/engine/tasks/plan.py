"""The plan of a task: the reading and the person's choices as an import profile (Product 0.16
AP6a, AP-D12, AP-D26).

Each table read as an update, and not left out by the person, becomes one source of the profile:
its sheet, header row and block, the type and application it loads, ``record: upsert`` keyed by the
reading's key, its bound columns, ``missing: delete`` when the person removes the records the file
does not name and ``report`` otherwise. The value maps are:

- the meaning matches, on the key column: the file's key to the stored record's key, so the row
  updates that record and nothing is created twice;
- "Leave them out": each new key to ``null``, with ``rowsWithoutKey: skip``;
- "Keep the stored names": each name cell that differs from the stored name to the stored name;
- the assistant's fixes (a refused cell value to the value it means), on any bound column;
- a list's note row or second header row (the reading's ``noteText``) to nothing on the key and name
  columns, with ``rowsWithoutKey: skip``: it is no record.

A table that followed a stored profile starts from the source exactly as stored and the profile's
value maps; the person's choices, the meaning matches and the fixes are added to it, and the plan
names the profile when none of that changed anything (``Built.profile_key``).

:func:`build` is pure: what PostgreSQL computes (the new keys, the names) arrives as
:class:`Computed`, so the profile of a choice is decided here and tested without a database.
"""

import copy
from dataclasses import dataclass, field
from typing import Any

# What the plan keeps of a table the person did not leave out.
LOADABLE = "update"


@dataclass
class Computed:
    """What the database says about a table: its new keys, the stored name each name cell that
    differs maps to, and the name cells that cannot be mapped (module docstring of ``reading``)."""

    new_keys: list[str] = field(default_factory=list)
    names: dict[str, str] = field(default_factory=dict)
    unmapped_names: list[str] = field(default_factory=list)


@dataclass
class Built:
    profile: dict[str, Any]
    steps: list[dict[str, Any]]
    # The profile's sources: the table each loads.
    sources: list[dict[str, Any]]
    notes: list[str]
    # The stored profile the plan is, unchanged.
    profile_key: str | None = None


def loads(table: dict[str, Any]) -> bool:
    return table["as"] == LOADABLE and table["choices"]["load"]["value"] is True


def build(
    tables: list[dict[str, Any]],
    computed: dict[str, Computed],
    fixes: list[dict[str, Any]],
    *,
    csv_delimiter: str | None,
    skip: frozenset[str] = frozenset(),
    profile: dict[str, Any] | None = None,
    profile_maps: dict[str, dict[str, Any]] | None = None,
) -> Built | None:
    """The profile, its steps and notes; ``None`` when no table is loaded. ``skip`` leaves out
    tables the profile check refused; ``profile`` and ``profile_maps`` are the stored profile the
    reading followed and its value maps."""
    sources: list[dict[str, Any]] = []
    value_maps: dict[str, dict[str, Any]] = {}
    steps: list[dict[str, Any]] = []
    notes: list[str] = []
    listed: list[dict[str, Any]] = []
    from_profile = 0
    changed = False
    for table in tables:
        if not loads(table) or table["table"] in skip:
            continue
        followed = table.get("profile") is not None
        source, maps, table_steps, table_notes, differs = _source(
            table,
            computed.get(table["table"], Computed()),
            [f for f in fixes if f["table"] == table["table"]],
            csv_delimiter,
            profile_maps or {},
        )
        listed.append({"table": table["table"], "index": len(sources)})
        sources.append(source)
        value_maps.update(maps)
        steps += table_steps
        notes += table_notes
        from_profile += followed
        changed = changed or differs
    if not sources:
        return None
    if from_profile:
        value_maps = {**(profile_maps or {}), **value_maps}
    out: dict[str, Any] = {"sources": sources, "valueMaps": value_maps}
    if csv_delimiter is not None:
        out["csv"] = {"delimiter": csv_delimiter}
    steps.append(
        {
            "kind": "destination",
            "owner": "rules",
            "reason": "A new change set; live data is not changed",
            "params": {"changeSet": "new"},
        }
    )
    unchanged = (
        profile is not None and from_profile == profile["sources"] == len(sources) and not changed
    )
    return Built(out, steps, listed, notes, profile["key"] if unchanged and profile else None)


def _source(
    table: dict[str, Any],
    computed: Computed,
    fixes: list[dict[str, Any]],
    csv_delimiter: str | None,
    profile_maps: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]], list[str], bool]:
    """The table's source of the profile, the value maps it needs, its steps, notes, and whether it
    differs from the stored profile's source it followed (always for a table the rules read)."""
    name = table["table"]
    place = table["place"]
    key_letter = table["keyColumn"]
    choices = table["choices"]
    notes: list[str] = []
    steps: list[dict[str, Any]] = []
    maps: dict[str, dict[str, Any]] = {}
    entries: dict[str, dict[str, Any]] = {}
    followed = table.get("profile") is not None

    def add(
        column: str, values: dict[str, Any], owner: str, reason: str, origin: dict[str, Any] | None
    ) -> None:
        if values:
            entries.setdefault(column, {}).update(
                {k: v for k, v in values.items() if k not in entries.get(column, {})}
            )
            steps.append(
                {
                    "kind": "valueMap",
                    "owner": owner,
                    "reason": reason,
                    **({"origin": origin} if origin else {}),
                    "params": {"table": name, "column": column, "entries": len(values)},
                }
            )

    name_column = next(
        (
            c
            for c in table["columns"]
            if c["binding"] == {"field": "name"} and c["column"] != key_letter
        ),
        None,
    )
    keyed = key_letter is not None
    skipping = False
    note_text = place.get("noteText")
    if keyed and note_text and not followed:
        skipping = True
        for letter in (key_letter, name_column["column"] if name_column else None):
            if letter is not None:
                add(
                    letter,
                    {note_text: None},
                    "rules",
                    f"The row “{note_text}” under the header is a note, not a record",
                    None,
                )
    meaning = {m["value"]: m["to"] for m in table["meaning"]} if keyed else {}
    if meaning:
        add(
            key_letter,
            meaning,
            "assistant",
            f"{len(meaning)} keys the file spells differently mean stored records",
            table["meaning"][0]["origin"],
        )
    if keyed and choices["newRecords"]["value"] == "leaveOut":
        skipping = True
        new = [key for key in computed.new_keys if key not in meaning]
        add(
            key_letter,
            {key: None for key in new},
            choices["newRecords"]["owner"],
            f"{len(new)} new keys are left out of this load",
            None,
        )
    if keyed and name_column is not None and choices["names"]["value"] == "stored":
        names = dict(computed.names)
        for match in table["meaning"]:
            cell = match.get("nameCell")
            if cell and cell != match["record"]["name"] and cell not in names:
                names[cell] = match["record"]["name"]
        add(
            name_column["column"],
            names,
            choices["names"]["owner"],
            f"{len(names)} names keep the stored spelling",
            None,
        )
        if computed.unmapped_names:
            notes.append(
                f"{len(computed.unmapped_names)} names that differ from the stored ones could not "
                "keep the stored spelling: the same text stands for different stored names or for "
                f"a new record in '{table['sheet']}'"
            )
    for fix in fixes:
        add(
            fix["column"],
            {fix["value"]: fix["to"]},
            "assistant",
            fix["reason"] or "A refused value mapped",
            fix.get("origin"),
        )
    missing = "delete" if choices["missing"]["value"] == "remove" else "report"
    if followed:
        source, differs = _profile_source(
            table, entries, skipping, missing, profile_maps, maps, csv_delimiter
        )
    else:
        source, differs = (
            _rules_source(table, entries, skipping, missing, maps, csv_delimiter),
            True,
        )
    steps.insert(
        0,
        {
            "kind": "profileSource",
            "owner": table["owner"],
            "reason": table["reason"],
            **({"origin": table["origin"]} if table["origin"] else {}),
            "params": {
                "table": name,
                "sheet": table["sheet"],
                "objectTypeKey": table["objectTypeKey"],
                "keyColumn": key_letter,
                "missing": source.get("missing") or "report",
            },
        },
    )
    return source, maps, steps, notes, differs


def _rules_source(
    table: dict[str, Any],
    entries: dict[str, dict[str, Any]],
    skipping: bool,
    missing: str,
    maps: dict[str, dict[str, Any]],
    csv_delimiter: str | None,
) -> dict[str, Any]:
    place = table["place"]
    columns = []
    for column in table["columns"]:
        if column["binding"] is None:
            continue
        binding: dict[str, Any] = {"column": column["header"], **column["binding"]}
        if column["column"] in entries:
            binding["valueMap"] = f"{table['table']}-{column['column']}"
            maps[binding["valueMap"]] = entries[column["column"]]
        columns.append(binding)
    source: dict[str, Any] = {
        "sheet": None if csv_delimiter is not None else table["sheet"],
        "headerRow": place["headerRow"],
        "applicationKey": table["applicationKey"],
        "objectTypeKey": table["objectTypeKey"],
        "record": "upsert",
        "key": dict(table["key"]),
        "columns": columns,
        "missing": missing,
    }
    if place.get("block"):
        source["block"] = {
            k: v
            for k, v in place["block"].items()
            if k in ("firstColumn", "lastColumn", "lastRow") and v is not None
        }
    if skipping:
        source["rowsWithoutKey"] = "skip"
    if table.get("parent"):
        source["parent"] = {k: v for k, v in table["parent"].items() if k != "source"}
    return {k: v for k, v in source.items() if v is not None}


def _profile_source(
    table: dict[str, Any],
    entries: dict[str, dict[str, Any]],
    skipping: bool,
    missing: str,
    profile_maps: dict[str, dict[str, Any]],
    maps: dict[str, dict[str, Any]],
    csv_delimiter: str | None,
) -> tuple[dict[str, Any], bool]:
    """The source exactly as the profile stores it (as it reads this file), with what the plan
    adds: value maps, rows without a key skipped, the records missing from the file removed, the
    columns the assistant bound. ``True`` when any of it changed the source."""
    source = copy.deepcopy(table["profileSource"])
    differs = False
    if csv_delimiter is not None:
        source["sheet"] = None
    # Columns the assistant (or the person) bound after the profile was read.
    for column in table["columns"]:
        if column["owner"] in ("assistant", "person") and column["binding"] is not None:
            source["columns"] = [
                b for b in source["columns"] if b.get("column") != column["header"]
            ] + [{"column": column["header"], **column["binding"]}]
            differs = True
    for binding in source["columns"]:
        column = next((c for c in table["columns"] if c["header"] == binding.get("column")), None)
        if column is None or column["column"] not in entries:
            continue
        name = f"{table['table']}-{column['column']}"
        previous = profile_maps.get(binding.get("valueMap") or "", {})
        maps[name] = {**previous, **entries[column["column"]]}
        binding["valueMap"] = name
        differs = True
    if source.get("key") is not None and source.get("record") != "existing":
        if missing != (source.get("missing") or "report"):
            source["missing"] = missing
            differs = True
        if skipping and source.get("rowsWithoutKey") != "skip":
            source["rowsWithoutKey"] = "skip"
            differs = True
    return source, differs
