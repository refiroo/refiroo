import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { useJobStream } from "@/features/jobs/useJobStream";
import { outlineFixture } from "@/test/draftOutline";
import { useHeldAnywhere } from "@/features/security/permissions";
import { useCapabilities } from "@/features/settings/useSystem";
import { ToastProvider } from "@/ui/Toast";
import type { DraftProfile, JoinCandidates, SourceColumn } from "@/types/sources";
import { DRAG_COLUMN, DRAG_COLUMNS } from "./CanvasBoard";
import { WorkbookCanvas } from "./WorkbookCanvas";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});
vi.mock("@/features/jobs/useJobStream", async (load) => ({
  ...(await load<typeof import("@/features/jobs/useJobStream")>()),
  useJobStream: vi.fn(),
}));

// Who may do what is not under test here, except that the one-step finish is left out for a person who may not.
vi.mock("@/features/security/permissions", async (load) => ({
  ...(await load<typeof import("@/features/security/permissions")>()),
  useHeldAnywhere: vi.fn(),
}));
vi.mock("@/features/settings/useSystem", async (load) => ({
  ...(await load<typeof import("@/features/settings/useSystem")>()),
  useCapabilities: vi.fn(),
}));

const everything = {
  workspaceAdmin: { manageWorkspaces: true },
  modelAdmin: { manageDrafts: true, install: true },
  integrationJobs: { createJobs: true },
};
const groups = ["workspace-admin", "model-authoring", "model-install", "bulk"].map((key) => ({ key, instance: true }));

const column = (letter: string, header: string, part: Partial<SourceColumn> = {}): SourceColumn => ({
  sheet: "Shelves",
  letter,
  header,
  block: 0,
  rows: 40,
  filled: 40,
  distinct: 40,
  valueTypes: { text: 40 },
  candidateKey: false,
  delimiters: [],
  placeholders: [],
  overlaps: [],
  ...part,
});

const profile: DraftProfile = {
  version: 4,
  profile: {
    key: "shelves",
    name: "Shelves",
    sources: [
      {
        id: "shelves-shelf",
        sheet: "Shelves",
        headerRow: 1,
        applicationKey: "shop",
        objectTypeKey: "shelf",
        block: { firstColumn: "A", lastColumn: "E", lastRow: 40 },
        columns: [{ column: "Shelf", field: "name" }],
      },
      {
        id: "areas-area",
        sheet: "Shelves",
        headerRow: 1,
        applicationKey: "shop",
        objectTypeKey: "area",
        block: { firstColumn: "A", lastColumn: "E", lastRow: 40 },
        columns: [{ column: "Region", field: "name" }],
      },
    ],
    valueMaps: {},
  },
  definition: null,
  valid: true,
  diagnostics: [],
  sourceFile: { id: "f1", name: "shelves.xlsx", profile: "completed" },
};

const answer = (candidates: Partial<JoinCandidates["candidates"][number]>[]): JoinCandidates => ({
  column: { sheet: "Shelves", letter: "C", header: "Region", rows: 40, distinct: 5 },
  candidates: candidates.map((item, index) => ({
    sheet: "Shelves",
    letter: "DE"[index],
    header: `Col ${index}`,
    rows: 40,
    distinct: 5,
    matchedValues: 5,
    matchedRows: 40,
    share: 1,
    unique: false,
    ...item,
  })),
  best: null,
  tie: false,
  tied: [],
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useJobStream).mockReturnValue(undefined as never);
  vi.mocked(api.modelDraftOutline).mockResolvedValue({ ...outlineFixture(), valid: true, diagnostics: [] });
  vi.mocked(api.modelDraft).mockResolvedValue({
    id: "d1",
    name: "Shelves draft",
    baseReleaseId: null,
    model: {},
    version: 4,
    createdAt: "2026-11-12T10:00:00Z",
    updatedAt: "2026-11-12T10:00:00Z",
  });
  vi.mocked(api.modelDraftProfile).mockResolvedValue(profile);
  vi.mocked(api.modelDraftDryRun).mockResolvedValue({
    state: "completed",
    jobId: "j1",
    draftVersion: 4,
    summary: {
      rows: { total: 80 },
      ranAt: "2026-11-12T10:00:00Z",
      sources: [
        {
          source: 0,
          sheet: "Shelves",
          objectTypeKey: "shelf",
          rows: 40,
          records: { created: 30, updated: 0, unchanged: 0 },
          rejections: [{ code: "REFERENCE_NOT_FOUND", rows: 10 }],
        },
      ],
    },
  } as never);
  vi.mocked(api.modelDraftModel).mockResolvedValue({ version: 4, valid: true, diagnostics: [] });
  vi.mocked(api.modelDraftInference).mockRejectedValue(new ApiError(404, "INFERENCE_NOT_FOUND", "No inference"));
  vi.mocked(api.modelDraftProposals).mockResolvedValue([]);
  vi.mocked(api.modelDraftCanvas).mockResolvedValue({ positions: {} });
  vi.mocked(api.moveCanvasCards).mockResolvedValue({ positions: {} });
  vi.mocked(api.sourceSheets).mockResolvedValue({
    items: [
      {
        index: 0,
        name: "Shelves",
        rows: 40,
        headerRow: 1,
        blocks: [{ index: 0, range: "A1:E40", firstColumn: "A", lastColumn: "E", headerRow: 1, lastRow: 40, rows: 39 }],
      },
    ],
    nextCursor: null,
  });
  vi.mocked(api.sourceColumns).mockResolvedValue({
    items: [column("A", "Shelf"), column("B", "Title"), column("C", "Area"), column("D", "2022"), column("E", "2023")],
    nextCursor: null,
  });
  vi.mocked(api.sourceCells).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(useHeldAnywhere).mockReturnValue([]);
  vi.mocked(useCapabilities).mockReturnValue({ capabilities: everything } as never);
  vi.mocked(api.applyModelDraftOperations).mockResolvedValue({ version: 5, entries: [], valid: true, diagnostics: [] });
  vi.mocked(api.modelDraftDryRunRows).mockResolvedValue({ items: [], nextCursor: null });
});

function renderCanvas(onNavigate = vi.fn()) {
  render(
    <ToastProvider>
      <WorkbookCanvas draftId="d1" workspaceKey="default" onNavigate={onNavigate} />
    </ToastProvider>,
  );
  return onNavigate;
}

function dropOf(headers: string[]) {
  const data: Record<string, string> = {
    [DRAG_COLUMN]: `Shelves\u0000${headers[0]}`,
    ...(headers.length > 1 ? { [DRAG_COLUMNS]: JSON.stringify({ sheet: "Shelves", headers }) } : {}),
  };
  return { dataTransfer: { types: Object.keys(data), getData: (type: string) => data[type] ?? "" } };
}

describe("the workbook canvas page", () => {
  it("draws the lists with the count of rows after the check, and a column dropped on a field is one request", async () => {
    renderCanvas();
    const shelf = await screen.findByLabelText("Shelf", { selector: "section" });
    expect(await screen.findByText(/Workbook check: 80 rows, every one/)).toBeTruthy();
    expect(within(shelf).getByText("30 load")).toBeTruthy();
    expect(within(shelf).getByRole("button", { name: "10 refused" })).toBeTruthy();
    const nameField = shelf.querySelector('[data-canvas-field="name"]') as HTMLElement;
    fireEvent.drop(nameField, dropOf(["Title"]));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "mapColumn", source: "shelves-shelf", column: "Title", binding: { field: "name" } },
      ]),
    );
    expect(await screen.findByText("Title fills Name of Shelf")).toBeTruthy();
  });

  it("sends a parent and child with the column that names the parent, found over every row, in one request", async () => {
    vi.mocked(api.joinCandidates).mockResolvedValue(
      answer([
        { header: "Area", matchedRows: 40 },
        { header: "Title", matchedRows: 7 },
      ]),
    );
    renderCanvas();
    // The sheet loads shelves and areas: put the shelf under the area by its menu.
    fireEvent.click(await screen.findByRole("button", { name: "Actions for Shelf" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Put under Area" }));
    await waitFor(() => expect(api.joinCandidates).toHaveBeenCalled());
    expect(vi.mocked(api.joinCandidates).mock.calls[0][1]).toMatchObject({
      column: { sheet: "Shelves", column: "Region" },
      against: { sheet: "Shelves" },
    });
    await waitFor(() => expect(api.applyModelDraftOperations).toHaveBeenCalled());
    const sent = vi.mocked(api.applyModelDraftOperations).mock.calls[0][2];
    expect(sent.map((item) => item.kind)).toEqual(["setContainment", "mapColumn"]);
    expect(sent[1]).toEqual({
      kind: "mapColumn",
      source: "shelves-shelf",
      column: "Area",
      binding: { parent: { objectTypeKey: "area", matchBy: { field: "name" }, missing: "create" } },
    });
  });

  it("asks which column when two match equally and sends nothing until one is chosen", async () => {
    vi.mocked(api.joinCandidates).mockResolvedValue(
      answer([
        { header: "Area copy", letter: "D" },
        { header: "Area again", letter: "E" },
      ]),
    );
    renderCanvas();
    fireEvent.click(await screen.findByRole("button", { name: "Actions for Shelf" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Relate to Area" }));
    expect(await screen.findByText("Which column names the Area records?")).toBeTruthy();
    expect(api.applyModelDraftOperations).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Area again/ }));
    await waitFor(() => expect(api.applyModelDraftOperations).toHaveBeenCalled());
    const sent = vi.mocked(api.applyModelDraftOperations).mock.calls[0][2];
    expect(sent.map((item) => item.kind)).toEqual(["addRelationType", "allowRelation", "mapColumn"]);
    expect(sent[2]).toMatchObject({ column: "Area again", source: "shelves-shelf" });
  });

  it("reads the other list's own column as the join when both lists read the same sheet and the route names none", async () => {
    vi.mocked(api.joinCandidates).mockResolvedValue(answer([]));
    renderCanvas();
    fireEvent.click(await screen.findByRole("button", { name: "Actions for Shelf" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Relate to Area" }));
    await waitFor(() => expect(api.applyModelDraftOperations).toHaveBeenCalled());
    const sent = vi.mocked(api.applyModelDraftOperations).mock.calls[0][2] as { kind: string; column?: string }[];
    expect(sent.find((item) => item.kind === "mapColumn")).toMatchObject({ source: "shelves-shelf", column: "Region" });
  });

  it("makes the link only and says no column was found when none of the sheet names the other list", async () => {
    vi.mocked(api.joinCandidates).mockResolvedValue(answer([]));
    vi.mocked(api.modelDraftProfile).mockResolvedValue({
      ...profile,
      profile: {
        ...profile.profile!,
        sources: profile.profile!.sources.map((item) =>
          item.id === "areas-area" ? { ...item, sheet: "Areas" } : item,
        ),
      },
    });
    renderCanvas();
    fireEvent.click(await screen.findByRole("button", { name: "Actions for Shelf" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Relate to Area" }));
    await waitFor(() => expect(api.applyModelDraftOperations).toHaveBeenCalled());
    expect(await screen.findByText(/no column of the workbook was found/)).toBeTruthy();
  });

  it("reads several chosen columns as rows after naming the two new columns, in one request", async () => {
    renderCanvas();
    const shelf = await screen.findByLabelText("Shelf", { selector: "section" });
    const list = await screen.findByRole("list", { name: "Columns of Shelves" });
    fireEvent.click(await within(list).findByText("2022"));
    fireEvent.click(within(list).getByText("2023"), { ctrlKey: true });
    expect(await screen.findByText("2 columns chosen")).toBeTruthy();
    fireEvent.drop(shelf, dropOf(["2022", "2023"]));
    expect(await screen.findByText("Read 2 columns as rows")).toBeTruthy();
    expect((screen.getByLabelText("The column's header goes in") as HTMLInputElement).value).toBe("Year");
    fireEvent.click(screen.getByRole("button", { name: "Read as rows" }));
    await waitFor(() => expect(api.applyModelDraftOperations).toHaveBeenCalled());
    const sent = vi.mocked(api.applyModelDraftOperations).mock.calls[0][2];
    expect(sent[0]).toEqual({
      kind: "setUnpivot",
      source: "shelves-shelf",
      columns: ["2022", "2023"],
      nameColumn: "Year",
      valueColumn: "Value",
    });
    expect(sent.filter((item) => item.kind === "mapColumn").map((item) => item.column)).toEqual(["Year", "Value"]);
  });

  it("says a refusal above the board, changes nothing and shows no toast", async () => {
    vi.mocked(api.applyModelDraftOperations).mockRejectedValue(
      new ApiError(422, "KEY_TAKEN", "The table already has a column 'Year'"),
    );
    renderCanvas();
    const shelf = await screen.findByLabelText("Shelf", { selector: "section" });
    fireEvent.drop(shelf.querySelector('[data-canvas-field="name"]') as HTMLElement, dropOf(["Title"]));
    expect(await screen.findByText("The table already has a column 'Year'")).toBeTruthy();
    expect(screen.queryByText("Title fills Name of Shelf")).toBeNull();
  });

  it("asks about the steps that depend on an undo the engine refused", async () => {
    vi.mocked(api.undoModelDraftStep).mockRejectedValueOnce(
      new ApiError(409, "OPERATION_HAS_DEPENDANTS", "Later steps use it", { steps: [2], dependants: [3] }),
    );
    renderCanvas();
    await screen.findByLabelText("Shelf", { selector: "section" });
    fireEvent.click(screen.getByRole("button", { name: /Undo/ }));
    expect(await screen.findByText(/Step 3 uses what step 2 created or re-keyed/)).toBeTruthy();
    vi.mocked(api.undoModelDraftStep).mockResolvedValue({ version: 6, entries: [], valid: true, diagnostics: [] });
    fireEvent.click(screen.getByRole("button", { name: "Undo steps 2, 3" }));
    await waitFor(() => expect(api.undoModelDraftStep).toHaveBeenLastCalledWith("d1", 4, [2, 3]));
  });

  it("shows why rows were refused and lets the wrong values be corrected with a value map", async () => {
    vi.mocked(api.modelDraftDryRunRows).mockResolvedValue({
      items: [
        {
          ref: "r1",
          sheet: "Shelves",
          row: 3,
          status: "rejected",
          actions: { created: 0, updated: 0, unchanged: 0, deleted: 0 },
          outcomes: [
            {
              index: 0,
              ref: null,
              status: "rejected",
              error: {
                code: "REFERENCE_NOT_FOUND",
                message: 'No area record matches "Nord" in column Area',
                details: { column: "Area", count: 0 },
              },
            },
          ],
        },
      ],
      nextCursor: null,
    } as never);
    renderCanvas();
    const shelf = await screen.findByLabelText("Shelf", { selector: "section" });
    fireEvent.click(await within(shelf).findByRole("button", { name: "10 refused" }));
    expect(await screen.findByText(/No area record matches "Nord"/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Correct the values of Area…" }));
    const value = await screen.findByLabelText("Text 1");
    expect((value as HTMLInputElement).value).toBe("Nord");
  });

  it("offers Create workspace… only to a person who may take every step of it", async () => {
    renderCanvas();
    await screen.findByLabelText("Shelf", { selector: "section" });
    expect(screen.queryByRole("button", { name: "Create workspace…" })).toBeNull();
  });

  it("creates the workspace through the one route when the person may, and says what loads", async () => {
    vi.mocked(useHeldAnywhere).mockReturnValue(groups as never);
    vi.mocked(api.createWorkspaceFromWorkbook).mockResolvedValue({
      workspace: { key: "shelves" },
      job: { id: "job1" },
    } as never);
    const onNavigate = vi.fn();
    render(
      <ToastProvider>
        <WorkbookCanvas draftId="d1" workspaceKey="default" onNavigate={onNavigate} />
      </ToastProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Create workspace…" }));
    expect(await screen.findByText(/30 rows load; 10 are refused and stay out/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Create workspace" }));
    await waitFor(() =>
      expect(api.createWorkspaceFromWorkbook).toHaveBeenCalledWith({
        draftId: "d1",
        expectedVersion: 4,
        name: "Shelves draft",
      }),
    );
    // The workspace's own page, where the load's progress and result are shown.
    await waitFor(() => expect(onNavigate).toHaveBeenCalledWith({ kind: "workspace", workspaceKey: "shelves" }));
  });

  it("hides the finishes and Tidy on an empty board, where nothing could be loaded or arranged", async () => {
    vi.mocked(useHeldAnywhere).mockReturnValue(groups as never);
    vi.mocked(api.modelDraftProfile).mockResolvedValue({
      ...profile,
      profile: { ...profile.profile!, sources: [] },
    });
    vi.mocked(api.modelDraftOutline).mockResolvedValue({
      ...outlineFixture(),
      objectTypes: [],
      applications: [],
      relations: [],
      valid: true,
      diagnostics: [],
    });
    renderCanvas();
    await screen.findByText(/Nothing is on the board yet/);
    expect(screen.queryByRole("button", { name: "Create workspace…" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Tidy" })).toBeNull();
    // The editor is one press away through the switch, which every draft shows.
    expect(screen.getByRole("button", { name: "Editor" })).toBeTruthy();
  });

  it("moves a focused card sixteen pixels an arrow key and keeps the place on the draft's canvas", async () => {
    renderCanvas();
    const shelf = (await screen.findByLabelText("Shelf", { selector: "section" })) as HTMLElement;
    const before = parseInt(shelf.style.left, 10);
    shelf.focus();
    fireEvent.keyDown(shelf, { key: "ArrowRight" });
    await waitFor(() => expect(parseInt(shelf.style.left, 10)).toBe(before + 16));
    expect(api.moveCanvasCards).toHaveBeenCalledWith("d1", { shelf: expect.objectContaining({ x: before + 16 }) });
  });
});
