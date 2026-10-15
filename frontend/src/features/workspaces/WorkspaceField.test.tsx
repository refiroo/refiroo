import { render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { WorkspaceField } from "@/features/workspaces/WorkspaceField";
import type { Workspace } from "@/types";
import { testWorkspaceModel } from "@/test/fixtures";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const workspace = (key: string): Workspace => ({
  key,
  label: key[0].toUpperCase() + key.slice(1),
  status: "active",
  version: 1,
  createdAt: "2026-10-15T00:00:00Z",
  updatedAt: "2026-10-15T00:00:00Z",
  model: testWorkspaceModel,
});

function Chooser({ withDefault }: { withDefault?: boolean }) {
  const [value, setValue] = useState("");
  return <WorkspaceField value={value} onChange={setValue} onError={() => {}} withDefault={withDefault} />;
}

describe("WorkspaceField (0.10 R: the export, import and load dialogs' workspace)", () => {
  it("offers the workspaces of every page and chooses the first when none is chosen", async () => {
    vi.mocked(api.workspaces).mockImplementation(
      async (options) =>
        (options?.cursor
          ? { items: [workspace("later")], nextCursor: null }
          : { items: [workspace("default")], nextCursor: "next" }) as never,
    );
    render(<Chooser />);
    const select = screen.getByRole("combobox", { name: "Workspace" });
    await waitFor(() => expect(select).toHaveValue("default"));
    expect(screen.getByRole("option", { name: "Later" })).toBeInTheDocument();
  });

  it("keeps the default workspace chosen where it is offered", async () => {
    vi.mocked(api.workspaces).mockResolvedValue({ items: [workspace("west")], nextCursor: null } as never);
    render(<Chooser withDefault />);
    await screen.findByRole("option", { name: "West" });
    expect(screen.getByRole("combobox", { name: "Workspace" })).toHaveValue("");
  });
});
