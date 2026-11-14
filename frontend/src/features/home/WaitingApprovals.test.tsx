import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { WaitingApprovals } from "@/features/home/HomePage";
import { resetPermissionsForTests } from "@/state/permissions";
import { heldAnywhereFixture } from "@/test/permissions";
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

afterEach(() => {
  vi.restoreAllMocks();
  resetPermissionsForTests();
});

/** `GET /me/action-groups` holding Approve in these workspaces only (none: not held at all). */
const approvingIn = (...keys: string[]) =>
  vi.spyOn(api, "myActionGroups").mockResolvedValue({
    items: keys.length
      ? [{ key: "approve", name: "Approve", instance: false, workspaces: keys.map((key) => ({ key, label: key })) }]
      : [{ key: "browse", name: "Browse", instance: true, workspaces: [] }],
  });

describe("WaitingApprovals (0.12 A3)", () => {
  it("lists a request for an approver, hides own ones under second person, and opens its review", async () => {
    approvingIn("west");
    const myPermissions = vi.spyOn(api, "myPermissions");
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
    // One read says where the person approves; no per-workspace permissions are read for it.
    expect(myPermissions).not.toHaveBeenCalled();
  });

  it("counts every listed workspace for a group held at the instance, and only the named ones otherwise", async () => {
    const east = { ...workspace, key: "east", label: "East office" } as OwnWorkspace;
    vi.spyOn(api, "myActionGroups").mockResolvedValue(heldAnywhereFixture(["approve"]));
    const read = vi.spyOn(api, "publicationRequests").mockResolvedValue({ items: [], nextCursor: null });
    vi.spyOn(api, "approvalPolicy").mockResolvedValue(undefined as never);
    const { unmount } = render(<WaitingApprovals personId="me" workspaces={[workspace, east]} onNavigate={vi.fn()} />);
    await waitFor(() => expect(read.mock.calls.map(([key]) => key).sort()).toEqual(["east", "west"]));
    unmount();
    read.mockClear();
    resetPermissionsForTests();
    approvingIn("east");
    render(<WaitingApprovals personId="me" workspaces={[workspace, east]} onNavigate={vi.fn()} />);
    await waitFor(() => expect(read.mock.calls.map(([key]) => key)).toEqual(["east"]));
  });

  it("renders nothing without approval rights", async () => {
    approvingIn();
    const read = vi.spyOn(api, "publicationRequests");
    const { container } = render(<WaitingApprovals personId="me" workspaces={[workspace]} onNavigate={vi.fn()} />);
    await waitFor(() => expect(api.myActionGroups).toHaveBeenCalled());
    expect(read).not.toHaveBeenCalled();
    expect(container).toBeEmptyDOMElement();
  });
});
