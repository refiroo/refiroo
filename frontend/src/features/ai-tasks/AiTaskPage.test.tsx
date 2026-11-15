import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { AiTask } from "@/types";
import { AiTaskPage } from "./AiTaskPage";
import { designTask } from "./designFixture";

vi.mock("@/api/aiClient", () => ({
  ai: {
    task: vi.fn(),
    runTask: vi.fn(),
    cancelTask: vi.fn(),
    taskChanges: vi.fn(),
    correctModel: vi.fn(),
    retryTask: vi.fn(),
    discardTask: vi.fn(),
    reopenProposal: vi.fn(),
    acceptModel: vi.fn(),
  },
}));
vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { workspace: vi.fn(), job: vi.fn(), model: vi.fn() },
}));
vi.mock("./useAssistantOffers", () => ({ useAssistantOffers: () => ({ changeModel: true, askRecords: true }) }));
// No stream is opened: a job's changes are not under test here.
vi.mock("@/api/eventStream", () => ({
  openEventStream: (url: string) => ({ url, addEventListener: () => undefined, close: () => undefined }),
}));
const groups = vi.hoisted(() => ({ held: ["change-sets", "model-release"] as string[] }));
vi.mock("@/state/permissions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/state/permissions")>()),
  useHeldAnywhere: () => [{ key: "model-release", name: "Model release", instance: true, workspaces: [] }],
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

  it("says a task waits for the assistant instead of what it will do (AQ)", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ state: "checking", phase: "checking", check: null, ahead: 1 }));
    open();
    expect(await screen.findByText("Waiting for the assistant: 1 task ahead")).toBeInTheDocument();
    expect(screen.queryByText("Checking every row")).not.toBeInTheDocument();
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
        changeSetName: "Load of timetable",
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
    vi.mocked(ai.runTask).mockRejectedValue(new ApiError(409, "VERSION_CONFLICT", "Changed", { currentVersion: 5 }));
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

  it("counts the relationships a load added when it added no record", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({
        state: "loaded",
        version: 7,
        result: {
          changeSetId: "cs-1",
          changeSetName: "Links only",
          counts: { created: 0, updated: 0, unchanged: 0, relationsCreated: 231 },
        },
      }),
    );
    open();
    await screen.findByRole("heading", { name: "Loaded into the change set “Links only”" });
    expect(screen.getByText(/231 relationships new/)).toBeInTheDocument();
    expect(screen.queryByText(/Nothing changed/)).not.toBeInTheDocument();
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

  it("says why the assistant stopped and takes the person's words, which go to the same session", async () => {
    const failed = task({
      state: "failed",
      check: null,
      canTell: true,
      notes: [{ kind: "warning", text: "The proposal still breaks consumers of the model: the API rdm.", at: "t" }],
    });
    vi.mocked(ai.task).mockResolvedValue(failed);
    vi.mocked(ai.correctModel).mockResolvedValue(task({ state: "checking", version: 5 }));
    open();
    expect(await screen.findByRole("heading", { name: "The assistant stopped" })).toBeInTheDocument();
    expect(screen.getByText(/still breaks consumers of the model/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Tell the assistant how to go on"), {
      target: { value: "Keep the colour code." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send to the assistant" }));
    await waitFor(() =>
      expect(ai.correctModel).toHaveBeenCalledWith("task-1", {
        expectedVersion: 4,
        correction: "Keep the colour code.",
      }),
    );
  });

  it("goes on as it was, opens the draft, discards, and goes back from a task that stopped", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ state: "failed", check: null, canTell: true }));
    vi.mocked(ai.retryTask).mockResolvedValue(task({ state: "checking", version: 5 }));
    const { onNavigate } = open();
    await screen.findByRole("heading", { name: "The assistant stopped" });
    expect(screen.getByText("The assistant could not finish.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open the draft in the editor" }));
    expect(onNavigate).toHaveBeenCalledWith(expect.objectContaining({ page: "model", draftId: "draft-1" }));
    fireEvent.click(screen.getByRole("button", { name: "Try again as it was" }));
    await waitFor(() => expect(ai.retryTask).toHaveBeenCalledWith("task-1", { expectedVersion: 4 }));
  });

  it("keeps the change set a failed load left reachable: what it loaded, a way to review it, and a discard that takes it along", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({
        state: "failed",
        check: null,
        canTell: true,
        notes: [{ kind: "warning", text: "The session ended before it said what it loaded.", at: "t" }],
        result: {
          changeSetId: "cs-1",
          changeSetName: "Station availability",
          counts: { created: 0, updated: 0, unchanged: 0, relationsCreated: 231 },
        },
      }),
    );
    vi.mocked(ai.discardTask).mockResolvedValue(task({ state: "cancelled", check: null, canTell: false }));
    const { onNavigate } = open();
    await screen.findByRole("heading", { name: "The assistant stopped" });
    expect(screen.getByText(/The session ended before it said what it loaded/)).toBeInTheDocument();
    expect(
      screen.getByText(/It loaded 231 relationships new into “Station availability” before it stopped/),
    ).toBeInTheDocument();
    expect(screen.queryByText(/Nothing was installed or loaded/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Review the change set" }));
    expect(onNavigate).toHaveBeenCalledWith(expect.objectContaining({ changeSetId: "cs-1" }));
    fireEvent.click(screen.getByRole("button", { name: "Discard the task and its change set" }));
    fireEvent.click(await screen.findByRole("button", { name: "Discard" }));
    await waitFor(() => expect(ai.discardTask).toHaveBeenCalledWith("task-1"));
  });

  it("discards a task that stopped and then says it was discarded", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ state: "stopped", check: null, canTell: true, draftId: null }));
    vi.mocked(ai.discardTask).mockResolvedValue(task({ state: "cancelled", check: null, canTell: false }));
    open();
    expect(await screen.findByRole("heading", { name: "You stopped the assistant" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Go on as it was" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Discard this task" }));
    expect(await screen.findByRole("heading", { name: "Discarded" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Tell the assistant how to go on")).not.toBeInTheDocument();
  });

  it("offers no words box to a task that stopped when the assistant cannot be told", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ state: "failed", check: null, canTell: false }));
    open();
    await screen.findByRole("heading", { name: "The assistant stopped" });
    expect(screen.queryByLabelText("Tell the assistant how to go on")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back to the workspace" })).toBeInTheDocument();
  });

  it("reads a task an older version left in the state read, with a plan, as stopped", async () => {
    vi.mocked(ai.task).mockResolvedValue({
      ...task({ check: null, design: null, jobId: "job-1" }),
      state: "read",
      plan: { profile: {}, steps: [] },
      reading: { tables: [], sheets: [] },
    } as unknown as AiTask);
    open();
    expect(await screen.findByRole("heading", { name: "You stopped the assistant" })).toBeInTheDocument();
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

  it("says a task that is not kept or does not exist is not here, with a way to the workspaces", async () => {
    vi.mocked(ai.task).mockRejectedValue(new ApiError(404, "AI_TASK_NOT_FOUND", "No such task", undefined));
    const { onNavigate } = open();
    expect(await screen.findByRole("heading", { name: "This task is no longer here" })).toBeInTheDocument();
    expect(screen.getByText(/What it loaded or published is unchanged/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Go to the workspaces" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "workspaces" });
  });

  it("keeps a retry for a task that could not be read for another reason", async () => {
    vi.mocked(ai.task).mockRejectedValue(new ApiError(500, "SERVER", "The server stopped", undefined));
    open();
    expect(await screen.findByText("The server stopped")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  it("stops a load that is running", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ state: "loading", check: null }));
    vi.mocked(ai.cancelTask).mockResolvedValue(task({ state: "checked" }));
    open();
    fireEvent.click(await screen.findByRole("button", { name: "Stop" }));
    await waitFor(() => expect(ai.cancelTask).toHaveBeenCalledWith("task-1"));
  });

  it("tells the assistant what is wrong with a loaded change set, discarding it first on confirmation", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({
        state: "loaded",
        canTell: true,
        result: { changeSetId: "cs-1", changeSetName: "Load", counts: { created: 3, updated: 0, unchanged: 0 } },
      }),
    );
    vi.mocked(ai.correctModel).mockResolvedValue(task({ state: "checking", version: 5 }));
    open();
    await screen.findByRole("heading", { name: "Loaded into the change set “Load”" });
    fireEvent.change(screen.getByLabelText("Not what you wanted? Tell the assistant"), {
      target: { value: "Leave out packages without a price." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Discard and load again" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(within(dialog).getByText(/any edits you made in it/)).toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "Discard and load again" }));
    await waitFor(() =>
      expect(ai.correctModel).toHaveBeenCalledWith("task-1", {
        expectedVersion: 4,
        correction: "Leave out packages without a price.",
      }),
    );
  });

  it("says an items load only installed its release, and that new words are a correction checked again", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({
        state: "loaded",
        canTell: true,
        design: { ...task().design!, itemsLoad: true },
        result: { changeSetId: "cs-1", changeSetName: "Load", releaseId: "rel-2", counts: { created: 3 } },
      }),
    );
    open();
    await screen.findByRole("heading", { name: "Loaded into the change set “Load”" });
    expect(screen.getByText(/installed, not activated: publishing the change set moves/)).toBeInTheDocument();
    expect(screen.queryByText(/installed and activated/)).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Not what you wanted? Tell the assistant"), {
      target: { value: "Leave out packages." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Discard and load again" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(
      within(dialog).getByText(/correction of its proposal, which is checked again and accepted again/),
    ).toBeInTheDocument();
  });

  it("discards a loaded change set from the task and says the task was discarded", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({ state: "loaded", canTell: false, result: { changeSetId: "cs-1", changeSetName: "Load" } }),
    );
    vi.mocked(ai.discardTask).mockResolvedValue(task({ state: "cancelled", check: null }));
    open();
    await screen.findByRole("heading", { name: "Loaded into the change set “Load”" });
    expect(screen.queryByLabelText("Not what you wanted? Tell the assistant")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Discard the change set" }));
    fireEvent.click(within(await screen.findByRole("alertdialog")).getByRole("button", { name: "Discard" }));
    expect(await screen.findByRole("heading", { name: "Discarded" })).toBeInTheDocument();
  });

  it("offers the way onward and Discard when the session of a loaded task has ended (a task from before AP13)", async () => {
    const ended = task({ state: "loaded", canTell: false, result: { changeSetId: "cs-1", changeSetName: "Load" } });
    ended.design = { ...ended.design!, agentSession: "session-1" };
    vi.mocked(ai.task).mockResolvedValue(ended);
    open();
    await screen.findByRole("heading", { name: "Loaded into the change set “Load”" });
    expect(screen.getByText(/session for this task has ended/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Not what you wanted? Tell the assistant")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Discard the change set" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Change this model…" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask about these records…" })).toBeInTheDocument();
  });

  it("says a change set was published and points to the model and the records", async () => {
    vi.mocked(ai.task).mockResolvedValue(
      task({
        state: "loaded",
        canTell: false,
        result: {
          changeSetId: "cs-1",
          changeSetName: "Load",
          published: true,
          publicationId: "pub-1",
          counts: { created: 9746, updated: 0, unchanged: 0 },
        },
      }),
    );
    open();
    expect(await screen.findByRole("heading", { name: "Published: “Load”" })).toBeInTheDocument();
    expect(screen.getByText(/9,746 records new/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Review the change set" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Discard the change set" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Something not right?" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask about these records…" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Change this model…" }));
    expect(await screen.findByRole("dialog", { name: "Change this model" })).toBeInTheDocument();
  });

  it("names who can load instead of showing a Load button when Work in change sets is gone", async () => {
    groups.held = ["model-release"];
    vi.mocked(ai.task).mockResolvedValue(task());
    open();
    await screen.findByRole("heading", { name: "What the load would do" });
    expect(screen.queryByRole("button", { name: /load/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Loading needs Work in change sets in/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy the link to this task" })).toBeInTheDocument();
  });

  it("goes back from the load stage to the proposal and tells the assistant about the refused rows", async () => {
    vi.mocked(ai.task).mockResolvedValue(task({ canTell: true }));
    vi.mocked(ai.reopenProposal).mockResolvedValue(task());
    vi.mocked(ai.correctModel).mockResolvedValue(task({ state: "checking", version: 5 }));
    open();
    await screen.findByRole("heading", { name: "What the load would do" });
    fireEvent.click(screen.getByRole("button", { name: "Back to the proposal" }));
    await waitFor(() => expect(ai.reopenProposal).toHaveBeenCalledWith("task-1", { expectedVersion: 4 }));
    fireEvent.change(screen.getByLabelText("Tell the assistant what to do with the refused rows"), {
      target: { value: "Treat n/a as empty." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send to the assistant" }));
    await waitFor(() =>
      expect(ai.correctModel).toHaveBeenCalledWith("task-1", { expectedVersion: 4, correction: "Treat n/a as empty." }),
    );
  });

  it("reads a saved layout that no longer fits with the assistant", async () => {
    const unfit = task({
      check: null,
      canTell: true,
      notes: [{ kind: "warning", text: "The saved layout does not fit the workbook", at: "t" }],
    });
    unfit.design = { ...unfit.design!, agentSession: undefined };
    vi.mocked(ai.task).mockResolvedValue(unfit);
    vi.mocked(ai.retryTask).mockResolvedValue(task({ state: "checking", version: 5 }));
    open();
    expect(await screen.findByRole("heading", { name: "The saved layout does not fit this file" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Read it with the assistant" }));
    await waitFor(() => expect(ai.retryTask).toHaveBeenCalledWith("task-1", { expectedVersion: 4 }));
  });

  it("names the workspace in the trail", async () => {
    vi.mocked(ai.task).mockResolvedValue(task());
    open();
    const trail = await screen.findByRole("navigation", { name: "Where you are" });
    await waitFor(() => expect(within(trail).getByRole("link", { name: "West" })).toBeInTheDocument());
    expect(within(trail).getByText("Load a workbook")).toBeInTheDocument();
  });
});
