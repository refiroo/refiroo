"""Assistant tasks as the API answers them (Product 0.16 AP6a, API.md § Loading a workbook with the
assistant)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import CollectionPage, PrincipalResponse

TaskState = Literal[
    "reading", "read", "checking", "checked", "loading", "loaded", "failed", "cancelled"
]
Owner = Literal["rules", "assistant", "person", "profile"]
Phase = Literal["profiling", "reading", "designing", "checking"]


class TaskOrigin(BaseModel):
    """Where an assistant's proposal came from (AP-D5)."""

    kind: Literal["ai"]
    provider: str
    model: str
    promptVersion: str
    confidence: float
    reason: str


class Choice(BaseModel):
    value: Any
    owner: Owner


class TaskChoices(BaseModel):
    newRecords: Choice
    names: Choice
    missing: Choice
    load: Choice


class TaskColumn(BaseModel):
    """A column of the table: what it fills (``binding``, of the kind ``kind``: ``field``,
    ``attributeTypeKey``, ``parent``, ``relation``, ``relationFlags``, ``relatedRecord``,
    ``ignore``, or ``other`` for a column read with another's binding) with a plain ``label`` of
    it, or why it is left out."""

    column: str
    header: str
    binding: dict[str, Any] | None
    kind: str | None = None
    label: str = ""
    evidence: str | None = None
    leftOut: str | None = None
    # Left out by the followed profile from the file it read before too: no decision now.
    known: bool = False
    owner: Owner
    origin: TaskOrigin | None = None


class LeftOutColumn(BaseModel):
    column: str
    header: str
    reason: str


class TableProfile(BaseModel):
    """The stored import profile a table is read by: ``source`` is the source of the profile it
    follows."""

    key: str
    name: str
    version: int
    source: int | None = None


class ReadingProfile(BaseModel):
    key: str
    name: str
    version: int


class KeyOption(BaseModel):
    column: str
    header: str
    key: dict[str, Any]
    matched: int


class MeaningMatch(BaseModel):
    value: str
    record: dict[str, str]
    to: str
    reason: str
    confidence: float
    origin: TaskOrigin


class TaskTable(BaseModel):
    """A table of the workbook: what the assistant and the rules think it is, with its evidence."""

    model_config = ConfigDict(populate_by_name=True)

    table: str
    sheet: str
    range: str | None = None
    list_: int | None = Field(default=None, alias="list")
    rows: int
    as_: Literal["update", "newData", "notData"] = Field(alias="as")
    objectTypeKey: str | None = None
    applicationKey: str | None = None
    parentTypeKeys: list[str] = []
    typeName: str | None = None
    reason: str
    evidence: str
    owner: Owner
    origin: TaskOrigin | None = None
    profile: TableProfile | None = None
    keyColumn: str | None = None
    key: dict[str, Any] | None = None
    keyOptions: list[KeyOption]
    matched: int
    new: int
    missing: int
    namesDiffer: int
    meaning: list[MeaningMatch]
    parent: dict[str, Any] | None = None
    notes: list[str] = []
    attention: list[str] = []
    leftOut: list[LeftOutColumn] = []
    columns: list[TaskColumn]
    choices: TaskChoices


class NotDataSheet(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sheet: str
    rows: int
    as_: Literal["notData"] = Field(alias="as")
    reason: str


class TitleBlock(BaseModel):
    """A block of a header with no rows below it: a title, not a table."""

    sheet: str
    range: str
    text: str


class ReadingSummary(BaseModel):
    tables: int
    sheets: int
    updates: int
    notLoaded: int
    needDecision: int
    types: int
    applications: int


class TaskReading(BaseModel):
    tables: list[TaskTable]
    sheets: list[NotDataSheet]
    titles: list[TitleBlock] = []
    profile: ReadingProfile | None = None
    summary: ReadingSummary | None = None


class PlanStep(BaseModel):
    kind: Literal["profileSource", "valueMap", "destination"]
    owner: Owner
    reason: str
    origin: TaskOrigin | None = None
    params: dict[str, Any]


class TaskPlan(BaseModel):
    profile: dict[str, Any]
    steps: list[PlanStep]


class RefusedGroup(BaseModel):
    code: str | None
    rows: int
    column: str | None = None
    header: str | None = None
    values: list[dict[str, Any]] | None = None
    message: str | None = None


class CheckTable(BaseModel):
    table: str
    sheet: str
    typeName: str | None
    rows: int
    changed: int
    unchanged: int
    created: int
    removed: int
    skipped: int
    translations: int = 0
    nothingToDo: bool = False
    refused: list[RefusedGroup]
    leftOut: list[str]


class CheckFix(BaseModel):
    table: str
    column: str
    value: str
    to: str | None
    reason: str
    origin: TaskOrigin | None = None


class CheckSummary(BaseModel):
    changed: int
    unchanged: int
    created: int
    removed: int
    refused: int
    translations: int
    tablesWithChanges: int


class TaskCheck(BaseModel):
    dryRunJobId: str
    ranAt: str
    tables: list[CheckTable]
    summary: CheckSummary | None = None
    fixes: list[CheckFix]
    rounds: int


class DesignQuestion(BaseModel):
    text: str
    options: list[str] = []
    assumed: str | None = None


class DesignRecord(BaseModel):
    """A record the structure needs that no row gives (a domain, a list, a language, a system)."""

    ref: str
    objectTypeKey: str
    applicationKey: str | None = None
    name: str
    attributes: dict[str, Any] = {}
    parent: dict[str, str] | None = None


class TaskDesign(BaseModel):
    """The assistant's design (0.16 AP6): what the workbook is, the model-draft operations applied
    to the task's draft, the records the structure needs, the profile of the person's sheets, the
    questions with the option assumed, the person's answers and the engine's last outcome."""

    summary: str = ""
    operations: list[dict[str, Any]] = []
    records: list[DesignRecord] = []
    profile: dict[str, Any] | None = None
    # Relationships between the records two queries find (``{relationTypeKey, from, to, reason}``).
    links: list[dict[str, Any]] = []
    questions: list[DesignQuestion] = []
    answers: dict[str, str] = {}
    rounds: int = 0
    origin: dict[str, Any] | None = None
    outcome: dict[str, Any] | None = None
    # The columns of the sheets the design reads that no source loads, each with the assistant's
    # reason (``{sheet, column, reason}``; ``reason`` null when it gave none).
    leftOut: list[dict[str, Any]] = []
    # 0.16 AP6r: ``model`` while the steward shapes the proposed model, ``load`` once accepted.
    stage: Literal["model", "load"] = "load"
    # The proposed model in a steward's words: ``{objectTypeKey, text}`` per type.
    outline: list[dict[str, Any]] = []
    # The engine's design checks: ``{id, kind, text, open, explanation?}``.
    checks: list[dict[str, Any]] = []
    # The steward's corrections in words, the newest last.
    corrections: list[str] = []
    # While a session works: ``{now, seconds, refused, milestones: [{key, label, done, times}]}``.
    progress: dict[str, Any] | None = None
    # The Claude Code session working on this design.
    agentSession: str | None = None


class DesignSheet(BaseModel):
    # The source's index in the dry run's profile: ``GET /ai/tasks/{id}/changes?source=`` pages its
    # changed records.
    source: int | None = None
    sheet: str | None
    objectTypeKey: str | None
    structure: bool = False
    rows: int
    created: int
    updated: int
    unchanged: int
    refused: int
    # Rows of a source that skips rows without a key the dry run wrote nothing for.
    skipped: int = 0


class DesignCheck(BaseModel):
    """A design's dry run of every row of the working copy against the draft, per sheet, with
    what it refused by code and three examples each."""

    dryRunJobId: str | None
    ranAt: str
    sheets: list[DesignSheet]
    refused: list[dict[str, Any]]
    # Each relationship rule with how many records each side finds and the pairs it makes.
    links: list[dict[str, Any]] = []
    summary: dict[str, int]
    rounds: int


class TaskNote(BaseModel):
    kind: Literal["note", "warning", "refused"]
    text: str
    at: str


class TaskResult(BaseModel):
    changeSetId: str
    # The release a design's draft was installed as and activated in the workspace (0.16 AP6).
    releaseId: str | None = None
    # The batch writing a design's relationships into the change set after its import.
    linksJobId: str | None = None
    changeSetName: str | None = None
    importJobId: str | None = None
    profileKey: str | None = None
    counts: dict[str, int] | None = None


class AiTaskResponse(BaseModel):
    """An assistant task: the workbook, the reading per table, the plan, the latest check and the
    result of the load."""

    id: str
    workspaceKey: str
    fileName: str
    sourceFileId: str
    words: str | None
    state: TaskState
    version: int
    jobId: str | None
    phase: Phase | None
    createdAt: datetime
    updatedAt: datetime
    requestedBy: PrincipalResponse | None
    reading: TaskReading | None
    plan: TaskPlan | None
    check: TaskCheck | DesignCheck | None
    design: TaskDesign | None = None
    # The task's draft of the workspace's model (0.16 AP6), opened in the model editor.
    draftId: str | None = None
    notes: list[TaskNote]
    result: TaskResult | None


class AiTaskPage(CollectionPage[AiTaskResponse]):
    pass


class FieldChange(BaseModel):
    field: str
    label: str
    now: Any
    after: Any


class TaskChange(BaseModel):
    recordId: str
    name: str | None
    table: str
    fields: list[FieldChange]


class TaskChangePage(CollectionPage[TaskChange]):
    pass
