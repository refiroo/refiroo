import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import type { CapabilitiesResponse, Workspace } from "@/types";
import { WorkspaceAdmin } from "@/features/workspaces/WorkspaceAdmin";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const time = "2026-09-26T08:00:00Z";
const primary: Workspace = {
  key: "default",
  label: "Default",
  status: "active",
  version: 1,
  createdAt: time,
  updatedAt: time,
};
const retail: Workspace = {
  key: "retail",
  label: "Retail",
  status: "active",
  version: 3,
  createdAt: time,
  updatedAt: time,
};
const archive: Workspace = {
  key: "archive",
  label: "Archive",
  status: "retired",
  version: 2,
  createdAt: time,
  updatedAt: time,
};
const runtime = { defaultWorkspaceKey: "default", version: 4, updatedAt: time };

function capabilities(manageWorkspaces: boolean): CapabilitiesResponse {
  return {
    modelAdmin: {
      readReleases: true,
      manageDrafts: false,
      install: false,
      activate: false,
      setting: "MODEL_ADMIN_MUTATIONS_ENABLED",
    },
    workspaceAdmin: { manageWorkspaces, setting: "WORKSPACE_ADMIN_MUTATIONS_ENABLED" },
  };
}

function renderAdmin(selectedWorkspaceKey?: string, overrides: Partial<Parameters<typeof WorkspaceAdmin>[0]> = {}) {
  const props = {
    route: { kind: "workspaces" as const, ...(selectedWorkspaceKey ? { selectedWorkspaceKey } : {}) },
    onRouteChange: vi.fn(),
    onDefaultChanged: vi.fn(),
    onOpenWorkspace: vi.fn(),
    ...overrides,
  };
  return { ...render(<WorkspaceAdmin {...props} />), props };
}

const byKey = new Map([primary, retail, archive].map((item) => [item.key, item]));

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.capabilities).mockResolvedValue(capabilities(true));
  vi.mocked(api.workspaceRuntimeState).mockResolvedValue(runtime);
  vi.mocked(api.workspaces).mockResolvedValue({ items: [archive, primary, retail], nextCursor: null });
  vi.mocked(api.workspace).mockImplementation(async (key) => byKey.get(key)!);
});

describe("WorkspaceAdmin", () => {
  it("lists every workspace including retired ones and opens on the default", async () => {
    renderAdmin();
    const catalogue = await screen.findByRole("navigation", { name: "Workspace catalogue" });
    await within(catalogue).findByText("Retail");
    expect(api.workspaces).toHaveBeenCalledWith(expect.objectContaining({ status: "all" }));
    expect(within(catalogue).getByRole("button", { name: /Archive.*Retired/ })).toBeInTheDocument();
    expect(within(catalogue).getByRole("button", { name: /Default.*Default/ })).toHaveAttribute("aria-current", "page");
    expect(await screen.findByRole("heading", { level: 2, name: "Default" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retire…" })).toBeDisabled();
    expect(screen.getByText(/default workspace cannot be retired/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Set as default" })).not.toBeInTheDocument();
  });

  it("reports a failed catalogue read in place and retries it", async () => {
    vi.mocked(api.workspaces).mockRejectedValueOnce(new Error("Catalogue unavailable"));
    renderAdmin();
    const catalogue = await screen.findByRole("navigation", { name: "Workspace catalogue" });
    expect(await within(catalogue).findByText("Catalogue unavailable")).toBeInTheDocument();
    fireEvent.click(within(catalogue).getByRole("button", { name: "Retry" }));
    expect(await within(catalogue).findByText("Retail")).toBeInTheDocument();
  });

  it("reports a failed capability read above the page and retries it", async () => {
    vi.mocked(api.capabilities).mockRejectedValueOnce(new Error("Capabilities unavailable"));
    renderAdmin();
    expect(await screen.findByText("Capabilities unavailable")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 1, name: "Workspaces" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("region", { name: "Deployment capabilities" })).toBeInTheDocument();
    expect(screen.queryByText("Capabilities unavailable")).not.toBeInTheDocument();
  });

  it("keeps the catalogue read only and names the setting when administration is disabled", async () => {
    vi.mocked(api.capabilities).mockResolvedValue(capabilities(false));
    renderAdmin("retail");
    expect(await screen.findByRole("heading", { level: 2, name: "Retail" })).toBeInTheDocument();
    const status = screen.getByRole("region", { name: "Deployment capabilities" });
    expect(status).toHaveTextContent(/Workspace administration\s*Disabled/);
    expect(status).toHaveTextContent("WORKSPACE_ADMIN_MUTATIONS_ENABLED");
    expect(screen.queryByRole("button", { name: /New workspace/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rename…" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Set as default" })).not.toBeInTheDocument();
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
    fireEvent.click(within(dialog).getByRole("button", { name: "Create workspace" }));

    await waitFor(() =>
      expect(props.onRouteChange).toHaveBeenCalledWith({ kind: "workspaces", selectedWorkspaceKey: "central-europe" }),
    );
    expect(api.createWorkspace).toHaveBeenCalledWith({ key: "central-europe", label: "Central Europe" });
    expect(screen.queryByRole("dialog", { name: "New workspace" })).not.toBeInTheDocument();
    expect(api.workspaces).toHaveBeenCalledTimes(2);
  });

  it("keeps the dialog and its input when the key already exists", async () => {
    vi.mocked(api.createWorkspace).mockRejectedValue(
      new ApiError(409, "workspace_already_exists", "Workspace 'retail' already exists"),
    );
    renderAdmin();
    fireEvent.click(await screen.findByRole("button", { name: /New workspace/ }));
    const dialog = await screen.findByRole("dialog", { name: "New workspace" });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: "Retail" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Create workspace" }));
    expect(await within(dialog).findByText("Workspace 'retail' already exists")).toBeInTheDocument();
    expect(within(dialog).getByRole("textbox", { name: "Name" })).toHaveValue("Retail");
  });

  it("renames with the version it read and updates the catalogue", async () => {
    vi.mocked(api.updateWorkspace).mockResolvedValue({ ...retail, label: "Retail Europe", version: 4 });
    renderAdmin("retail");
    fireEvent.click(await screen.findByRole("button", { name: "Rename…" }));
    const dialog = await screen.findByRole("dialog", { name: "Rename workspace" });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: "Retail Europe" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save name" }));

    expect(await screen.findByRole("heading", { level: 2, name: "Retail Europe" })).toBeInTheDocument();
    expect(api.updateWorkspace).toHaveBeenCalledWith("retail", { expectedVersion: 3, label: "Retail Europe" });
    const catalogue = screen.getByRole("navigation", { name: "Workspace catalogue" });
    expect(within(catalogue).getByText("Retail Europe")).toBeInTheDocument();
    expect(screen.getByText("Workspace renamed.")).toBeInTheDocument();
  });

  it("shows a concurrent rename, keeps the user's name and saves again only on request", async () => {
    vi.mocked(api.updateWorkspace)
      .mockRejectedValueOnce(new ApiError(409, "version_conflict", "Workspace version has changed"))
      .mockResolvedValueOnce({ ...retail, label: "Mine", version: 5 });
    renderAdmin("retail");
    fireEvent.click(await screen.findByRole("button", { name: "Rename…" }));
    const dialog = await screen.findByRole("dialog", { name: "Rename workspace" });
    vi.mocked(api.workspace).mockResolvedValue({ ...retail, label: "Theirs", version: 4 });
    fireEvent.change(within(dialog).getByRole("textbox", { name: "Name" }), { target: { value: "Mine" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save name" }));

    expect(await within(dialog).findByText(/It is now named “Theirs”/)).toBeInTheDocument();
    expect(within(dialog).getByRole("textbox", { name: "Name" })).toHaveValue("Mine");
    expect(api.updateWorkspace).toHaveBeenCalledTimes(1);
    fireEvent.click(within(dialog).getByRole("button", { name: "Save name" }));
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
    fireEvent.click(await screen.findByRole("button", { name: "Set as default" }));

    expect(await screen.findByText("Retail is now the default workspace.")).toBeInTheDocument();
    expect(api.setDefaultWorkspace).toHaveBeenCalledWith("retail", 4);
    expect(props.onDefaultChanged).toHaveBeenCalledWith("retail");
    expect(screen.queryByRole("button", { name: "Set as default" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retire…" })).toBeDisabled();
    const catalogue = screen.getByRole("navigation", { name: "Workspace catalogue" });
    expect(within(catalogue).getByRole("button", { name: /Retail.*Default/ })).toBeInTheDocument();
  });

  it("names the new default after a concurrent default switch instead of retrying", async () => {
    vi.mocked(api.setDefaultWorkspace).mockRejectedValue(
      new ApiError(409, "version_conflict", "Workspace runtime-state version has changed"),
    );
    renderAdmin("retail");
    await screen.findByRole("button", { name: "Set as default" });
    vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
      defaultWorkspaceKey: "archive",
      version: 6,
      updatedAt: time,
    });
    fireEvent.click(screen.getByRole("button", { name: "Set as default" }));

    expect(await screen.findByText(/default workspace changed to “archive”/)).toBeInTheDocument();
    expect(api.setDefaultWorkspace).toHaveBeenCalledTimes(1);
  });

  it("retires after confirmation and offers reactivation", async () => {
    vi.mocked(api.updateWorkspace).mockResolvedValue({ ...retail, status: "retired", version: 4 });
    renderAdmin("retail");
    fireEvent.click(await screen.findByRole("button", { name: "Retire…" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Retire Retail?" });
    expect(within(confirm).getByText(/can be reactivated later/)).toBeInTheDocument();
    fireEvent.click(within(confirm).getByRole("button", { name: "Retire workspace" }));

    expect(await screen.findByText(/Workspace retired/)).toBeInTheDocument();
    expect(api.updateWorkspace).toHaveBeenCalledWith("retail", { expectedVersion: 3, status: "retired" });
    expect(screen.getByRole("button", { name: "Reactivate" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Set as default" })).not.toBeInTheDocument();
  });

  it("reports a refused retirement inside the confirmation", async () => {
    vi.mocked(api.updateWorkspace).mockRejectedValue(
      new ApiError(409, "default_workspace_cannot_be_retired", "The default workspace cannot be retired"),
    );
    renderAdmin("retail");
    fireEvent.click(await screen.findByRole("button", { name: "Retire…" }));
    const confirm = await screen.findByRole("alertdialog", { name: "Retire Retail?" });
    fireEvent.click(within(confirm).getByRole("button", { name: "Retire workspace" }));
    expect(await within(confirm).findByText("The default workspace cannot be retired")).toBeInTheDocument();
    expect(api.workspaceRuntimeState).toHaveBeenCalledTimes(2);
  });

  it("reactivates a retired workspace", async () => {
    vi.mocked(api.updateWorkspace).mockResolvedValue({ ...archive, status: "active", version: 3 });
    renderAdmin("archive");
    expect(await screen.findByText("Retired · read only")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Reactivate" }));
    expect(await screen.findByText("Workspace reactivated.")).toBeInTheDocument();
    expect(api.updateWorkspace).toHaveBeenCalledWith("archive", { expectedVersion: 2, status: "active" });
  });

  it("opens the selected workspace", async () => {
    const { props } = renderAdmin("retail");
    fireEvent.click(await screen.findByRole("button", { name: "Open workspace" }));
    expect(props.onOpenWorkspace).toHaveBeenCalledWith("retail");
  });

  it("reports an unknown workspace in the detail and retries the read", async () => {
    vi.mocked(api.workspace).mockRejectedValueOnce(
      new ApiError(404, "workspace_not_found", "Workspace 'gone' not found"),
    );
    renderAdmin("gone");
    expect(await screen.findByText("Workspace 'gone' not found")).toBeInTheDocument();
    vi.mocked(api.workspace).mockResolvedValue({ ...retail, key: "gone", label: "Gone after all" });
    fireEvent.click(within(screen.getByRole("alert")).getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { level: 2, name: "Gone after all" })).toBeInTheDocument();
  });
});
