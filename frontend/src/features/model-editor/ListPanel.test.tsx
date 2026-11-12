import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ListPanel } from "@/features/model-editor/ListPanel";
import { outlineFixture } from "@/test/draftOutline";
import type { ProfileSource, SourceBlock } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const outline = outlineFixture();
const block: SourceBlock = {
  index: 0,
  range: "A1:B4",
  firstColumn: "A",
  lastColumn: "B",
  headerRow: 1,
  lastRow: 4,
  rows: 3,
};
const source: ProfileSource = {
  id: "items",
  sheet: "Lists",
  headerRow: 1,
  applicationKey: null,
  objectTypeKey: outline.objectTypes[0]!.key,
  key: { field: "name" },
  columns: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.sourceCells).mockResolvedValue({ items: [], nextCursor: null } as never);
});

function show(onSetMissing?: (operations: unknown[]) => void) {
  render(
    <ListPanel
      sheet="Lists"
      block={block}
      header="Items"
      fileId="f1"
      listSource={source}
      status="loaded"
      outline={outline}
      busy={false}
      onAdjust={vi.fn()}
      onDrop={vi.fn()}
      onLoad={vi.fn()}
      onShowType={vi.fn()}
      onSetMissing={onSetMissing}
    />,
  );
}

describe("the list's panel and what a load does with the records no row names (PP-D82)", () => {
  it("changes the choice where it stands, as one setMissing step", () => {
    const onSetMissing = vi.fn();
    show(onSetMissing);
    fireEvent.click(screen.getByRole("radio", { name: "Delete them" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete them on load" }));
    expect(onSetMissing).toHaveBeenCalledWith([{ kind: "setMissing", source: "items", missing: "delete" }]);
  });

  it("shows no choice to a page that cannot send it", () => {
    show();
    expect(screen.queryByRole("radio", { name: "Delete them" })).toBeNull();
  });
});
