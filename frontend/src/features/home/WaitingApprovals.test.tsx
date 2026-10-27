import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { WaitingApprovals } from "@/features/home/HomePage";
import { permissionsFixture } from "@/test/permissions";
import type { OwnWorkspace, PublicationRequest } from "@/types";

const workspace = {
  key: "west",
  label: "West office",
  applications: [{ key: "test-app", name: "App", defaultView: "all" }],
} as unknown as OwnWorkspace;

const request = (id: string, submitterId: string): PublicationRequest => ({
  id,
  workspaceKey: "west",
  changeSetId: `cs-${id}`,
  changeSetName: `Update ${id}`,
  version: 2,
  state: "submitted",
  submitter: { kind: "user", id: submitterId, name: submitterId === "me" ? "Me" : "Ana Varga" },
  comment: null,
  submittedAt: "2026-10-26T08:00:00Z",
  publicationId: null,
  decisions: [],
});

afterEach(() => vi.restoreAllMocks());

describe("WaitingApprovals (0.12 A3)", () => {
  it("lists a request for an approver, hides own ones under second person, and opens its review", async () => {
    vi.spyOn(api, "myPermissions").mockResolvedValue(permissionsFixture("west", ["browse", "approve"]));
    vi.spyOn(api, "publicationRequests").mockResolvedValue({
      items: [request("1", "ana"), request("2", "me")],
      nextCursor: null,
    });
    vi.spyOn(api, "approvalPolicy").mockResolvedValue({
      workspaceKey: "west",
      requireApproval: true,
      secondPerson: true,
      version: 1,
      approverCount: 1,
    });
    const onNavigate = vi.fn();
    render(<WaitingApprovals personId="me" workspaces={[workspace]} onNavigate={onNavigate} />);
    expect(await screen.findByRole("heading", { name: "Waiting for your approval" })).toBeVisible();
    expect(screen.getByText(/Submitted by Ana Varga/)).toBeVisible();
    expect(screen.queryByText("Update 2")).not.toBeInTheDocument();
    screen.getByRole("button", { name: "Review Update 1" }).click();
    expect(onNavigate).toHaveBeenCalledWith(expect.objectContaining({ kind: "changeSetChanges", changeSetId: "cs-1" }));
  });

  it("renders nothing without approval rights", async () => {
    vi.spyOn(api, "myPermissions").mockResolvedValue(permissionsFixture("west", ["browse"]));
    const read = vi.spyOn(api, "publicationRequests");
    const { container } = render(<WaitingApprovals personId="me" workspaces={[workspace]} onNavigate={vi.fn()} />);
    await waitFor(() => expect(api.myPermissions).toHaveBeenCalled());
    expect(read).not.toHaveBeenCalled();
    expect(container).toBeEmptyDOMElement();
  });
});
