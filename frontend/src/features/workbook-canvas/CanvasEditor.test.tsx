import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { useJobStream } from "@/state/useJobStream";
import { useHeldAnywhere } from "@/state/permissions";
import { useCapabilities } from "@/state/useSystem";
import { outlineFixture } from "@/test/draftOutline";
import type { CanvasSelection, ModelDraftOperationEntry } from "@/types";
import type { DraftProfile } from "@/types/sources";
import { ToastProvider } from "@/ui/Toast";
import { DRAG_FIELD } from "./BoardCard";
import { WorkbookCanvas } from "./WorkbookCanvas";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});
vi.mock("@/state/useJobStream", async (load) => ({
  ...(await load<typeof import("@/state/useJobStream")>()),
  useJobStream: vi.fn(),
}));
vi.mock("@/state/permissions", async (load) => ({
  ...(await load<typeof import("@/state/permissions")>()),
  useHeldAnywhere: vi.fn(),
}));
vi.mock("@/state/useSystem", async (load) => ({
  ...(await load<typeof import("@/state/useSystem")>()),
  useCapabilities: vi.fn(),
}));

const entry = (step: number, kind: string, parameters: Record<string, unknown>): ModelDraftOperationEntry => ({
  sequence: step,
  step,
  kind,
  parameters,
  inverse: {},
  draftVersion: step,
  author: null,
  at: "2026-11-12T10:00:00Z",
  undone: false,
  origin: { type: "request" },
});

const workbook: DraftProfile = {
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
    ],
    valueMaps: {},
  },
  definition: null,
  valid: true,
  diagnostics: [],
  sourceFile: { id: "f1", name: "shelves.xlsx", profile: "completed" },
};

const answered = { version: 5, entries: [], valid: true, diagnostics: [] };

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useJobStream).mockReturnValue(undefined as never);
  vi.mocked(api.modelDraftOutline).mockResolvedValue(outlineFixture());
  vi.mocked(api.modelDraft).mockResolvedValue({
    id: "d1",
    name: "Shelves draft",
    baseReleaseId: null,
    model: {},
    version: 4,
    createdAt: "2026-11-12T10:00:00Z",
    updatedAt: "2026-11-12T10:00:00Z",
  });
  vi.mocked(api.modelDraftProfile).mockResolvedValue(workbook);
  vi.mocked(api.modelDraftDryRun).mockResolvedValue(undefined as never);
  vi.mocked(api.modelDraftModel).mockResolvedValue({ version: 4, valid: false, diagnostics: [] });
  vi.mocked(api.modelDraftInference).mockRejectedValue(new Error("none"));
  vi.mocked(api.modelDraftProposals).mockResolvedValue([]);
  vi.mocked(api.modelDraftCanvas).mockResolvedValue({ positions: {}, folded: [], scope: null });
  vi.mocked(api.moveCanvasCards).mockResolvedValue({ positions: {} } as never);
  vi.mocked(api.arrangeCanvas).mockResolvedValue({ positions: {}, folded: [], scope: null } as never);
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
  vi.mocked(api.sourceColumns).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.sourceCells).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.modelDraftOperations).mockResolvedValue({
    items: [entry(3, "addObjectType", { name: "Bin", parent: null }), entry(4, "setLabel", { name: "Shelf" })],
    nextCursor: null,
    prevCursor: null,
  });
  vi.mocked(useHeldAnywhere).mockReturnValue([]);
  vi.mocked(useCapabilities).mockReturnValue({
    capabilities: {
      workspaceAdmin: { manageWorkspaces: true },
      modelAdmin: { manageDrafts: true, install: true },
      integrationJobs: { createJobs: true },
    },
  } as never);
  vi.mocked(api.applyModelDraftOperations).mockResolvedValue(answered as never);
});

function renderCanvas(extra: { selection?: CanvasSelection; onSelect?: (selection: CanvasSelection) => void } = {}) {
  return render(
    <ToastProvider>
      <WorkbookCanvas draftId="d1" workspaceKey="default" onNavigate={vi.fn()} {...extra} />
    </ToastProvider>,
  );
}

const card = (name: string) => screen.findByLabelText(name, { selector: "section" });

describe("a model made by hand on the canvas (0.17 CE1)", () => {
  it("adds an object type with the editor's Add menu: the same trigger, entries and form", async () => {
    renderCanvas();
    await card("Shelf");
    expect(screen.queryByRole("button", { name: /New list/ })).toBeNull();
    fireEvent.click(await screen.findByRole("button", { name: "Add to the model" }));
    expect(await screen.findByRole("menuitem", { name: /Application…/ })).toBeTruthy();
    fireEvent.click(await screen.findByRole("menuitem", { name: /Object type…/ }));
    expect(await screen.findByRole("dialog")).toBeTruthy();
  });

  it("opens the editor's New attribute form from a card", async () => {
    renderCanvas();
    const shelf = await card("Shelf");
    expect(within(shelf).queryByLabelText(/New field/)).toBeNull();
    fireEvent.click(within(shelf).getByRole("button", { name: /New attribute/ }));
    expect(await screen.findByRole("dialog")).toBeTruthy();
  });

  it("an attribute row dragged beside another of its card changes its position; Alt+ArrowUp does the same", async () => {
    renderCanvas();
    const shelf = await card("Shelf");
    const row = (id: string) => shelf.querySelector(`[data-canvas-field="${id}"]`) as HTMLElement;
    const drag = { types: [DRAG_FIELD], setData: vi.fn(), getData: () => "", effectAllowed: "" };
    fireEvent.dragStart(row("attribute:depth"), { dataTransfer: drag });
    fireEvent.dragOver(row("attribute:code"), { dataTransfer: drag });
    expect(row("attribute:code").classList.contains("drop-before")).toBe(true);
    fireEvent.drop(row("attribute:code"), { dataTransfer: drag });
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setAttributeBinding", objectType: "shelf", attributeType: "depth", position: 0 },
      ]),
    );
    vi.mocked(api.applyModelDraftOperations).mockClear();
    fireEvent.keyDown(row("attribute:depth"), { key: "ArrowUp", altKey: true });
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setAttributeBinding", objectType: "shelf", attributeType: "depth", position: 0 },
      ]),
    );
  });

  it("an attribute row dropped on another object type's card is the editor's Move to…", async () => {
    renderCanvas();
    fireEvent.click(await screen.findByRole("button", { name: "Whole model" }));
    const area = await card("Area");
    const shelf = await card("Shelf");
    const drag = { types: [DRAG_FIELD], setData: vi.fn(), getData: () => "", effectAllowed: "" };
    fireEvent.dragStart(shelf.querySelector('[data-canvas-field="attribute:depth"]') as HTMLElement, {
      dataTransfer: drag,
    });
    // Its own card's body does nothing.
    fireEvent.drop(shelf, { dataTransfer: drag });
    expect(api.applyModelDraftOperations).not.toHaveBeenCalled();
    fireEvent.dragStart(shelf.querySelector('[data-canvas-field="attribute:depth"]') as HTMLElement, {
      dataTransfer: drag,
    });
    fireEvent.drop(area, { dataTransfer: drag });
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "moveAttribute", attributeType: "depth", from: "shelf", to: "area" },
      ]),
    );
  });

  it("an attribute the engine refuses to move says why above the board, in the editor's words, and changes nothing", async () => {
    const why = "'area' already binds 'code'";
    vi.mocked(api.applyModelDraftOperations).mockRejectedValueOnce(
      new ApiError(422, "INVALID_OPERATION", why, { index: 0, pointer: "/operations/0/to", reason: "alreadyAttached" }),
    );
    renderCanvas();
    fireEvent.click(await screen.findByRole("button", { name: "Whole model" }));
    const area = await card("Area");
    const shelf = await card("Shelf");
    const drag = { types: [DRAG_FIELD], setData: vi.fn(), getData: () => "", effectAllowed: "" };
    fireEvent.dragStart(shelf.querySelector('[data-canvas-field="attribute:code"]') as HTMLElement, {
      dataTransfer: drag,
    });
    fireEvent.drop(area, { dataTransfer: drag });
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "moveAttribute", attributeType: "code", from: "shelf", to: "area" },
      ]),
    );
    const notice = await screen.findByText(why);
    expect(notice.closest(".canvas-notices")).not.toBeNull();
    // Nothing changed: no success toast and the outline was not read again.
    expect(screen.queryByText(/moved to Area/)).toBeNull();
    expect(api.modelDraftOutline).toHaveBeenCalledTimes(1);
  });

  describe("what the Add menu makes that has no card is selected and said", () => {
    async function make(
      entry: RegExp,
      fields: Record<string, string>,
      after: (outline: ReturnType<typeof outlineFixture>) => void,
    ) {
      renderCanvas();
      await card("Shelf");
      fireEvent.click(await screen.findByRole("button", { name: "Add to the model" }));
      fireEvent.click(await screen.findByRole("menuitem", { name: entry }));
      const dialog = await screen.findByRole("dialog");
      for (const [label, value] of Object.entries(fields))
        fireEvent.change(within(dialog).getByLabelText(label), { target: { value } });
      const grown = outlineFixture();
      after(grown);
      vi.mocked(api.modelDraftOutline).mockResolvedValue(grown);
      fireEvent.click(within(dialog).getByRole("button", { name: /^(Add|Apply)/ }));
    }

    it("an attribute type: its own panel in the inspector, and the toast", async () => {
      await make(/Attribute type…/, { Name: "Weight" }, (outline) =>
        outline.attributeTypes.push({
          key: "weight",
          name: "Weight",
          valueType: "text",
          features: {},
          boundBy: [],
          mark: "new",
        }),
      );
      expect(await screen.findByText("Weight added")).toBeTruthy();
      const inspector = screen.getByRole("complementary", { name: "Inspector" });
      expect(await within(inspector).findByRole("heading", { name: /Weight/ })).toBeTruthy();
    });

    it("a relation type: its own panel in the inspector, and the toast", async () => {
      await make(/Relation type…/, { Name: "Faces", "Reverse name": "Faced by" }, (outline) =>
        outline.relationTypes.push({
          key: "faces",
          reverseKey: "faced-by",
          name: "Faces",
          reverseName: "Faced by",
          containment: false,
          mark: "new",
        }),
      );
      expect(await screen.findByText("Faces added")).toBeTruthy();
      const inspector = screen.getByRole("complementary", { name: "Inspector" });
      expect(await within(inspector).findByRole("heading", { name: /Faces/ })).toBeTruthy();
    });

    it("a navigation group: the Navigation tab with the group selected, and the toast", async () => {
      await make(/Navigation group…/, { Label: "Storage" }, (outline) =>
        outline.applications[0].navigation.groups.push({
          key: "storage",
          label: "Storage",
          collapsed: false,
          collections: [],
          entries: [],
          mark: "new",
        }),
      );
      expect(await screen.findByText("Storage added")).toBeTruthy();
      expect(screen.getByRole("tab", { name: "Navigation" }).getAttribute("aria-selected")).toBe("true");
      await waitFor(() => expect(document.querySelector(".canvas-group.selected")?.textContent).toContain("Storage"));
    });
  });

  it("a stored layout whose cards overlap is read apart and the moved places are written back once, as places", async () => {
    vi.mocked(api.modelDraftCanvas).mockResolvedValue({
      positions: { area: { x: 40, y: 80 }, shelf: { x: 60, y: 100 }, bin: { x: 700, y: 80 } },
      folded: [],
      scope: "model",
    });
    renderCanvas();
    await card("Shelf");
    await waitFor(() => expect(api.moveCanvasCards).toHaveBeenCalledTimes(1));
    const [, moved] = vi.mocked(api.moveCanvasCards).mock.calls[0];
    expect(Object.keys(moved)).toEqual(["shelf"]);
    expect(moved.shelf).toMatchObject({ x: 60 });
    expect(moved.shelf!.y).toBeGreaterThan(100 + 100);
    // A place, never a model step.
    expect(api.applyModelDraftOperations).not.toHaveBeenCalled();
  });

  it("renames an object type where it stands: the value becomes its input, leaving it saves the editor's heading rename", async () => {
    renderCanvas();
    const shelf = await card("Shelf");
    fireEvent.click(within(shelf).getByRole("button", { name: /Name of the object type Shelf/ }));
    const input = within(shelf).getByLabelText("Name of the object type Shelf");
    fireEvent.change(input, { target: { value: "Rack" } });
    fireEvent.keyDown(input, { key: "Enter" });
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setLabel", element: { objectType: "shelf" }, name: "Rack" },
      ]),
    );
  });

  it("puts a name back with Escape and sends nothing", async () => {
    renderCanvas();
    const shelf = await card("Shelf");
    fireEvent.click(within(shelf).getByRole("button", { name: /Name of the object type Shelf/ }));
    const input = within(shelf).getByLabelText("Name of the object type Shelf");
    fireEvent.change(input, { target: { value: "Rack" } });
    fireEvent.keyDown(input, { key: "Escape" });
    expect(api.applyModelDraftOperations).not.toHaveBeenCalled();
  });
});

describe("the whole model on the board", () => {
  it("opens on the workbook's lists, widens to the whole model and narrows to what the draft changed, kept on the draft", async () => {
    renderCanvas();
    await card("Shelf");
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "From the workbook" }).getAttribute("aria-pressed")).toBe("true"),
    );
    fireEvent.click(screen.getByRole("button", { name: "Changed in this draft" }));
    await waitFor(() => expect(screen.queryByLabelText("Shelf", { selector: "section" })).toBeNull());
    expect(api.arrangeCanvas).toHaveBeenCalledWith("d1", { scope: "changed" });
    fireEvent.click(screen.getByRole("button", { name: "Whole model" }));
    expect(await card("Shelf")).toBeTruthy();
    expect(api.arrangeCanvas).toHaveBeenCalledWith("d1", { scope: "model" });
  });

  it("draws a frame per application with its name, and the mark of each list", async () => {
    renderCanvas();
    const shelf = await card("Shelf");
    expect(document.querySelector('[data-canvas-frame="shop"]')).toBeTruthy();
    expect(screen.getByRole("button", { name: "Application Shop" })).toBeTruthy();
    expect(within(shelf).getByText("Released")).toBeTruthy();
    expect(within(await card("Bin")).getByText("New")).toBeTruthy();
    expect(within(await card("Area")).getByText("Changed")).toBeTruthy();
  });

  it("folds a card to its top bar, kept on the draft, and unfolds it", async () => {
    renderCanvas();
    const shelf = await card("Shelf");
    fireEvent.click(within(shelf).getByRole("button", { name: "Fold Shelf to its top bar" }));
    expect(api.arrangeCanvas).toHaveBeenCalledWith("d1", { folded: { shelf: true } });
    expect(shelf.querySelector(".canvas-fields")).toBeNull();
    fireEvent.click(within(shelf).getByRole("button", { name: "Unfold Shelf" }));
    // The writes of one board go out in order: the second goes once the first has answered.
    await waitFor(() => expect(api.arrangeCanvas).toHaveBeenLastCalledWith("d1", { folded: { shelf: null } }));
    expect(shelf.querySelector(".canvas-fields")).toBeTruthy();
  });

  it("finds an object type or an attribute by name and selects it", async () => {
    const onSelect = vi.fn();
    renderCanvas({ onSelect });
    await card("Shelf");
    const find = screen.getByRole("combobox", { name: "Find an object type or attribute" });
    fireEvent.change(find, { target: { value: "dep" } });
    expect(await screen.findByRole("option", { name: /Depth/ })).toBeTruthy();
    fireEvent.keyDown(find, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledWith({ show: "canvas", element: "field", key: "shelf", field: "attribute:depth" });
  });

  it("zooms with the buttons and steps and resets it", async () => {
    renderCanvas();
    await card("Shelf");
    fireEvent.click(screen.getByRole("button", { name: "Zoom out" }));
    expect(screen.getByRole("button", { name: "Zoom to 100%" }).textContent).toBe("90%");
    fireEvent.click(screen.getByRole("button", { name: "Zoom to 100%" }));
    expect(screen.getByRole("button", { name: "Zoom to 100%" }).textContent).toBe("100%");
  });
});

describe("the inspector shows the editor's panels", () => {
  it("shows the list's panel for a selected list and keeps the selection in the address", async () => {
    const onSelect = vi.fn();
    renderCanvas({ onSelect });
    const shelf = await card("Shelf");
    fireEvent.pointerDown(shelf);
    expect(onSelect).toHaveBeenCalledWith({ show: "canvas", element: "type", key: "shelf" });
  });

  it("opens on a list named in the address", async () => {
    renderCanvas({ selection: { show: "canvas", element: "type", key: "bin" } });
    const inspector = await screen.findByRole("complementary", { name: "Inspector" });
    expect(await within(inspector).findByRole("heading", { name: "Bin" })).toBeTruthy();
  });

  it("shows an attribute's rows with the editor's operations, above its attribute type", async () => {
    renderCanvas({ selection: { show: "canvas", element: "field", key: "shelf", field: "attribute:depth" } });
    const panel = await screen.findByRole("region", { name: "Attribute Depth" });
    expect(within(panel).getByText("Attribute of Shelf · decimal number")).toBeTruthy();
    fireEvent.click(within(panel).getByRole("switch", { name: "Required" }));
    await waitFor(() => expect(api.applyModelDraftOperations).toHaveBeenCalled());
    expect(vi.mocked(api.applyModelDraftOperations).mock.calls[0][2][0]).toMatchObject({ kind: "setAttributeBinding" });
  });

  it("shows a relationship line's type and the rule popover a click opens", async () => {
    renderCanvas({ selection: { show: "canvas", element: "line", key: "relates:stores:shelf:bin" } });
    const inspector = await screen.findByRole("complementary", { name: "Inspector" });
    expect(await within(inspector).findByRole("heading", { name: "Stores" })).toBeTruthy();
    fireEvent.click(await screen.findByRole("button", { name: /Rule of: Shelf Stores Bin/ }));
    const popover = await screen.findByRole("dialog", { name: /Rule of Shelf Stores Bin/ });
    fireEvent.change(within(popover).getByLabelText("How many"), { target: { value: "one-to-one" } });
    await waitFor(() => expect(api.applyModelDraftOperations).toHaveBeenCalled());
    expect(vi.mocked(api.applyModelDraftOperations).mock.calls[0][2][0]).toMatchObject({
      kind: "setRelationRule",
      relationType: "stores",
      from: "shelf",
      to: "bin",
      cardinality: "one-to-one",
    });
  });

  it("shows an application's panel and a navigation group's", async () => {
    const { unmount } = renderCanvas({ selection: { show: "canvas", element: "application", key: "shop" } });
    expect(await screen.findByRole("heading", { name: "Shop" })).toBeTruthy();
    unmount();
    renderCanvas({ selection: { show: "canvas", element: "group", application: "shop", key: "lists" } });
    expect(await screen.findByRole("heading", { name: "Lists" })).toBeTruthy();
  });

  it("shows the list panel of a sheet, with what a load does with the records no row names", async () => {
    renderCanvas({ selection: { show: "canvas", element: "list", sheet: "Shelves", block: 0 } });
    expect(await screen.findByRole("heading", { name: /Shelves|Shelf/ })).toBeTruthy();
  });

  it("has the four tabs, and the navigation tab offers the group operations", async () => {
    renderCanvas();
    await card("Shelf");
    for (const name of ["Inspector", "Navigation", "Views", "Consumer APIs"])
      expect(screen.getByRole("tab", { name })).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Navigation" }));
    expect(await screen.findByRole("button", { name: "Operations for the group Lists" })).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Consumer APIs" }));
    expect(await screen.findByRole("button", { name: "Add a consumer API" })).toBeTruthy();
  });
});

describe("the editor's own issues and history drawer", () => {
  it("counts them, and an issue leads to its card", async () => {
    const onSelect = vi.fn();
    renderCanvas({ onSelect });
    await card("Shelf");
    const toggle = screen.getByRole("button", { name: /^Issues(,| and) history.*1 issue/ });
    expect(await screen.findByText("4 steps")).toBeTruthy();
    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");
    fireEvent.click(await screen.findByRole("button", { name: /^Go to/ }));
    await waitFor(() => expect(onSelect).toHaveBeenCalledWith({ show: "canvas", element: "type", key: "bin" }));
  });
});

describe("a draft without a workbook", () => {
  it("has no workbook pane and offers Add a workbook… in the strip", async () => {
    vi.mocked(api.modelDraftProfile).mockResolvedValue({ ...workbook, profile: null, sourceFile: null } as never);
    vi.mocked(api.sourceSheets).mockResolvedValue({ items: [], nextCursor: null });
    renderCanvas();
    await card("Shelf");
    expect(await screen.findByRole("button", { name: "Add a workbook…" })).toBeTruthy();
    expect(screen.queryByRole("tablist", { name: "Sheets" })).toBeNull();
    expect(screen.queryByRole("complementary", { name: "Workbook" })).toBeNull();
    // Whole model by default: no workbook to scope the board by.
    expect(screen.getByRole("button", { name: "Whole model" }).getAttribute("aria-pressed")).toBe("true");
    // Nothing to scope by: "From the workbook" is not offered.
    expect(screen.queryByRole("button", { name: "From the workbook" })).toBeNull();
  });
});

describe("every kind of target has its menu on the page (canvasSurfaces)", () => {
  const names = () =>
    screen
      .queryAllByRole("button")
      .map((button) => button.getAttribute("aria-label") ?? "")
      .filter(Boolean);

  it("shows the draft's, an application's, an object type's and an attribute's menus", async () => {
    renderCanvas({ selection: { show: "canvas", element: "field", key: "shelf", field: "attribute:depth" } });
    await card("Shelf");
    expect(await screen.findByRole("button", { name: "Add to the model" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Operations for the application Shop" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Actions for Shelf" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Operations for the attribute Depth" })).toBeTruthy();
    // The editor's attribute type panel stands under the field's rows.
    expect(names().some((name) => /^Operations for Depth/.test(name))).toBe(true);
  });

  it("shows a relationship's menu in its popover and its type's in the inspector", async () => {
    renderCanvas({ selection: { show: "canvas", element: "line", key: "relates:stores:shelf:bin" } });
    await card("Shelf");
    fireEvent.click(await screen.findByRole("button", { name: /Rule of: Shelf Stores Bin/ }));
    const popover = await screen.findByRole("dialog", { name: /Rule of Shelf Stores Bin/ });
    expect(within(popover).getByRole("button", { name: /Operations for Shelf Stores Bin/ })).toBeTruthy();
    expect(names().some((name) => /^Operations for Stores/.test(name))).toBe(true);
  });

  it("shows the navigation's, the views' and the consumer APIs' menus in their tabs", async () => {
    renderCanvas({ selection: { show: "canvas", element: "type", key: "bin" } });
    await card("Bin");
    fireEvent.click(screen.getByRole("tab", { name: "Navigation" }));
    expect(await screen.findByRole("button", { name: "Operations for the group Lists" })).toBeTruthy();
    expect(screen.getByRole("button", { name: /Operations for the entry/ })).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Views" }));
    expect(await screen.findByRole("button", { name: "Operations for the view Bins" })).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "Consumer APIs" }));
    expect(await screen.findByRole("button", { name: "Add a consumer API" })).toBeTruthy();
  });
});
