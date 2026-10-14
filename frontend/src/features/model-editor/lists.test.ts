import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import type { DraftProfileDocument, ProfileSource, SourceBlock } from "@/types";
import {
  adjustOperations,
  columnLetter,
  columnNumber,
  dropOperations,
  listStatus,
  rectangleOf,
  sourceOfList,
} from "@/features/model-editor/lists";

const outline = outlineFixture();
const type = outline.objectTypes[0].key;

function block(index: number, range: [string, number, string, number]): SourceBlock {
  const [first, top, last, bottom] = range;
  return {
    index,
    range: `${first}${top}:${last}${bottom}`,
    firstColumn: first,
    lastColumn: last,
    headerRow: top,
    lastRow: bottom,
    rows: bottom - top,
  };
}

function source(id: string, headerRow: number, first: string, last: string, lastRow: number): ProfileSource {
  return {
    id,
    sheet: "Lists",
    headerRow,
    block: { firstColumn: first, lastColumn: last, lastRow },
    applicationKey: null,
    objectTypeKey: type,
    key: { field: "name" },
    columns: [],
  };
}

const profile = (...sources: ProfileSource[]): DraftProfileDocument => ({
  key: "lists",
  name: "Lists",
  sources,
  valueMaps: {},
});

describe("lists of a sheet laid out for reading (0.10 A8b)", () => {
  it("numbers and letters columns both ways", () => {
    for (const [letter, number] of [
      ["A", 1],
      ["Z", 26],
      ["AA", 27],
      ["AZ", 52],
      ["BA", 53],
    ] as const) {
      expect(columnNumber(letter)).toBe(number);
      expect(columnLetter(number)).toBe(letter);
    }
  });

  it("finds a list's source among lists side by side and stacked, after its header moved", () => {
    const top = block(0, ["A", 3, "B", 9]);
    const under = block(1, ["A", 12, "B", 18]);
    const beside = block(2, ["D", 3, "D", 7]);
    const sources = profile(
      source("top", 3, "A", "B", 9),
      source("under", 13, "A", "B", 18),
      source("beside", 3, "D", "D", 7),
    );
    expect(sourceOfList(sources, "Lists", top)?.id).toBe("top");
    expect(sourceOfList(sources, "Lists", under)?.id).toBe("under");
    expect(sourceOfList(sources, "Lists", beside)?.id).toBe("beside");
    expect(sourceOfList(sources, "Other", top)).toBeUndefined();
    expect(sourceOfList(profile(source("top", 3, "A", "B", 9)), "Lists", under)).toBeUndefined();
  });

  it("reads a list as proposed while its source or type is the engine's, loaded otherwise, and not loaded without one", () => {
    const loaded = source("s", 3, "A", "B", 9);
    expect(listStatus(loaded, new Set(["source:s"]))).toBe("proposed");
    expect(listStatus(loaded, new Set([`objectType:${type}`]))).toBe("proposed");
    expect(listStatus(loaded, new Set())).toBe("loaded");
    expect(listStatus(undefined, new Set(["source:s"]))).toBe("notLoaded");
  });

  it("adjusts the source's rectangle, and renames the list only when asked", () => {
    const loaded = source("s", 3, "A", "B", 9);
    const rectangle = rectangleOf(block(0, ["A", 3, "B", 9]), loaded);
    expect(rectangle).toEqual({ headerRow: 3, block: { firstColumn: "A", lastColumn: "B", lastRow: 9 } });
    const moved = { ...rectangle, headerRow: 4 };
    expect(adjustOperations(loaded, moved)).toEqual([
      { kind: "setSource", source: "s", headerRow: 4, block: moved.block },
    ]);
    expect(adjustOperations(loaded, moved, "Role")[1]).toEqual({
      kind: "setLabel",
      element: { objectType: type },
      name: "Role",
    });
  });

  it("drops a list's type with its source only when nothing else loads, relates to or holds it", () => {
    const loaded = source("s", 3, "A", "B", 9);
    expect(
      dropOperations(
        { ...outline, relations: [], objectTypes: [{ ...outline.objectTypes[0], parents: [] }] },
        profile(loaded),
        loaded,
      ),
    ).toEqual([
      { kind: "removeSource", source: "s" },
      { kind: "removeObjectType", objectType: type },
    ]);
    const twice = profile(loaded, { ...loaded, id: "t" });
    expect(dropOperations({ ...outline, relations: [] }, twice, loaded)).toEqual([
      { kind: "removeSource", source: "s" },
    ]);
    const related = {
      ...outline,
      relations: [
        { relationType: "r", from: "other", to: type, required: false, containment: false, mark: "new" as const },
      ],
    };
    expect(dropOperations(related, profile(loaded), loaded)).toEqual([{ kind: "removeSource", source: "s" }]);
  });
});
