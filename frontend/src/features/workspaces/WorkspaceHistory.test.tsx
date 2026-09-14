import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import type { WorkspaceDraft, WorkspaceRevision } from "@/types";
import { WorkspaceHistory } from "./WorkspaceHistory";

const current: WorkspaceRevision = {
  id: "revision-10",
  workspaceKey: "west",
  modelReleaseId: "model-new",
  revisionNumber: 10,
  status: "active",
  derivedFromRevisionId: "revision-2",
  supersedesRevisionId: "revision-9",
  createdAt: "2026-09-10T10:00:00Z",
  activatedAt: "2026-09-10T10:00:00Z",
  retiredAt: null,
};

afterEach(() => vi.restoreAllMocks());

describe("workspace publication history", () => {
  it("retains loaded newest-first history and retries the exact failed older page", async () => {
    const revisions = vi
      .spyOn(api, "workspaceRevisions")
      .mockResolvedValueOnce({ items: [current], nextCursor: "older-page" })
      .mockRejectedValueOnce(new Error("History temporarily unavailable"))
      .mockResolvedValueOnce({
        items: [{ ...current, id: "revision-9", revisionNumber: 9, status: "retired" }],
        nextCursor: null,
      });
    render(<WorkspaceHistory workspaceKey="west" readOnly={false} onOpen={vi.fn()} onDraftCreated={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: /Revision 10 · Current publication/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load older revisions" }));
    expect(await screen.findByText("History temporarily unavailable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Revision 10 · Current publication/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: /Revision 9 · Historical snapshot/ })).toBeInTheDocument();
    expect(revisions.mock.calls).toEqual([
      ["west", undefined],
      ["west", "older-page"],
      ["west", "older-page"],
    ]);
  });

  it("creates an explicitly historical draft and explains retirement without claiming data withdrawal", async () => {
    vi.spyOn(api, "workspaceRevisions").mockResolvedValue({ items: [current], nextCursor: null });
    const draft: WorkspaceDraft = {
      id: "draft-from-history",
      workspaceKey: "west",
      name: "Review history",
      modelReleaseId: current.modelReleaseId,
      modelReleaseKey: "rdm-starter",
      modelReleaseVersion: "0.7.0",
      source: "revision",
      derivedFromRevisionId: current.id,
      version: 1,
      createdAt: "",
      updatedAt: "",
    };
    const create = vi.spyOn(api, "createHistoricalWorkspaceDraft").mockResolvedValue(draft);
    const retire = vi.spyOn(api, "retireWorkspacePublication").mockResolvedValue();
    const onDraftCreated = vi.fn();
    const rendered = render(
      <WorkspaceHistory workspaceKey="west" readOnly={false} onOpen={vi.fn()} onDraftCreated={onDraftCreated} />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "Start a draft from this revision" }));
    expect(screen.getByText(/does not restore or change live data/i)).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Draft name" }), { target: { value: "Review history" } });
    fireEvent.click(screen.getByRole("button", { name: "Create draft" }));
    await waitFor(() => expect(onDraftCreated).toHaveBeenCalledWith(draft.id));
    expect(create).toHaveBeenCalledWith("west", "Review history", current.id);

    rendered.unmount();
    render(<WorkspaceHistory workspaceKey="west" readOnly={false} onOpen={vi.fn()} onDraftCreated={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retire publication" }));
    expect(screen.getByText(/Live records and all historical snapshots remain available/)).toBeInTheDocument();
    fireEvent.click(screen.getAllByRole("button", { name: "Retire publication" }).at(-1)!);
    await waitFor(() => expect(retire).toHaveBeenCalledWith("west", current.id));
    expect(await screen.findByText(/Live records and history remain available/)).toBeInTheDocument();
  });
});
