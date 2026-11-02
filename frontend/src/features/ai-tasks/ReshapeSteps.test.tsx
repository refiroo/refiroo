import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { AiTask, ChangeSet, Job, WorkspaceModel } from "@/types";
import { ReshapeSteps, activationRefusals, reshapeStates } from "./ReshapeSteps";
import { designTask } from "./designFixture";

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: {
    workspaceModel: vi.fn(),
    changeSet: vi.fn(),
    startWorkspaceMigration: vi.fn(),
    jobs: vi.fn(),
    modelReleaseDiff: vi.fn(),
  },
}));

const running = (releaseId: string) => ({ releaseId, version: 4 }) as WorkspaceModel;
const open = (modelReleaseId: string) => ({ id: "cs-1", modelReleaseId }) as ChangeSet;

const migrationTask = (): AiTask => {
  const task = designTask();
  task.state = "loaded";
  task.design = {
    ...task.design!,
    moves: [
      { from: "supplier", fromName: "Suppliers", to: "partner", toName: "Partners", records: 1420 },
      { from: "vendor", fromName: "Vendors", to: "partner", toName: "Partners", records: 720 },
    ],
  };
  task.result = {
    migration: {
      releaseId: "rel-final",
      typeMappings: [{ fromObjectTypeKey: "supplier", toObjectTypeKey: "partner" }],
    },
  };
  return task;
};

const phasedTask = (): AiTask => {
  const task = designTask();
  task.state = "loaded";
  task.result = { changeSetId: "cs-1", thenReleaseId: "rel-final", counts: { applied: 600 } };
  return task;
};

describe("reshapeStates", () => {
  it("knows nothing until the workspace and the change set are read", () => {
    expect(reshapeStates(undefined, undefined, "f")).toEqual(["later", "later", "later"]);
  });

  it("goes step by step: both shapes, the published change set, the final release", () => {
    expect(reshapeStates(running("old"), open("both"), "f")).toEqual(["next", "later", "later"]);
    expect(reshapeStates(running("both"), open("both"), "f")).toEqual(["done", "next", "later"]);
    expect(reshapeStates(running("both"), null, "f")).toEqual(["done", "done", "next"]);
    expect(reshapeStates(running("f"), null, "f")).toEqual(["done", "done", "done"]);
  });
});

describe("What is left to the person after a reshaping (0.16 AP12)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.jobs).mockResolvedValue({ items: [] } as never);
    vi.mocked(api.modelReleaseDiff).mockResolvedValue({
      compatibility: { classification: "compatible", diagnostics: [] },
    } as never);
    vi.mocked(api.workspaceModel).mockResolvedValue(running("old"));
    vi.mocked(api.changeSet).mockResolvedValue(open("both"));
  });

  it("previews the migration with the assistant's choices and opens its page, the way back kept", async () => {
    const onNavigate = vi.fn();
    vi.mocked(api.startWorkspaceMigration).mockResolvedValue({ id: "job-9" } as Job);
    render(<ReshapeSteps task={migrationTask()} workspaceLabel="Partners" canRelease onNavigate={onNavigate} />);
    expect(screen.getByText(/Suppliers becomes/)).toBeInTheDocument();
    expect(screen.getByText(/1,420 records/)).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Preview the migration" }));
    await waitFor(() => expect(onNavigate).toHaveBeenCalled());
    expect(api.startWorkspaceMigration).toHaveBeenCalledWith("west", {
      targetReleaseId: "rel-final",
      expectedVersion: 4,
      typeMappings: [{ fromObjectTypeKey: "supplier", toObjectTypeKey: "partner" }],
    });
    expect(onNavigate).toHaveBeenCalledWith({
      kind: "settings",
      page: "model",
      migrationJobId: "job-9",
      forWorkspace: "west",
      journey: { kind: "aiTask", taskId: expect.any(String) },
    });
  });

  it("shows what the engine refused in the migration and takes the person's words (AP13, AP-D60)", async () => {
    const onTell = vi.fn();
    vi.mocked(api.jobs).mockResolvedValue({
      items: [
        {
          kind: "migration",
          workspaceKey: "west",
          state: "awaiting_confirmation",
          migration: { targetReleaseId: "rel-final", counts: { refused: 16, loss: 0, conversion: 0, reclassified: 0 } },
        },
      ],
    } as never);
    const task = { ...migrationTask(), canTell: true };
    render(<ReshapeSteps task={task} workspaceLabel="Partners" canRelease onNavigate={vi.fn()} onTell={onTell} />);
    expect(await screen.findByText(/16 records would be refused/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Tell the assistant what to change"), {
      target: { value: "Give the new type the place under the group." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send to the assistant" }));
    expect(onTell).toHaveBeenCalledWith("Give the new type the place under the group.");
  });

  it("shows what the engine would refuse of the next step, from the activation's own check (AP13, AP-D60)", async () => {
    vi.mocked(api.modelReleaseDiff).mockResolvedValue({
      compatibility: {
        classification: "migration_required",
        diagnostics: [
          { severity: "error", code: "X", path: "/", message: "12 records hold a type the release removes." },
        ],
      },
      consumerContracts: { classification: "version_required", diagnostics: [] },
    } as never);
    const task = { ...phasedTask(), canTell: true };
    render(<ReshapeSteps task={task} workspaceLabel="Partners" canRelease onNavigate={vi.fn()} />);
    expect(await screen.findByText(/12 records hold a type the release removes/)).toBeInTheDocument();
    expect(screen.getByText(/A consumer API changes what its consumers read/)).toBeInTheDocument();
    expect(api.modelReleaseDiff).toHaveBeenCalledWith("both", "old", "west");
  });

  it("reads a compatible release as nothing to refuse", () => {
    expect(activationRefusals({ compatibility: { classification: "compatible", diagnostics: [] } } as never)).toEqual(
      [],
    );
  });

  it("hides the button from a person without Model release and says who can do it", async () => {
    render(<ReshapeSteps task={migrationTask()} workspaceLabel="Partners" canRelease={false} onNavigate={vi.fn()} />);
    expect(await screen.findByText(/Someone who holds Model release in Partners/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Preview the migration" })).not.toBeInTheDocument();
  });

  it("says the move is done once the workspace runs the new release", async () => {
    vi.mocked(api.workspaceModel).mockResolvedValue(running("rel-final"));
    render(<ReshapeSteps task={migrationTask()} workspaceLabel="Partners" canRelease onNavigate={vi.fn()} />);
    expect(await screen.findByText(/Partners runs the new model/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Preview the migration" })).not.toBeInTheDocument();
  });

  it("shows each of the three steps only when it can be done", async () => {
    const onNavigate = vi.fn();
    const review = { kind: "changeSets", applicationKey: "a", workspaceKey: "default" } as never;
    render(
      <ReshapeSteps task={phasedTask()} workspaceLabel="Items" canRelease review={review} onNavigate={onNavigate} />,
    );
    // Step 1 first: the release holding both shapes. Review and removal wait.
    const first = await screen.findByRole("button", { name: "Open the release" });
    expect(screen.queryByRole("button", { name: "Review the change set" })).not.toBeInTheDocument();
    fireEvent.click(first);
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "model", releaseId: "both" });
  });

  it("shows two steps when the final release is the change set's own, also after publishing", async () => {
    vi.mocked(api.workspaceModel).mockResolvedValue(running("rel-final"));
    vi.mocked(api.changeSet).mockResolvedValue(open("rel-final"));
    const review = { kind: "changeSets", applicationKey: "a", workspaceKey: "default" } as never;
    const onNavigate = vi.fn();
    const same = () => {
      const task = phasedTask();
      task.result = { ...task.result!, changeSetReleaseId: "rel-final" };
      return task;
    };
    const { unmount } = render(
      <ReshapeSteps task={same()} workspaceLabel="Items" canRelease review={review} onNavigate={onNavigate} />,
    );
    expect(await screen.findByText("Two steps are yours")).toBeInTheDocument();
    expect(screen.queryByText(/Remove the emptied types/)).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Review the change set" }));
    expect(onNavigate).toHaveBeenCalledWith(review);
    unmount();

    // Opened for the first time after publishing: the change set is gone, the page is still right.
    vi.mocked(api.changeSet).mockRejectedValue(new ApiError(404, "CHANGE_SET_NOT_FOUND", "gone"));
    render(<ReshapeSteps task={same()} workspaceLabel="Items" canRelease onNavigate={onNavigate} />);
    expect(await screen.findByText("Two steps are yours")).toBeInTheDocument();
    expect(await screen.findByText("Items runs the new model.")).toBeInTheDocument();
    expect(screen.queryByText(/Remove the emptied types/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open the release" })).not.toBeInTheDocument();
    expect(reshapeStates(running("rel-final"), open("rel-final"), "rel-final", true)).toEqual([
      "done",
      "next",
      "later",
    ]);
  });

  it("offers the review after the first step and the removal after publication", async () => {
    vi.mocked(api.workspaceModel).mockResolvedValue(running("both"));
    const review = { kind: "changeSets", applicationKey: "a", workspaceKey: "default" } as never;
    const onNavigate = vi.fn();
    const { unmount } = render(
      <ReshapeSteps task={phasedTask()} workspaceLabel="Items" canRelease review={review} onNavigate={onNavigate} />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Review the change set" }));
    expect(onNavigate).toHaveBeenCalledWith(review);
    unmount();

    vi.mocked(api.changeSet).mockRejectedValue(new ApiError(404, "CHANGE_SET_NOT_FOUND", "gone"));
    render(
      <ReshapeSteps task={phasedTask()} workspaceLabel="Items" canRelease review={review} onNavigate={onNavigate} />,
    );
    fireEvent.click(await screen.findByRole("button", { name: "Open the release" }));
    expect(onNavigate).toHaveBeenLastCalledWith({ kind: "settings", page: "model", releaseId: "rel-final" });
  });
});
