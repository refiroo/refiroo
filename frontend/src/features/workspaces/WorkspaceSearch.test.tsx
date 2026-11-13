import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { WorkspaceSearch, groupByType } from "@/features/workspaces/WorkspaceSearch";
import { testModel } from "@/test/fixtures";
import type { ObjectItem } from "@/types";

const record = (id: string, name: string, objectTypeKey: string, path: ObjectItem["path"] = []): ObjectItem =>
  ({
    id,
    name,
    objectTypeKey,
    applicationKey: "test-app",
    workspaceKey: "stops",
    parentObjectId: null,
    path: [...path, { id, name, objectTypeKey }],
    attributes: [],
    version: 1,
    createdAt: null,
    updatedAt: null,
  }) as ObjectItem;

const found = [
  record("d1", "Connections hub", "domain"),
  record("c1", "Hub codes", "codelist", [{ id: "d1", name: "Connections hub", objectTypeKey: "domain" }]),
  record("c2", "Tariff hub", "codelist"),
];

async function typeHub() {
  const box = screen.getByRole("combobox", { name: "Find a record" });
  fireEvent.change(box, { target: { value: "hub" } });
  await act(async () => {
    await vi.advanceTimersByTimeAsync(250);
  });
  return box;
}

describe("WorkspaceSearch (0.17 SH1)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.spyOn(api, "findRecords").mockResolvedValue({ items: found, nextCursor: null });
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("focuses the bar's input on Ctrl+K and leaves the page variant alone", () => {
    const bar = render(<WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={vi.fn()} />);
    const box = screen.getByRole("combobox", { name: "Find a record" });
    expect(box).not.toHaveFocus();
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(box).toHaveFocus();
    bar.unmount();
    render(<WorkspaceSearch workspaceKey="stops" model={testModel} variant="page" onOpen={vi.fn()} />);
    const pageBox = screen.getByRole("combobox", { name: "Find a record" });
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(pageBox).not.toHaveFocus();
  });

  it("searches every type of the workspace and groups what it finds by type, with where each stands", async () => {
    render(<WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={vi.fn()} />);
    await typeHub();
    expect(api.findRecords).toHaveBeenCalledWith("stops", "hub");
    const results = within(screen.getByRole("listbox"));
    expect(results.getAllByRole("option")).toHaveLength(3);
    expect(screen.getByText("Domains")).toBeInTheDocument();
    expect(screen.getByText("Codelists")).toBeInTheDocument();
    const second = results.getByRole("option", { name: "Hub codes, Codelists" });
    expect(second).toHaveTextContent("Test App · Connections hub");
    expect(screen.getByRole("status")).toHaveTextContent("3 records found");
  });

  it("walks the results with the arrow keys and opens the marked record with Enter", async () => {
    const onOpen = vi.fn();
    render(<WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={onOpen} />);
    const box = await typeHub();
    fireEvent.keyDown(box, { key: "ArrowDown" });
    fireEvent.keyDown(box, { key: "ArrowDown" });
    expect(box).toHaveAttribute("aria-activedescendant", screen.getAllByRole("option")[1].id);
    fireEvent.keyDown(box, { key: "Enter" });
    expect(onOpen).toHaveBeenCalledWith(found[1]);
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("opens the first record with Enter when none is marked, and closes the list with Escape", async () => {
    const onOpen = vi.fn();
    render(<WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={onOpen} />);
    const box = await typeHub();
    fireEvent.keyDown(box, { key: "Escape" });
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    fireEvent.change(box, { target: { value: "hub " } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(250);
    });
    fireEvent.keyDown(box, { key: "Enter" });
    expect(onOpen).toHaveBeenCalledWith(found[0]);
  });

  it("opens a record on a click", async () => {
    const onOpen = vi.fn();
    render(<WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={onOpen} variant="page" />);
    await typeHub();
    fireEvent.click(screen.getByRole("option", { name: "Tariff hub, Codelists" }));
    expect(onOpen).toHaveBeenCalledWith(found[2]);
  });

  it("says when no record's name matches", async () => {
    vi.spyOn(api, "findRecords").mockResolvedValue({ items: [], nextCursor: null });
    render(<WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={vi.fn()} />);
    await typeHub();
    expect(screen.getByText("No record’s name contains “hub”.")).toBeInTheDocument();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("groups consecutive records of one type", () => {
    expect(groupByType(testModel, found).map((group) => [group.name, group.items.length])).toEqual([
      ["Domains", 1],
      ["Codelists", 2],
    ]);
  });
  describe("finding lists by name (0.17 UX1)", () => {
    async function typeText(text: string) {
      const box = screen.getByRole("combobox", { name: "Find a record" });
      fireEvent.change(box, { target: { value: text } });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(250);
      });
      return box;
    }

    it("shows a typed list name under Lists and opens the list on a click", async () => {
      vi.spyOn(api, "findRecords").mockResolvedValue({ items: [], nextCursor: null });
      const onOpenList = vi.fn();
      render(<WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={vi.fn()} onOpenList={onOpenList} />);
      await typeText("dom");
      const lists = within(screen.getByRole("group", { name: "Lists" }));
      expect(lists.getByText("Domains")).toBeInTheDocument();
      expect(lists.getByText("Test App")).toBeInTheDocument();
      fireEvent.click(lists.getByRole("button", { name: /Domains/ }));
      expect(onOpenList).toHaveBeenCalledWith(
        expect.objectContaining({ applicationKey: "test-app", viewKey: "domains" }),
      );
      expect(screen.queryByRole("group", { name: "Lists" })).not.toBeInTheDocument();
    });

    it("opens the first list with Enter when no record matches, and the record when one does", async () => {
      vi.spyOn(api, "findRecords").mockResolvedValue({ items: [], nextCursor: null });
      const onOpen = vi.fn();
      const onOpenList = vi.fn();
      const first = render(
        <WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={onOpen} onOpenList={onOpenList} />,
      );
      const box = await typeText("dom");
      fireEvent.keyDown(box, { key: "Enter" });
      expect(onOpenList).toHaveBeenCalledWith(
        expect.objectContaining({ applicationKey: "test-app", viewKey: "domains" }),
      );
      expect(onOpen).not.toHaveBeenCalled();
      first.unmount();
      vi.spyOn(api, "findRecords").mockResolvedValue({ items: found, nextCursor: null });
      onOpenList.mockClear();
      render(<WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={onOpen} onOpenList={onOpenList} />);
      fireEvent.keyDown(await typeText("dom"), { key: "Enter" });
      expect(onOpen).toHaveBeenCalledWith(found[0]);
      expect(onOpenList).not.toHaveBeenCalled();
    });

    it("shows no list without onOpenList", async () => {
      vi.spyOn(api, "findRecords").mockResolvedValue({ items: [], nextCursor: null });
      render(<WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={vi.fn()} />);
      await typeText("dom");
      expect(screen.queryByRole("group", { name: "Lists" })).not.toBeInTheDocument();
    });
  });

  describe("going to places (0.17 UX1)", () => {
    const places = (onOpen: () => void) => [{ label: "Change sets", hint: "Review and approve", onOpen }];
    async function typeText(text: string) {
      const box = screen.getByRole("combobox", { name: "Find a record" });
      fireEvent.change(box, { target: { value: text } });
      await act(async () => {
        await vi.advanceTimersByTimeAsync(250);
      });
      return box;
    }

    it("shows a typed place name under Go to and opens it on a click", async () => {
      vi.spyOn(api, "findRecords").mockResolvedValue({ items: [], nextCursor: null });
      const onOpenPlace = vi.fn();
      render(
        <WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={vi.fn()} destinations={places(onOpenPlace)} />,
      );
      await typeText("change");
      const group = within(screen.getByRole("group", { name: "Go to" }));
      expect(group.getByText("Review and approve")).toBeInTheDocument();
      fireEvent.click(group.getByRole("button", { name: /Change sets/ }));
      expect(onOpenPlace).toHaveBeenCalledTimes(1);
      expect(screen.queryByRole("group", { name: "Go to" })).not.toBeInTheDocument();
    });

    it("opens the first place with Enter when no record and no list match", async () => {
      vi.spyOn(api, "findRecords").mockResolvedValue({ items: [], nextCursor: null });
      const onOpen = vi.fn();
      const onOpenPlace = vi.fn();
      render(
        <WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={onOpen} destinations={places(onOpenPlace)} />,
      );
      fireEvent.keyDown(await typeText("change"), { key: "Enter" });
      expect(onOpenPlace).toHaveBeenCalledTimes(1);
      expect(onOpen).not.toHaveBeenCalled();
    });

    it("shows no place that the typed text does not name", async () => {
      vi.spyOn(api, "findRecords").mockResolvedValue({ items: [], nextCursor: null });
      render(
        <WorkspaceSearch workspaceKey="stops" model={testModel} onOpen={vi.fn()} destinations={places(vi.fn())} />,
      );
      await typeText("zzz");
      expect(screen.queryByRole("group", { name: "Go to" })).not.toBeInTheDocument();
    });
  });
});
