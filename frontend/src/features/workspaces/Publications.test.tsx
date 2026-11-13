import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import type { ChangeSet, Publication } from "@/types";
import { permissionsFixture } from "@/test/permissions";
import * as workspaceContext from "@/state/WorkspaceDataContext";
import { Publications } from "./Publications";

const current: Publication = {
  id: "publication-10",
  workspaceKey: "west",
  modelReleaseId: "model-new",
  modelReleaseKey: "rdm-starter",
  modelReleaseVersion: "0.8.0",
  publicationNumber: 10,
  status: "active",
  derivedFromPublicationId: "publication-2",
  supersedesPublicationId: "publication-9",
  createdAt: "2026-09-10T10:00:00Z",
  publishedAt: "2026-09-10T10:00:00Z",
  withdrawnAt: null,
  publishedBy: null,
  withdrawnBy: null,
};

beforeEach(() => {
  // A person holding every group, read: nothing is offered before the permissions are known.
  vi.spyOn(workspaceContext, "useWorkspaceData").mockReturnValue({
    api,
    warning: "",
    permissions: permissionsFixture("west"),
  });
});

afterEach(() => vi.restoreAllMocks());

describe("workspace publications", () => {
  it("retains loaded newest-first publications and retries the exact failed older page", async () => {
    const publications = vi
      .spyOn(api, "publications")
      .mockResolvedValueOnce({ items: [current], nextCursor: "older-page" })
      .mockRejectedValueOnce(new Error("Publications temporarily unavailable"))
      .mockResolvedValueOnce({
        items: [{ ...current, id: "publication-9", publicationNumber: 9, status: "withdrawn" }],
        nextCursor: null,
      });
    render(<Publications workspaceKey="west" readOnly={false} onOpen={vi.fn()} onChangeSetCreated={vi.fn()} />);

    expect(await screen.findByRole("heading", { name: "Publication 10 Current" })).toBeInTheDocument();
    expect(screen.getByText(/Model 0\.8\.0 · Published/)).toBeInTheDocument();
    expect(screen.getByText("Publication ID publication-9")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load older publications" }));
    expect(await screen.findByText("Publications temporarily unavailable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Publication 10 Current" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: "Publication 9" })).toBeInTheDocument();
    expect(screen.getByText(/Published .* · Withdrawn/)).toBeInTheDocument();
    // Once loaded, the earlier publication is named by its number.
    expect(screen.queryByText("Publication ID publication-9")).not.toBeInTheDocument();
    expect(publications.mock.calls).toEqual([
      ["west", undefined],
      ["west", "older-page"],
      ["west", "older-page"],
    ]);
  });

  it("starts a change set from a publication and explains withdrawal without claiming data removal", async () => {
    vi.spyOn(api, "publications").mockResolvedValue({ items: [current], nextCursor: null });
    const changeSet: ChangeSet = {
      id: "change-set-from-history",
      workspaceKey: "west",
      name: "Review history",
      modelReleaseId: current.modelReleaseId,
      modelReleaseKey: "rdm-starter",
      modelReleaseVersion: "0.7.0",
      source: "publication",
      derivedFromPublicationId: current.id,
      version: 1,
      createdAt: "",
      updatedAt: "",
      createdBy: null,
    };
    const create = vi.spyOn(api, "createChangeSetFromPublication").mockResolvedValue(changeSet);
    const withdraw = vi.spyOn(api, "withdrawPublication").mockResolvedValue();
    const onChangeSetCreated = vi.fn();
    const rendered = render(
      <Publications workspaceKey="west" readOnly={false} onOpen={vi.fn()} onChangeSetCreated={onChangeSetCreated} />,
    );

    fireEvent.click(await screen.findByRole("button", { name: "More actions for Publication 10" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Start a change set from this publication" }));
    expect(screen.getByText(/does not restore or change live data/i)).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Name" }), { target: { value: "Review history" } });
    fireEvent.click(screen.getByRole("button", { name: "Start change set" }));
    await waitFor(() => expect(onChangeSetCreated).toHaveBeenCalledWith(changeSet.id));
    expect(create).toHaveBeenCalledWith("west", "Review history", current.id);

    rendered.unmount();
    render(<Publications workspaceKey="west" readOnly={false} onOpen={vi.fn()} onChangeSetCreated={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "More actions for Publication 10" }));
    fireEvent.click(await screen.findByRole("menuitem", { name: "Withdraw publication" }));
    expect(screen.getByText("Withdraw Publication 10?")).toBeInTheDocument();
    expect(screen.getByText(/Live records and all publications remain available/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Withdraw publication" }));
    await waitFor(() => expect(withdraw).toHaveBeenCalledWith(current.id));
    expect(await screen.findByText(/Publication 10 is withdrawn and no longer current/)).toBeInTheDocument();
  });
});
