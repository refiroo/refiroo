import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";
import { testWorkspaceModel, testAvailability } from "@/test/fixtures";

vi.mock("@/api/client", () => ({
  api: { workspace: vi.fn(), workspaces: vi.fn() },
}));

const defaultWorkspace = {
  key: "default",
  label: "Default workspace",
  status: "active" as const,
  version: 1,
  createdAt: "2026-09-05T00:00:00Z",
  updatedAt: "2026-09-05T00:00:00Z",
  model: testWorkspaceModel,
  availability: testAvailability,
  deletable: false,
};

describe("WorkspaceSelector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.workspace).mockResolvedValue(defaultWorkspace);
    vi.mocked(api.workspaces).mockResolvedValue({
      items: [defaultWorkspace, { ...defaultWorkspace, key: "central-europe", label: "Central Europe" }],
      nextCursor: null,
    });
  });

  it("selects a catalogue result while retaining its stable key", async () => {
    const onChange = vi.fn();
    render(<WorkspaceSelector workspaceKey="default" onChange={onChange} />);

    expect(await screen.findByRole("combobox", { name: "Workspace" })).toHaveValue("Default workspace");
    fireEvent.change(screen.getByRole("combobox", { name: "Workspace" }), { target: { value: "central-europe" } });
    await waitFor(() =>
      expect(api.workspaces).toHaveBeenLastCalledWith({
        search: "central-europe",
        // Retired workspaces are opened from Settings › Workspaces, not chosen here (the user, 2026-10-19).
        status: "active",
        pageSize: 50,
        // Only the workspaces the person may browse are offered (0.12 Z5, D327).
        holding: "browse",
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: /Show workspace options/ }));
    fireEvent.click(await screen.findByRole("option", { name: /Central Europe/ }));

    expect(onChange).toHaveBeenCalledWith("central-europe");
  });

  it("keeps the label visible when the current workspace is selected again", async () => {
    const onChange = vi.fn();
    render(<WorkspaceSelector workspaceKey="default" onChange={onChange} />);

    const selector = await screen.findByRole("combobox", { name: "Workspace" });
    fireEvent.click(screen.getByRole("button", { name: /Show workspace options/ }));
    fireEvent.click(await screen.findByRole("option", { name: /Default workspace/ }));

    expect(selector).toHaveValue("Default workspace");
    expect(onChange).not.toHaveBeenCalled();
  });

  it("labels retired route context as read only", async () => {
    vi.mocked(api.workspace).mockResolvedValue({
      ...defaultWorkspace,
      key: "archive",
      label: "Archive",
      status: "retired",
    });
    const { rerender } = render(<WorkspaceSelector workspaceKey="default" onChange={vi.fn()} />);
    rerender(<WorkspaceSelector workspaceKey="archive" onChange={vi.fn()} />);
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Workspace" })).toHaveValue("Archive"));
    expect(screen.getByText("Starter model 0.3.0 · Retired · read only")).toBeInTheDocument();
  });

  it("offers workspace administration at the end of the options when the deployment allows it", async () => {
    const onChange = vi.fn();
    const onManage = vi.fn();
    render(<WorkspaceSelector workspaceKey="default" onChange={onChange} onManage={onManage} />);

    const selector = await screen.findByRole("combobox", { name: "Workspace" });
    await waitFor(() => expect(api.workspaces).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: /Show workspace options/ }));
    const options = await screen.findAllByRole("option");
    expect(options.at(-1)).toHaveTextContent("Manage workspaces");
    fireEvent.click(options.at(-1)!);

    expect(onManage).toHaveBeenCalledTimes(1);
    expect(onChange).not.toHaveBeenCalled();
    expect(selector).toHaveValue("Default workspace");
    // When navigation is refused (an unsaved editor), the selector stays on the current workspace.
    fireEvent.blur(selector);
    await waitFor(() => expect(selector).toHaveValue("Default workspace"));
  });

  it("does not offer workspace administration without the capability", async () => {
    render(<WorkspaceSelector workspaceKey="default" onChange={vi.fn()} />);
    await screen.findByRole("combobox", { name: "Workspace" });
    fireEvent.click(screen.getByRole("button", { name: /Show workspace options/ }));
    await screen.findAllByRole("option");
    expect(screen.queryByRole("option", { name: /Manage workspaces/ })).not.toBeInTheDocument();
  });

  it("shows the only workspace as a read-only label with the administration link", async () => {
    vi.mocked(api.workspaces).mockResolvedValue({ items: [defaultWorkspace], nextCursor: null });
    const onManage = vi.fn();
    render(<WorkspaceSelector workspaceKey="default" onChange={vi.fn()} onManage={onManage} />);

    const group = await screen.findByRole("group", { name: "Workspace" });
    expect(group).toHaveTextContent("Default workspace");
    expect(screen.queryByRole("combobox", { name: "Workspace" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Manage workspaces" }));
    expect(onManage).toHaveBeenCalledTimes(1);
  });

  it("keeps the selector while a search narrows a larger catalogue to one result", async () => {
    render(<WorkspaceSelector workspaceKey="default" onChange={vi.fn()} />);
    const selector = await screen.findByRole("combobox", { name: "Workspace" });
    await waitFor(() => expect(api.workspaces).toHaveBeenCalled());
    vi.mocked(api.workspaces).mockResolvedValue({ items: [defaultWorkspace], nextCursor: null });
    fireEvent.change(selector, { target: { value: "defa" } });
    await waitFor(() => expect(api.workspaces).toHaveBeenLastCalledWith(expect.objectContaining({ search: "defa" })));
    expect(screen.getByRole("combobox", { name: "Workspace" })).toBeInTheDocument();
  });

  it("keeps an unknown-workspace error visible when catalogue search succeeds", async () => {
    vi.mocked(api.workspace).mockRejectedValue(new Error("Workspace 'missing' not found"));
    render(<WorkspaceSelector workspaceKey="missing" onChange={vi.fn()} />);

    expect(await screen.findByText("Workspace 'missing' not found")).toBeInTheDocument();
    await waitFor(() => expect(api.workspaces).toHaveBeenCalled());
    expect(screen.getByText("Workspace 'missing' not found")).toBeInTheDocument();
  });

  it("lists every workspace when opened before the current one has resolved (UA0)", async () => {
    let resolve: (workspace: typeof defaultWorkspace) => void = () => {};
    vi.mocked(api.workspace).mockReturnValue(new Promise((done) => (resolve = done)));
    render(<WorkspaceSelector workspaceKey="default" onChange={vi.fn()} />);
    await waitFor(() => expect(api.workspaces).toHaveBeenCalled());
    const show = screen.getByRole("button", { name: /Show workspace options/ });
    fireEvent.click(show);
    resolve(defaultWorkspace);
    expect(await screen.findByRole("combobox", { name: "Workspace" })).toHaveValue("Default workspace");
    if (!screen.queryByRole("listbox")) fireEvent.click(show);
    expect(await screen.findByRole("option", { name: /Central Europe/ })).toBeInTheDocument();
  });

  it("names each workspace's model and marks another model or release (0.11 D46)", async () => {
    const otherRelease = { ...testWorkspaceModel, releaseId: "next", releaseVersion: "2" };
    const otherModel = {
      ...testWorkspaceModel,
      releaseId: "x",
      releaseKey: "archive",
      releaseName: "Archive register",
    };
    vi.mocked(api.workspaces).mockResolvedValue({
      items: [
        defaultWorkspace,
        { ...defaultWorkspace, key: "south", label: "South", model: otherRelease },
        { ...defaultWorkspace, key: "archive", label: "Archive", model: otherModel },
        { ...defaultWorkspace, key: "twin", label: "Twin", model: testWorkspaceModel, availability: testAvailability },
      ],
      nextCursor: null,
    });
    render(<WorkspaceSelector workspaceKey="default" onChange={vi.fn()} />);

    await screen.findByRole("combobox", { name: "Workspace" });
    const runs = `${testWorkspaceModel.releaseName} ${testWorkspaceModel.releaseVersion}`;
    expect(screen.getByText(runs)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Show workspace options/ }));
    expect(await screen.findByRole("option", { name: /South.*Other release/ })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Archive.*Archive register.*Other model/ })).toBeInTheDocument();
    const twin = screen.getByRole("option", { name: /Twin/ });
    expect(twin).not.toHaveTextContent(/Other/);
  });
});
