/**
 * The pieces the model editor shares with the canvas (0.17 CE1, PP-D3), each mounted by a tiny host and no
 * `ModelEditor`: the editing hook with its dialogs and notices, the draft's action set, the preview, the
 * element panel, the matrix and the issues. A second page does what these hosts do.
 */

import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { DraftEditingDialogs, DraftEditingNotices } from "@/features/model-editor/DraftEditingDialogs";
import { DraftPreview } from "@/features/model-editor/DraftPreview";
import { ElementPanel } from "@/features/model-editor/ElementPanel";
import { IssuesAndHistory } from "@/features/model-editor/IssuesAndHistory";
import { OperationsMenu } from "@/features/model-editor/OperationsMenu";
import { RelationshipMatrix } from "@/features/model-editor/RelationshipMatrix";
import { useDraftActions, type DraftActionId } from "@/features/model-editor/useDraftActions";
import { useDraftEditing } from "@/features/model-editor/useDraftEditing";
import type { DraftSource } from "@/features/model-editor/useDraftSource";
import { capabilitiesFixture } from "@/test/capabilities";
import { outlineFixture } from "@/test/draftOutline";
import { domainObject, testModel } from "@/test/fixtures";
import { ToastProvider } from "@/ui/Toast";
import type { EditorSelection, EngineModel } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const step = (version: number) => ({ version, entries: [], valid: true, diagnostics: [] });
const noop = () => undefined;

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.modelDraftOutline).mockResolvedValue(outlineFixture());
  vi.mocked(api.modelDraft).mockResolvedValue({
    id: "d1",
    name: "Store changes",
    baseReleaseId: "r1",
    model: {},
    version: 4,
    createdAt: "2026-10-11T10:00:00Z",
    updatedAt: "2026-10-11T10:00:00Z",
  });
});

/** A second page: the editing hook, a target's menu and its panel, and what the hook opens and says. */
function Host({ selection = { show: "type", key: "shelf" } }: { selection?: EditorSelection }) {
  const editing = useDraftEditing("d1");
  const [current, select] = useState<EditorSelection>(selection);
  const { outline } = editing;
  if (!outline) return <p>Loading</p>;
  return (
    <ToastProvider>
      <OperationsMenu
        label="Shelf operations"
        target={{ on: "objectType", objectType: "shelf" }}
        outline={outline}
        onOperation={editing.operate}
      />
      <ElementPanel
        outline={outline}
        selection={current}
        tab="attributes"
        onTab={noop}
        menuOpen={editing.menuOpen}
        onMenuOpenChange={editing.setMenuOpen}
        canDrag={false}
        onOperation={editing.operate}
        onSelect={select}
        run={editing.run}
        onPreview={noop}
      />
      <button type="button" onClick={() => void editing.undo()}>
        Undo from the host
      </button>
      <DraftEditingNotices editing={editing} />
      <DraftEditingDialogs editing={editing} />
    </ToastProvider>
  );
}

describe("useDraftEditing on a page of its own", () => {
  it("starts an operation from a menu, sends it at the draft's version and reads the draft again", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue(step(5));
    render(<Host />);
    fireEvent.click(await screen.findByRole("button", { name: "Shelf operations" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: /^Change key…/ }));
    const dialog = await screen.findByRole("dialog", { name: "Change key" });
    fireEvent.change(within(dialog).getByLabelText("Key"), { target: { value: "rack" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [
        { kind: "setKey", element: { objectType: "shelf" }, key: "rack" },
      ]),
    );
    await waitFor(() => expect(vi.mocked(api.modelDraftOutline).mock.calls.length).toBeGreaterThan(1));
  });

  it("holds a step the draft moved on from and sends it again when asked (D41)", async () => {
    vi.mocked(api.applyModelDraftOperations)
      .mockRejectedValueOnce(new ApiError(409, "VERSION_CONFLICT", "Moved on", { operations: [], more: false }))
      .mockResolvedValue(step(6));
    render(<Host />);
    fireEvent.click(await screen.findByRole("button", { name: "Shelf operations" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: /^Change key…/ }));
    const dialog = await screen.findByRole("dialog", { name: "Change key" });
    fireEvent.change(within(dialog).getByLabelText("Key"), { target: { value: "rack" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    fireEvent.click(await screen.findByRole("button", { name: "Apply mine again" }));
    await waitFor(() => expect(api.applyModelDraftOperations).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByText("Another change came first")).toBeNull());
  });

  it("asks about the dependants of an undo the engine refused, and undoes them together", async () => {
    vi.mocked(api.undoModelDraftStep)
      .mockRejectedValueOnce(
        new ApiError(409, "OPERATION_HAS_DEPENDANTS", "Later steps depend on it", { steps: [2], dependants: [3] }),
      )
      .mockResolvedValue(step(6));
    render(<Host />);
    fireEvent.click(await screen.findByRole("button", { name: "Undo from the host" }));
    expect(await screen.findByText(/Step 3 uses what step 2 created/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Undo steps 2, 3" }));
    await waitFor(() => expect(api.undoModelDraftStep).toHaveBeenLastCalledWith("d1", 4, [2, 3]));
  });
});

describe("the draft's action set", () => {
  const sourceFile = { id: "f1", name: "book.xlsx" };
  const source = (withFile: boolean) =>
    ({
      profile: { sourceFile: withFile ? sourceFile : null, profile: null, diagnostics: [] },
      sheets: [],
      columns: () => undefined,
    }) as unknown as DraftSource;

  function Actions({
    withFile,
    forWorkspace,
    proposing,
    ids,
  }: {
    withFile: boolean;
    forWorkspace?: string;
    proposing?: boolean;
    ids: DraftActionId[];
  }) {
    const editing = useDraftEditing("d1");
    const actions = useDraftActions({
      editing,
      source: source(withFile),
      forWorkspace,
      workspaceKey: "default",
      proposing,
      onActivated: async () => undefined,
      onNavigate: vi.fn(),
      onOpenChangeSet: vi.fn(),
      onShowIssues: noop,
    });
    if (!editing.outline) return <p>Loading</p>;
    return (
      <>
        <ul>
          {actions.items(ids).map((item) => (
            <li key={item.id} data-disabled={item.disabled ? "yes" : "no"}>
              {item.label}
            </li>
          ))}
        </ul>
        <button type="button" onClick={() => actions.open("install")}>
          Open install
        </button>
        {actions.dialogs}
      </>
    );
  }
  const renderActions = (props: Parameters<typeof Actions>[0]) =>
    render(
      <ToastProvider>
        <Actions {...props} />
      </ToastProvider>,
    );
  const ALL: DraftActionId[] = ["apply", "install", "load", "workbook", "json", "delete"];
  const labels = () => screen.getAllByRole("listitem").map((item) => item.textContent);

  it("offers Apply only from a workspace, Load only with a workbook, and says Upload a newer one for a second", async () => {
    const { unmount } = renderActions({ withFile: false, ids: ALL });
    await screen.findByText("Install and activate…");
    expect(labels()).toEqual(["Install and activate…", "Add a workbook…", "Open as JSON", "Delete draft…"]);
    unmount();
    renderActions({ withFile: true, forWorkspace: "ws", ids: ALL });
    await screen.findByText("Install and activate…");
    expect(labels()).toEqual([
      "Apply to this workspace…",
      "Install and activate…",
      "Load into a change set…",
      "Upload a newer workbook…",
      "Open as JSON",
      "Delete draft…",
    ]);
  });

  it("waits while the engine proposes: Delete is not offered and only Open as JSON stays enabled", async () => {
    renderActions({ withFile: true, ids: ALL, proposing: true });
    await screen.findByText("Install and activate…");
    expect(labels()).not.toContain("Delete draft…");
    const enabled = screen.getAllByRole("listitem").filter((item) => item.dataset.disabled === "no");
    expect(enabled.map((item) => item.textContent)).toEqual(["Open as JSON"]);
  });

  it("opens its dialog without the editor", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture({ manageModel: true }));
    vi.mocked(api.compileModelDraft).mockResolvedValue({
      valid: true,
      diagnostics: [],
      compatibility: { classification: "compatible", activeReleaseId: "r1", diagnostics: [], workspaces: [] },
      changes: [],
    });
    vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
    renderActions({ withFile: false, ids: ALL });
    fireEvent.click(await screen.findByRole("button", { name: "Open install" }));
    expect(await screen.findByRole("dialog", { name: /Install/ })).toBeTruthy();
  });
});

describe("the preview, the matrix and the issues on a page of their own", () => {
  const base = testModel.applications[0]!;
  const model: EngineModel = {
    ...testModel,
    applications: [{ ...base, key: "shelf-app", name: "Shelf app" }],
  };

  function Preview({ mode }: { mode: "preview" | "layout" }) {
    const editing = useDraftEditing("d1");
    if (!editing.outline) return <p>Loading</p>;
    return (
      <ToastProvider>
        <DraftPreview
          editing={editing}
          mode={mode}
          objectTypeKey="domain"
          activeModel={model}
          workspaceKey="default"
          onShowIssues={noop}
          actions={<button type="button">Back</button>}
        />
        <DraftEditingDialogs editing={editing} />
      </ToastProvider>
    );
  }

  beforeEach(() => {
    vi.mocked(api.modelDraftModel).mockResolvedValue({
      version: 4,
      valid: true,
      diagnostics: [],
      model,
      placements: model.placements,
    });
    vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.model).mockResolvedValue(model);
    vi.mocked(api.object).mockResolvedValue({ ...domainObject, applicationKey: "shelf-app" });
    vi.mocked(api.objects).mockResolvedValue({ items: [], nextCursor: null, prevCursor: null });
    vi.mocked(api.objectHistory).mockResolvedValue({ items: [], nextCursor: null });
    vi.mocked(api.relations).mockResolvedValue({ items: [], nextCursor: null, prevCursor: null });
  });

  it("shows a type's preview from the draft, and its layout editor, with the page's own actions", async () => {
    const { unmount } = render(<Preview mode="preview" />);
    expect(await screen.findByRole("region", { name: "Preview" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Back" })).toBeTruthy();
    expect(api.modelDraftModel).toHaveBeenCalledWith("d1");
    unmount();
    render(<Preview mode="layout" />);
    expect(await screen.findByRole("region", { name: "Layout editor" })).toBeTruthy();
  });

  it("draws the matrix and the issues from props alone", async () => {
    function Rest() {
      const editing = useDraftEditing("d1");
      if (!editing.outline) return <p>Loading</p>;
      return (
        <>
          <RelationshipMatrix outline={editing.outline} onOperation={editing.operate} />
          <IssuesAndHistory
            outline={editing.outline}
            tab="issues"
            onTab={noop}
            history={{ items: [], loading: false, error: "", hasMore: false, loadMore: noop, reload: noop } as never}
            onSelect={noop}
            onUndoStep={noop}
          />
        </>
      );
    }
    render(<Rest />);
    await waitFor(() => expect(screen.queryByText("Loading")).toBeNull());
  });
});
