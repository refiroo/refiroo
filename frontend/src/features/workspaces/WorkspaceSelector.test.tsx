import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";

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
        status: "all",
        pageSize: 50,
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
    expect(screen.getByText("Retired · read only")).toBeInTheDocument();
  });

  it("keeps an unknown-workspace error visible when catalogue search succeeds", async () => {
    vi.mocked(api.workspace).mockRejectedValue(new Error("Workspace 'missing' not found"));
    render(<WorkspaceSelector workspaceKey="missing" onChange={vi.fn()} />);

    expect(await screen.findByText("Workspace 'missing' not found")).toBeInTheDocument();
    await waitFor(() => expect(api.workspaces).toHaveBeenCalled());
    expect(screen.getByText("Workspace 'missing' not found")).toBeInTheDocument();
  });
});
