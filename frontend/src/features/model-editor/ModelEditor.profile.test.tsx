import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, jobEventsUrl } from "@/api/client";
import { outlineFixture } from "@/test/draftOutline";
import { ModelEditor } from "@/features/model-editor/ModelEditor";
import { proposeWhenProfiled, takeWaitingProposal } from "@/model/proposing";
import { ToastProvider } from "@/ui/Toast";
import type { DraftProfile, EngineModel, Inference } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});
// The job's event stream is held by the test: the run stays where it leaves it, and an event is sent by hand.
const streams = vi.hoisted(() => new Map<string, ((event: { data: string }) => void)[]>());
vi.mock("@/api/eventStream", () => ({
  openEventStream: (url: string) => ({
    url,
    addEventListener: (_type: string, listener: (event: { data: string }) => void) =>
      streams.set(url, [...(streams.get(url) ?? []), listener]),
    close: () => streams.delete(url),
  }),
}));

const activeModel = {
  attributeTypes: [],
  objectTypes: [],
  relationTypes: [],
  objectTypeRelations: [],
  applications: [],
} as unknown as EngineModel;

const conflict: DraftProfile = {
  version: 4,
  profile: { key: "X", name: "X profile", sources: [], valueMaps: {} },
  definition: null,
  valid: false,
  diagnostics: [
    {
      severity: "error",
      code: "IMPORT_PROFILE_MODEL_MISMATCH",
      path: "/profile/key",
      message: "Import profile 'X' belongs to the model 'draf-2'.",
    },
  ],
  sourceFile: { id: "f1", name: "book.xlsx", profile: "completed" },
  freeKey: "X-2",
};

const checking = (): Inference => ({
  jobId: "j1",
  state: "checking",
  mode: "extend",
  draftVersion: 4,
  sourceFileId: "f1",
  counts: { open: 0, applied: 0, held: 0, rejected: 0 },
  disagreements: [],
  warnings: [],
  proposed: [],
  error: null,
});

beforeEach(() => {
  vi.clearAllMocks();
  takeWaitingProposal("d1");
  vi.mocked(api.modelDraftModel).mockResolvedValue({ version: 4, valid: false, diagnostics: [] });
  vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.modelDraftOutline).mockResolvedValue(outlineFixture());
  vi.mocked(api.modelDraftProfile).mockResolvedValue(conflict);
  vi.mocked(api.modelDraftDryRun).mockRejectedValue(new ApiError(404, "DRY_RUN_NOT_FOUND", "No dry run"));
  vi.mocked(api.modelDraftInference).mockRejectedValue(new ApiError(404, "INFERENCE_NOT_FOUND", "No inference"));
  vi.mocked(api.modelDraftProposals).mockResolvedValue([]);
  vi.mocked(api.sourceSheets).mockResolvedValue({ items: [], nextCursor: null });
  vi.mocked(api.system).mockResolvedValue({ ai: { configured: true, provider: "ollama", model: "qwen3:8b" } } as never);
  vi.mocked(api.modelDraftOperations).mockResolvedValue({ items: [], nextCursor: null, prevCursor: null });
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

function renderEditor(onNavigate = vi.fn(), journey?: { kind: "aiTask"; taskId: string }) {
  return render(
    <ToastProvider>
      <ModelEditor
        draftId="d1"
        journey={journey}
        selection={{}}
        onSelect={vi.fn()}
        onNavigate={onNavigate}
        onActivated={vi.fn()}
        onOpenApplication={vi.fn()}
        onOpenChangeSet={vi.fn()}
        activeModel={activeModel}
        workspaceKey="default"
      />
    </ToastProvider>,
  );
}

describe("the draft profile's key (the user, 2026-10-28)", () => {
  it("shows the key and name in the source pane and sets the free key in one step", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue({
      version: 5,
      entries: [],
      valid: true,
      diagnostics: [],
    });
    renderEditor();
    const pane = await screen.findByLabelText("Import profile");
    expect(within(pane).getByText("X")).toBeTruthy();
    expect(within(pane).getByText("X profile")).toBeTruthy();
    fireEvent.click(within(pane).getByRole("button", { name: "Use 'X-2'" }));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [{ kind: "setProfile", key: "X-2" }]),
    );
  });

  it("lists the conflict in Issues with the same action", async () => {
    vi.mocked(api.applyModelDraftOperations).mockResolvedValue({
      version: 5,
      entries: [],
      valid: true,
      diagnostics: [],
    });
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: /^Issues and history/ }));
    const row = (await screen.findByText(/Import profile 'X' belongs to the model/)).closest("li") as HTMLElement;
    expect(within(row).getByText("Error")).toBeTruthy();
    expect(within(row).getByRole("button", { name: "Go to the profile key" })).toBeTruthy();
    fireEvent.click(within(row).getByRole("button", { name: "Use 'X-2'" }));
    await waitFor(() =>
      expect(api.applyModelDraftOperations).toHaveBeenCalledWith("d1", 4, [{ kind: "setProfile", key: "X-2" }]),
    );
  });
});

describe("the editor while the engine proposes (the user, 2026-10-28)", () => {
  it("shows the reading phase, pauses editing and resumes it on Stop with nothing applied", async () => {
    vi.mocked(api.modelDraftProfile).mockResolvedValue({ ...conflict, diagnostics: [], freeKey: null });
    vi.mocked(api.proposeFromWorkbook).mockResolvedValue(checking());
    vi.mocked(api.cancelJob).mockResolvedValue({} as never);
    proposeWhenProfiled("d1", { mode: "extend" });
    renderEditor();
    expect(await screen.findByText("Finding the model in every sheet…")).toBeTruthy();
    expect(screen.getByText(/Editing is paused until the proposals are applied/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Install and activate…" }) as HTMLButtonElement).disabled).toBe(true);
    // The profile's key is read, not edited, meanwhile.
    expect(screen.queryByRole("button", { name: /Edit Profile key/ })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    await waitFor(() => expect(api.cancelJob).toHaveBeenCalledWith("j1"));
    await waitFor(() => expect(screen.queryByText(/Editing is paused/)).toBeNull());
    expect((screen.getByRole("button", { name: "Install and activate…" }) as HTMLButtonElement).disabled).toBe(false);
    expect(api.applyProposals).not.toHaveBeenCalled();
  });

  it("cancels the job when Stop is pressed before the start request has answered (R17-F49)", async () => {
    vi.mocked(api.modelDraftProfile).mockResolvedValue({ ...conflict, diagnostics: [], freeKey: null });
    let answer: (inference: ReturnType<typeof checking>) => void = () => undefined;
    vi.mocked(api.proposeFromWorkbook).mockReturnValue(new Promise((resolve) => (answer = resolve)));
    vi.mocked(api.cancelJob).mockResolvedValue({} as never);
    proposeWhenProfiled("d1", { mode: "extend" });
    renderEditor();
    fireEvent.click(await screen.findByRole("button", { name: "Stop" }));
    expect(api.cancelJob).not.toHaveBeenCalled();
    await act(async () => answer(checking()));
    await waitFor(() => expect(api.cancelJob).toHaveBeenCalledWith("j1"));
    await waitFor(() => expect(screen.queryByText(/Editing is paused/)).toBeNull());
    expect(api.applyProposals).not.toHaveBeenCalled();
  });

  it("submits exactly one inference for New from a workbook, and none when one is resumed", async () => {
    vi.mocked(api.modelDraftProfile).mockResolvedValue({ ...conflict, diagnostics: [], freeKey: null });
    vi.mocked(api.proposeFromWorkbook).mockResolvedValue(checking());
    proposeWhenProfiled("d1", { mode: "extend" });
    const first = renderEditor();
    await screen.findByText("Finding the model in every sheet…");
    // More steps and re-reads while it runs must not submit it again.
    await act(async () => new Promise((resolve) => setTimeout(resolve, 50)));
    expect(api.proposeFromWorkbook).toHaveBeenCalledTimes(1);
    first.unmount();
    vi.clearAllMocks();
    vi.mocked(api.modelDraftInference).mockResolvedValue(checking());
    renderEditor();
    await screen.findByText("Finding the model in every sheet…");
    expect(api.proposeFromWorkbook).not.toHaveBeenCalled();
  });

  it("names the reading phase while the rules read every sheet", async () => {
    vi.mocked(api.modelDraftProfile).mockResolvedValue({ ...conflict, diagnostics: [], freeKey: null });
    vi.mocked(api.proposeFromWorkbook).mockResolvedValue(checking());
    proposeWhenProfiled("d1", { mode: "extend" });
    renderEditor();
    expect(await screen.findByText("Finding the model in every sheet…")).toBeTruthy();
  });

  it("names the profiling phase while the workbook is read", async () => {
    vi.mocked(api.modelDraftProfile).mockResolvedValue({
      ...conflict,
      diagnostics: [],
      freeKey: null,
      sourceFile: { id: "f1", name: "book.xlsx", profile: "running" },
    });
    vi.mocked(api.sourceFile).mockResolvedValue({ profile: { jobId: null } } as never);
    proposeWhenProfiled("d1", { mode: "extend" });
    renderEditor();
    expect(await screen.findByText("Reading the workbook…")).toBeTruthy();
  });

  it("picks up an inference still running when the editor opens, then applies it", async () => {
    vi.mocked(api.modelDraftProfile).mockResolvedValue({ ...conflict, diagnostics: [], freeKey: null });
    vi.mocked(api.modelDraftInference).mockResolvedValue(checking());
    vi.mocked(api.applyProposals).mockResolvedValue({ version: 5, entries: [], valid: true, diagnostics: [] });
    renderEditor();
    expect(await screen.findByText("Finding the model in every sheet…")).toBeTruthy();
    expect(screen.getByText(/Editing is paused until the proposals are applied/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Stop" })).toBeTruthy();
    expect((screen.getByRole("button", { name: "Install and activate…" }) as HTMLButtonElement).disabled).toBe(true);
    // The job ends: the inference now reads completed, .
    vi.mocked(api.modelDraftInference).mockResolvedValue({
      ...checking(),
      state: "completed",
      counts: { open: 2, applied: 0, held: 0, rejected: 0 },
    });
    const follow = streams.get(jobEventsUrl("j1"))?.at(-1);
    expect(follow).toBeTruthy();
    await act(async () => follow!({ data: JSON.stringify({ id: "j1", state: "completed" }) }));
    await waitFor(() => expect(api.applyProposals).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.queryByText(/Editing is paused/)).toBeNull());
  });
});

describe("stepping away from the editor (the user, 2026-10-28)", () => {
  const models = { kind: "settings", page: "model" };

  it("says work is kept and closes to Settings › Model", async () => {
    const onNavigate = vi.fn();
    renderEditor(onNavigate);
    expect(await screen.findByText("Saved as you go: closing keeps the draft and its proposals.")).toBeTruthy();
    fireEvent.click(screen.getByRole("link", { name: "Close" }));
    expect(onNavigate).toHaveBeenCalledWith(models);
    expect(api.deleteModelDraft).not.toHaveBeenCalled();
  });

  it("closes back to the assistant's task when it was opened from there", async () => {
    const onNavigate = vi.fn();
    renderEditor(onNavigate, { kind: "aiTask", taskId: "t-1" });
    fireEvent.click(await screen.findByRole("link", { name: "Close" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "ai-tasks", taskId: "t-1" });
  });

  async function openDelete() {
    fireEvent.click(await screen.findByRole("button", { name: "More actions" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Delete draft…" }));
  }

  it("deletes after a confirmation that says what is lost, then returns with a toast", async () => {
    const onNavigate = vi.fn();
    vi.mocked(api.deleteModelDraft).mockResolvedValue(undefined);
    renderEditor(onNavigate);
    await openDelete();
    const dialog = await screen.findByRole("alertdialog");
    expect(
      within(dialog).getByText(/its steps and proposals and the workbook attached to it \(book.xlsx\)/),
    ).toBeTruthy();
    expect(within(dialog).getByText(/Installed releases are not affected/)).toBeTruthy();
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete draft" }));
    await waitFor(() => expect(api.deleteModelDraft).toHaveBeenCalledWith("d1", 4));
    await waitFor(() => expect(onNavigate).toHaveBeenCalledWith(models));
    expect(await screen.findByText("Draft Store changes was deleted.")).toBeTruthy();
  });

  it("keeps the draft when the confirmation is cancelled", async () => {
    const onNavigate = vi.fn();
    renderEditor(onNavigate);
    await openDelete();
    fireEvent.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Cancel" }));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).toBeNull());
    expect(api.deleteModelDraft).not.toHaveBeenCalled();
    expect(onNavigate).not.toHaveBeenCalled();
  });

  it("does not offer Delete while the engine proposes", async () => {
    vi.mocked(api.modelDraftInference).mockResolvedValue(checking());
    renderEditor();
    await screen.findByRole("button", { name: "Stop" });
    fireEvent.click(screen.getByRole("button", { name: "More actions" }));
    await screen.findByRole("menuitem", { name: /Add a workbook|Upload|workbook/i });
    expect(screen.queryByRole("menuitem", { name: "Delete draft…" })).toBeNull();
  });
});
