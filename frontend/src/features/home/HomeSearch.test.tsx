import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { HomeSearch } from "@/features/home/HomeSearch";
import { testModel } from "@/test/fixtures";
import type { ObjectItem, OwnWorkspace } from "@/types";

const openIn = vi.fn();
vi.mock("@/features/home/openWorkspace", () => ({
  openIn: (...args: unknown[]) => openIn(...args),
}));
vi.mock("@/model/workspaceModels", () => ({
  loadedWorkspaceModel: () => undefined,
  workspaceModel: () => Promise.resolve(testModel),
}));

const workspace = (key: string, label: string) => ({ key, label }) as OwnWorkspace;
const workspaces = [workspace("stops", "STOPS Reference Data"), workspace("timetables", "Timetables")];

const record = (id: string, name: string, workspaceKey: string): ObjectItem =>
  ({
    id,
    name,
    objectTypeKey: "domain",
    applicationKey: "test-app",
    workspaceKey,
    parentObjectId: null,
    path: [{ id, name, objectTypeKey: "domain" }],
    attributes: [],
    version: 1,
    createdAt: null,
    updatedAt: null,
  }) as ObjectItem;

const found = [
  record("a1", "Station alpha", "stops"),
  record("a2", "Station beta", "stops"),
  record("b1", "Station gamma", "timetables"),
];

async function typeStation() {
  const box = screen.getByRole("combobox", { name: "Find a record in any workspace" });
  fireEvent.change(box, { target: { value: "station" } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(300);
  });
  return box;
}

describe("HomeSearch (0.17 UX1)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    openIn.mockReset();
    vi.spyOn(api, "findRecordsAcross").mockResolvedValue({ items: found, nextCursor: null } as never);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("asks every workspace and groups the results by workspace label", async () => {
    render(<HomeSearch workspaces={workspaces} onNavigate={vi.fn()} />);
    await typeStation();
    expect(api.findRecordsAcross).toHaveBeenCalledWith(["stops", "timetables"], "station");
    const results = within(screen.getByRole("listbox"));
    expect(results.getByText("STOPS Reference Data")).toBeInTheDocument();
    expect(results.getByText("Timetables")).toBeInTheDocument();
    expect(results.getAllByRole("option").map((option) => option.getAttribute("aria-label"))).toEqual([
      "Station alpha, STOPS Reference Data",
      "Station beta, STOPS Reference Data",
      "Station gamma, Timetables",
    ]);
    expect(screen.getByRole("status")).toHaveTextContent("3 records found");
  });

  it("opens the record marked with Down through openIn, and the first one when none is marked", async () => {
    const onNavigate = vi.fn();
    render(<HomeSearch workspaces={workspaces} onNavigate={onNavigate} />);
    const box = await typeStation();
    fireEvent.keyDown(box, { key: "ArrowDown" });
    fireEvent.keyDown(box, { key: "ArrowDown" });
    fireEvent.keyDown(box, { key: "ArrowDown" });
    expect(box).toHaveAttribute("aria-activedescendant", screen.getAllByRole("option")[2].id);
    fireEvent.keyDown(box, { key: "Enter" });
    expect(openIn).toHaveBeenCalledTimes(1);
    const [workspaceKey, path, navigate, route] = openIn.mock.calls[0];
    expect(workspaceKey).toBe("timetables");
    expect(path).toContain("/apps/test-app/objects/domain/b1");
    expect(path).toContain("workspaceKey=timetables");
    expect(navigate).toBe(onNavigate);
    expect(route(testModel)).toEqual({
      kind: "detail",
      applicationKey: "test-app",
      objectTypeKey: "domain",
      objectId: "b1",
      workspaceKey: "timetables",
    });

    openIn.mockClear();
    fireEvent.change(box, { target: { value: "station " } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });
    fireEvent.keyDown(box, { key: "Enter" });
    expect(openIn.mock.calls[0][0]).toBe("stops");
  });

  it("opens a record on a click", async () => {
    render(<HomeSearch workspaces={workspaces} onNavigate={vi.fn()} />);
    await typeStation();
    fireEvent.click(screen.getByRole("option", { name: "Station beta, STOPS Reference Data" }));
    expect(openIn.mock.calls[0][1]).toContain("/a2?");
  });

  it("puts the caret in the box on Ctrl+K", () => {
    render(<HomeSearch workspaces={workspaces} onNavigate={vi.fn()} />);
    const box = screen.getByRole("combobox", { name: "Find a record in any workspace" });
    expect(box).not.toHaveFocus();
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(box).toHaveFocus();
  });

  it("says so when no record matches", async () => {
    vi.spyOn(api, "findRecordsAcross").mockResolvedValue({ items: [], nextCursor: null } as never);
    render(<HomeSearch workspaces={workspaces} onNavigate={vi.fn()} />);
    await typeStation();
    expect(screen.getByText("No record’s name contains “station” in your workspaces.")).toBeInTheDocument();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });
});
