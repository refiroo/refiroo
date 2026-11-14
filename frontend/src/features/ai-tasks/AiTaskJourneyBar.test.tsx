import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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

describe("the mark that the model change was reviewed (FX1, D9)", () => {
  const key = "rdm:journey:model-reviewed:task-1";
  const stored = new Map<string, string>();
  beforeEach(() => {
    vi.clearAllMocks();
    stored.clear();
    stored.set(key, "1");
    vi.stubGlobal("localStorage", {
      getItem: (name: string) => stored.get(name) ?? null,
      setItem: (name: string, value: string) => stored.set(name, value),
      removeItem: (name: string) => stored.delete(name),
    });
    vi.mocked(api.workspace).mockResolvedValue({ key: "west", label: "West" } as never);
    vi.mocked(api.model).mockResolvedValue({ applications: [] } as never);
  });
  afterEach(() => vi.unstubAllGlobals());

  it("is kept while the task can still be at the model step and dropped once it is loaded", async () => {
    vi.mocked(ai.task).mockResolvedValue({ ...proposal(), state: "checked" });
    const { unmount } = render(
      <AiTaskJourneyBar journey={{ kind: "aiTask", taskId: "task-1" }} place="task" onNavigate={vi.fn()} />,
    );
    await screen.findByRole("button");
    expect(stored.get(key) ?? null).toBe("1");
    unmount();
    vi.mocked(ai.task).mockResolvedValue({ ...proposal(), state: "loaded" });
    render(<AiTaskJourneyBar journey={{ kind: "aiTask", taskId: "task-1" }} place="task" onNavigate={vi.fn()} />);
    await waitFor(() => expect(stored.get(key) ?? null).toBeNull());
  });
});
