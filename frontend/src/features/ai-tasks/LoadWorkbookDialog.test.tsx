import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import type { AiTask, Workspace } from "@/types";
import { LoadWorkbookDialog, SENT_WITH_WORKBOOK } from "./LoadWorkbookDialog";

vi.mock("@/api/aiClient", () => ({ ai: { createTask: vi.fn() } }));
vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { workspaces: vi.fn() },
}));

const file = new File(["a,b\n1,2\n"], "codes.csv", { type: "text/csv" });
const workspace = (key: string, label: string) => ({ key, label }) as Workspace;

function open(start: { workspaceKey?: string; file?: File } = {}, onStarted = vi.fn(), onClose = vi.fn()) {
  const onImportManually = vi.fn();
  render(
    <LoadWorkbookDialog start={start} onClose={onClose} onStarted={onStarted} onImportManually={onImportManually} />,
  );
  return { onStarted, onClose, onImportManually };
}

describe("Load a workbook (0.16 AP6a)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.workspaces).mockResolvedValue({
      items: [workspace("east", "East"), workspace("west", "West")],
      nextCursor: null,
    } as never);
  });

  it("says what it does and what is sent, asking only the workspaces where the person may use the assistant", async () => {
    open({ workspaceKey: "west" });
    expect(await screen.findByRole("dialog", { name: "Load a workbook" })).toBeInTheDocument();
    expect(screen.getByText(/Nothing changes until you confirm\./)).toBeInTheDocument();
    expect(screen.getByText(SENT_WITH_WORKBOOK)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("Into")).toHaveValue("west"));
    expect(api.workspaces).toHaveBeenCalledWith(expect.objectContaining({ holding: "ai-proposals" }));
    expect(screen.getByRole("button", { name: "Ask the assistant" })).toBeDisabled();
  });

  it("offers Import without the assistant…, carrying the file chosen so far whatever its kind", () => {
    const { onImportManually } = open({ workspaceKey: "west" });
    fireEvent.click(screen.getByRole("button", { name: "Import without the assistant…" }));
    expect(onImportManually).toHaveBeenLastCalledWith(undefined);
    const lines = new File(["{}\n"], "items.jsonl");
    fireEvent.change(screen.getByLabelText("Workbook"), { target: { files: [lines] } });
    fireEvent.click(screen.getByRole("button", { name: "Import without the assistant…" }));
    expect(onImportManually).toHaveBeenLastCalledWith(lines);
  });

  it("sends the workbook, the workspace and the words, and hands the task on", async () => {
    const started = { id: "task-1" } as AiTask;
    vi.mocked(ai.createTask).mockResolvedValue(started);
    const { onStarted } = open({ workspaceKey: "west" });
    await waitFor(() => expect(screen.getByLabelText("Into")).toHaveValue("west"));
    fireEvent.change(screen.getByLabelText("Workbook"), { target: { files: [file] } });
    fireEvent.change(screen.getByLabelText("Tell the assistant about this file (optional)"), {
      target: { value: "  Q3 supplier list  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Read the workbook" }));
    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(started));
    expect(ai.createTask).toHaveBeenCalledWith(file, { workspaceKey: "west", words: "Q3 supplier list" });
  });

  it("shows a file given to it", async () => {
    vi.mocked(ai.createTask).mockResolvedValue({ id: "t" } as AiTask);
    open({ workspaceKey: "east", file });
    expect(await screen.findByText(/codes\.csv · /)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByLabelText("Into")).toHaveValue("east"));
    fireEvent.click(screen.getByRole("button", { name: "Read the workbook" }));
    await waitFor(() => expect(ai.createTask).toHaveBeenCalledWith(file, { workspaceKey: "east" }));
  });

  it("says why it was refused inside the dialog", async () => {
    vi.mocked(ai.createTask).mockRejectedValue(
      new ApiError(413, "IMPORT_TOO_LARGE", "The file is larger than the limit.", undefined),
    );
    const { onStarted } = open({ workspaceKey: "east", file });
    await waitFor(() => expect(screen.getByLabelText("Into")).toHaveValue("east"));
    fireEvent.click(screen.getByRole("button", { name: "Read the workbook" }));
    expect(await screen.findByText("The file is larger than the limit.")).toBeInTheDocument();
    expect(onStarted).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Read the workbook" })).toBeEnabled();
  });

  it("closes with Cancel", async () => {
    const { onClose } = open({ workspaceKey: "east" });
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("asks the assistant with words alone: the file is optional, the button says so", async () => {
    const started = { id: "task-2" } as AiTask;
    vi.mocked(ai.createTask).mockResolvedValue(started);
    const { onStarted } = open({ workspaceKey: "west" });
    await waitFor(() => expect(screen.getByLabelText("Into")).toHaveValue("west"));
    expect(screen.getByRole("button", { name: "Ask the assistant" })).toBeDisabled();
    expect(screen.getByText(/Without a workbook, your words are the whole instruction/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Tell the assistant about this file (optional)"), {
      target: { value: "Relate frequencies and stations" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask the assistant" }));
    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(started));
    expect(ai.createTask).toHaveBeenCalledWith(undefined, {
      workspaceKey: "west",
      words: "Relate frequencies and stations",
    });
  });

  it("shows AI_TASK_NEEDS_WORDS as the words field's error", async () => {
    vi.mocked(ai.createTask).mockRejectedValue(
      new ApiError(422, "AI_TASK_NEEDS_WORDS", "Give a workbook or some words."),
    );
    open({ workspaceKey: "west" });
    await waitFor(() => expect(screen.getByLabelText("Into")).toHaveValue("west"));
    fireEvent.change(screen.getByLabelText("Tell the assistant about this file (optional)"), {
      target: { value: "x" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask the assistant" }));
    expect(await screen.findByText("Give a workbook or some words.")).toHaveClass("field-error");
  });

  it("changes a workspace's model from words: the workspace fixed, the words first and required, the workbook optional (AP12)", async () => {
    const task = { id: "t1" } as AiTask;
    vi.mocked(ai.createTask).mockResolvedValue(task);
    const onStarted = vi.fn();
    render(
      <LoadWorkbookDialog
        start={{ workspaceKey: "west", changeModel: true, workspaceLabel: "West" }}
        onClose={vi.fn()}
        onStarted={onStarted}
        onImportManually={vi.fn()}
      />,
    );
    expect(await screen.findByRole("dialog", { name: "Change this model" })).toBeInTheDocument();
    expect(screen.getByText("West")).toBeInTheDocument();
    expect(screen.queryByLabelText("Into")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Import without the assistant/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Sent to Claude Code: your words and the workspace's model/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask the assistant" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("What should change?"), {
      target: { value: "Merge Suppliers and Vendors" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ask the assistant" }));
    await waitFor(() => expect(onStarted).toHaveBeenCalledWith(task));
    expect(ai.createTask).toHaveBeenCalledWith(undefined, {
      workspaceKey: "west",
      words: "Merge Suppliers and Vendors",
    });
  });
});
