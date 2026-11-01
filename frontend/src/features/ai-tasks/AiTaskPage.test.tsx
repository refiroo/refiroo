import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { AiTask } from "@/types";
import { AiTaskPage } from "./AiTaskPage";
import { designTask } from "./designFixture";

vi.mock("@/api/aiClient", () => ({
  ai: { task: vi.fn(), runTask: vi.fn(), cancelTask: vi.fn(), taskChanges: vi.fn() },
}));
vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { workspace: vi.fn(), job: vi.fn(), model: vi.fn() },
}));
vi.mock("@/features/jobs/useJobStream", () => ({ useJobStream: vi.fn() }));
const groups = vi.hoisted(() => ({ held: ["change-sets", "model-release"] as string[] }));
vi.mock("@/features/security/permissions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/security/permissions")>()),
  useWorkspacePermissions: () => ({
    workspaceKey: "west",
    actionGroups: groups.held.map((key) => ({ key, label: key })),
    scopes: [],
  }),
}));

/** A session's task as the server sends it; `extra` overrides. */
const task = (extra: Partial<AiTask> = {}): AiTask => ({ ...designTask(), ...extra });

function open(onNavigate = vi.fn(), onOpenWorkspace = vi.fn()) {
  render(<AiTaskPage taskId="task-1" onNavigate={onNavigate} onOpenWorkspace={onOpenWorkspace} />);
  return { onNavigate, onOpenWorkspace };
}

describe("The assistant task page (0.16 AP6a, AP10)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    groups.held = ["change-sets", "model-release"];
    vi.mocked(api.workspace).mockResolvedValue({ key: "west", label: "West" } as never);
    vi.mocked(api.job).mockResolvedValue({ error: null } as never);
    vi.mocked(api.model).mockResolvedValue({ applications: [] } as never);
    vi.mocked(ai.taskChanges).mockResolvedValue({ items: [], nextCursor: null });
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
    vi.mocked(ai.task).mockResolvedValue(task({ state: "reading", phase: "designing", check: null }));
    vi.mocked(ai.cancelTask).mockResolvedValue(task({ state: "cancelled", check: null }));
    open();
    expect(await screen.findByText("The assistant is designing the model and the load")).toBeInTheDocument();
    expect(screen.getByText(/Editing is not possible while this runs/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    await waitFor(() => expect(ai.cancelTask).toHaveBeenCalledWith("task-1"));
  });

  it("follows the task until the proposal is ready", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const proposed = task({ check: null });
    proposed.design = { ...proposed.design!, stage: "model", questions: [], outline: [], checks: [] };
    vi.mocked(ai.task)
      .mockResolvedValueOnce(task({ state: "reading", phase: "profiling", check: null, design: null }))
      .mockResolvedValue(proposed);
    open();
    expect(await screen.findByText("Reading the workbook")).toBeInTheDocument();
    await vi.advanceTimersByTimeAsync(2100);
    expect(await screen.findByRole("heading", { name: "The assistant’s proposal" })).toBeInTheDocument();
  });

  it("shows a warning of the proposal beside the held records and keeps Accept", async () => {
    const proposed = task({ check: null });
    proposed.design = {
      ...proposed.design!,
      stage: "model",
      questions: [],
      outline: [],
      checks: [
        {
          id: "beside-held-product",
          kind: "besideHeld",
          text: "667 new Products beside the 667 held. If this is an update, the rows did not find their records.",
          open: true,
        },
      ],
    };
    vi.mocked(ai.task).mockResolvedValue(proposed);
    open();
    expect(await screen.findByText(/667 new Products beside the 667 held/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept the model" })).toBeEnabled();
  });

  it("shows the saved-layout check and loads into a change set, saving the profile under a key", async () => {
    vi.mocked(ai.task).mockResolvedValue(task());
    vi.mocked(ai.runTask).mockResolvedValue(task({ state: "loading", version: 5 }));
    open();
    await screen.findByRole("heading", { name: "What the load would do" });
    fireEvent.change(screen.getByLabelText("Profile name"), { target: { value: "Supplier Systems" } });
    expect(screen.getByText("Its key is “supplier-systems”.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Activate the model and load" }));
    await waitFor(() =>
      expect(ai.runTask).toHaveBeenCalledWith("task-1", {
        expectedVersion: 4,
        changeSetName: "Load of scheduling",
        saveProfile: { key: "supplier-systems", name: "Supplier Systems" },
      }),
    );
    expect(await screen.findByText("Loading into the change set…")).toBeInTheDocument();
  });

  it("does not offer the load without Work in change sets", async () => {
    groups.held = [];
    vi.mocked(ai.task).mockResolvedValue(task());
    open();
    await screen.findByRole("heading", { name: "What the load would do" });
    expect(screen.queryByRole("button", { name: /load/i })).not.toBeInTheDocument();
  });

  it("reloads the task and says so on a version conflict", async () => {
    vi.mocked(ai.task).mockResolvedValue(task());
    vi.mocked(ai.runTask).mockRejectedValue(
      new ApiError(409, "AI_TASK_VERSION_CONFLICT", "Changed", { currentVersion: 5 }),
    );
    open();
    await screen.findByRole("heading", { name: "What the load would do" });
    fireEvent.click(screen.getByRole("button", { name: "Activate the model and load" }));
    expect(await screen.findByText(/The task changed while you were working/)).toBeInTheDocument();
    expect(vi.mocked(ai.task).mock.calls.length).toBeGreaterThan(1);
  });

  it("says where the load went and that the profile was saved", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({
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
    expect(screen.getByText(/2 records new and 3 records changed\./)).toBeInTheDocument();
    expect(screen.getByText(/The other 7 records were already as the file says\./)).toBeInTheDocument();
    expect(
      screen.getByText(
        /Saved the profile “supplier-systems”: the next file of this layout loads without the assistant/,
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Not saved as a profile/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review the change set" }));
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "changeSetChanges", changeSetId: "cs-1", workspaceKey: "west" }),
    );
  });

  it("says why no profile was saved, as a plain line", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({
        state: "loaded",
        version: 7,
        result: {
          changeSetId: "cs-1",
          changeSetName: "Load of systems",
          counts: { created: 2, updated: 0, unchanged: 0 },
          profileNotSaved:
            "Not saved as a profile: “Packages” has no key, so a second load would create its rows again.",
        },
      }),
    );
    open();
    await screen.findByRole("heading", { name: "Loaded into the change set “Load of systems”" });
    expect(screen.getByText(/Not saved as a profile: “Packages” has no key/)).toBeInTheDocument();
    expect(screen.queryByText(/Saved the profile/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open the profile" })).not.toBeInTheDocument();
  });

  it("says a failed reading failed, with the job's error, and a way back", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ state: "failed", check: null, design: null, jobId: "job-1" }));
    vi.mocked(api.job).mockResolvedValue({ error: { code: "X", message: "The workbook could not be read." } } as never);
    const { onOpenWorkspace } = open();
    expect(await screen.findByText("The reading failed")).toBeInTheDocument();
    expect(await screen.findByText("The workbook could not be read.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Back to the workspace" }));
    expect(onOpenWorkspace).toHaveBeenCalledWith("west");
  });

  it("reads a task an older version left in the state read, with a plan, as stopped", async () => {
    vi.mocked(ai.task).mockResolvedValue({
      ...task({ check: null, design: null, jobId: "job-1" }),
      state: "read",
      plan: { profile: {}, steps: [] },
      reading: { tables: [], sheets: [] },
    } as unknown as AiTask);
    open();
    expect(await screen.findByText("The reading was stopped")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back to the workspace" })).toBeInTheDocument();
  });

  it("opens an older loaded task whose check holds tables, without a design", async () => {
    vi.mocked(ai.task).mockResolvedValue({
      ...task({
        design: null,
        state: "loaded",
        result: { changeSetId: "cs-1", changeSetName: "Old load", counts: { created: 1, updated: 0, unchanged: 4 } },
      }),
      check: { dryRunJobId: "d", ranAt: "t", rounds: 0, fixes: [], tables: [{ table: "t1", sheet: "S" }] },
    } as unknown as AiTask);
    open();
    const heading = await screen.findByRole("heading", { name: "Loaded into the change set “Old load”" });
    expect(within(heading.closest("section")!).getByText(/1 record new/)).toBeInTheDocument();
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
});
