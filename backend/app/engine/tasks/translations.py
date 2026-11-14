"""A column of translations (Product 0.16 AP6a, J50.14).

A textual column the rules would otherwise leave out is a **translation** when the model gives the
column's type exactly one related-record structure (a relationship it may hold to a type that is
contained in a parent type, ``catalog.Related``) and the column's header names a language: a stored
record of one of that type's parent types named as the header (case and punctuation ignored), else a
language word of the header. It is bound as the inference binds translations: a related record of
the structure's type under the language's record, filled with the cell, the language's record
created when it is missing and may stand at the top. Several structures, or none, leave the column
out with the reason saying which; the assistant's ``translationColumn`` is checked against the same
structure.
"""

import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..sources.inference.patterns import header_language, is_language
from .catalog import Related, TypeInfo, normal

TEXT_TYPES = ("text", "longText")


@dataclass(frozen=True)
class Bound:
    binding: dict[str, Any]
    evidence: str


def structure(info: TypeInfo) -> tuple[Related | None, str | None]:
    """The type's one related-record structure, or why it has none."""
    if not info.related:
        return None, (
            f"{info.label} may hold no relationship to a type contained in a parent, so a column "
            "of translations has nowhere to go; it is left out of this load"
        )
    if len(info.related) > 1:
        names = ", ".join(f"“{r.relation_name}” to {r.type_label}" for r in info.related)
        return None, (
            f"{info.label} has several relationships to records contained in a parent ({names}): "
            "the model does not say which holds translations, so the column is left out of this load"
        )
    return info.related[0], None


def language_of(header: str) -> str | None:
    """The language the header names: the header itself when it is a language, else its language
    word."""
    stripped = header.strip()
    return stripped if is_language(stripped) else header_language(header)


# Letters and digits only, as a column header names a parent loosely: one of five comparisons of a
# name kept apart on purpose (see ``matching._FACTS``).
_NAMED = """
SELECT DISTINCT object_type_key, name FROM objects
WHERE workspace_key = :workspace AND object_type_key = ANY(:types)
  AND regexp_replace(lower(name), '[^0-9a-z]', '', 'g') = :wanted
ORDER BY object_type_key, name
"""


def named_parents(
    session: Session, workspace: str, related: Related, header: str
) -> list[tuple[str, str]]:
    """The stored records of the structure's parent types named as ``header``: (type, name)."""
    wanted = normal(header)
    if not wanted:
        return []
    return [
        (type_key, name)
        for type_key, name in session.execute(
            text(_NAMED),
            {"workspace": workspace, "types": [p[0] for p in related.parents], "wanted": wanted},
        )
    ]


def bind(
    session: Session,
    workspace: str,
    info: TypeInfo,
    related: Related,
    header: str,
    language: str | None,
    group: str | None,
) -> Bound | str:
    """The related-record binding of a column headed ``header`` that holds ``language``'s
    translations; ``group`` is the parent type the table's other language columns use. A string is
    the reason the column cannot be read as translations."""
    found = named_parents(session, workspace, related, header)
    if language is not None and language != header.strip():
        found = found or named_parents(session, workspace, related, language)
    by_type = {type_key for type_key, _ in found}
    if len(by_type) > 1:
        return (
            f"'{header}' names records of several types ({', '.join(sorted(by_type))}); which "
            "holds this language is not decided, so the column is left out of this load"
        )
    created = False
    if found:
        group_key, value = found[0]
    else:
        if language is None:
            return ""
        top = [key for key, _, top in related.parents if top]
        group_key = group if group in top else (top[0] if len(top) == 1 else None)
        if group_key is None:
            label = " or ".join(label for _, label, _ in related.parents)
            return (
                f"'{header}' names a language, but no {label} record is named “{language}” and "
                + (
                    "the language's records cannot be created at the top"
                    if not top
                    else "more than one type could hold it"
                )
                + "; the column is left out of this load"
            )
        value, created = language, True
    parents = {key: (label, top) for key, label, top in related.parents}
    label, top = parents[group_key]
    parent: dict[str, Any] = {
        "objectTypeKey": group_key,
        "matchBy": {"field": "name"},
        "value": value,
    }
    if top:
        parent["missing"] = "create"
    binding = {
        "relatedRecord": {
            "relationTypeKey": related.relation,
            "applicationKey": related.application,
            "objectTypeKey": related.type_key,
            "parent": parent,
            "field": "name",
        }
    }
    said = f"“{value}” is created" if created else f"the stored {label} “{value}”"
    return Bound(
        binding,
        f"{header}: the {language or value} names of each {info.label}, as translations: "
        f"{related.type_label} records under {said}",
    )


def apply(session: Session, workspace: str, info: TypeInfo, columns: list[dict[str, Any]]) -> None:
    """Read the textual ``columns`` that name a language (columns the rules left out, as column
    dictionaries of a table) as translations, or say why they cannot be; the others stay."""
    candidates = [
        c
        for c in columns
        if c["binding"] is None
        and c["owner"] == "rules"
        and c.get("valueType") in TEXT_TYPES
        and (language_of(c["header"]) is not None)
    ]
    if not candidates:
        return
    related, why = structure(info)
    if related is None:
        for column in candidates:
            column["leftOut"] = why
        return
    # Language records the table's columns name that exist stand under one parent type.
    group = None
    for column in candidates:
        named = named_parents(session, workspace, related, column["header"])
        if named:
            group = named[0][0]
            break
    for column in candidates:
        result = bind(
            session,
            workspace,
            info,
            related,
            column["header"],
            language_of(column["header"]),
            group,
        )
        if isinstance(result, Bound):
            column["binding"] = result.binding
            column["leftOut"] = None
            column["evidence"] = result.evidence
        elif result:
            column["leftOut"] = result


def check_language(
    session: Session,
    workspace: str,
    info: TypeInfo,
    table_columns: list[dict[str, Any]],
    column: dict[str, Any],
    language: str,
) -> Bound | str:
    """What ``translationColumn`` would bind, or why it is refused: the same structure and the
    language's record as for a column the rules read."""
    related, why = structure(info)
    if related is None:
        return why or ""
    if not re.search(r"\w", language):
        return "A language is named"
    group = next(
        (
            named[0][0]
            for other in table_columns
            if other is not column
            and isinstance(other.get("binding"), dict)
            and "relatedRecord" in other["binding"]
            and (named := named_parents(session, workspace, related, other["header"]))
        ),
        None,
    )
    return bind(session, workspace, info, related, column["header"], language.strip(), group) or (
        f"No record is named “{language}” and none can be created for it"
    )
