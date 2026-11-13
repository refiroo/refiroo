"""Every text the assistant is told or the person is told about it: the prompts, the refusals, and the
wording helpers (counts, losses, attribute changes)."""

import json
import logging
import re
from typing import Any

from ...model.migrations import LandingRefusal
from .sandbox import loopback

log = logging.getLogger(__name__)


log = logging.getLogger(__name__)

PROMPT_VERSION = "agent/20"
LAST_LINE = "CHANGE_SET:"
THEN_LINE = "THEN_RELEASE:"
RELEASE_LINE = "RELEASE:"
DEFAULT_WORDS = "Create a model for this or map it to the current model, and import it."
PROPOSAL = "proposal.json"
CALL = re.compile(r"(?:-X\s*(GET|POST|PUT|PATCH|DELETE)\b[^\n]*?)?/api/v1/([A-Za-z0-9_\-/{}$.]+)")


def _connection(workspace: str, url: str, *, workbook: bool = True) -> str:
    file = (
        "workbook.xlsx is the file, "
        if workbook
        else "There is no file: the words are about the stored records. "
    )
    data = "The data comes from this workbook alone. " if workbook else ""
    return (
        f"{file}model.json the workspace's model, openapi.json the API of the "
        f"engine at {url}, with the header 'Authorization: Bearer $REFIROO_TOKEN' (curl{' -k' if loopback(url) else ''} --noproxy ''). "
        "The network is reached with curl: Python cannot open a socket in the sandbox. The "
        "language of a model is components.schemas.EngineModel in openapi.json. Keep every file "
        "you make in this folder ($TMPDIR is in it) and name it by a relative path: nothing outside "
        "the folder can be read. A refused command is not the end of the turn: run it again that way. "
        f"{data}Work only in the workspace {workspace}: no other "
        "workspace is read or changed. Where the data gives one thing two names or values, that "
        "is intended: keep them all as they are, correct nothing and do not keep only the most "
        "common; say it in one line of the summary, never as a question."
    )


def _starting_point(held: dict[str, int]) -> str:
    """Whether the session adds to the model or may start anew: what the workspace holds decides."""
    total = sum(held.values())
    if total:
        return (
            f"The workspace holds {total} records in all its applications together: keep its model "
            "and add to it, unless the words ask otherwise."
        )
    return (
        "The workspace holds no records: if the words ask for a model, it may be a new one with "
        "only what this needs."
    )


_SHAPE = (
    "What the file repeats across columns or rows becomes types of its own, related to each other, "
    "unless the words ask otherwise; if you keep such a repetition flat, say so in one line of the "
    "summary."
)


_ITEMS = (
    "Load the file as the engine's batch items, not as an import profile: read the workbook in Python "
    "(layout, hidden rows and columns, blocks shifted against each other, notes), read the model and "
    "the workspace's records through the API, and change the draft where the file needs it. Write a "
    "script in your folder that turns the file into items (openapi.json, POST /batches; items only: "
    "send no batch and write nothing live): every new record gets an id you generate (uuid4) so later "
    "items can point to it; an existing record is found by reading the workspace's records and named by "
    "its ID; give each item a ref naming the cells it comes from, as Sheet!Q31:S31. Send the items to "
    "POST /model-drafts/{id}/dry-run as {workspaceKey, items} (no sourceFileId, no profile), read "
    "GET /model-drafts/{id}/dry-run until it completes, and read its items summary (per type: new, "
    "matched, changed, refused; the relationships; examples with their refs; the findings). Fix your "
    "items or the draft until nothing is refused and every finding is explained, then write the "
    "proposal. What you sent last is exactly what is loaded when the person accepts. Always send the "
    "items dry run and write the proposal, also when you believe the file is already fully in the "
    "workspace: then the draft is the workspace's current model, unchanged, every item names an "
    "existing record by its ID, and the engine's summary, not your reading, shows that everything "
    "matches and nothing is new; say that in the proposal's summary in the person's terms. A "
    "session that ends with no items sent and no proposal fails the task. An empty cell is "
    "no value: never call its row skipped or left out."
)


_QUESTIONS = (
    "Ask a question only about what the file and the words leave open, in the person's terms (what "
    "ends up in their data), the question first and each option an outcome, with the answer you "
    "assumed already in the draft and the items; never about the engine or how to load. What the data "
    "gives as it is (two names for one thing, likely typos, a repetition kept flat) and the findings "
    "are one line of the summary, never a question. The kinds of draft operation are in openapi.json."
)


_RECORDS = (
    "A record changes type and keeps its ID, values, relationships and history through a change set's "
    "restructurings or, for every record of a type, through the proposal's moves; creating new "
    "records and removing the old ones loses them. A consumer API that exposes a type the proposal "
    "moves or removes needs its contractVersion raised in the draft, and its definition to expose the "
    "new type where it exposed the old one: the engine refuses the release otherwise. A type that "
    "merges others must give their records the places they have now, their parents and "
    "relationships, or the engine refuses to move them; a migration creates no records."
)


_PARTIAL = (
    "When the words move only some of a type's records to other types, that is a partial move: put "
    "the final model in the draft, say so in the summary, and stage nothing now. Accepting is what "
    "prepares it, as steps the person takes: a release holding the final model with the old types "
    "beside it, a change set that restructures those records for review, and the release that "
    "removes the emptied types. Never tell the person to prepare a release or to restructure "
    "records by hand."
)


_WORDS = (
    "Build everything the words ask for, as they place it, also what the file has no data for (an "
    "empty type): the words go before the file's shape, and a question does not replace building. "
    "What the words name as a group holds its members as records under it; a field's candidate "
    "filter can name that group by a fixed value of an ancestor (ancestor:<type>.<field>). Say a "
    "thing cannot be built only after trying it on the draft."
)


_OWN_DRAFT = (
    "made with POST /model-drafts (name, model, and baseReleaseId the releaseId that "
    "GET /workspaces/{key}/model answers); never open the workspace's own draft (POST /workspaces/{key}/model/draft) and never "
    "use or change a draft you did not make, since it is a person's; on a later turn keep using "
    "the draft you made"
)


def propose_prompt(
    words: str | None, workspace: str, url: str, held: dict[str, int], *, workbook: bool = True
) -> str:
    check = (
        f"Build the model in a model draft of your own, {_OWN_DRAFT}, and check what you load with "
        "the draft's dry run"
        if workbook
        else f"Put any model change the words need in a model draft of your own, {_OWN_DRAFT}; if "
        "the model does not change, make no draft and write draftId null. Work out every record the words touch, and write "
        "in the summary the change as what to do, in terms of the records; stage no change set"
    )
    return (
        f"{(words or '').strip() or DEFAULT_WORDS}\n\n"
        f"{_connection(workspace, url, workbook=workbook)} {_starting_point(held)} "
        f"{_WORDS} {_RECORDS} {_PARTIAL} {_SHAPE + ' ' + _ITEMS + ' ' + _QUESTIONS + ' ' if workbook else ''}{check}; install, "
        "activate, load and publish nothing yet: the person reviews first. Then write "
        f'{PROPOSAL}: {{"draftId": {"..." if workbook else "... (null when the model does not change)"}, "title": a few words naming what the person asks for, as an instruction (for example "Move types under the person group"), "summary": two sentences a person reads, "questions": '
        '[{"text": the question itself first, at most three short sentences, "options", "assumed"}] '
        'for what only a person can decide, "moves": '
        '[{"from": a type key, "to": its type key in the draft, "attributes": [{"attributeTypeKey", '
        '"from"}]}] only for a whole type that becomes another, kept in order, "removals": '
        '[{"kind": "objectType", "application", "attribute" or "relationType", "key", "objectType" '
        '(the type that holds the field, for an attribute), "words": the person\'s own words that ask '
        "for it; for a type whose records the change set restructures into other types, also "
        "\"movedTo\": those types' keys}] listing only what the person's words explicitly ask "
        "to remove, quoted, never "
        "something you decided to drop: every other record, value, relationship and translation must "
        "come through, and a change that would lose any of them is not offered}."
    )


_PART = (
    " If instead you move part of a type's records to other types, install the draft (the final "
    "model) and a second release that holds the final model with the old types beside it, make "
    "the change set on the second release (source currentLive, modelReleaseId), restructure the "
    f"records in it, and end with the lines {LAST_LINE} <its id> and {THEN_LINE} <the final "
    "release's id>."
)


ACCEPTED = (
    "The person accepted. They may have edited the draft in the model editor: read it again. Install "
    "it as exactly one new release and do not activate it, make the change (a workbook's rows, or "
    "what the words ask of the stored records) in a new change set "
    f"on that release, do not publish it, and end with the line {LAST_LINE} <its id>.{_PART} If "
    "the words ask nothing of the stored records (no workbook rows, no record changes), the model "
    "alone changes: install exactly one new release, do not activate it, make no change set, and "
    f"end with the line {RELEASE_LINE} <its id>."
)


ACCEPTED_UNCHANGED = (
    "The person accepted. The model does not change: install no release and activate none. Make the "
    "change the words ask of the stored records in a new change set on the workspace's current live "
    "release (source currentLive), do not publish it, and end with the line "
    f"{LAST_LINE} <its id>."
)


MOVED = (
    "The person accepted. They may have edited the draft in the model editor: read it again. Install "
    "it as exactly one new release and do not activate it, and end with the line "
    f"{RELEASE_LINE} <its id>. The records of the proposal's moves are moved by a migration the "
    "person confirms: do not move or create them."
)


def reprompt(prompt: str, words: str | None) -> str:
    """The load prompt of a second try: the person's words, and that what was loaded before is gone
    (a failed load, or a change set the person discarded to say this)."""
    if not words:
        return prompt
    return (
        f"{prompt}\n\nThe person adds:\n{words}\n\nWhat you loaded before, if anything, failed or was "
        "discarded: do the load again from the start, changing the draft first if the words ask for it."
    )


def said_prompt(said: str) -> str:
    return (
        f"The person says:\n{said}\n\nThey may have edited the draft in the model editor: read it "
        f"again. Change the draft as they say (if the model does not change, there is none: change the "
        f"proposal as they say), check the records again (send the items to the dry run again) and "
        f"write {PROPOSAL} again."
    )


VOICE = (
    "Your messages are shown to the person in the app. Write them in the person's terms: the model, "
    "its types and fields, the records and the change. Never name files (such as proposal.json), JSON "
    "keys or lists (such as draftId, moves, removals or movedTo: say what they hold, in words), ids, "
    "endpoints or commands, except the closing lines the instructions "
    f"ask for ({LAST_LINE} and {THEN_LINE}). Every count you give says plainly what it counts, so "
    "nobody can read it as something else: the records the change touches are counted for the "
    'types, lists or applications it touches, named (such as "the 179 records of the 20 lists that '
    'move"), and the rest of the workspace, if you mention it, is said apart (such as "the other '
    "4478 records of the workspace are not touched\"). Never give the workspace's total as if it "
    "were the size of the change."
)


# The proposal file's own vocabulary: a sentence that names one of its keys or lists is the
# session talking about its file, not about the person's data.
_INTERNAL = re.compile(
    r"\b(draftId|movedTo|changeSetId|releaseId|thenReleaseId)\b"
    r"|\b(moves|removals|questions)\s+(list|entry|entries|array|field)\b"
    r"|\b(list|entry|entries)\s+of\s+(moves|removals)\b",
    re.IGNORECASE,
)


def without_files(line: str) -> str:
    """A line of the session's closing words without the sentences that name its own file: the
    person reads the proposal on the page, not in a folder they cannot open."""
    sentences = re.split(r"(?<=[.!?])\s+", line)
    return " ".join(s for s in sentences if PROPOSAL not in s and not _INTERNAL.search(s))


def plural(number: int, word: str) -> str:
    return f"{number:,} {word}{'' if number == 1 else 's'}"


def _binding(found: dict[str, Any]) -> tuple[bool, bool, str]:
    """What of an attribute binding is meaning, not form: required, read-only and the screen hints
    (a missing value reads as the default; the order of the list is not a change)."""
    return (
        bool(found.get("required")),
        bool(found.get("readOnly")),
        json.dumps(found.get("ui") or {}, sort_keys=True),
    )


def attribute_changes(
    names: dict[str, Any], attributes: list[dict[str, Any]], earlier: dict[str, Any]
) -> tuple[list[str], list[str], list[str]]:
    """The attributes a type gains, loses and has changed (named), comparing meaning only."""
    now = {b.get("attributeTypeKey"): _binding(b) for b in attributes}
    was = {b.get("attributeTypeKey"): _binding(b) for b in earlier.get("attributes") or []}

    def label(keys: list[Any]) -> list[str]:
        return [str(names.get(k) or k) for k in keys]

    return (
        label([k for k in now if k not in was]),
        label([k for k in was if k not in now]),
        label([k for k in now if k in was and now[k] != was[k]]),
    )


def contract_words(errors: list[Any]) -> str:
    return "; ".join(found.message for found in errors)


def contract_prompt(errors: list[Any]) -> str:
    return (
        "The engine refuses the draft for the consumers of the workspace's model: "
        f"{contract_words(errors)}. Raise the contractVersion of each consumer API named, and make "
        "its definition expose the new type where it exposed a type the proposal moves or removes. "
        f"Check the draft again and write {PROPOSAL} again."
    )


def not_its_draft_prompt() -> str:
    return (
        "The draft in your proposal is not one you made, so it is a person's and you may not "
        "propose, use or change it. Make your own model draft with POST /model-drafts (name, model, "
        "and baseReleaseId the releaseId that GET "
        "/workspaces/{key}/model answers), build the model in it, check it "
        f"with the draft's dry run, and write {PROPOSAL} again naming that draft."
    )


def refusal_words(refusals: tuple[LandingRefusal, ...], names: dict[str, str]) -> str:
    """The engine's refusals with their counts per type and a few example records."""
    return "; ".join(
        f"{found.code}: {found.message} ({found.count} record{'s' if found.count != 1 else ''}"
        + (
            f" of type '{found.type_key}' ({names[found.type_key]})"
            if found.type_key in names
            else ""
        )
        + (
            f", for example {', '.join(repr(name) for name in found.examples)}"
            if found.examples
            else ""
        )
        + ")"
        for found in refusals
    )


def refusal_prompt(words: str) -> str:
    return (
        "The engine refuses the draft for the records the workspace holds: "
        f"{words}. Change the draft so the records the proposal moves keep the places they have "
        "now: give the type they become the parents and relationships they have, as the types they "
        f"come from do. Check the draft again and write {PROPOSAL} again."
    )


REMOVAL_KINDS = ("objectType", "application", "attribute", "relationType")


def plain(text: str) -> str:
    """Text for comparing quotes: case, quote marks, punctuation and whitespace set aside."""
    return " ".join(re.sub(r"[\"'`“”‘’«».,;:!?()\[\]]+", " ", text.casefold()).split())


def counted(count: int, word: str) -> str:
    return f"{count:,} {word}{'' if count == 1 else 's'}"


_LOSS_KINDS = (("records", "record"), ("values", "value"), ("relationships", "relationship"))


def loss_words(losses: dict[str, dict[str, int]], names: dict[str, str]) -> str:
    """What a migration would lose, per type with counts, in plain words (records, values and
    relationships, translation links among them)."""
    parts = []
    for type_key, counts in sorted(losses.items()):
        things = [
            f"{counts[kind]} {word}{'s' if counts[kind] != 1 else ''}"
            for kind, word in _LOSS_KINDS
            if counts.get(kind)
        ]
        if things:
            parts.append(f"{names.get(type_key, type_key)}: {', '.join(things)}")
    return "; ".join(parts)


def type_names(*models: dict[str, Any]) -> dict[str, str]:
    """Type keys with their names, the first model's name winning."""
    names: dict[str, str] = {}
    for model in reversed(models):
        for item in model.get("objectTypes") or []:
            names[item["key"]] = item.get("name") or item["key"]
    return names


def loss_prompt(words: str) -> str:
    return (
        "The engine finds that the migration this draft needs would lose the person's data: "
        f"{words}. Nothing the person did not ask to remove may be lost: every record, value, "
        "relationship and translation comes through, except what the person's words explicitly ask "
        "to remove, which you list in removals with their words. Change the draft (and the moves, splits or "
        "conversions) so that none is lost, or, if that cannot be done, write the proposal with a "
        "question that says why. "
        f"Check the draft again and write {PROPOSAL} again."
    )
