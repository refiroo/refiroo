import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { security } from "@/api/securityClient";
import type { Group } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { GroupsPage } from "./GroupsPage";

vi.mock("@/api/securityClient", () => ({
  security: {
    groups: vi.fn(),
    group: vi.fn(),
    updateGroup: vi.fn(),
    createGroup: vi.fn(),
    signInProviders: vi.fn(async () => ({ items: [] })),
    members: vi.fn(async () => ({ items: [], nextCursor: null, totalCount: 0 })),
  },
}));
vi.mock("./GrantsSection", () => ({ GrantsSection: () => null, useWorkspaceLabels: () => ({}) }));

const group = (over: Partial<Group> = {}): Group =>
  ({ id: "g1", name: "Curators", description: "Edit the herbarium", members: 0, version: 2, ...over }) as Group;

function open(groupId?: string, onNavigate = vi.fn()) {
  render(
    <ToastProvider>
      <GroupsPage route={{ kind: "settings", page: "groups", groupId }} onNavigate={onNavigate} />
    </ToastProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(security.groups).mockResolvedValue({ items: [group()], nextCursor: null, totalCount: 1 } as never);
  vi.mocked(security.group).mockResolvedValue(group());
});

describe("A group's name and description where they stand (0.17 UX1)", () => {
  it("clears the description in place through the same call, with no dialog", async () => {
    vi.mocked(security.updateGroup).mockResolvedValue(group({ description: undefined, version: 3 }));
    open("g1");
    fireEvent.click(await screen.findByRole("button", { name: /Edit Description:/ }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Description"), { target: { value: "" } });
    fireEvent.keyDown(screen.getByLabelText("Description"), { key: "Enter" });
    await waitFor(() =>
      expect(security.updateGroup).toHaveBeenCalledWith("g1", {
        expectedVersion: 2,
        name: "Curators",
        description: null,
      }),
    );
    expect(await screen.findByRole("button", { name: "Undo" })).toBeInTheDocument();
  });

  it("opens New group as a sheet that adds the group", async () => {
    open();
    fireEvent.click(await screen.findByRole("button", { name: "New group" }));
    const dialog = await screen.findByRole("dialog", { name: "New group" });
    expect(within(dialog).getByText("Description (optional)")).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Add group" })).toBeDisabled();
  });
});

describe("the list and a group's page (0.17 ST1)", () => {
  it("lists groups, and a row opens the group's page", async () => {
    const onNavigate = vi.fn();
    open(undefined, onNavigate);
    fireEvent.click(await screen.findByRole("button", { name: /Curators/ }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "groups", groupId: "g1" });
  });

  it("goes back to the list from the page's trail", async () => {
    const onNavigate = vi.fn();
    open("g1", onNavigate);
    fireEvent.click(await screen.findByRole("link", { name: "Groups" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "groups" });
  });
});
