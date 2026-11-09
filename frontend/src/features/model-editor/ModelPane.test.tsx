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
