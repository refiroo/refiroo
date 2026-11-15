import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { MovesPage } from "@/features/moves/MovesPage";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});
const holds = vi.hoisted(() => ({ copyMove: true }));
vi.mock("@/state/useMe", () => ({ useHoldsGroup: () => holds.copyMove }));
vi.mock("@/state/useSystem", () => ({
  useCapabilities: () => ({
    capabilities: {
      integrationJobs: { createJobs: true, setting: "JOBS" },
      modelAdmin: { activate: true, setting: "ADMIN" },
    },
  }),
}));

const mapping = {
  key: "shop-to-store",
  name: "Shop to store",
  sourceModelKey: "shop",
  targetModelKey: "store",
  sourceReleaseId: "r1",
  targetReleaseId: "r2",
  version: 3,
  updatedAt: "2026-11-01T10:00:00Z",
};

beforeEach(() => {
  vi.clearAllMocks();
  holds.copyMove = true;
  vi.mocked(api.modelMappings).mockResolvedValue({ items: [mapping], nextCursor: null } as never);
  vi.mocked(api.moveJobs).mockResolvedValue({ items: [], nextCursor: null } as never);
  vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null } as never);
});

describe("deleting a mapping (0.13 ED)", () => {
  it("asks first, in its own words, then deletes at the mapping's version and takes it from the list", async () => {
    vi.mocked(api.deleteModelMapping).mockResolvedValue(undefined);
    render(<MovesPage onNavigate={vi.fn()} />);
    fireEvent.click(await screen.findByRole("button", { name: "Delete…" }));
    const dialog = await screen.findByRole("alertdialog", { name: "Delete the mapping Shop to store?" });
    expect(within(dialog).getByText(/deleted with its history and proposals/)).toBeTruthy();
    expect(api.deleteModelMapping).not.toHaveBeenCalled();
    fireEvent.click(within(dialog).getByRole("button", { name: "Delete the mapping" }));
    await waitFor(() => expect(api.deleteModelMapping).toHaveBeenCalledWith("shop-to-store", 3));
    await waitFor(() => expect(screen.queryByText("Shop to store")).toBeNull());
  });

  it("is not offered to a person who may not copy and move", async () => {
    holds.copyMove = false;
    render(<MovesPage onNavigate={vi.fn()} />);
    expect(await screen.findByText("Shop to store")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Delete…" })).toBeNull();
  });
});
