"""The table patterns (Product 0.10 A6, D90): fixed rules over a workbook's statistics and the facts
between its columns, each finding a pattern with the columns and the evidence it rests on.

A rule reads a :class:`~.facts.Workbook`, never the database, and claims the columns it explains, so
a later rule does not explain them again. The rules run in a fixed order per sheet: translations
of another sheet's records, the key and the name, flag columns, code and name pairs, level
columns, a repeated parent, multi-valued cells, references to another sheet, translations by column,
text lookups, external IDs, and every remaining column as an attribute; then placeholders and name
drift for the columns found, and a navigation group per sheet that proposes two or more lists.

The thresholds are stated in MODEL_AUTHORING's pattern catalogue so a test names what a rule finds.
Scored similarity is deliberately absent: the same workbook always gives the same findings.
"""

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from .facts import Column, Table, Workbook

# D90's thresholds.
NAME_FILLED = 0.95
LOOKUP_DISTINCT = 50
LOOKUP_SHARE = 0.20
PAIR_NAMES_PER_CODE = 1.5
PARENT_GROUPS_SHARE = 1 / 3
CONSTANT_SHARE = 0.98
REFERENCE_SHARE = 0.90
SPLIT_CELLS = 0.10
SPLIT_FOUND = 0.80
# Translations found by their values (2026-10-14): a column with about as many values as its base
# (within these shares), one value per base value and the other way round, mostly different.
ALIGNED_DISTINCT = (0.8, 1.25)
ALIGNED_SHARE = 0.8
ALIGNED_SAME = 0.5
FLAG_VOCABULARIES = (
    frozenset({"y", "n"}),
    frozenset({"yes", "no"}),
    frozenset({"x"}),
    frozenset({"true", "false"}),
    frozenset({"1", "0"}),
)
# ISO 639-1 codes and the English names of languages (D90): the only words the rules know beyond the
# placeholders (D70) and D97's three.
LANGUAGE_CODES = frozenset(
    ["aa", "ab", "af", "ak", "am", "an", "ar", "as", "av", "ay", "az", "ba", "be", "bg", "bh", "bi", "bm", "bn", "bo", "br", "bs", "ca", "ce", "ch", "co", "cr", "cs", "cu", "cv", "cy", "da", "de", "dv", "dz", "ee", "el", "en", "eo", "es", "et", "eu", "fa", "ff", "fi", "fj", "fo", "fr", "fy", "ga", "gd", "gl", "gn", "gu", "gv", "ha", "he", "hi", "ho", "hr", "ht", "hu", "hy", "hz", "ia", "id", "ie", "ig", "ii", "ik", "io", "is", "it", "iu", "ja", "jv", "ka", "kg", "ki", "kj", "kk", "kl", "km", "kn", "ko", "kr", "ks", "ku", "kv", "kw", "ky", "la", "lb", "lg", "li", "ln", "lo", "lt", "lu", "lv", "mg", "mh", "mi", "mk", "ml", "mn", "mr", "ms", "mt", "my", "na", "nb", "nd", "ne", "ng", "nl", "nn", "no", "nr", "nv", "ny", "oc", "oj", "om", "or", "os", "pa", "pi", "pl", "ps", "pt", "qu", "rm", "rn", "ro", "ru", "rw", "sa", "sc", "sd", "se", "sg", "si", "sk", "sl", "sm", "sn", "so", "sq", "sr", "ss", "st", "su", "sv", "sw", "ta", "te", "tg", "th", "ti", "tk", "tl", "tn", "to", "tr", "ts", "tt", "tw", "ty", "ug", "uk", "ur", "uz", "ve", "vi", "vo", "wa", "wo", "xh", "yi", "yo", "za", "zh", "zu"]
)
LANGUAGE_NAMES = frozenset(
    ["arabic", "bulgarian", "chinese", "croatian", "czech", "danish", "dutch", "english", "estonian", "finnish", "french", "german", "greek", "hebrew", "hindi", "hungarian", "icelandic", "indonesian", "irish", "italian", "japanese", "korean", "latvian", "lithuanian", "maltese", "norwegian", "polish", "portuguese", "romanian", "russian", "serbian", "slovak", "slovenian", "spanish", "swedish", "thai", "turkish", "ukrainian", "vietnamese", "welsh"]
)
_LEVEL = re.compile(r"^(.*?)\s*(\d+)$")
_TRANSLATED = re.compile(r"^(?P<base>.+?)[\s_\-]*[\(\[]?(?P<language>[A-Za-z]+)[\)\]]?$")


def fold(label: str) -> str:
    """A name compared as D91 compares names: case, accents and punctuation folded, a final plural
    ``s`` of each word dropped."""
    ascii_text = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
    words = re.findall(r"[a-z0-9]+", ascii_text)
    return " ".join(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words)


def is_language(value: str) -> bool:
    folded = value.strip().lower()
    return folded in LANGUAGE_CODES or folded in LANGUAGE_NAMES


@dataclass
class Finding:
    pattern: str
    sheet: str
    # Column numbers, in the order the pattern names them.
    columns: list[int]
    evidence: dict[str, Any]
    # What the builder needs beyond the columns (the rule's own terms).
    detail: dict[str, Any] = field(default_factory=dict)


def evidence_of(column: Column) -> dict[str, Any]:
    return {
        "column": column.header,
        "letter": column.letter,
        "rows": column.rows,
        "filled": column.filled,
        "distinct": column.distinct,
        "values": list(column.values[:5]),
    }


class _Sheet:
    """One table with the columns claimed so far."""

    def __init__(self, table: Table) -> None:
        self.table = table
        self.by_number = {c.number: c for c in table.columns}
        self.claimed: set[int] = set()
        self.key: Column | None = None
        self.name: Column | None = None

    def free(self) -> list[Column]:
        return [c for c in self.table.columns if c.number not in self.claimed]

    def claim(self, *columns: Column) -> None:
        self.claimed |= {c.number for c in columns}

    def finding(self, pattern: str, columns: Sequence[Column], **detail: Any) -> Finding:
        evidence = detail.pop("evidence", {})
        return Finding(
            pattern,
            self.table.name,
            [c.number for c in columns],
            {"columns": [evidence_of(c) for c in columns], **evidence},
            detail,
        )


def find(workbook: Workbook) -> list[Finding]:
    """Every pattern the workbook holds, in the order a draft would take them."""
    sheets = [_Sheet(table) for table in workbook.sheets]
    for sheet in sheets:
        sheet.key = key_column(sheet.table.columns)
        if sheet.key is not None:
            sheet.name = name_column(sheet.table, sheet.key)
        # D99: a text key leaving the rows without a name, beside a GUID ID: the ID is the key and
        # the text the name, as in a list of an ID and a name (a record needs a name).
        guid = next((c for c in sheet.table.columns if c.candidate_key and c.guid), None)
        if sheet.key is not None and sheet.name is None and guid is not None and sheet.key.textual:
            sheet.key, sheet.name = guid, sheet.key
    findings: list[Finding] = []
    for sheet in sheets:
        translations = _translations_by_row(sheet, sheets, workbook)
        if translations is not None:
            findings.append(translations)
            continue
        if sheet.key is None:
            continue
        found: list[Finding] = []
        named = [sheet.key] + ([sheet.name] if sheet.name else [])
        sheet.claim(*named)
        found.append(sheet.finding("keyColumn", named, evidence={"key": evidence_of(sheet.key)}))
        # Claimed before the other rules read them, proposed after what they translate.
        aligned = _aligned_translations(sheet)
        found += _flags(sheet)
        found += _pairs(sheet)
        found += _levels(sheet)
        found += _parents(sheet)
        found += _multi_valued(sheet)
        found += _references(sheet, sheets, workbook)
        found += _translations_by_column(sheet)
        found += _lookups(sheet)
        found += _external_ids(sheet)
        found += _attributes(sheet)
        findings += _with_values(sheet, found) + aligned
    for sheet in sheets:
        lists = [f for f in findings if f.sheet == sheet.table.name and f.pattern in LIST_PATTERNS]
        if len(lists) >= 2:
            findings.append(
                Finding(
                    "navigationGroup",
                    sheet.table.name,
                    [],
                    {"lists": len(lists), "sheet": sheet.table.name},
                    {"lists": lists},
                )
            )
    return findings


# Patterns whose proposal adds a list type.
LIST_PATTERNS = ("textLookup", "codeAndName", "flagColumns", "multiValued")


def key_column(columns: Sequence[Column]) -> Column | None:
    """D90: a candidate key, text without spaces or integer, not a GUID; the leftmost. Without one,
    a GUID filled and different on every row (D99: lists of an ID and a name)."""
    for column in columns:
        if not column.candidate_key or column.guid:
            continue
        if column.all("integer") or (column.textual and not column.spaced):
            return column
    return next((c for c in columns if c.candidate_key and c.guid), None)


def _lookup_like(column: Column) -> bool:
    return column.distinct <= LOOKUP_DISTINCT and column.distinct <= LOOKUP_SHARE * max(column.filled, 1)


def name_column(table: Table, key: Column) -> Column | None:
    """D90: a text column filled on 95% of rows that reads neither as a lookup nor a code; a header
    holding the word name first, else the leftmost."""
    candidates = [
        c
        for c in table.columns
        if c.number != key.number
        and c.textual
        and not c.code_like
        and c.filled >= NAME_FILLED * max(table.rows, 1)
        and not _lookup_like(c)
    ]
    named = [c for c in candidates if "name" in fold(c.header).split()]
    return (named or candidates or [None])[0]


def _flag(column: Column) -> frozenset[str] | None:
    if column.filled == 0 or column.distinct > 2 or len(column.values) < column.distinct:
        return None
    seen = frozenset(str(v["value"]).strip().lower() for v in column.values)
    return next((vocabulary for vocabulary in FLAG_VOCABULARIES if seen <= vocabulary), None)


def _split(sheet: _Sheet, column: Column) -> dict[str, Any] | None:
    """D90: a delimiter in at least 10% of the cells whose parts are at least 80% values found whole
    in the column."""
    if not column.textual:
        return None
    for entry in column.delimiters:
        if entry["share"] < SPLIT_CELLS:
            continue
        total, found = sheet.table.split_parts(column.number, entry["character"])
        if total and found / total >= SPLIT_FOUND:
            return {"delimiter": entry["character"], "share": entry["share"], "partsFound": round(found / total, 3)}
    return None


def _flags(sheet: _Sheet) -> list[Finding]:
    """D90, D101: the columns of a sheet whose every cell is one of the same yes/no vocabulary form
    one set, adjacent or not; a multi-valued column beside one of them joins it (D97)."""
    sets: dict[frozenset[str], list[Column]] = {}
    for column in sheet.free():
        vocabulary = _flag(column)
        if vocabulary is not None:
            sets.setdefault(vocabulary, []).append(column)
    found = []
    for run in (r for r in sets.values() if len(r) >= 2):
        joined = None
        for number in (n for c in run for n in (c.number + 1, c.number - 1)):
            neighbour = sheet.by_number.get(number)
            if neighbour is not None and neighbour.number not in sheet.claimed and neighbour not in run:
                split = _split(sheet, neighbour)
                if split is not None:
                    joined = (neighbour, split)
                    break
        columns = run + ([joined[0]] if joined else [])
        sheet.claim(*columns)
        evidence = {
            "flags": [c.header for c in run],
            "vocabulary": sorted(_flag(run[0]) or ()),
            "joined": joined[0].header if joined else None,
            **({"split": joined[1]} if joined else {}),
        }
        found.append(
            sheet.finding(
                "flagColumns",
                columns,
                evidence=evidence,
                flags=[c.number for c in run],
                joined=joined[0].number if joined else None,
                delimiter=joined[1]["delimiter"] if joined else None,
            )
        )
    return found


def _pairs(sheet: _Sheet) -> list[Finding]:
    """D90: a code-like column and a text column with at most 1.5 names per code, each name with
    one code in 98% of its groups."""
    found = []
    for code in sheet.free():
        if not code.code_like or code.candidate_key or code.distinct < 2 or code.number in sheet.claimed:
            continue
        names = [
            c
            for c in sheet.free()
            if c.number != code.number
            and c.textual
            and not c.code_like
            and not c.prose
            and code.distinct <= c.distinct <= PAIR_NAMES_PER_CODE * code.distinct
        ]
        names.sort(key=lambda c: abs(c.number - code.number))
        for name in names:
            pairs = sheet.table.pairs(code.number, name.number)
            if pairs > PAIR_NAMES_PER_CODE * code.distinct:
                continue
            constant = sheet.table.constant_within(name.number, [code.number]).get(code.number, 0)
            if constant < CONSTANT_SHARE * name.distinct:
                continue
            drift = sheet.table.names_per_code(code.number, name.number)
            sheet.claim(code, name)
            found.append(
                sheet.finding(
                    "codeAndName",
                    [code, name],
                    evidence={
                        "code": code.header,
                        "name": name.header,
                        "codes": code.distinct,
                        "names": name.distinct,
                        "namesPerCode": round(pairs / code.distinct, 2),
                        "drift": drift,
                    },
                    code=code.number,
                    name=name.number,
                    drift=drift,
                )
            )
            break
    return found


def _parents(sheet: _Sheet) -> list[Finding]:
    """D90: a text column with at most a third as many values as rows grouping other columns that
    are constant within 98% of its groups."""
    found = []
    rows = max(sheet.table.rows, 1)
    for group in sheet.free():
        if group.number in sheet.claimed or not group.textual or group.code_like or group.candidate_key:
            continue
        # D102: sentences repeated over rows are a shared description, not a parent.
        if group.prose:
            continue
        if not 2 <= group.distinct <= PARENT_GROUPS_SHARE * rows:
            continue
        others = [c for c in sheet.free() if c.number != group.number and c.distinct > 1 and not c.candidate_key]
        constant = sheet.table.constant_within(group.number, [c.number for c in others])
        dependents = [c for c in others if constant.get(c.number, 0) >= CONSTANT_SHARE * group.distinct]
        if not dependents:
            continue
        key = next(
            (c for c in dependents if c.distinct == group.distinct and (c.guid or c.code_like or c.all("integer"))),
            None,
        )
        if key is not None and key.all("integer"):
            key = next((c for c in dependents if c.distinct == group.distinct and (c.guid or c.code_like)), key)
        sheet.claim(group, *dependents)
        found.append(
            sheet.finding(
                "repeatedParent",
                [group, *dependents],
                evidence={
                    "groups": group.distinct,
                    "dependents": [{"column": c.header, "constantIn": constant.get(c.number, 0)} for c in dependents],
                    "key": key.header if key else None,
                },
                group=group.number,
                dependents=[c.number for c in dependents],
                key=key.number if key else None,
            )
        )
    return found


def _levels(sheet: _Sheet) -> list[Finding]:
    """D90: headers differing only by a number (Level 1, Level 2, …), or a column whose values are
    90% the sheet's own keys."""
    found = []
    groups: dict[str, list[tuple[int, Column]]] = {}
    for column in sheet.free():
        match = _LEVEL.match(column.header)
        if match and column.textual:
            groups.setdefault(fold(match.group(1)), []).append((int(match.group(2)), column))
    for members in groups.values():
        members.sort(key=lambda m: m[0])
        if len(members) >= 2 and [m[0] for m in members] == list(range(members[0][0], members[0][0] + len(members))):
            columns = [m[1] for m in members]
            sheet.claim(*columns)
            found.append(
                sheet.finding("levelColumns", columns, evidence={"levels": len(columns)}, levels=[c.number for c in columns])
            )
    if sheet.key is not None:
        for column in sheet.free():
            if column.candidate_key:
                continue
            share = _overlap(column, sheet.table.name, sheet.key.letter)
            if share >= REFERENCE_SHARE:
                sheet.claim(column)
                found.append(
                    sheet.finding(
                        "levelColumns",
                        [column],
                        evidence={"parentOf": sheet.key.header, "share": share},
                        parent_code=column.number,
                    )
                )
    return found


def _overlap(column: Column, sheet: str, letter: str) -> float:
    return max(
        (o["share"] for o in column.overlaps if o.get("sheet") == sheet and o.get("column") == letter),
        default=0.0,
    )


def _multi_valued(sheet: _Sheet) -> list[Finding]:
    found = []
    for column in sheet.free():
        split = _split(sheet, column)
        if split is not None:
            sheet.claim(column)
            found.append(sheet.finding("multiValued", [column], evidence=split, delimiter=split["delimiter"]))
    return found


def _references(sheet: _Sheet, sheets: list[_Sheet], workbook: Workbook) -> list[Finding]:
    """D90: 90% of a column's distinct values in another sheet's key column, or its name column
    (D99: a list keyed by an ID is referred to by its names)."""
    found = []
    for column in sheet.free():
        for other in sheets:
            if other is sheet or other.key is None:
                continue
            for target, by_name in ((other.key, False), (other.name, True)):
                if target is None:
                    continue
                share = _overlap(column, other.table.name, target.letter)
                if share >= REFERENCE_SHARE:
                    break
            else:
                continue
            sheet.claim(column)
            found.append(
                sheet.finding(
                    "sheetReference",
                    [column],
                    evidence={"sheet": other.table.name, "column": target.header, "share": share},
                    target=other.table.name,
                    by_name=by_name,
                )
            )
            break
    return found


def _translations_by_row(sheet: _Sheet, sheets: list[_Sheet], workbook: Workbook) -> Finding | None:
    """D90: a column of two or more language codes or names, and a column repeating another sheet's
    key once per language; the column named as that sheet's name holds the translated names."""
    if sheet.key is not None:
        return None
    languages = [
        c
        for c in sheet.table.columns
        if c.distinct >= 2
        and len(c.values) >= c.distinct
        and all(is_language(str(v["value"])) for v in c.values)
    ]
    if not languages:
        return None
    language = languages[0]
    for column in sheet.table.columns:
        if column.number == language.number:
            continue
        for other in sheets:
            if other is sheet or other.key is None or other.name is None:
                continue
            share = _overlap(column, other.table.name, other.key.letter)
            if share < REFERENCE_SHARE or sheet.table.pairs(column.number, language.number) != column.filled:
                continue
            name = next(
                (c for c in sheet.table.columns if c.number not in (column.number, language.number) and fold(c.header) == fold(other.name.header)),
                None,
            )
            if name is None:
                continue
            columns = [column, language, name]
            sheet.claim(*columns)
            return sheet.finding(
                "translationsByRow",
                columns,
                evidence={
                    "reference": {"sheet": other.table.name, "column": other.key.header, "share": share},
                    "languages": [str(v["value"]) for v in language.values],
                    "name": name.header,
                },
                target=other.table.name,
                reference=column.number,
                language=language.number,
                name=name.number,
            )
    return None


def _translations_by_column(sheet: _Sheet) -> list[Finding]:
    """D90: headers differing only by a language suffix, translating the name column."""
    if sheet.name is None:
        return []
    columns = []
    for column in sheet.free():
        match = _TRANSLATED.match(column.header)
        if match and is_language(match.group("language")) and fold(match.group("base")) == fold(sheet.name.header):
            columns.append((column, match.group("language")))
    if not columns:
        return []
    sheet.claim(*(c for c, _ in columns))
    return [
        sheet.finding(
            "translationsByColumn",
            [c for c, _ in columns],
            evidence={"name": sheet.name.header, "languages": [language for _, language in columns]},
            languages={c.number: language for c, language in columns},
        )
    ]


def _aligned_translations(sheet: _Sheet) -> list[Finding]:
    """D100: columns translating another by their values, wherever they stand and whatever their
    headers say: about as many values as the base (within ``ALIGNED_DISTINCT``), one value per base
    value and one base value per value (80% of each: translators split and merge a few), and at
    most half the rows the same. The base's
    values repeat: two columns of all different values match one to one whatever they hold. The base
    is the leftmost of such a set; the k-th translation of every base is in the k-th language, named
    by its header's language word when it has one."""
    candidates = [
        c
        for c in sheet.table.columns
        if c.number not in sheet.claimed or (sheet.name is not None and c.number == sheet.name.number)
    ]
    candidates = [c for c in candidates if c.textual and not c.code_like and c.distinct >= 2]
    taken: set[int] = set()
    found = []
    for base in candidates:
        if base.number in taken or base.distinct >= base.filled:
            continue
        low, high = ALIGNED_DISTINCT
        aligned = []
        for other in candidates:
            if other.number <= base.number or other.number in taken or other.number == getattr(sheet.name, "number", None):
                continue
            if not low * base.distinct <= other.distinct <= high * base.distinct:
                continue
            within = sheet.table.constant_within(base.number, [other.number]).get(other.number, 0)
            back = sheet.table.constant_within(other.number, [base.number]).get(base.number, 0)
            if within < ALIGNED_SHARE * base.distinct or back < ALIGNED_SHARE * other.distinct:
                continue
            if sheet.table.same(base.number, other.number) > ALIGNED_SAME * min(base.filled, other.filled):
                continue
            aligned.append(other)
        if not aligned:
            continue
        taken |= {base.number, *(c.number for c in aligned)}
        sheet.claim(*aligned)
        languages = {c.number: _language_of(c.header, index) for index, c in enumerate(aligned)}
        found.append(
            sheet.finding(
                "translationsByColumn",
                aligned,
                evidence={"name": base.header, "languages": list(languages.values()), "byValues": True},
                base=base.number,
                languages=languages,
            )
        )
    return found


def _language_of(header: str, index: int) -> str:
    """A translation column's language: a language word of its header, else the index-th
    translation language (the administrator names it in the editor)."""
    match = _TRANSLATED.match(header)
    if match and match.group("base").strip() and is_language(match.group("language")):
        return match.group("language")
    words = re.findall(r"[A-Za-z]+", header)
    return next((w for w in reversed(words) if len(w) > 2 and is_language(w)), f"Language {index + 1}")


def _lookups(sheet: _Sheet) -> list[Finding]:
    """D90: text with at most 50 values that are at most 20% of its filled cells."""
    found = []
    for column in sheet.free():
        if column.textual and not column.prose and column.distinct >= 2 and _lookup_like(column) and _flag(column) is None:
            sheet.claim(column)
            share = round(column.distinct / max(column.filled, 1), 3)
            found.append(sheet.finding("textLookup", [column], evidence={"distinct": column.distinct, "share": share}))
    return found


def _external_ids(sheet: _Sheet) -> list[Finding]:
    """D90: every cell a GUID."""
    found = []
    for column in sheet.free():
        if column.guid:
            sheet.claim(column)
            found.append(sheet.finding("externalId", [column], evidence={"guids": column.guids, "unique": column.candidate_key}))
    return found


def _attributes(sheet: _Sheet) -> list[Finding]:
    """Every remaining column: an attribute of the sheet's type, of the value type its cells read
    as, unique when it is a candidate key; a lone yes/no column is a yes/no attribute reading its
    words through a value map."""
    found = []
    for column in sheet.free():
        sheet.claim(column)
        vocabulary = _flag(column)
        if vocabulary is not None and not column.all("boolean"):
            found.append(
                sheet.finding(
                    "attribute",
                    [column],
                    evidence={"valueType": "boolean", "unique": False, "vocabulary": sorted(vocabulary)},
                    vocabulary=sorted(vocabulary),
                )
            )
            continue
        found.append(
            sheet.finding(
                "attribute",
                [column],
                evidence={"valueType": column.value_type(), "unique": column.candidate_key},
            )
        )
    return found


def _with_values(sheet: _Sheet, found: list[Finding]) -> list[Finding]:
    """The sheet's findings with placeholders (D70) after the lookup or attribute holding them, and
    name drift after its code and name pair."""
    result = []
    for finding in found:
        result.append(finding)
        if finding.pattern in ("textLookup", "attribute") and finding.columns:
            column = sheet.by_number[finding.columns[0]]
            if column.placeholders:
                result.append(
                    sheet.finding(
                        "placeholders",
                        [column],
                        evidence={"placeholders": list(column.placeholders)},
                        values=[p["value"] for p in column.placeholders],
                    )
                )
        if finding.pattern == "codeAndName" and finding.detail["drift"]:
            code, name = (sheet.by_number[n] for n in finding.columns)
            result.append(
                sheet.finding(
                    "nameDrift",
                    [code, name],
                    evidence={"drift": finding.detail["drift"]},
                    drift=finding.detail["drift"],
                )
            )
    return result
