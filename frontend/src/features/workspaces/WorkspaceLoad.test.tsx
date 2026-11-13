import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { forgetWorkspaceLoad, rememberWorkspaceLoad } from "@/features/workspaces/fromWorkbook";
import { WorkspaceLoad } from "@/features/workspaces/WorkspaceLoad";
import type { Job } from "@/types";

vi.mock("@/state/useJobStream", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/state/useJobStream")>()),
  useJobStream: () => undefined,
}));

const done = (rejected: number) =>
  ({
    id: "j1",
    state: "completed",
    progress: { total: 12, processed: 12 },
    counts: { created: 10, updated: 0, unchanged: 0, rejected },
  }) as unknown as Job;

describe("WorkspaceLoad", () => {
  beforeEach(() => {
    forgetWorkspaceLoad("new-one");
    vi.restoreAllMocks();
  });

  it("shows nothing for a workspace no sheet made", () => {
    const { container } = render(<WorkspaceLoad workspaceKey="new-one" onNavigate={vi.fn()} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("says what loaded and what did not, and opens the job's rows", async () => {
    vi.spyOn(api, "job").mockResolvedValue(done(2));
    rememberWorkspaceLoad("new-one", "j1", "office.xlsx");
    const onNavigate = vi.fn();
    render(<WorkspaceLoad workspaceKey="new-one" onNavigate={onNavigate} />);
    expect(await screen.findByText("office.xlsx is loaded")).toBeInTheDocument();
    expect(screen.getByText(/10 created, 0 updated, 0 unchanged; 2 rows did not load\./)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "See the rows" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "jobs", jobId: "j1" });
    fireEvent.click(screen.getByRole("button", { name: "Dismiss" }));
    expect(screen.queryByText("office.xlsx is loaded")).not.toBeInTheDocument();
  });

  it("says that every row loaded", async () => {
    vi.spyOn(api, "job").mockResolvedValue(done(0));
    rememberWorkspaceLoad("new-one", "j1", "office.xlsx");
    render(<WorkspaceLoad workspaceKey="new-one" onNavigate={vi.fn()} />);
    expect(await screen.findByText(/every row loaded/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "See the rows" })).not.toBeInTheDocument();
  });
});
