import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { AiOrigin, AiTask, AiTaskChange, AiTaskTable, ApplicationDefinition } from "@/types";
import { AiTaskPage } from "./AiTaskPage";

vi.mock("@/api/aiClient", () => ({
  ai: { task: vi.fn(), planTask: vi.fn(), runTask: vi.fn(), cancelTask: vi.fn(), taskChanges: vi.fn() },
}));
vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { workspace: vi.fn(), job: vi.fn(), model: vi.fn() },
}));
vi.mock("@/features/jobs/useJobStream", () => ({ useJobStream: vi.fn() }));
const groups = vi.hoisted(() => ({ held: ["change-sets"] as string[] }));
vi.mock("@/features/security/permissions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/security/permissions")>()),
  useWorkspacePermissions: () => ({
    workspaceKey: "west",
    actionGroups: groups.held.map((key) => ({ key, label: key })),
    scopes: [],
  }),
}));

const origin: AiOrigin = {
  kind: "ai",
  provider: "fake",
  model: "fake-1",
  promptVersion: "v1",
  confidence: 0.86,
  reason: "The sheet lists the same codes as the stored records.",
};

const application = (key: string, name: string, groups?: { key: string; label: string; collections: string[] }[]) =>
  ({ key, name, objectTypeKeys: [], navigation: groups ? { groups } : undefined }) as unknown as ApplicationDefinition;

const applications = [
  application("rdm-systems", "RDM Systems", [
    { key: "core", label: "Core systems", collections: ["system", "interface"] },
  ]),
  application("rdm-master", "RDM Master"),
];

const column = (letter: string, header: string, leftOut: string | null = null) => ({
  column: letter,
  header,
  binding: leftOut ? null : { attributeTypeKey: header.toLowerCase() },
  kind: leftOut ? null : "attributeTypeKey",
  leftOut,
  owner: "rules" as const,
});

/** A table the rules and the assistant read as an update, as the server sends it (J50). */
const update = (extra: Partial<AiTaskTable> = {}): AiTaskTable => ({
  table: "t1",
  sheet: "Systems",
  range: "A1:D11",
  list: null,
  rows: 12,
  as: "update",
  objectTypeKey: "system",
  applicationKey: "rdm-systems",
  typeName: "System",
  reason: "Every code in the sheet is a stored system.",
  evidence: "10 of 12 codes match.",
  owner: "assistant",
  origin,
  keyColumn: "A",
  key: { attributeTypeKey: "system-code" },
  keyOptions: [
    { column: "A", header: "Code", key: { attributeTypeKey: "system-code" }, matched: 10 },
    { column: "B", header: "Name", key: { field: "name" }, matched: 9 },
  ],
  matched: 10,
  new: 2,
  missing: 3,
  namesDiffer: 2,
  meaning: [
    {
      value: "Cargo",
      record: { id: "r1", name: "Freight" },
      to: "r1",
      reason: "Cargo means freight.",
      confidence: 0.8,
      origin,
    },
  ],
  columns: [column("A", "Code"), column("B", "Name"), column("C", "Weight", "The type has no weight.")],
  parentTypeKeys: [],
  profile: null,
  parent: null,
  notes: [],
  attention: ["newKeys", "namesDiffer", "missing"],
  leftOut: [{ column: "C", header: "Weight", reason: "The type has no weight." }],
  choices: {
    newRecords: { value: "create", owner: "rules" },
    names: { value: "stored", owner: "rules" },
    missing: { value: "leave", owner: "rules" },
    load: { value: true, owner: "rules" },
  },
  ...extra,
});

const something = update({
  table: "t2",
  sheet: "Ideas",
  as: "newData",
  typeName: null,
  objectTypeKey: null,
  applicationKey: null,
  new: 0,
  missing: 0,
  namesDiffer: 0,
  meaning: [],
  keyOptions: [],
  columns: [],
  attention: ["notLoaded"],
  leftOut: [],
  reason: "Nothing stored looks like this.",
  evidence: "No code matches.",
  owner: "rules",
  origin: null,
});

const task = (extra: Partial<AiTask> = {}): AiTask => ({
  id: "task-1",
  workspaceKey: "west",
  fileName: "systems.xlsx",
  sourceFileId: "f1",
  words: null,
  state: "read",
  version: 3,
  jobId: "job-1",
  phase: null,
  createdAt: "2026-11-01T10:00:00Z",
  updatedAt: "2026-11-01T10:00:00Z",
  requestedBy: null,
  reading: {
    tables: [update(), something],
    sheets: [{ sheet: "About", rows: 4, as: "notData", reason: "A cover page with prose." }],
  },
  plan: null,
  check: null,
  notes: [],
  result: null,
  ...extra,
});

const checked = (extra: Partial<AiTask> = {}) =>
  task({
    state: "checked",
    version: 5,
    check: {
      dryRunJobId: "dry-1",
      ranAt: "2026-11-01T10:05:00Z",
      rounds: 1,
      fixes: [
        {
          table: "t1",
          column: "C",
          value: "Y",
          to: "Yes",
          reason: "Y is a yes.",
          origin,
        },
      ],
      tables: [
        {
          table: "t1",
          sheet: "Systems",
          typeName: "System",
          rows: 12,
          changed: 3,
          unchanged: 7,
          created: 2,
          removed: 0,
          skipped: 1,
          refused: [
            {
              code: "VALUE_NOT_ALLOWED",
              rows: 2,
              column: "D",
              header: "Type",
              values: [{ value: "Odd", count: 2 }],
            },
          ],
          translations: 2,
          nothingToDo: false,
          leftOut: ["Weight"],
        },
      ],
      summary: { changed: 3, unchanged: 7, created: 2, removed: 0, refused: 2, translations: 2, tablesWithChanges: 1 },
    },
    ...extra,
  });

const change: AiTaskChange = {
  recordId: "r9",
  name: "System 03",
  table: "t1",
  fields: [
    { field: "description", label: "Description", now: "Old", after: "New" },
    { field: "name", label: "Name", now: "System 03", after: "System three" },
  ],
};

function open(onNavigate = vi.fn(), onOpenWorkspace = vi.fn()) {
  render(<AiTaskPage taskId="task-1" onNavigate={onNavigate} onOpenWorkspace={onOpenWorkspace} />);
  return { onNavigate, onOpenWorkspace };
}

describe("The assistant task page (0.16 AP6a)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    groups.held = ["change-sets"];
    vi.mocked(api.workspace).mockResolvedValue({ key: "west", label: "West" } as never);
    vi.mocked(api.job).mockResolvedValue({ error: null } as never);
    vi.mocked(api.model).mockResolvedValue({ applications } as never);
    vi.mocked(ai.taskChanges).mockResolvedValue({ items: [change], nextCursor: null });
  });
  afterEach(() => vi.useRealTimers());

  it("reads the workspace's model again once a load activated a model change", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({ state: "loaded", result: { changeSetId: "cs-1", changeSetName: "Load", releaseId: "release-2" } }),
    );
    const onActiveModelChange = vi.fn();
    render(
      <AiTaskPage
        taskId="task-1"
        onNavigate={vi.fn()}
        onOpenWorkspace={vi.fn()}
        onActiveModelChange={onActiveModelChange}
      />,
    );
    await waitFor(() => expect(onActiveModelChange).toHaveBeenCalledWith("west"));
    expect(onActiveModelChange).toHaveBeenCalledTimes(1);
  });

  it("says what a running job is doing and stops it", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ state: "reading", phase: "designing", reading: null }));
    vi.mocked(ai.cancelTask).mockResolvedValue(task({ state: "reading", phase: "designing", reading: null }));
    open();
    expect(await screen.findByText("The assistant is designing the model and the load")).toBeInTheDocument();
    expect(screen.getByText(/Editing is not possible while this runs/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Prepare the load" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    await waitFor(() => expect(ai.cancelTask).toHaveBeenCalledWith("task-1"));
  });

  it("follows the task until it is read", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.mocked(ai.task)
      .mockResolvedValueOnce(task({ state: "reading", phase: "profiling", reading: null }))
      .mockResolvedValue(task());
    open();
    expect(await screen.findByText("Reading the workbook")).toBeInTheDocument();
    await vi.advanceTimersByTimeAsync(2100);
    expect(await screen.findByRole("heading", { name: "What the assistant read" })).toBeInTheDocument();
  });

  it("shows a small file as a summary and the table that needs the person", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({
        notes: [
          { kind: "warning", text: "The AI provider could not help (timeout); the rules' reading stands.", at: "t" },
        ],
        reading: {
          tables: [update()],
          sheets: [{ sheet: "About", rows: 4, as: "notData", reason: "A cover page with prose." }],
          titles: [],
          summary: { tables: 1, sheets: 2, updates: 1, notLoaded: 0, needDecision: 1, types: 1, applications: 1 },
        },
      }),
    );
    open();
    await screen.findByRole("heading", { name: "What the assistant read" });
    expect(screen.getByText(/The AI provider could not help/)).toBeInTheDocument();
    const sentence = screen.getByRole("region", { name: "What the file does" });
    expect(sentence).toHaveTextContent("1 list on 2 sheets updates 1 type of RDM Systems. 1 needs you.");
    expect(screen.getByRole("heading", { name: "Needs you" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "As your model is organised" })).not.toBeInTheDocument();
    const systems = screen.getByRole("region", { name: "System · Core systems, Systems A1:D11" });
    expect(within(systems).getByText(/System · Core systems · sheet “Systems” A1:D11 · 12 rows/)).toBeInTheDocument();
    expect(within(systems).getByText("New keys to decide")).toBeInTheDocument();
    expect(within(systems).getAllByText(/Proposed by the AI/)).toHaveLength(2);
    expect(within(systems).getByRole("radio", { name: "Code (10 match)" })).toBeChecked();
    expect(within(systems).getByRole("radio", { name: "Name (9 match)" })).not.toBeChecked();
    expect(within(systems).getByText("The 2 new keys")).toBeInTheDocument();
    expect(within(systems).getByRole("radio", { name: "Create them" })).toBeChecked();
    expect(within(systems).getByText("2 names differ from the stored ones")).toBeInTheDocument();
    expect(within(systems).getByRole("radio", { name: "Keep the stored names" })).toBeChecked();
    expect(within(systems).getByText("3 stored records are missing from the file")).toBeInTheDocument();
    expect(within(systems).getByText("“Cargo” is “Freight”")).toBeInTheDocument();
    // The left-out column is one folded line, not a notice.
    expect(within(systems).queryByText(/The type has no weight/)).not.toBeInTheDocument();
    fireEvent.click(within(systems).getByRole("button", { name: "Show 1 column left out" }));
    expect(within(systems).getByText(/“Weight”: The type has no weight\./)).toBeInTheDocument();
  });

  it("shows only the choices that apply, and a table that is not loaded with its reason", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({
        reading: {
          tables: [update({ new: 0, namesDiffer: 0, missing: 2, attention: ["missing"] }), something],
          sheets: [],
          titles: [{ sheet: "Systems", range: "A1:D1", text: "Systems of the west" }],
        },
      }),
    );
    open();
    const systems = await screen.findByRole("region", { name: /System · Core systems/ });
    expect(within(systems).queryByText(/new keys?$/)).not.toBeInTheDocument();
    expect(within(systems).queryByText(/names? differs?/)).not.toBeInTheDocument();
    expect(within(systems).getByText("2 stored records are missing from the file")).toBeInTheDocument();
    const ideas = screen.getByRole("region", { name: /Ideas/ });
    expect(within(ideas).getByText("Not loaded: something new")).toBeInTheDocument();
    expect(within(ideas).getByText(/Nothing stored looks like this/)).toBeInTheDocument();
    expect(within(ideas).queryByRole("radio")).not.toBeInTheDocument();
    // The skipped title block is named by sheet, folded.
    expect(screen.queryByText(/Systems of the west/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show Not loaded: 1 title row" }));
    expect(screen.getByText("Sheet “Systems”")).toBeInTheDocument();
    expect(screen.getByText(/title “Systems of the west”/)).toBeInTheDocument();
  });

  it("says when a workbook has no table", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ reading: { tables: [], sheets: [] } }));
    open();
    expect(await screen.findByText("The assistant found no table in this workbook.")).toBeInTheDocument();
  });

  it("prepares the load with only the choices the person changed, then follows the check", async () => {
    vi.mocked(ai.task).mockResolvedValue(task());
    vi.mocked(ai.planTask).mockResolvedValue(task({ state: "checking", phase: "checking", version: 4 }));
    open();
    const systems = await screen.findByRole("region", { name: /System · Core systems/ });
    fireEvent.click(within(systems).getByRole("radio", { name: "Take the file's names" }));
    fireEvent.click(within(systems).getByRole("radio", { name: "Name (9 match)" }));
    fireEvent.click(screen.getByRole("button", { name: "Prepare the load" }));
    await waitFor(() =>
      expect(ai.planTask).toHaveBeenCalledWith("task-1", {
        expectedVersion: 3,
        tables: [{ table: "t1", keyColumn: "B", names: "file" }],
      }),
    );
    expect(await screen.findByText("Checking every row")).toBeInTheDocument();
  });

  it("sends no table when nothing was changed", async () => {
    vi.mocked(ai.task).mockResolvedValue(task());
    vi.mocked(ai.planTask).mockResolvedValue(task({ state: "checking", version: 4 }));
    open();
    await screen.findByRole("heading", { name: "What the assistant read" });
    fireEvent.click(screen.getByRole("button", { name: "Prepare the load" }));
    await waitFor(() => expect(ai.planTask).toHaveBeenCalledWith("task-1", { expectedVersion: 3, tables: [] }));
  });

  it("reloads the reading and says so on a version conflict", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ version: 4 }));
    vi.mocked(ai.planTask).mockRejectedValue(
      new ApiError(409, "AI_TASK_VERSION_CONFLICT", "Changed", { currentVersion: 4 }),
    );
    open();
    await screen.findByRole("heading", { name: "What the assistant read" });
    fireEvent.click(screen.getByRole("button", { name: "Prepare the load" }));
    expect(await screen.findByText(/The reading changed while you were choosing/)).toBeInTheDocument();
    expect(vi.mocked(ai.task).mock.calls.length).toBeGreaterThan(1);
  });

  it("leaves the page with Cancel", async () => {
    vi.mocked(ai.task).mockResolvedValue(task());
    const { onOpenWorkspace } = open();
    await screen.findByRole("heading", { name: "What the assistant read" });
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(onOpenWorkspace).toHaveBeenCalledWith("west");
  });

  it("shows the check as a summary, the changes of the table that changes and the fixes", async () => {
    vi.mocked(ai.task).mockResolvedValue(checked());
    open();
    expect(await screen.findByRole("heading", { name: "What the load would do" })).toBeInTheDocument();
    expect(screen.getByText("Every row checked · the assistant fixed 1 problem and checked again")).toBeInTheDocument();
    const summary = screen.getByRole("region", { name: "What the check found" });
    expect(summary).toHaveTextContent("1 of 1 list changes something.");
    const figures = within(summary).getByRole("group", { name: "Figures of the check" });
    expect(within(figures).getByText("Records new").previousSibling).toHaveTextContent("2");
    expect(within(figures).getByText("Records changed").previousSibling).toHaveTextContent("3");
    expect(within(figures).getByText("Translations new or changed").previousSibling).toHaveTextContent("2");
    expect(within(figures).getByText("Records as stored").previousSibling).toHaveTextContent("7");
    expect(within(figures).getByText("Rows refused").previousSibling).toHaveTextContent("2");
    expect(within(figures).queryByText("Records removed")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "System · Core systems" })).toBeInTheDocument();
    const refusals = screen.getByRole("list", { name: "Refused rows of Systems" });
    expect(within(refusals).getByText(/2 rows: Value not allowed/)).toBeInTheDocument();
    expect(within(refusals).getByText(/in column “Type”/)).toBeInTheDocument();
    expect(within(refusals).getByText(/“Odd” \(2\)/)).toBeInTheDocument();
    const changes = await screen.findByRole("group", { name: "Changed records of Systems" });
    const rows = within(changes).getAllByRole("row");
    expect(rows).toHaveLength(3);
    expect(within(rows[0]).getByText("What")).toBeInTheDocument();
    expect(within(rows[1]).getByText("System 03")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Old")).toBeInTheDocument();
    expect(within(rows[1]).getByText("New")).toBeInTheDocument();
    expect(ai.taskChanges).toHaveBeenCalledWith("task-1", { table: "t1" }, undefined);
    expect(screen.getByText(/Fixed by the assistant: “Y” in column C is read as “Yes”/)).toBeInTheDocument();
    expect(screen.getByText("1 row skipped", { exact: false })).toBeInTheDocument();
    // The columns left out are folded, by sheet.
    fireEvent.click(screen.getByRole("button", { name: "Show Not loaded: 1 column left out" }));
    expect(screen.getByText("Column “Weight” is left out")).toBeInTheDocument();
  });

  it("goes back to the reading and prepares again", async () => {
    vi.mocked(ai.task).mockResolvedValue(checked());
    open();
    await screen.findByRole("heading", { name: "What the load would do" });
    fireEvent.click(screen.getByRole("button", { name: "Back to the reading" }));
    expect(await screen.findByRole("heading", { name: "What the assistant read" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Prepare the load" })).toBeEnabled();
  });

  it("loads into a change set, saving the profile under a key made from its name", async () => {
    vi.mocked(ai.task).mockResolvedValue(checked());
    vi.mocked(ai.runTask).mockResolvedValue(checked({ state: "loading", version: 6 }));
    open();
    await screen.findByRole("heading", { name: "What the load would do" });
    fireEvent.click(screen.getByRole("checkbox", { name: /Save as a new profile/ }));
    fireEvent.change(screen.getByLabelText("Profile name"), { target: { value: "Supplier Systems" } });
    expect(screen.getByText("Its key is “supplier-systems”.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load into a change set" }));
    await waitFor(() =>
      expect(ai.runTask).toHaveBeenCalledWith("task-1", {
        expectedVersion: 5,
        changeSetName: "Load of systems",
        saveProfile: { key: "supplier-systems", name: "Supplier Systems" },
      }),
    );
    expect(await screen.findByText("Loading into the change set…")).toBeInTheDocument();
  });

  it("does not offer the load without Work in change sets", async () => {
    groups.held = [];
    vi.mocked(ai.task).mockResolvedValue(checked());
    open();
    await screen.findByRole("heading", { name: "What the load would do" });
    expect(screen.queryByRole("button", { name: "Load into a change set" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back to the reading" })).toBeInTheDocument();
  });

  it("says where the load went and what was left out", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      checked({
        state: "loaded",
        version: 7,
        result: {
          changeSetId: "cs-1",
          changeSetName: "Load of systems",
          importJobId: "imp-1",
          profileKey: "supplier-systems",
          counts: { created: 2, updated: 3, unchanged: 7 },
        },
      }),
    );
    const { onNavigate } = open();
    expect(
      await screen.findByRole("heading", { name: "Loaded into the change set “Load of systems”" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/2 records new, 3 records changed and 2 translations new or changed in 1 of 1 list\./),
    ).toBeInTheDocument();
    expect(screen.getByText(/The other 7 records were already as the file says\./)).toBeInTheDocument();
    expect(
      screen.getByText(
        /Saved the profile “supplier-systems”: the next file of this layout loads without the assistant/,
      ),
    ).toBeInTheDocument();
    fireEvent.click(
      screen.getByRole("button", { name: "Show Not loaded: 1 column left out and 2 sheets and blocks not loaded" }),
    );
    expect(screen.getByText("Column “Weight” is left out")).toBeInTheDocument();
    expect(screen.getByText(/Not data: A cover page with prose\./)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review the change set" }));
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "changeSetChanges", changeSetId: "cs-1", workspaceKey: "west" }),
    );
  });

  it("says a failed reading failed, with the job's error, and a way back", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ state: "failed", reading: null }));
    vi.mocked(api.job).mockResolvedValue({ error: { code: "X", message: "The workbook could not be read." } } as never);
    const { onOpenWorkspace } = open();
    expect(await screen.findByText("The reading failed")).toBeInTheDocument();
    expect(await screen.findByText("The workbook could not be read.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back to the workspace" }));
    expect(onOpenWorkspace).toHaveBeenCalledWith("west");
  });

  it("says a task that is not there is not found, with a retry", async () => {
    vi.mocked(ai.task).mockRejectedValue(new ApiError(404, "AI_TASK_NOT_FOUND", "No such task", undefined));
    open();
    expect(await screen.findByText("No such task")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("names the workspace in the trail", async () => {
    vi.mocked(ai.task).mockResolvedValue(task());
    open();
    const trail = await screen.findByRole("navigation", { name: "Breadcrumb" });
    await waitFor(() => expect(within(trail).getByRole("link", { name: "West" })).toBeInTheDocument());
    expect(within(trail).getByText("Load a workbook")).toBeInTheDocument();
  });

  describe("a workbook of many lists", () => {
    /** 38 lists of two applications on four sheets: three need a decision, the others match. */
    const many = () => {
      const make = (n: number, extra: Partial<AiTaskTable>) =>
        update({
          table: `t${n}`,
          sheet: `Sheet ${(n % 4) + 1}`,
          range: `A${n}:C${n + 5}`,
          rows: 10 + n,
          matched: 10 + n,
          new: 0,
          missing: 0,
          namesDiffer: 0,
          meaning: [],
          owner: "rules",
          origin: null,
          attention: [],
          leftOut: [],
          columns: [],
          ...extra,
        });
      const systems = Array.from({ length: 30 }, (_, i) =>
        make(i + 1, {
          objectTypeKey: i === 0 ? "system" : i === 1 ? "interface" : `kind-${i}`,
          typeName: i === 0 ? "System" : i === 1 ? "Interface" : `Kind ${i}`,
          parentTypeKeys: i === 1 ? ["system"] : [],
          // The first three need the person.
          ...(i === 2 || i === 3 ? { new: 1, attention: ["newKeys"] as AiTaskTable["attention"] } : {}),
        }),
      );
      const master = Array.from({ length: 8 }, (_, i) =>
        make(31 + i, {
          applicationKey: "rdm-master",
          objectTypeKey: `list-${i}`,
          typeName: `List ${i}`,
          // One loads Spanish names as translations.
          ...(i === 0
            ? {
                columns: [
                  {
                    column: "B",
                    header: "Spanish",
                    binding: { relatedRecord: { parent: { value: "ES" } } },
                    kind: "relatedRecord",
                    leftOut: null,
                    owner: "rules" as const,
                  },
                ],
              }
            : {}),
          ...(i === 7 ? { missing: 4, attention: ["missing"] as AiTaskTable["attention"] } : {}),
        }),
      );
      return task({
        reading: {
          tables: [...systems, ...master],
          sheets: [],
          titles: [
            { sheet: "Sheet 1", range: "A1:A1", text: "Lists" },
            { sheet: "Sheet 2", range: "A1:A1", text: "More lists" },
          ],
          summary: { tables: 38, sheets: 4, updates: 38, notLoaded: 0, needDecision: 3, types: 38, applications: 2 },
        },
      });
    };

    it("opens with a summary, the few that need the person and the rest folded by the model's groups", async () => {
      vi.mocked(ai.task).mockResolvedValue(many());
      open();
      const summary = await screen.findByRole("region", { name: "What the file does" });
      expect(summary).toHaveTextContent(
        "38 lists on 4 sheets update 38 types of RDM Systems and RDM Master, with their ES names as translations. 3 need you. The other 35 match their stored records.",
      );
      expect(screen.getAllByRole("region", { name: /, Sheet \d A/ })).toHaveLength(3);
      const rest = screen.getByRole("heading", { name: "As your model is organised" }).closest("section")!;
      // Two applications: one more level; the group with a type contained in another is a row, folded.
      expect(within(rest).getByRole("heading", { name: "RDM Systems" })).toBeInTheDocument();
      expect(within(rest).getByRole("heading", { name: "RDM Master" })).toBeInTheDocument();
      const core = within(rest).getByRole("button", { name: /^Core systems/ });
      expect(core).toHaveAttribute("aria-expanded", "false");
      expect(core).toHaveTextContent("Core systems · 2 types · 23 rows · all match");
      expect(within(rest).getByRole("button", { name: /^Other lists · 26 types/ })).toBeInTheDocument();
      expect(within(rest).getByRole("button", { name: /^Other lists · 7 types.*ES translations/ })).toBeInTheDocument();
      expect(within(rest).queryByRole("table")).not.toBeInTheDocument();
    });

    it("opens a group by keyboard into a table, a contained type under its parent", async () => {
      vi.mocked(ai.task).mockResolvedValue(many());
      open();
      const rest = (await screen.findByRole("heading", { name: "As your model is organised" })).closest("section")!;
      const core = within(rest).getByRole("button", { name: /^Core systems/ });
      core.focus();
      // A button opens with Enter or Space: the browser clicks it; the test clicks the focused control.
      fireEvent.click(document.activeElement as HTMLElement);
      expect(core).toHaveAttribute("aria-expanded", "true");
      const table = within(rest).getByRole("group", { name: /Core systems of RDM Systems/ });
      const rows = within(table).getAllByRole("row");
      expect(rows).toHaveLength(3);
      expect(
        within(rows[0])
          .getAllByRole("columnheader")
          .map((cell) => cell.textContent),
      ).toEqual(["Type", "Found on", "Rows", "Match", "Also loads"]);
      expect(rows[1]).toHaveTextContent("System");
      expect(rows[1]).toHaveTextContent("Sheet 2 A1:C6");
      expect(rows[1]).toHaveTextContent("11");
      expect(rows[1]).toHaveTextContent("11 of 11");
      expect(rows[2]).toHaveTextContent("↳ Interface");
    });

    it("sends only the choices changed in the cards that need the person", async () => {
      vi.mocked(ai.task).mockResolvedValue(many());
      vi.mocked(ai.planTask).mockResolvedValue(task({ state: "checking", version: 4 }));
      open();
      const [first] = await screen.findAllByRole("region", { name: /, Sheet \d A/ });
      fireEvent.click(within(first).getByRole("radio", { name: "Leave them out" }));
      fireEvent.click(screen.getByRole("button", { name: "Prepare the load" }));
      await waitFor(() =>
        expect(ai.planTask).toHaveBeenCalledWith("task-1", {
          expectedVersion: 3,
          tables: [{ table: "t3", newRecords: "leaveOut" }],
        }),
      );
    });

    it("shows the check with the two tables that change and the rest folded by group", async () => {
      const read = many();
      const tables = read.reading!.tables;
      const quiet = (table: AiTaskTable) => ({
        table: table.table,
        sheet: table.sheet,
        typeName: table.typeName,
        rows: table.rows,
        changed: 0,
        unchanged: table.rows,
        created: 0,
        removed: 0,
        skipped: 0,
        translations: 0,
        nothingToDo: true,
        refused: [],
        leftOut: [],
      });
      const check = tables.map(quiet);
      check[2] = { ...check[2], changed: 2, unchanged: 8, nothingToDo: false };
      check[31] = { ...check[31], translations: 5, nothingToDo: false };
      vi.mocked(ai.task).mockResolvedValue({
        ...read,
        state: "checked",
        version: 5,
        check: {
          dryRunJobId: "d",
          ranAt: "2026-11-01T10:05:00Z",
          rounds: 0,
          fixes: [],
          tables: check,
          summary: {
            changed: 2,
            unchanged: 800,
            created: 0,
            removed: 0,
            refused: 0,
            translations: 5,
            tablesWithChanges: 2,
          },
        },
      });
      open();
      const summary = await screen.findByRole("region", { name: "What the check found" });
      expect(summary).toHaveTextContent("2 of 38 lists change something. The other 36 load exactly what is stored.");
      expect(within(summary).getByText("Records as stored").previousSibling).toHaveTextContent("800");
      expect(screen.getAllByRole("heading", { level: 3 })).toHaveLength(2);
      expect(ai.taskChanges).toHaveBeenCalledTimes(1);
      const fold = screen.getByRole("button", { name: "Show 36 lists with nothing to change, by group" });
      expect(screen.queryByRole("button", { name: /^Core systems/ })).not.toBeInTheDocument();
      fireEvent.click(fold);
      expect(screen.getByRole("button", { name: /^Core systems · 2 types · 23 rows/ })).toHaveAttribute(
        "aria-expanded",
        "false",
      );
    });

    it("says in a sentence what was loaded, with no list of left-outs", async () => {
      const read = many();
      vi.mocked(ai.task).mockResolvedValue({
        ...read,
        state: "loaded",
        version: 7,
        check: {
          dryRunJobId: "d",
          ranAt: "t",
          rounds: 0,
          fixes: [],
          tables: [],
          summary: {
            changed: 3,
            unchanged: 708,
            created: 1,
            removed: 0,
            refused: 0,
            translations: 0,
            tablesWithChanges: 2,
          },
        },
        result: { changeSetId: "cs-1", changeSetName: "Load", counts: { created: 1, updated: 3, unchanged: 708 } },
      });
      open();
      await screen.findByRole("heading", { name: "Loaded into the change set “Load”" });
      expect(screen.getByText(/1 record new and 3 records changed in 2 of 0 lists\./)).toBeInTheDocument();
      expect(screen.getByText(/The other 708 records were already as the file says\./)).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: "Show Not loaded: 2 sheets and blocks not loaded" }),
      ).toBeInTheDocument();
    });
  });
});
