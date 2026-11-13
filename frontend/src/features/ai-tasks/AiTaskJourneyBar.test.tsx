import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import type { AiTask } from "@/types";
import { AiTaskJourneyBar } from "./AiTaskJourneyBar";
import { AiTaskPage } from "./AiTaskPage";
import { designTask } from "./designFixture";

vi.mock("@/api/aiClient", () => ({
  ai: { task: vi.fn(), acceptModel: vi.fn(), taskChanges: vi.fn(), cancelTask: vi.fn() },
}));
vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { workspace: vi.fn(), job: vi.fn(), model: vi.fn() },
}));
vi.mock("./useAssistantOffers", () => ({ useAssistantOffers: () => ({ changeModel: true, askRecords: true }) }));
vi.mock("@/state/useWorkspaceAiOffer", () => ({
  useAssistantOfferIn: () => ({ assistant: true }),
}));
vi.mock("@/state/useJobStream", () => ({ useJobStream: vi.fn() }));
vi.mock("@/state/permissions", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/state/permissions")>()),
  useHeldAnywhere: () => [{ key: "model-release", name: "Model release", instance: true, workspaces: [] }],
  useWorkspacePermissions: () => ({
    workspaceKey: "west",
    actionGroups: ["change-sets", "model-release"].map((key) => ({ key, label: key })),
    scopes: [],
  }),
}));

const proposal = (): AiTask => {
  const task = designTask();
  task.check = null;
  task.design = { ...task.design!, stage: "model", questions: [], checks: [] };
  return task;
};

describe("the journey bar's primary button on a proposal (DOC11 14)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.workspace).mockResolvedValue({ key: "west", label: "West" } as never);
    vi.mocked(api.model).mockResolvedValue({ applications: [] } as never);
    vi.mocked(ai.task).mockResolvedValue(proposal());
  });

  it("takes the person to the Accept button on the page and does not accept by itself", async () => {
    render(
      <>
        <AiTaskJourneyBar journey={{ kind: "aiTask", taskId: "task-1" }} place="task" onNavigate={vi.fn()} />
        <AiTaskPage taskId="task-1" onNavigate={vi.fn()} onOpenWorkspace={vi.fn()} />
      </>,
    );
    await screen.findByRole("button", { name: "Discard this proposal" });
    const buttons = screen.getAllByRole("button", { name: "Accept the model" });
    expect(buttons.length).toBe(2);
    fireEvent.click(buttons[0]);
    await waitFor(() => expect(document.activeElement === buttons[1]).toBe(true));
    expect(ai.acceptModel).not.toHaveBeenCalled();
  });
});
