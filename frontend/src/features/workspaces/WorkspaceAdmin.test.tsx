import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import type { ChangeEntry, WorkspaceDetail } from "@/types";
import { WorkspaceAdmin, resetWorkspaceAdminCacheForTests } from "@/features/workspaces/WorkspaceAdmin";
import { capabilitiesFixture } from "@/test/capabilities";
import { resetPermissionsForTests } from "@/state/permissions";
import { EVERY_GROUP, heldAnywhereFixture, permissionsFixture } from "@/test/permissions";
import { security } from "@/api/securityClient";
import { testModel, testWorkspaceModel, testAvailability } from "@/test/fixtures";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/state/useWorkspaceAiOffer", () => ({ useHistoryAccountOffer: () => undefined }));
vi.mock("@/api/securityClient", () => ({ security: { access: vi.fn() } }));
vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const time = "2026-09-26T08:00:00Z";
const primary: WorkspaceDetail = {
  key: "default",
  label: "Default",
  status: "active",
  version: 1,
  createdAt: time,
  updatedAt: time,
  model: testWorkspaceModel,
  availability: testAvailability,
  deletable: false,
  deleteBlockedBy: "default",
};
const retail: WorkspaceDetail = {
  key: "retail",
  label: "Retail",
  status: "active",
  version: 3,
  createdAt: time,
  updatedAt: time,
  model: testWorkspaceModel,
  availability: testAvailability,
  deletable: false,
  deleteBlockedBy: "published",
};
const archive: WorkspaceDetail = {
  key: "archive",
  label: "Archive",
  status: "retired",
  version: 2,
  createdAt: time,
  updatedAt: time,
  model: testWorkspaceModel,
  availability: testAvailability,
  deletable: false,
  deleteBlockedBy: "notEmpty",
};
const runtime = { defaultWorkspaceKey: "default", version: 4, updatedAt: time };

const capabilities = (manageWorkspaces: boolean) => capabilitiesFixture({ manageWorkspaces });

const LIST = { kind: "settings", page: "workspaces" } as const;

function renderAdmin(workspaceKey?: string, overrides: Partial<Parameters<typeof WorkspaceAdmin>[0]> = {}) {
  const props = {
    route: { ...LIST, ...(workspaceKey ? { workspaceKey } : {}) },
    onRouteChange: vi.fn(),
    onNavigate: vi.fn(),
    onDefaultChanged: vi.fn(),
    onOpenWorkspace: vi.fn(),
    ...overrides,
  };
  return {
    ...render(
      <ToastProvider>
        <WorkspaceAdmin {...props} />
      </ToastProvider>,
    ),
    props,
  };
}

const byKey = new Map<string, WorkspaceDetail>();

beforeEach(() => {
  vi.clearAllMocks();
  resetWorkspaceAdminCacheForTests();
  // A caller holding every group but Security administration: the workspace's Access is not
  // shown (0.12 SP1); the workspaces are managed and opened (Z5, D323).
  const groups = EVERY_GROUP.filter((key) => key !== "security-admin");
  vi.mocked(api.myPermissions).mockImplementation(async (key) => permissionsFixture(key, groups));
  vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture(groups));
  vi.mocked(api.approvalPolicy).mockResolvedValue({
    workspaceKey: "x",
    requireApproval: false,
    secondPerson: false,
    version: 0,
    approverCount: 1,
  });
  vi.mocked(api.model).mockResolvedValue(testModel);
  vi.mocked(api.changes).mockResolvedValue({ items: [], nextCursor: null } as never);
  byKey.clear();
  for (const item of [primary, retail, archive]) byKey.set(item.key, item);
  vi.mocked(api.capabilities).mockResolvedValue(capabilities(true));
  vi.mocked(api.workspaceRuntimeState).mockResolvedValue(runtime);
  vi.mocked(api.subscriptions).mockResolvedValue({ items: [], nextCursor: null });
  // The server's answer: the status and the search narrow the list; the default is not first here.
  vi.mocked(api.workspaces).mockImplementation(async (options = {}) => {
    const needle = (options.search ?? "").toLowerCase();
    const items = [archive, retail, primary].filter(
      (item) =>
        item.status === (options.status ?? "active") &&
        (!needle || item.label.toLowerCase().includes(needle) || item.key.includes(needle)),
    );
    return { items, nextCursor: null };
  });
  vi.mocked(api.workspace).mockImplementation(async (key) => byKey.get(key)!);
});

/** Opens the ⋯ menu of the opened workspace and returns its items (none where the menu is not offered). */
async function openMenu() {
  const trigger = await screen.findByRole("button", { name: "More actions" });
  fireEvent.keyDown(trigger, { key: "ArrowDown", code: "ArrowDown" });
  return screen.findAllByRole("menuitem");
}

/** Chooses an action from the opened workspace's ⋯ menu. */
async function chooseAction(name: string) {
  await openMenu();
  fireEvent.keyDown(await screen.findByRole("menuitem", { name: new RegExp(`^${name}`) }), {
    key: "Enter",
    code: "Enter",
  });
}

/** The names of the ⋯ menu's items, the menu closed again; empty where the page offers no menu. */
async function menuNames() {
  if (!screen.queryByRole("button", { name: "More actions" })) return [];
  const items = await openMenu();
  const names = items.map((item) => item.textContent ?? "");
  fireEvent.keyDown(items[0], { key: "Escape", code: "Escape" });
  return names;
}

describe("WorkspaceAdmin", () => {
  it("opens on the list, not on a workspace, with the default named in the description", async () => {
    renderAdmin();
    expect(await screen.findByRole("region", { name: "Active" })).toBeInTheDocument();
    // Only the list's group headings (title · count); no workspace's own heading.
    for (const heading of screen.queryAllByRole("heading", { level: 2 })) expect(heading.textContent).toMatch(/ · \d+/);
    expect(screen.queryByRole("navigation", { name: "Where you are" })).not.toBeInTheDocument();
    expect(await screen.findByText("Default · Default")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /New workspace/ })).toBeInTheDocument();
  });

  it("lists the active workspaces, the default first, then the retired ones, with counts", async () => {
    renderAdmin();
    const active = await screen.findByRole("region", { name: "Active" });
    const rows = within(active).getAllByRole("button");
    expect(rows.map((row) => row.querySelector("strong")?.textContent)).toEqual(["Default", "Retail"]);
    expect(rows[0]).toHaveAccessibleName(/default.*Model: Starter model, Release: 0\.3\.0/i);
    expect(within(rows[0]).getByText("default")).toHaveClass("mono");
    expect(within(rows[0]).getByText("0.3.0")).toHaveClass("mono");
    expect(active).toHaveTextContent("Active · 2");
    const retired = screen.getByRole("region", { name: "Retired" });
    expect(retired).toHaveTextContent("Retired · 1");
    expect(within(retired).getByRole("button", { name: /Archive.*Retired/ })).toBeInTheDocument();
    expect(api.workspaces).toHaveBeenCalledWith(expect.objectContaining({ status: "active", pageSize: 100 }));
    expect(api.workspaces).toHaveBeenCalledWith(expect.objectContaining({ status: "retired", pageSize: 100 }));
  });

  it("shows no Retired group when no workspace is retired", async () => {
    byKey.delete("archive");
    vi.mocked(api.workspaces).mockImplementation(async (options = {}) => ({
      items: options.status === "retired" ? [] : [primary, retail],
      nextCursor: null,
    }));
    renderAdmin();
    await screen.findByRole("region", { name: "Active" });
    await waitFor(() => expect(screen.queryByRole("status", { name: /Loading/ })).not.toBeInTheDocument());
    expect(screen.queryByRole("region", { name: "Retired" })).not.toBeInTheDocument();
  });

  it("narrows both groups through the search and says when nothing matches", async () => {
    renderAdmin();
    await screen.findByRole("region", { name: "Retired" });
    fireEvent.change(screen.getByRole("searchbox", { name: "Search workspaces" }), { target: { value: "arch" } });
    await waitFor(() => expect(api.workspaces).toHaveBeenCalledWith(expect.objectContaining({ search: "arch" })));
    await waitFor(() => expect(screen.queryByRole("region", { name: "Active" })).not.toBeInTheDocument());
    expect(screen.getByRole("region", { name: "Retired" })).toBeInTheDocument();
    expect(api.workspaces).toHaveBeenCalledWith(expect.objectContaining({ status: "active", search: "arch" }));
    expect(api.workspaces).toHaveBeenCalledWith(expect.objectContaining({ status: "retired", search: "arch" }));

    fireEvent.change(screen.getByRole("searchbox", { name: "Search workspaces" }), { target: { value: "zzz" } });
    expect(await screen.findByText("No workspace matches “zzz”")).toBeInTheDocument();
  });

  it("opens the chosen workspace through the route", async () => {
    const { props } = renderAdmin();
    fireEvent.click(await screen.findByRole("button", { name: /Retail/ }));
    expect(props.onRouteChange).toHaveBeenCalledWith({ ...LIST, workspaceKey: "retail" });
  });

  it("shows a workspace under the bar with a plain heading, and the trail returns to the list", async () => {
    const { props } = renderAdmin("retail");
    expect(await screen.findByRole("heading", { level: 1, name: "Retail" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Switch workspace/ })).not.toBeInTheDocument();
    const trail = screen.getByRole("navigation", { name: "Where you are" });
    expect(trail).toHaveTextContent("Workspaces");
    expect(screen.queryByRole("button", { name: "← All workspaces" })).not.toBeInTheDocument();
    fireEvent.click(within(trail).getByRole("button", { name: "Workspaces" }));
    expect(props.onRouteChange).toHaveBeenLastCalledWith(LIST);
    expect(props.onRouteChange).toHaveBeenCalledTimes(1);
  });

  it("shows the lists last read at once on the next visit and refreshes them in place", async () => {
    const first = renderAdmin();
    await screen.findByRole("region", { name: "Retired" });
    first.unmount();

    // The next read never settles on its own: the rows must come from what was read before.
    const release: Array<() => void> = [];
    vi.mocked(api.workspaces).mockImplementation(
      (options = {}) =>
        new Promise((resolve) =>
          release.push(() =>
            resolve({
              items: options.status === "retired" ? [] : [{ ...retail, label: "Retail EU" }],
              nextCursor: null,
            }),
          ),
        ),
    );
    renderAdmin();
    expect(screen.getByRole("region", { name: "Retired" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Archive/ })).toBeInTheDocument();
    expect(screen.queryByRole("status", { name: /Loading/ })).not.toBeInTheDocument();

    await act(async () => release.forEach((resolve) => resolve()));
    expect(await screen.findByRole("button", { name: /Retail EU/ })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Retired" })).not.toBeInTheDocument();
  });

  it("reports a failed read inside the list and retries it", async () => {
    renderAdmin();
    await screen.findByRole("region", { name: "Active" });
    vi.mocked(api.workspaces).mockRejectedValueOnce(new Error("Catalogue unavailable"));
    fireEvent.change(screen.getByRole("searchbox", { name: "Search workspaces" }), { target: { value: "r" } });
    expect(await screen.findByText("Catalogue unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: /Retail/ })).toBeInTheDocument();
  });

  it("reports a failed capability read above the page and retries it", async () => {
    vi.mocked(api.capabilities).mockRejectedValueOnce(new Error("Capabilities unavailable"));
    renderAdmin();
    expect(await screen.findByText("Capabilities unavailable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Workspaces" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: /New workspace/ })).toBeInTheDocument();
    expect(screen.queryByText("Capabilities unavailable")).not.toBeInTheDocument();
  });

  it("keeps the catalogue read only and names the setting when administration is disabled", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilities(false));
    renderAdmin("retail");
    expect(await screen.findByRole("heading", { level: 1, name: "Retail" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /New workspace/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Edit Name:/ })).not.toBeInTheDocument();
    expect(await menuNames()).toEqual([]);
    expect(screen.getByRole("button", { name: "Open workspace" })).toBeEnabled();
  });

  it("creates a workspace with a key suggested from its name and selects it", async () => {
    const created = { ...retail, key: "central-europe", label: "Central Europe", version: 1 };
    vi.mocked(api.createWorkspace).mockResolvedValue(created);
    const { props } = renderAdmin();
    fireEvent.click(await screen.findByRole("button", { name: /New workspace/ }));
    const dialog = await screen.findByRole("dialog", { name: "New workspace" });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: "Central Europe" } });
    expect(within(dialog).getByRole("textbox", { name: /^Key/ })).toHaveValue("central-europe");
    fireEvent.click(within(dialog).getByRole("button", { name: "Add workspace" }));

    await waitFor(() => expect(props.onRouteChange).toHaveBeenCalledWith({ ...LIST, workspaceKey: "central-europe" }));
    expect(api.createWorkspace).toHaveBeenCalledWith({ key: "central-europe", label: "Central Europe" });
    expect(screen.queryByRole("dialog", { name: "New workspace" })).not.toBeInTheDocument();
  });

  it("keeps the dialog and its input when the key already exists", async () => {
    vi.mocked(api.createWorkspace).mockRejectedValue(
      new ApiError(409, "WORKSPACE_ALREADY_EXISTS", "Workspace 'retail' already exists"),
    );
    renderAdmin();
    fireEvent.click(await screen.findByRole("button", { name: /New workspace/ }));
    const dialog = await screen.findByRole("dialog", { name: "New workspace" });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: "Retail" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add workspace" }));
    expect(await within(dialog).findByText("Workspace 'retail' already exists")).toBeInTheDocument();
    expect(within(dialog).getByRole("textbox", { name: "Name" })).toHaveValue("Retail");
  });

  it("renames with the version it read", async () => {
    vi.mocked(api.updateWorkspace).mockResolvedValue({ ...retail, label: "Retail Europe", version: 4 });
    renderAdmin("retail");
    fireEvent.click(await screen.findByRole("button", { name: /Edit Name:/ }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: "Name" }), { target: { value: "Retail Europe" } });
    fireEvent.keyDown(screen.getByRole("textbox", { name: "Name" }), { key: "Enter" });

    expect(await screen.findByRole("heading", { level: 1, name: "Retail Europe" })).toBeInTheDocument();
    expect(api.updateWorkspace).toHaveBeenCalledWith("retail", { expectedVersion: 3, label: "Retail Europe" });
    expect(screen.getByText("Workspace renamed.")).toBeInTheDocument();
  });

  it("shows a concurrent rename, keeps the user's name and saves again only on request", async () => {
    vi.mocked(api.updateWorkspace)
      .mockRejectedValueOnce(new ApiError(409, "VERSION_CONFLICT", "Workspace version has changed"))
      .mockResolvedValueOnce({ ...retail, label: "Mine", version: 5 });
    renderAdmin("retail");
    fireEvent.click(await screen.findByRole("button", { name: /Edit Name:/ }));
    vi.mocked(api.workspace).mockResolvedValue({ ...retail, label: "Theirs", version: 4 });
    fireEvent.change(screen.getByRole("textbox", { name: "Name" }), { target: { value: "Mine" } });
    fireEvent.keyDown(screen.getByRole("textbox", { name: "Name" }), { key: "Enter" });

    expect(await screen.findByText(/It is now named “Theirs”/)).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Name" })).toHaveValue("Mine");
    expect(api.updateWorkspace).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Save again" }));
    await waitFor(() =>
      expect(api.updateWorkspace).toHaveBeenLastCalledWith("retail", { expectedVersion: 4, label: "Mine" }),
    );
  });

  it("sets the default with the runtime-state version and reports it", async () => {
    vi.mocked(api.setDefaultWorkspace).mockResolvedValue({
      defaultWorkspaceKey: "retail",
      version: 5,
      updatedAt: time,
    });
    const { props } = renderAdmin("retail");
    await chooseAction("Set as default");

    expect(await screen.findByText("Retail is now the default workspace.")).toBeInTheDocument();
    expect(api.setDefaultWorkspace).toHaveBeenCalledWith("retail", 4);
    expect(props.onDefaultChanged).toHaveBeenCalledWith("retail");
    expect(await menuNames()).toEqual([expect.stringMatching(/^Retire…/)]);
    await openMenu();
    expect(screen.getByRole("menuitem", { name: /^Retire…/ })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText("Default")).toBeInTheDocument();
  });

  it("names the new default after a concurrent default switch instead of retrying", async () => {
    vi.mocked(api.setDefaultWorkspace).mockRejectedValue(
      new ApiError(409, "VERSION_CONFLICT", "Workspace runtime-state version has changed"),
    );
    renderAdmin("retail");
    await screen.findByRole("button", { name: "More actions" });
    vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
      defaultWorkspaceKey: "archive",
      version: 6,
      updatedAt: time,
    });
    await chooseAction("Set as default");

    expect(await screen.findByText(/default workspace changed to “archive”/)).toBeInTheDocument();
    expect(api.setDefaultWorkspace).toHaveBeenCalledTimes(1);
  });

  it("retires after confirmation and offers reactivation", async () => {
    vi.mocked(api.updateWorkspace).mockResolvedValue({ ...retail, status: "retired", version: 4 });
    renderAdmin("retail");
    await chooseAction("Retire…");
    const confirm = await screen.findByRole("alertdialog", { name: "Retire Retail?" });
    expect(within(confirm).getByText(/can be reactivated later/)).toBeInTheDocument();
    fireEvent.click(within(confirm).getByRole("button", { name: "Retire workspace" }));

    expect(await screen.findByText(/Workspace retired/)).toBeInTheDocument();
    expect(api.updateWorkspace).toHaveBeenCalledWith("retail", { expectedVersion: 3, status: "retired" });
    expect(await menuNames()).toEqual(["Reactivate"]);
  });

  it("reports a refused retirement inside the confirmation", async () => {
    vi.mocked(api.updateWorkspace).mockRejectedValue(
      new ApiError(409, "DEFAULT_WORKSPACE_CANNOT_BE_RETIRED", "The default workspace cannot be retired"),
    );
    renderAdmin("retail");
    await chooseAction("Retire…");
    const confirm = await screen.findByRole("alertdialog", { name: "Retire Retail?" });
    fireEvent.click(within(confirm).getByRole("button", { name: "Retire workspace" }));
    expect(await within(confirm).findByText("The default workspace cannot be retired")).toBeInTheDocument();
    expect(api.workspaceRuntimeState).toHaveBeenCalledTimes(2);
  });

  it("reactivates a retired workspace", async () => {
    vi.mocked(api.updateWorkspace).mockResolvedValue({ ...archive, status: "active", version: 3 });
    renderAdmin("archive");
    expect(await screen.findByText("Retired · read only")).toBeInTheDocument();
    await chooseAction("Reactivate");
    expect(await screen.findByText("Workspace reactivated.")).toBeInTheDocument();
    expect(api.updateWorkspace).toHaveBeenCalledWith("archive", { expectedVersion: 2, status: "active" });
  });

  it("deletes an unused workspace after a confirmation that names its key", async () => {
    const typo: WorkspaceDetail = { ...retail, key: "retial", label: "Retial", version: 1, deletable: true };
    byKey.set("retial", typo);
    vi.mocked(api.deleteWorkspace).mockResolvedValue(undefined);
    const { props, rerender } = renderAdmin("retial", { onWorkspaceDeleted: vi.fn() });
    await chooseAction("Delete…");
    const confirm = await screen.findByRole("alertdialog", { name: "Delete Retial?" });
    expect(within(confirm).getByText("retial")).toBeInTheDocument();
    expect(within(confirm).getByRole("button", { name: "Cancel" })).toHaveFocus();
    fireEvent.click(within(confirm).getByRole("button", { name: "Delete workspace" }));

    expect(await screen.findByText(/Workspace Retial \(retial\) was deleted/)).toBeInTheDocument();
    expect(api.deleteWorkspace).toHaveBeenCalledWith("retial", 1);
    expect(props.onRouteChange).toHaveBeenCalledWith(LIST);
    expect(props.onWorkspaceDeleted).toHaveBeenCalledWith("retial");

    // Creating the corrected key is confirmed beside the deletion; both are toasts, not page notices.
    vi.mocked(api.createWorkspace).mockResolvedValue({ ...typo, key: "retail-eu", label: "Retail EU" });
    rerender(
      <ToastProvider>
        <WorkspaceAdmin {...props} route={LIST} />
      </ToastProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: /New workspace/ }));
    const dialog = await screen.findByRole("dialog", { name: "New workspace" });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: "Retail EU" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Add workspace" }));
    await waitFor(() => expect(screen.queryByRole("dialog", { name: "New workspace" })).not.toBeInTheDocument());
    expect(await screen.findByText("Workspace Retail EU was created.")).toBeInTheDocument();
  });

  it.each([
    ["default", "default", /default workspace cannot be retired or deleted/],
    ["retail", "retail", /has been published, so it cannot be deleted.*Retire it instead/],
    ["archive", "archive", /Only an empty workspace can be deleted/],
    ["subscribed", "subscribed", /Delete its webhook subscriptions first, or retire it/],
  ])("offers no deletion for the %s workspace and says why", async (_, key, reason) => {
    byKey.set("subscribed", { ...retail, key: "subscribed", label: "Subscribed", deleteBlockedBy: "subscribed" });
    renderAdmin(key);
    expect(await screen.findByText(reason)).toBeInTheDocument();
    expect(await menuNames()).not.toContain("Delete…");
  });

  it("names the webhooks that keep a workspace from being deleted, each linked to its page", async () => {
    byKey.set("subscribed", { ...retail, key: "subscribed", label: "Subscribed", deleteBlockedBy: "subscribed" });
    vi.mocked(api.subscriptions).mockResolvedValue({
      items: [{ id: "s1", name: "Billing", url: "https://receiver.example.com/hook", consumerApi: "codes" } as never],
      nextCursor: null,
    });
    const { props } = renderAdmin("subscribed");
    fireEvent.click(await screen.findByRole("link", { name: "Billing" }));
    expect(api.subscriptions).toHaveBeenCalledWith({ cursor: undefined, workspaceKey: "subscribed" });
    expect(props.onRouteChange).toHaveBeenCalledWith({ kind: "settings", page: "webhooks", subscriptionId: "s1" });
  });

  it("does not suggest retiring a retired published workspace", async () => {
    byKey.set("archive", { ...archive, deleteBlockedBy: "published" });
    renderAdmin("archive");
    expect(await screen.findByText(/has been published, so it cannot be deleted/)).toBeInTheDocument();
    expect(screen.queryByText(/Retire it instead/)).not.toBeInTheDocument();
  });

  it("offers no deletion when administration is disabled", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilities(false));
    byKey.set("retial", { ...retail, key: "retial", label: "Retial", deletable: true, deleteBlockedBy: null });
    renderAdmin("retial");
    expect(await screen.findByRole("heading", { level: 1, name: "Retial" })).toBeInTheDocument();
    expect(await menuNames()).not.toContain("Delete…");
  });

  it("shows a refused deletion and the reason the workspace now has", async () => {
    byKey.set("retial", { ...retail, key: "retial", label: "Retial", deletable: true, deleteBlockedBy: null });
    vi.mocked(api.deleteWorkspace).mockRejectedValue(
      new ApiError(409, "WORKSPACE_NOT_EMPTY", "Workspace 'retial' still has objects or change sets", {
        objectCount: 1,
        changeSetCount: 0,
      }),
    );
    const { props } = renderAdmin("retial");
    await chooseAction("Delete…");
    byKey.set("retial", { ...retail, key: "retial", label: "Retial", deletable: false, deleteBlockedBy: "notEmpty" });
    const confirm = await screen.findByRole("alertdialog", { name: "Delete Retial?" });
    fireEvent.click(within(confirm).getByRole("button", { name: "Delete workspace" }));

    expect(await screen.findByText("Workspace 'retial' still has objects or change sets")).toBeInTheDocument();
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(screen.getByText(/Only an empty workspace can be deleted/)).toBeInTheDocument();
    expect(await menuNames()).not.toContain("Delete…");
    expect(props.onRouteChange).not.toHaveBeenCalled();
  });

  it("reports a concurrent change instead of deleting", async () => {
    byKey.set("retial", { ...retail, key: "retial", label: "Retial", deletable: true, deleteBlockedBy: null });
    vi.mocked(api.deleteWorkspace).mockRejectedValue(
      new ApiError(409, "VERSION_CONFLICT", "Workspace version has changed"),
    );
    renderAdmin("retial");
    await chooseAction("Delete…");
    byKey.set("retial", {
      ...retail,
      key: "retial",
      label: "Retail",
      version: 2,
      deletable: true,
      deleteBlockedBy: null,
    });
    fireEvent.click(
      within(await screen.findByRole("alertdialog", { name: "Delete Retial?" })).getByRole("button", {
        name: "Delete workspace",
      }),
    );
    expect(await screen.findByText(/It is now “Retail” and active/)).toBeInTheDocument();
    expect(api.deleteWorkspace).toHaveBeenCalledTimes(1);
  });

  it("opens the selected workspace", async () => {
    const { props } = renderAdmin("retail");
    fireEvent.click(await screen.findByRole("button", { name: "Open workspace" }));
    expect(props.onOpenWorkspace).toHaveBeenCalledWith("retail");
  });

  it("reports an unknown workspace in the detail and retries the read", async () => {
    vi.mocked(api.workspace).mockRejectedValueOnce(
      new ApiError(404, "WORKSPACE_NOT_FOUND", "Workspace 'gone' not found"),
    );
    renderAdmin("gone");
    expect(await screen.findByText("Workspace 'gone' not found")).toBeInTheDocument();
    vi.mocked(api.workspace).mockResolvedValue({ ...retail, key: "gone", label: "Gone after all" });
    fireEvent.click(within(screen.getByRole("alert")).getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { level: 1, name: "Gone after all" })).toBeInTheDocument();
  });
});

describe("WorkspaceAdmin approval policy (0.12 A3)", () => {
  it("saves the policy with the version read", async () => {
    vi.mocked(api.approvalPolicy).mockResolvedValue({
      workspaceKey: "retail",
      requireApproval: false,
      secondPerson: false,
      version: 2,
      approverCount: 1,
    });
    vi.mocked(api.setApprovalPolicy).mockResolvedValue({
      workspaceKey: "retail",
      requireApproval: true,
      secondPerson: true,
      version: 3,
      approverCount: 1,
    });
    renderAdmin("retail", { route: { ...LIST, workspaceKey: "retail", workspaceTab: "approval" } });
    const needs = await screen.findByRole("checkbox", { name: "Changes need approval before they are published" });
    const second = screen.getByRole("checkbox", { name: "The person who submitted a change set cannot approve it" });
    expect(second).toBeDisabled();
    fireEvent.click(needs);
    fireEvent.click(second);
    fireEvent.click(screen.getByRole("button", { name: "Save approval policy" }));
    await waitFor(() =>
      expect(api.setApprovalPolicy).toHaveBeenCalledWith("retail", {
        requireApproval: true,
        secondPerson: true,
        expectedVersion: 2,
      }),
    );
    expect(await screen.findByText("Approval policy saved.")).toBeVisible();
  });

  it("offers to reload the policy after a version conflict, and saves with the version it then reads", async () => {
    vi.mocked(api.approvalPolicy)
      .mockResolvedValueOnce({
        workspaceKey: "retail",
        requireApproval: false,
        secondPerson: false,
        version: 2,
        approverCount: 1,
      })
      .mockResolvedValue({
        workspaceKey: "retail",
        requireApproval: false,
        secondPerson: false,
        version: 5,
        approverCount: 1,
      });
    vi.mocked(api.setApprovalPolicy)
      .mockRejectedValueOnce(new ApiError(409, "VERSION_CONFLICT", "The policy changed"))
      .mockResolvedValue({
        workspaceKey: "retail",
        requireApproval: true,
        secondPerson: false,
        version: 6,
        approverCount: 1,
      });
    renderAdmin("retail", { route: { ...LIST, workspaceKey: "retail", workspaceTab: "approval" } });
    fireEvent.click(await screen.findByRole("checkbox", { name: "Changes need approval before they are published" }));
    fireEvent.click(screen.getByRole("button", { name: "Save approval policy" }));
    expect(await screen.findByText("The policy changed meanwhile. Reload to see it.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Save approval policy" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reload the policy" }));
    await screen.findByRole("button", { name: "Save approval policy" });
    fireEvent.click(screen.getByRole("checkbox", { name: "Changes need approval before they are published" }));
    fireEvent.click(screen.getByRole("button", { name: "Save approval policy" }));
    await waitFor(() =>
      expect(api.setApprovalPolicy).toHaveBeenLastCalledWith("retail", {
        requireApproval: true,
        secondPerson: false,
        expectedVersion: 5,
      }),
    );
  });

  function policyWith(approverCount: number, requireApproval = false) {
    vi.mocked(api.approvalPolicy).mockResolvedValue({
      workspaceKey: "retail",
      requireApproval,
      secondPerson: false,
      version: 1,
      approverCount,
    });
  }
  const approvalRoute = { ...LIST, workspaceKey: "retail", workspaceTab: "approval" } as const;

  it("says who can approve", async () => {
    policyWith(1);
    const first = renderAdmin("retail", { route: approvalRoute });
    expect(
      await screen.findByText("1 person or client can approve (Data owners hold Approve publications)."),
    ).toBeVisible();
    first.unmount();
    policyWith(2);
    renderAdmin("retail", { route: approvalRoute });
    expect(
      await screen.findByText("2 people or clients can approve (Data owners hold Approve publications)."),
    ).toBeVisible();
  });

  it("warns, without blocking, when the second-person rule has too few approvers", async () => {
    policyWith(1, true);
    const first = renderAdmin("retail", { route: approvalRoute });
    const second = await screen.findByRole("checkbox", {
      name: "The person who submitted a change set cannot approve it",
    });
    expect(screen.queryByText(/Only one person can approve/)).not.toBeInTheDocument();
    fireEvent.click(second);
    expect(screen.getByText(/Only one person can approve, so their own change sets will wait/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Save approval policy" })).toBeEnabled();
    first.unmount();
    policyWith(2, true);
    renderAdmin("retail", { route: approvalRoute });
    fireEvent.click(
      await screen.findByRole("checkbox", { name: "The person who submitted a change set cannot approve it" }),
    );
    expect(screen.queryByText(/Only one person can approve/)).not.toBeInTheDocument();
  });

  it("warns that every request waits when nobody can approve", async () => {
    policyWith(0);
    renderAdmin("retail", { route: approvalRoute });
    expect(await screen.findByText(/Nobody can approve yet/)).toBeVisible();
    expect(screen.queryByText(/every request will wait/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Changes need approval before they are published" }));
    expect(screen.getByText(/Nobody can approve, so every request will wait/)).toBeVisible();
  });

  it("shows no approval section to someone without workspace administration there", async () => {
    const groups = EVERY_GROUP.filter((key) => key !== "security-admin" && key !== "workspace-admin");
    vi.mocked(api.myPermissions).mockImplementation(async (key) => permissionsFixture(key, groups));
    renderAdmin("retail", { route: { ...LIST, workspaceKey: "retail", workspaceTab: "approval" } });
    expect(await screen.findByRole("heading", { level: 1, name: "Retail" })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Approval" })).not.toBeInTheDocument();
    expect(screen.queryByRole("checkbox", { name: /need approval/ })).not.toBeInTheDocument();
    // The route named a tab the person may not use: Overview opens.
    expect(screen.getByRole("tab", { name: "Overview", selected: true })).toBeInTheDocument();
  });
});

describe("WorkspaceAdmin tabs, applications and activity", () => {
  const change = (id: string, at: string, name: string): ChangeEntry => ({
    id,
    occurredAt: at,
    kind: "record",
    action: "created",
    workspace: { key: "retail", label: "Retail" },
    changeSet: null,
    subject: {
      id,
      name,
      applicationKey: "test-app",
      objectTypeKey: "domain",
      objectTypeName: "Domain",
      removed: false,
    },
    changedFields: [],
    attributes: [],
    cause: { kind: "user" },
    actor: { kind: "user", id: "p", name: "Ana Varga" },
  });

  it("shows every tab to an administrator and Overview and Activity to someone who may only browse", async () => {
    const all = [...EVERY_GROUP];
    vi.mocked(api.myPermissions).mockImplementation(async (key) => permissionsFixture(key, all));
    vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture(all));
    vi.mocked(security.access).mockResolvedValue({ items: [], nextCursor: null } as never);
    const first = renderAdmin("retail");
    await screen.findByRole("heading", { level: 1, name: "Retail" });
    await waitFor(() =>
      expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual([
        "Overview",
        "Access",
        "Approval",
        "Activity",
      ]),
    );
    first.unmount();
    resetPermissionsForTests();
    vi.mocked(api.myPermissions).mockImplementation(async (key) => permissionsFixture(key, ["browse"]));
    vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture(["browse"]));
    renderAdmin("retail");
    await screen.findByRole("heading", { level: 1, name: "Retail" });
    await screen.findByRole("button", { name: "Open workspace" });
    expect(screen.getAllByRole("tab").map((tab) => tab.textContent)).toEqual(["Overview", "Activity"]);
  });

  it("changes the tab in the address", async () => {
    const { props } = renderAdmin("retail");
    fireEvent.click(await screen.findByRole("tab", { name: "Approval" }));
    expect(props.onRouteChange).toHaveBeenCalledWith({ ...LIST, workspaceKey: "retail", workspaceTab: "approval" });
  });

  it("lists the model's applications as cards and opens one in this workspace", async () => {
    const { props } = renderAdmin("retail");
    const card = await screen.findByRole("link", { name: /Test App/ });
    expect(api.model).toHaveBeenCalledWith({ workspaceKey: "retail" });
    expect(card).toHaveTextContent(/declared views?/);
    expect(screen.getByRole("heading", { level: 2, name: "Applications" })).toBeInTheDocument();
    fireEvent.click(card);
    expect(props.onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "list", applicationKey: "test-app", workspaceKey: "retail" }),
    );
  });

  it("hides the applications from someone who may not browse the workspace", async () => {
    vi.mocked(api.myPermissions).mockImplementation(async (key) => permissionsFixture(key, ["workspace-admin"]));
    renderAdmin("retail");
    await screen.findByRole("heading", { level: 1, name: "Retail" });
    await screen.findByText(/Change sets and publications belong to this workspace/);
    expect(screen.queryByRole("heading", { name: /^Applications/ })).not.toBeInTheDocument();
  });

  it("lists the activity newest first by day and loads more", async () => {
    vi.mocked(api.changes)
      .mockResolvedValueOnce({
        items: [change("a", "2026-10-26T10:00:00Z", "Alpha"), change("b", "2026-10-25T09:00:00Z", "Beta")],
        nextCursor: "next",
      } as never)
      .mockResolvedValueOnce({ items: [change("c", "2026-10-24T08:00:00Z", "Gamma")], nextCursor: null } as never);
    renderAdmin("retail", { route: { ...LIST, workspaceKey: "retail", workspaceTab: "activity" } });
    const log = await screen.findByRole("group", { name: "Activity" });
    // The day headings are h2 under the page's h1 (R17-F46).
    expect(within(log).getAllByRole("heading", { level: 2 })).toHaveLength(2);
    expect(within(log).getByText("Added Alpha")).toBeInTheDocument();
    expect(within(log).getAllByText(/Ana Varga/).length).toBe(2);
    expect(api.changes).toHaveBeenCalledWith(expect.objectContaining({ workspaceKey: "retail" }));
    fireEvent.click(screen.getByRole("button", { name: "Load more" }));
    expect(await screen.findByText("Added Gamma")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("marks entries with tiles and kind pills and folds a change set's changes into one line", async () => {
    const inSet = (id: string, name: string, action: string): ChangeEntry => ({
      ...change(id, "2026-10-26T10:00:00", name),
      action,
      changeSet: { id: "cs1", name: "Spring", open: false },
    });
    const other = (id: string, kind: ChangeEntry["kind"], action: string): ChangeEntry => ({
      ...change(id, "2026-10-26T09:00:00", id),
      kind,
      action,
      subject: { id, name: kind === "model" ? "0.9" : null, number: 8 },
    });
    vi.mocked(api.changes).mockResolvedValueOnce({
      items: [
        inSet("a", "Alpha", "created"),
        inSet("b", "Beta", "updated"),
        other("p", "publication", "published"),
        other("m", "model", "activated"),
      ],
      nextCursor: null,
    } as never);
    renderAdmin("retail", { route: { ...LIST, workspaceKey: "retail", workspaceTab: "activity" } });
    const log = await screen.findByRole("group", { name: "Activity" });
    const toggle = await within(log).findByRole("button", { name: /2 records changed in “Spring”/ });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(within(log).queryByText("Added Alpha")).not.toBeInTheDocument();
    expect(within(log).getByText("Published")).toBeInTheDocument();
    expect(within(log).getByText("Model")).toBeInTheDocument();
    expect(log.querySelector('[data-mark="publication"]')).not.toBeNull();
    expect(log.querySelector('[data-mark="model"]')).not.toBeNull();
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(within(log).getByText("Added Alpha")).toBeInTheDocument();
    expect(within(log).getByText("Created")).toBeInTheDocument();
    expect(within(log).getByText("Changed")).toBeInTheDocument();
    expect(log.querySelectorAll(".hue-tile[data-hue]").length).toBeGreaterThan(2);
  });

  it("says when there is no activity and retries a failed read", async () => {
    vi.mocked(api.changes).mockRejectedValueOnce(new Error("Changes unavailable"));
    renderAdmin("retail", { route: { ...LIST, workspaceKey: "retail", workspaceTab: "activity" } });
    expect(await screen.findByText("Changes unavailable")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("No activity yet.")).toBeInTheDocument();
  });
});

describe("WorkspaceAdmin keeps what it has read", () => {
  /** The route held in state, as the router does: a tab change re-renders the page, nothing more. */
  function Stateful({ start }: { start: Parameters<typeof WorkspaceAdmin>[0]["route"] }) {
    const [route, setRoute] = useState(start);
    return (
      <ToastProvider>
        <WorkspaceAdmin
          route={route}
          onRouteChange={(next) => setRoute(next as typeof route)}
          onNavigate={vi.fn()}
          onOpenWorkspace={vi.fn()}
        />
      </ToastProvider>
    );
  }

  it("does not reload the page or read a tab again when the tab changes", async () => {
    render(<Stateful start={{ ...LIST, workspaceKey: "retail" }} />);
    await screen.findByRole("heading", { level: 1, name: "Retail" });
    await screen.findByRole("region", { name: "Applications" });
    await waitFor(() => expect(screen.getAllByRole("tab")).toHaveLength(3));
    const reads = () => ({
      capabilities: vi.mocked(api.capabilities).mock.calls.length,
      workspace: vi.mocked(api.workspace).mock.calls.length,
      model: vi.mocked(api.model).mock.calls.length,
      policy: vi.mocked(api.approvalPolicy).mock.calls.length,
    });
    const first = reads();
    const heading = screen.getByRole("heading", { level: 1, name: "Retail" });

    fireEvent.click(screen.getByRole("tab", { name: "Activity" }));
    await screen.findByRole("region", { name: "Activity" });
    await waitFor(() => expect(vi.mocked(api.model).mock.calls.length).toBe(first.model + 1));
    fireEvent.click(screen.getByRole("tab", { name: "Overview" }));
    fireEvent.click(await screen.findByRole("tab", { name: "Approval" }));
    await screen.findByLabelText("Changes need approval before they are published");
    fireEvent.click(screen.getByRole("tab", { name: "Overview" }));
    await screen.findByRole("region", { name: "Applications" });

    // The page stayed mounted (the same heading element) and nothing was read twice: Activity's
    // model read and the approval policy are the first reads of those tabs, none came back for Overview.
    expect(screen.getByRole("heading", { level: 1, name: "Retail" })).toBe(heading);
    const after = reads();
    expect(after.capabilities).toBe(first.capabilities);
    expect(after.workspace).toBe(first.workspace);
    expect(after.model).toBe(first.model + 1);
    expect(after.policy).toBe(first.policy + 1);
    // Only the selected tab is visible.
    expect(screen.getByRole("region", { name: "Applications" })).toBeVisible();
    expect(screen.queryByRole("region", { name: "Activity" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Activity", hidden: true })).not.toBeVisible();
  });

  it("shows the last known workspace at once when the page is opened again", async () => {
    const first = render(<Stateful start={{ ...LIST, workspaceKey: "retail" }} />);
    await screen.findByRole("heading", { level: 1, name: "Retail" });
    first.unmount();
    const never = new Promise<never>(() => undefined);
    vi.mocked(api.capabilities).mockReturnValue(never);
    vi.mocked(api.workspaceRuntimeState).mockReturnValue(never);
    vi.mocked(api.workspace).mockReturnValue(never);
    render(<Stateful start={{ ...LIST, workspaceKey: "retail" }} />);
    expect(screen.getByRole("heading", { level: 1, name: "Retail" })).toBeInTheDocument();
    expect(screen.queryByText("Loading workspace…")).not.toBeInTheDocument();
  });

  it("starts reading the workspace while the capabilities and runtime state are still loading", async () => {
    let release: (value: ReturnType<typeof capabilities>) => void = () => undefined;
    vi.mocked(api.capabilities).mockReturnValue(new Promise((resolve) => (release = resolve)));
    render(<Stateful start={{ ...LIST, workspaceKey: "retail" }} />);
    await waitFor(() => expect(api.workspace).toHaveBeenCalledWith("retail"));
    expect(screen.queryByRole("heading", { level: 1, name: "Retail" })).not.toBeInTheDocument();
    await act(async () => release(capabilities(true)));
    expect(await screen.findByRole("heading", { level: 1, name: "Retail" })).toBeInTheDocument();
    // One read serves the early start and the page that then mounts.
    expect(vi.mocked(api.workspace).mock.calls.filter(([key]) => key === "retail")).toHaveLength(1);
  });

  describe("a workspace the engine cannot serve (0.12 UW1)", () => {
    const stuck: WorkspaceDetail = {
      ...retail,
      availability: {
        state: "unavailable",
        reason: "schemaLeftWindow",
        releaseId: "release-old",
        schemaVersion: "0.8",
        supportedSchemaVersions: ["0.10"],
        raisable: true,
      },
    };

    it("marks it in the list with a badge that has text", async () => {
      byKey.set("retail", stuck);
      vi.mocked(api.workspaces).mockImplementation(async (options = {}) => ({
        items: options.status === "retired" ? [] : [stuck, primary],
        nextCursor: null,
      }));
      renderAdmin();
      const active = await screen.findByRole("region", { name: "Active" });
      expect(await within(active).findByRole("button", { name: /Retail.*Cannot be opened/ })).toBeInTheDocument();
      expect(within(active).getByRole("button", { name: /Default/ })).not.toHaveTextContent("Cannot be opened");
    });

    it("puts the banner at the top of its Overview", async () => {
      byKey.set("retail", stuck);
      renderAdmin("retail");
      expect(await screen.findByText("Retail cannot be opened")).toBeInTheDocument();
      expect(await screen.findByRole("button", { name: "Review the change…" })).toBeInTheDocument();
    });

    it("shows no banner on a workspace that is served", async () => {
      renderAdmin("retail");
      expect(await screen.findByRole("heading", { level: 1, name: "Retail" })).toBeInTheDocument();
      expect(screen.queryByText("Retail cannot be opened")).not.toBeInTheDocument();
    });
  });
});
