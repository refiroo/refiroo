import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WorkspaceSelector } from "@/features/workspaces/WorkspaceSelector";

describe("WorkspaceSelector", () => {
  it("preserves Base 0.5 custom-key submission until WP2 supplies a catalogue", () => {
    const onChange = vi.fn();
    render(<WorkspaceSelector workspaceKey="default" onChange={onChange} />);

    fireEvent.change(screen.getByRole("combobox", { name: "Workspace" }), { target: { value: "central-europe" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(onChange).toHaveBeenCalledWith("central-europe");
  });

  it("synchronizes the displayed key when route context changes", () => {
    const { rerender } = render(<WorkspaceSelector workspaceKey="default" onChange={vi.fn()} />);
    rerender(<WorkspaceSelector workspaceKey="archive" onChange={vi.fn()} />);
    expect(screen.getByRole("combobox", { name: "Workspace" })).toHaveValue("archive");
  });
});
