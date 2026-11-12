import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { outlineFixture } from "@/test/draftOutline";
import { ModelEditor } from "@/features/model-editor/ModelEditor";
import { ToastProvider } from "@/ui/Toast";
import type { EngineModel, ModelDraftOperationEntry } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const step = (version: number) => ({ version, entries: [], valid: true, diagnostics: [] });
const entry = (step: number, kind: string, parameters: Record<string, unknown>): ModelDraftOperationEntry => ({
  sequence: step,
  step,
  kind,
  parameters,
  inverse: {},
  draftVersion: step,
  author: null,
  at: "2026-10-11T10:00:00Z",
  undone: false,
  origin: { type: "request" },
});

/** The running model the preview reads records through; these tests do not reach its records. */
const activeModel = {
  attributeTypes: [],
  objectTypes: [],
  relationTypes: [],
  objectTypeRelations: [],
  applications: [],
} as unknown as EngineModel;

beforeEach(() => {
  vi.clearAllMocks();
  // The preview reads the draft compiled; these tests leave it uncompiled, so it renders no record.
  vi.mocked(api.modelDraftModel).mockResolvedValue({ version: 4, valid: false, diagnostics: [] });
  vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.modelDraftOutline).mockResolvedValue(outlineFixture());
  // A draft without a workbook: no source pane, no dry run (0.10 A5b).
  vi.mocked(api.modelDraftProfile).mockResolvedValue({
    version: 4,
    profile: null,
    definition: null,
    valid: false,
    diagnostics: [],
    sourceFile: null,
  });
  vi.mocked(api.modelDraftDryRun).mockRejectedValue(new ApiError(404, "DRY_RUN_NOT_FOUND", "No dry run"));
  vi.mocked(api.modelDraftInference).mockRejectedValue(new ApiError(404, "INFERENCE_NOT_FOUND", "No inference"));
  vi.mocked(api.modelDraft).mockResolvedValue({
    id: "d1",
    name: "Store changes",
    baseReleaseId: "r1",
    model: {},
    version: 4,
    createdAt: "2026-10-11T10:00:00Z",
    updatedAt: "2026-10-11T10:00:00Z",
  });
  vi.mocked(api.modelDraftOperations).mockResolvedValue({
    items: [entry(3, "addObjectType", { name: "Bin", parent: null })],
    nextCursor: null,
    prevCursor: null,
  });
});

function renderEditor(selection: Parameters<typeof ModelEditor>[0]["selection"] = { show: "type", key: "shelf" }) {
  return render(
    <ToastProvider>
      <ModelEditor
        draftId="d1"
        selection={selection}
        onSelect={vi.fn()}
        onNavigate={vi.fn()}
        onActivated={vi.fn()}
        onOpenApplication={vi.fn()}
        onOpenChangeSet={vi.fn()}
        activeModel={activeModel}
        workspaceKey="default"
      />
    </ToastProvider>,
  );
}

describe("ModelEditor", () => {
  it("applies a key change of a released element, the menu saying it needs a migration (0.13 MG)", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: "Operations for Shelf" }));
    const item = await screen.findByRole("menuitem", { name: /^Change key…/ });
    expect(item.textContent).toContain("Needs a migration when installed");
    fireEvent.click(item);
    const dialog = await screen.findByRole("dialog", { name: "Change key" });
    fireEvent.change(within(dialog).getByLabelText("Key"), { target: { value: "rack" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setKey", element: { objectType: "shelf" }, key: "rack" },
      ]),
    );
  });

  it("opens a one-control operation under the button whose menu started it, (UX1)", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    renderEditor();
    const button = await screen.findByRole("button", { name: "Operations for Shelf" });
    fireEvent.focusIn(button);
    fireEvent.click(button);
    fireEvent.click(await screen.findByRole("menuitem", { name: /^Change key…/ }));
    const popover = await screen.findByRole("dialog", { name: "Change key" });
    expect(popover.closest(".editor-popover")).not.toBeNull();
    fireEvent.change(within(popover).getByLabelText("Key"), { target: { value: "rack" } });
    fireEvent.click(within(popover).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setKey", element: { objectType: "shelf" }, key: "rack" },
      ]),
    );
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "Change key" })).toBeNull());
  });

  it("counts every step of the draft, though only its latest operations are read (R)", async () => {
    // The latest page holds one large step, 120, of 100 operations; the older ones are not read yet.
    vi.mocked(api.modelDraftOperations).mockResolvedValue({
      items: Array.from({ length: 100 }, (_, index) => ({
        ...entry(120, "mapColumn", { source: "lists", column: `C${index}` }),
        sequence: 400 + index,
      })),
      nextCursor: null,
      prevCursor: "older",
    });
    renderEditor();
    expect(await screen.findByText("120 steps")).toBeTruthy();
  });

  it("asks before applying a step again on a draft another editor moved on (D41)", async () => {
    vi.mocked(api.applyModelDraftOperations)
      .mockRejectedValueOnce(
        new ApiError(409, "VERSION_CONFLICT", "stale", {
          // The step as another author applied it: the element is named as it was before the rename.
          operations: [
            {
              ...entry(5, "setLabel", { element: { objectType: "bin" }, name: "Crate" }),
              inverse: { kind: "setLabel", element: { objectType: "bin" }, name: "Old bin" },
            },
          ],
        }),
      )
      .mockResolvedValueOnce(step(6));
    renderEditor();
    // The name is edited in place, as a record's title is.
    fireEvent.click(await screen.findByRole("button", { name: /^Edit Name:/ }));
    const form = await screen.findByRole("form", { name: "Edit Name" });
    fireEvent.change(within(form).getByLabelText(/Name/), { target: { value: "Rack" } });
    vi.mocked(api.modelDraftOutline).mockResolvedValue({ ...outlineFixture(), version: 5 });
    fireEvent.keyDown(within(form).getByLabelText(/Name/), { key: "Enter" });
    const notice = (await screen.findByText(/Another change came first/)).closest(".notice") as HTMLElement;
    expect(within(notice).getByText(/Applied since: Renamed Old bin to Crate\./)).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
    fireEvent.click(within(notice).getByRole("button", { name: "Apply mine again" }));
    await waitFor(() => expect(api.applyModelDraftOperations).toHaveBeenCalledTimes(2));
    expect(vi.mocked(api.applyModelDraftOperations).mock.calls.map((call) => call[1])).toEqual([4, 5]);
    expect(vi.mocked(api.applyModelDraftOperations).mock.calls[1][2]).toEqual([
      { kind: "setLabel", element: { objectType: "shelf" }, name: "Rack" },
    ]);
    await waitFor(() => expect(screen.queryByText(/Another change came first/)).toBeNull());
  });

  it("offers to undo a step together with the steps that depend on it (D8)", async () => {
    vi.mocked(api.undoModelDraftStep)
      .mockRejectedValueOnce(
        new ApiError(409, "OPERATION_HAS_DEPENDANTS", "dependants", { steps: [3], dependants: [4] }),
      )
      .mockResolvedValueOnce(step(5));
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: /^Issues and history/ }));
    fireEvent.click(await screen.findByRole("tab", { name: "History" }));
    fireEvent.click(await screen.findByRole("button", { name: "Undo step 3" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Undo the steps that depend on it too?" });
    fireEvent.click(within(confirm).getByRole("button", { name: "Undo steps 3, 4" }));
    await waitFor(() => expect(api.undoModelDraftStep).toHaveBeenLastCalledWith("d1", 4, [3, 4]));
  });

  it("opens the selected element's operations from the model pane by Shift+F10", async () => {
    const onSelect = vi.fn();
    render(
      <ToastProvider>
        <ModelEditor
          draftId="d1"
          selection={{ show: "type", key: "shelf" }}
          onSelect={onSelect}
          onNavigate={vi.fn()}
          onActivated={vi.fn()}
          onOpenApplication={vi.fn()}
          onOpenChangeSet={vi.fn()}
          activeModel={activeModel}
          workspaceKey="default"
        />
      </ToastProvider>,
    );
    const tree = await screen.findByRole("tree", { name: "Model" });
    const row = within(tree)
      .getAllByRole("treeitem")
      .find((item) => item.textContent?.startsWith("Shelf"))!;
    fireEvent.keyDown(row, { key: "F10", shiftKey: true });
    expect(onSelect).toHaveBeenCalledWith({ show: "type", key: "shelf", application: "shop" });
    expect(await screen.findByRole("menuitem", { name: /^Rename/ })).toBeTruthy();
  });

  it("edits a cell in place: a relation's cardinality is one step", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    renderEditor();
    fireEvent.click(await screen.findByRole("tab", { name: /^Relations/ }));
    fireEvent.click((await screen.findAllByRole("button", { name: /^Edit Cardinality:/ }))[0]);
    const form = await screen.findByRole("form", { name: "Edit Cardinality" });
    fireEvent.change(within(form).getByRole("combobox"), { target: { value: "one-to-one" } });
    // The choice saves as it is made (0.17 UX2).
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setRelationRule", relationType: "stores", from: "shelf", to: "bin", cardinality: "one-to-one" },
      ]),
    );
  });

  it("shows a type's settings and sets its display attribute in a dialog (0.13 ED)", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    renderEditor();
    fireEvent.click(await screen.findByRole("tab", { name: "Settings" }));
    expect(await screen.findByText("Display attribute")).toBeTruthy();
    expect(screen.getByText("At least one of")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^Edit Display attribute:/ }));
    const dialog = await screen.findByRole("dialog", { name: /Which attribute names a Shelf record/ });
    fireEvent.change(within(dialog).getByLabelText("Attribute"), { target: { value: "depth" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setObjectTypeProperty", objectType: "shelf", property: "displayAttributeTypeKey", value: "depth" },
      ]),
    );
  });

  it("sets a binding's help text and an attribute type's hidden flag in place (0.13 ED)", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    renderEditor();
    fireEvent.click((await screen.findAllByRole("button", { name: /^Edit Help text on this type:/ }))[0]);
    const form = await screen.findByRole("form", { name: "Edit Help text on this type" });
    fireEvent.change(within(form).getByLabelText(/Help text on this type/), { target: { value: "Where it stands" } });
    fireEvent.keyDown(within(form).getByLabelText(/Help text on this type/), { key: "Enter" });
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        {
          kind: "setAttributeBinding",
          objectType: "shelf",
          attributeType: "code",
          ui: { helpText: "Where it stands" },
        },
      ]),
    );
  });

  it("sets an attribute type's minimum in its dialog and a relation type's orientation in place (0.13 ED)", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    const first = renderEditor({ show: "attributeType", key: "depth" });
    fireEvent.click(await screen.findByRole("button", { name: /^Edit Minimum:/ }));
    const dialog = await screen.findByRole("dialog", { name: /Smallest and largest Depth accepted/ });
    fireEvent.change(within(dialog).getByLabelText("Minimum"), { target: { value: "2" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setAttributeTypeProperty", attributeType: "depth", property: "minimum", value: 2 },
      ]),
    );
    first.unmount();
    renderEditor({ show: "relationType", key: "stores" });
    fireEvent.click(await screen.findByRole("button", { name: /^Edit Oriented:/ }));
    const form = await screen.findByRole("form", { name: "Edit Oriented" });
    fireEvent.change(within(form).getByRole("combobox"), { target: { value: "false" } });
    // The choice saves as it is made (0.17 UX2).
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenLastCalledWith("d1", 4, [
        { kind: "setRelationTypeProperty", relationType: "stores", property: "isOriented", value: false },
      ]),
    );
  });

  // Reported by the user (2026-10-19): Show issues stored the pane open, so it opened empty after.
  it("opens the issues from a preview that cannot render, without keeping the pane open", async () => {
    const editor = (selection: Parameters<typeof ModelEditor>[0]["selection"]) => (
      <ToastProvider>
        <ModelEditor
          draftId="d1"
          selection={selection}
          onSelect={vi.fn()}
          onNavigate={vi.fn()}
          onActivated={vi.fn()}
          onOpenApplication={vi.fn()}
          onOpenChangeSet={vi.fn()}
          activeModel={activeModel}
          workspaceKey="default"
        />
      </ToastProvider>
    );
    vi.mocked(api.model).mockResolvedValue(activeModel);
    // A browser's storage, which keeps what the editor stores between the two editors.
    const stored = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => stored.get(key) ?? null,
      setItem: (key: string, value: string) => stored.set(key, value),
    });
    const first = render(editor({ show: "type", key: "bin", mode: "preview" }));
    fireEvent.click(await screen.findByRole("button", { name: "Show issues" }));
    expect(screen.getByRole("button", { name: /^Issues and history/ })).toHaveAttribute("aria-expanded", "true");
    first.unmount();
    render(editor({}));
    expect(await screen.findByRole("button", { name: /^Issues and history/ })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    vi.unstubAllGlobals();
  });

  it("links an issue to the element it concerns", async () => {
    const onSelect = vi.fn();
    render(
      <ToastProvider>
        <ModelEditor
          draftId="d1"
          selection={{}}
          onSelect={onSelect}
          onNavigate={vi.fn()}
          onActivated={vi.fn()}
          onOpenApplication={vi.fn()}
          onOpenChangeSet={vi.fn()}
          activeModel={activeModel}
          workspaceKey="default"
        />
      </ToastProvider>,
    );
    const toggle = await screen.findByRole("button", { name: /^Issues and history/ });
    // Closed until the reader opens it (the user, 2026-10-11).
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("button", { name: "Go to Bin" })).toBeNull();
    fireEvent.click(toggle);
    fireEvent.click(await screen.findByRole("button", { name: "Go to Bin" }));
    expect(onSelect).toHaveBeenCalledWith({ show: "type", key: "bin" });
  });

  it("offers Remove from page on a panel issue, which works while the draft is invalid", async () => {
    const base = outlineFixture();
    vi.mocked(api.modelDraftOutline).mockResolvedValue({
      ...base,
      diagnostics: [
        {
          severity: "error",
          code: "INVALID_MODEL",
          path: "/applications/shop/details/bin/panels/stock",
          message:
            "The Stock panel on the Bin page lists a relation Bin no longer has. Remove the panel or restore the relation.",
          element: { applicationKey: "shop", detail: "bin", panel: "stock" },
        },
      ],
    });
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    const onSelect = vi.fn();
    render(
      <ToastProvider>
        <ModelEditor
          draftId="d1"
          selection={{}}
          onSelect={onSelect}
          onNavigate={vi.fn()}
          onActivated={vi.fn()}
          onOpenApplication={vi.fn()}
          onOpenChangeSet={vi.fn()}
          activeModel={activeModel}
          workspaceKey="default"
        />
      </ToastProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: /^Issues and history/ }));
    expect(await screen.findByText(/The Stock panel on the Bin page/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^Go to / }));
    expect(onSelect).toHaveBeenCalledWith({ show: "type", key: "bin", application: "shop" });
    fireEvent.click(screen.getByRole("button", { name: "Remove from page" }));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "removeViewItem", applicationKey: "shop", detail: "bin", list: "panels", item: "stock" },
      ]),
    );
  });

  it("says so in a popup when a step leaves more issues, and not on opening or when they fall", async () => {
    const base = outlineFixture();
    const issue = (panel: string) => ({
      severity: "error" as const,
      code: "INVALID_MODEL",
      path: `/applications/shop/details/bin/panels/${panel}`,
      message: `The ${panel} panel lists a relation Bin no longer has.`,
      element: { applicationKey: "shop", detail: "bin", panel },
    });
    vi.mocked(api.modelDraftOutline).mockResolvedValue({ ...base, diagnostics: [issue("a")] });
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    render(
      <ToastProvider>
        <ModelEditor
          draftId="d1"
          selection={{}}
          onSelect={vi.fn()}
          onNavigate={vi.fn()}
          onActivated={vi.fn()}
          onOpenApplication={vi.fn()}
          onOpenChangeSet={vi.fn()}
          activeModel={activeModel}
          workspaceKey="default"
        />
      </ToastProvider>,
    );
    const toggle = await screen.findByRole("button", { name: /^Issues and history/ });
    // Opening an invalid draft is not news.
    expect(screen.queryByRole("button", { name: "Show issues" })).toBeNull();
    fireEvent.click(toggle);
    // A step that leaves three issues, two more than the one before, is.
    vi.mocked(api.modelDraftOutline).mockResolvedValue({
      ...base,
      version: 5,
      diagnostics: [issue("a"), issue("b"), issue("c")],
    });
    fireEvent.click(await screen.findByRole("button", { name: "Remove from page" }));
    expect(await screen.findByText("The draft now has 3 issues, 2 more than before.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Show issues" }));
    expect(screen.queryByText(/2 more than before/)).toBeNull();
  });

  describe("navigation groups: relation matrices as entries (0.13)", () => {
    /** Shop with a Lists group holding Bins and a matrix of shelves by bins, an empty More group, Area and Shelf in none. */
    function matrixOutline() {
      const outline = outlineFixture();
      const shop = outline.applications[0];
      shop.defaultView = "bins";
      shop.views = [
        { key: "bins", name: "Bins", type: "table", collection: "bin", shows: ["bin"], mark: "new" },
        { key: "shelves", name: "Shelves", type: "table", collection: "shelf", shows: ["shelf"], mark: "new" },
        {
          key: "shelves-by-bin",
          name: "Shelves by bin",
          type: "relationMatrix",
          collection: "shelf",
          shows: ["shelf", "bin", "bin"],
          mark: "new",
        },
      ];
      shop.navigation = {
        groups: [
          {
            key: "lists",
            label: "Lists",
            collapsed: false,
            collections: ["bin", "shelf"],
            entries: [{ collection: "bin" }, { view: "shelves-by-bin" }, { collection: "shelf" }],
            mark: "new",
          },
          { key: "more", label: "More", collapsed: true, collections: [], entries: [], mark: "new" },
        ],
        ungrouped: ["area"],
        opens: {},
      };
      return outline;
    }

    it("opens a group's panel with its entries, collections and matrices in one order", async () => {
      vi.mocked(api.modelDraftOutline).mockResolvedValue(matrixOutline());
      renderEditor({ show: "group", application: "shop", key: "lists" });
      const table = await screen.findByRole("table", { name: "Entries of Lists" });
      const rows = within(table).getAllByRole("row").slice(1);
      expect(
        rows.map((row) =>
          within(row)
            .getAllByRole("cell")
            .slice(0, 3)
            .map((cell) => cell.textContent?.trim()),
        ),
      ).toEqual([
        ["Bin", "List", expect.stringContaining("table · Bins")],
        ["Shelves by bin", "Relation matrix", "relation matrix · Shelves by bin"],
        ["Shelf", "List", expect.stringContaining("table · Shelves")],
      ]);
      expect(screen.getByText("Navigation group of")).toBeTruthy();
      expect(screen.getByRole("button", { name: "Add to group…" })).toBeTruthy();
      expect(screen.getByRole("button", { name: "Start folded" })).toBeTruthy();
    });

    it("sets what a collection opens on in place, and puts it back to the default as no choice", async () => {
      vi.mocked(api.modelDraftOutline).mockResolvedValue(matrixOutline());
      vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
      renderEditor({ show: "group", application: "shop", key: "lists" });
      await screen.findByRole("table", { name: "Entries of Lists" });
      fireEvent.click(screen.getByRole("button", { name: /^Edit Opens on: table · Shelves/ }));
      const form = await screen.findByRole("form", { name: "Edit Opens on" });
      fireEvent.change(within(form).getByRole("combobox"), { target: { value: "shelves-by-bin" } });
      // The choice saves as it is made (0.17 UX2).
      await waitFor(() =>
        expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
          { kind: "setCollectionOpening", applicationKey: "shop", collection: "shelf", view: "shelves-by-bin" },
        ]),
      );
    });

    it("moves an entry within its group, to another group and out of it, each as one operation", async () => {
      vi.mocked(api.modelDraftOutline).mockResolvedValue(matrixOutline());
      vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
      renderEditor({ show: "group", application: "shop", key: "lists" });
      await screen.findByRole("table", { name: "Entries of Lists" });
      fireEvent.click(screen.getByRole("button", { name: "Operations for Shelves by bin" }));
      fireEvent.click(await screen.findByRole("menuitem", { name: "Move up" }));
      await waitFor(() =>
        expect(api.applyModelDraftOperations).toHaveBeenLastCalledWith("d1", 4, [
          { kind: "placeCollection", applicationKey: "shop", view: "shelves-by-bin", group: "lists", position: 0 },
        ]),
      );
      fireEvent.click(screen.getByRole("button", { name: "Operations for Shelves by bin" }));
      fireEvent.click(await screen.findByRole("menuitem", { name: "Take out of the group" }));
      await waitFor(() =>
        expect(api.applyModelDraftOperations).toHaveBeenLastCalledWith("d1", 4, [
          { kind: "placeCollection", applicationKey: "shop", view: "shelves-by-bin", group: null },
        ]),
      );
    });

    it("adds several entries in one step from a dialog that searches and says where each stands", async () => {
      vi.mocked(api.modelDraftOutline).mockResolvedValue(matrixOutline());
      vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
      renderEditor({ show: "group", application: "shop", key: "more" });
      fireEvent.click(await screen.findByRole("button", { name: "Add to group…" }));
      const dialog = await screen.findByRole("dialog", { name: "Add to More" });
      expect(within(dialog).getByRole("group", { name: "Collections" })).toBeTruthy();
      expect(within(dialog).getByRole("group", { name: "Relation matrices" })).toBeTruthy();
      const area = within(dialog).getByRole("checkbox", { name: /Area/ });
      expect(area.closest("label")?.textContent).toContain("Top of the sidebar");
      expect(
        within(dialog)
          .getByRole("checkbox", { name: /Shelves by bin/ })
          .closest("label")?.textContent,
      ).toContain("In Lists");
      const send = within(dialog).getByRole("button", { name: "Add 0 items" });
      expect(send).toBeDisabled();
      fireEvent.change(within(dialog).getByRole("textbox", { name: "Search collections and matrices" }), {
        target: { value: "bin" },
      });
      expect(within(dialog).queryByRole("checkbox", { name: /Area/ })).toBeNull();
      fireEvent.click(within(dialog).getByRole("checkbox", { name: /Shelves by bin/ }));
      expect(
        within(dialog)
          .getByRole("checkbox", { name: /Shelves by bin/ })
          .closest("label")?.textContent,
      ).toContain("Moves from Lists");
      fireEvent.change(within(dialog).getByRole("textbox", { name: "Search collections and matrices" }), {
        target: { value: "" },
      });
      fireEvent.click(within(dialog).getByRole("checkbox", { name: /Area/ }));
      fireEvent.click(within(dialog).getByRole("button", { name: "Add 2 items" }));
      await waitFor(() =>
        expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
          { kind: "placeCollection", applicationKey: "shop", view: "shelves-by-bin", group: "more" },
          { kind: "placeCollection", applicationKey: "shop", collection: "area", group: "more" },
        ]),
      );
    });

    it("lists matrices among a group's entries on the application panel, and adds the ungrouped to a group", async () => {
      vi.mocked(api.modelDraftOutline).mockResolvedValue(matrixOutline());
      vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
      renderEditor({ show: "application", key: "shop" });
      const table = await screen.findByRole("table", { name: "Navigation groups of Shop" });
      expect(within(table).getByRole("columnheader", { name: "Entries" })).toBeTruthy();
      expect(within(table).getByText("Shelves by bin")).toBeTruthy();
      fireEvent.click(within(table).getByRole("button", { name: "Lists" }));
      fireEvent.click(screen.getByRole("button", { name: "Add to a group…" }));
      const dialog = await screen.findByRole("dialog", { name: "Add to a group" });
      expect(within(dialog).getByRole("checkbox", { name: /Area/ })).toBeChecked();
      fireEvent.change(within(dialog).getByLabelText("Group"), { target: { value: "more" } });
      fireEvent.click(within(dialog).getByRole("button", { name: "Add 1 item" }));
      await waitFor(() =>
        expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
          { kind: "placeCollection", applicationKey: "shop", collection: "area", group: "more" },
        ]),
      );
    });

    it("moves a relation matrix to a group from its own menu in the Views table", async () => {
      vi.mocked(api.modelDraftOutline).mockResolvedValue(matrixOutline());
      vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
      renderEditor({ show: "application", key: "shop" });
      await screen.findByRole("table", { name: "Views of Shop" });
      fireEvent.click(screen.getByRole("button", { name: "Operations for the view Shelves by bin" }));
      fireEvent.click(await screen.findByRole("menuitem", { name: "Move to group…" }));
      const dialog = await screen.findByRole("dialog", { name: /Place Shelves by bin in a navigation group/ });
      fireEvent.change(within(dialog).getByLabelText("Group"), { target: { value: "more" } });
      fireEvent.click(within(dialog).getByRole("button", { name: "Move" }));
      await waitFor(() =>
        expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
          { kind: "placeCollection", applicationKey: "shop", view: "shelves-by-bin", group: "more" },
        ]),
      );
    });
  });
});
