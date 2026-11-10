import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ModelPane } from "@/features/model-editor/ModelPane";
import { outlineFixture } from "@/test/draftOutline";
import type { EditorSelection } from "@/types";

/** The fixture's Shop, plus an Archive that lists Bin too, so Bin stands in two applications. */
function twoApplications() {
  const outline = outlineFixture();
  const shop = outline.applications[0]!;
  outline.applications.push({
    ...shop,
    key: "archive",
    name: "Archive",
    objectTypeKeys: ["bin"],
    tree: [{ objectType: "bin", children: [] }],
    navigation: { groups: [], ungrouped: ["bin"], opens: {} },
    views: [],
  });
  return outline;
}

function renderPane(selection: EditorSelection, onSelect = vi.fn()) {
  render(
    <ModelPane
      outline={twoApplications()}
      selection={selection}
      canDrag={false}
      onSelect={onSelect}
      onMenu={vi.fn()}
      onDrop={vi.fn()}
      proposed={new Set()}
    />,
  );
  return onSelect;
}

const binRows = () => screen.getAllByRole("treeitem").filter((row) => row.textContent?.includes("Bin"));

describe("ModelPane type rows", () => {
  it("puts the row's own application into the selection", () => {
    const onSelect = renderPane({});
    const archiveBin = binRows().at(-1)!;
    fireEvent.click(archiveBin);
    expect(onSelect).toHaveBeenCalledWith({ show: "type", key: "bin", application: "archive" });
  });

  it("marks only the row of the application the selection names", () => {
    renderPane({ show: "type", key: "bin", application: "archive" });
    const selected = binRows().filter((row) => row.getAttribute("aria-selected") === "true");
    expect(selected).toHaveLength(1);
    expect(binRows().at(-1)).toBe(selected[0]);
  });
});

/** Archive lists Bin (in a group), Shelf (in none) and Area (no view uses it) for Shop's records. */
function borrowing() {
  const outline = outlineFixture();
  const viaMatrix = (role: "rows" | "columns" | "cells") => ({
    view: "bins-by-shelf",
    viewName: "Bins by shelf",
    viewType: "relationMatrix",
    role,
    relationType: "stores",
    relationName: "Stores",
  });
  const shop = outline.applications[0]!;
  outline.applications.push({
    ...shop,
    key: "archive",
    name: "Archive",
    objectTypeKeys: ["bin", "shelf", "area"],
    tree: [
      { objectType: "area", children: [{ objectType: "shelf", children: [{ objectType: "bin", children: [] }] }] },
    ],
    ownTypes: [],
    ownTree: [],
    borrowed: [
      { objectType: "shelf", home: "shop", uses: [viaMatrix("columns")] },
      { objectType: "bin", home: "shop", uses: [viaMatrix("rows")] },
    ],
    borrowedTree: [
      { objectType: "shelf", children: [] },
      { objectType: "bin", children: [] },
    ],
    unused: ["area"],
    unlistable: ["area"],
    navigation: {
      groups: [
        {
          key: "lists",
          label: "Lists",
          collapsed: false,
          collections: ["bin"],
          entries: [{ collection: "bin" }],
          mark: "new",
        },
      ],
      ungrouped: ["shelf"],
      opens: {},
    },
    views: [],
  });
  return outline;
}

describe("ModelPane borrowed types", () => {
  const rowsOf = (application: string) =>
    screen
      .getAllByRole("treeitem")
      .filter((row) => new RegExp(`:${application}(:|$)`).test(row.getAttribute("data-row") ?? ""));

  function renderBorrowing(onSelect = vi.fn()) {
    render(
      <ModelPane
        outline={borrowing()}
        selection={{}}
        canDrag={false}
        onSelect={onSelect}
        onMenu={vi.fn()}
        onDrop={vi.fn()}
        proposed={new Set()}
      />,
    );
    return onSelect;
  }

  it("shows each type once in an application, a grouped one in its group only", () => {
    renderBorrowing();
    // Shop holds bin and lists it in a group: it stands in the group, not in the tree.
    const shop = rowsOf("shop");
    const bins = shop.filter((row) => row.textContent?.startsWith("Bin"));
    expect(bins).toHaveLength(1);
    expect(bins[0]!.getAttribute("data-row")).toMatch(/^collection:/);
    const archive = rowsOf("archive").map((row) => row.textContent ?? "");
    for (const name of ["Bin", "Shelf", "Area"])
      expect(archive.filter((text) => text.startsWith(name))).toHaveLength(1);
  });

  it("puts a held type of a group, with the types it contains, in the group and not in the tree", () => {
    const outline = borrowing();
    const group = outline.applications[0]!.navigation.groups[0]!;
    group.collections = ["area"];
    group.entries = [{ collection: "area" }];
    render(
      <ModelPane
        outline={outline}
        selection={{}}
        canDrag={false}
        onSelect={vi.fn()}
        onMenu={vi.fn()}
        onDrop={vi.fn()}
        proposed={new Set()}
      />,
    );
    const shop = rowsOf("shop");
    const labels = shop.map((row) => row.textContent ?? "");
    expect(labels.filter((text) => text.startsWith("Area"))).toHaveLength(1);
    expect(labels.filter((text) => text.startsWith("Shelf"))).toHaveLength(1);
    const ids = shop.map((row) => row.getAttribute("data-row") ?? "");
    const areaAt = ids.findIndex((id) => id.startsWith("collection:"));
    expect(shop[areaAt]!.getAttribute("aria-level")).toBe("3");
    expect(shop[areaAt + 1]!.textContent).toContain("Shelf");
    expect(shop[areaAt + 1]!.getAttribute("aria-level")).toBe("4");
    // Bin is no longer in the group, so it stands in the tree.
    expect(ids.filter((id) => id.startsWith("type:shop:"))).toHaveLength(1);
  });

  it("counts a group's entries in its note", () => {
    renderBorrowing();
    const group = rowsOf("archive").find((row) => row.getAttribute("data-row")?.startsWith("group:"))!;
    expect(group.textContent).toContain("group · 1");
  });

  it("says which view and relation bring a grouped borrowed type in, and where it is kept", () => {
    renderBorrowing();
    const bin = rowsOf("archive").find((row) => row.getAttribute("data-row")?.startsWith("collection:"))!;
    expect(bin.textContent).toContain("matrix");
    expect(bin.textContent).toContain("Bins by shelf · Stores · from Shop");
  });

  it("lists a borrowed type in no group under From other applications, with columns named as such", () => {
    renderBorrowing();
    const labels = rowsOf("archive").map((row) => row.textContent ?? "");
    const head = labels.findIndex((text) => text.startsWith("From other applications"));
    expect(labels[head]).toContain("1");
    expect(labels[head + 1]).toContain("columns of Bins by shelf · Stores · from Shop");
  });

  it("lists the types no view uses last, marking the ones that can be unlisted", () => {
    renderBorrowing();
    const labels = rowsOf("archive").map((row) => row.textContent ?? "");
    const head = labels.findIndex((text) => text.startsWith("Listed, used by no view here"));
    expect(labels[head + 1]).toContain("Area");
    expect(labels[head + 1]).toContain("can be unlisted");
  });

  it("gives a borrowed row the full text as its tooltip", () => {
    renderBorrowing();
    const bin = rowsOf("archive").find((row) => row.getAttribute("data-row")?.startsWith("collection:"))!;
    expect(bin.getAttribute("title")).toBe("Bin · matrix · Bins by shelf · Stores · from Shop");
  });

  it("opens a borrowed type on the application that keeps its records", () => {
    const onSelect = renderBorrowing();
    const bin = rowsOf("archive").find((row) => row.getAttribute("data-row")?.startsWith("collection:"))!;
    fireEvent.click(bin);
    expect(onSelect).toHaveBeenCalledWith({ show: "type", key: "bin", application: "shop" });
  });
});
