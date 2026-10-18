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
  it("shows a refused draft-only operation with what it would affect, applying nothing (D39)", async () => {
    vi.mocked(api.applyModelDraftOperations).mockRejectedValue(
      new ApiError(409, "OPERATION_REQUIRES_MIGRATION", "needs a migration", {
        element: { objectType: "shelf" },
        impact: { records: 12, values: "10000+", relationships: 3 },
      }),
    );
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: "Operations for Shelf" }));
    const item = await screen.findByRole("menuitem", { name: /^Change key…/ });
    expect(item.textContent).toContain("Needs a migration");
    fireEvent.click(item);
    const dialog = await screen.findByRole("dialog", { name: "Change key" });
    fireEvent.change(within(dialog).getByLabelText("Key"), { target: { value: "rack" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Apply" }));
    expect(
      await within(dialog).findByText(
        "Shelf is released, so this change needs a migration (planned for 1.0). It would affect 12 records, 10000+ values and 3 relationships. Nothing was applied.",
      ),
    ).toBeTruthy();
    expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
      { kind: "setKey", element: { objectType: "shelf" }, key: "rack" },
    ]);
    expect(api.modelDraftOutline).toHaveBeenCalledTimes(1);
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
          operations: [entry(5, "setLabel", { element: { objectType: "bin" }, name: "Crate" })],
        }),
      )
      .mockResolvedValueOnce(step(6));
    renderEditor();
    // The name is edited in place, as a record's title is.
    fireEvent.click(await screen.findByRole("button", { name: /^Edit Name:/ }));
    const form = await screen.findByRole("form", { name: "Edit Name" });
    fireEvent.change(within(form).getByLabelText(/Name/), { target: { value: "Rack" } });
    vi.mocked(api.modelDraftOutline).mockResolvedValue({ ...outlineFixture(), version: 5 });
    fireEvent.click(within(form).getByRole("button", { name: "Save" }));
    const notice = (await screen.findByText(/Another change came first/)).closest(".notice") as HTMLElement;
    expect(within(notice).getByText(/Applied since: Renamed Bin to Crate\./)).toBeTruthy();
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
    expect(onSelect).toHaveBeenCalledWith({ show: "type", key: "shelf" });
    expect(await screen.findByRole("menuitem", { name: /^Rename/ })).toBeTruthy();
  });

  it("edits a cell in place: a relation's cardinality is one step", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    renderEditor();
    fireEvent.click(await screen.findByRole("tab", { name: /^Relations/ }));
    fireEvent.click((await screen.findAllByRole("button", { name: /^Edit Cardinality:/ }))[0]);
    const form = await screen.findByRole("form", { name: "Edit Cardinality" });
    fireEvent.change(within(form).getByRole("combobox"), { target: { value: "one-to-one" } });
    fireEvent.click(within(form).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setRelationRule", relationType: "stores", from: "shelf", to: "bin", cardinality: "one-to-one" },
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
});
