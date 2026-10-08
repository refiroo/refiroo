import { describe, expect, it } from "vitest";
import {
  emptySelection,
  isSelected,
  loadedState,
  range,
  selectedCount,
  selectMatching,
  toggle,
  toggleLoaded,
  withVersions,
  type RecordSelection,
  type SelectableRow,
} from "@/lib/recordSelection";

// Six records match the list; the first four are loaded.
const matching: SelectableRow[] = ["a", "b", "c", "d", "e", "f"].map((id, index) => ({ id, version: index + 1 }));
const loaded = matching.slice(0, 4);

type Operation = { name: string; apply: (selection: RecordSelection) => RecordSelection };

const operations: Operation[] = [
  ...loaded.map((row) => ({ name: `toggle ${row.id}`, apply: (s: RecordSelection) => toggle(s, row) })),
  ...loaded.map((row) => ({ name: `range to ${row.id}`, apply: (s: RecordSelection) => range(s, loaded, row) })),
  { name: "header", apply: (s) => toggleLoaded(s, loaded) },
  { name: "all matching", apply: () => selectMatching(matching.length) },
  { name: "clear", apply: () => emptySelection },
];

/** The rules written out over plain sets: what each gesture should leave selected. */
function expected(sequence: Operation[]) {
  let selected = new Set<string>();
  let matchingMode = false;
  let anchor: string | undefined;
  for (const operation of sequence) {
    const [verb, , target] = operation.name.split(" ");
    if (operation.name === "all matching") {
      selected = new Set(matching.map((row) => row.id));
      matchingMode = true;
      anchor = undefined;
    } else if (operation.name === "clear") {
      selected = new Set();
      matchingMode = false;
      anchor = undefined;
    } else if (operation.name === "header") {
      if (loaded.every((row) => selected.has(row.id))) {
        if (matchingMode) {
          selected = new Set();
          matchingMode = false;
        } else loaded.forEach((row) => selected.delete(row.id));
        if (!matchingMode) anchor = undefined;
      } else loaded.forEach((row) => selected.add(row.id));
    } else {
      const id = verb === "toggle" ? operation.name.split(" ")[1] : target;
      const to = loaded.findIndex((row) => row.id === id);
      const from = verb === "range" ? loaded.findIndex((row) => row.id === anchor) : -1;
      const state = !selected.has(id);
      const covered = from < 0 ? [id] : loaded.slice(Math.min(from, to), Math.max(from, to) + 1).map((row) => row.id);
      covered.forEach((each) => (state ? selected.add(each) : selected.delete(each)));
      anchor = id;
      if (selected.size === 0) matchingMode = false;
    }
  }
  return selected;
}

function sequences(length: number): Operation[][] {
  if (length === 0) return [[]];
  return sequences(length - 1).flatMap((head) => operations.map((operation) => [...head, operation]));
}

describe("record selection", () => {
  it("selects what each sequence of gestures should, in every combination of three", () => {
    for (const sequence of sequences(3)) {
      const selection = sequence.reduce((current, operation) => operation.apply(current), emptySelection);
      const want = expected(sequence);
      const names = sequence.map((operation) => operation.name).join(", ");
      expect(
        matching.filter((row) => isSelected(selection, row.id)).map((row) => row.id),
        names,
      ).toEqual(matching.filter((row) => want.has(row.id)).map((row) => row.id));
      expect(selectedCount(selection), names).toBe(want.size);
    }
  });

  it("keeps the version each row showed when picked by hand", () => {
    const selection = range(toggle(emptySelection, loaded[0]), loaded, loaded[2]);
    expect(selection.mode === "ids" && [...selection.ids].map(([id, row]) => [id, row.version])).toEqual([
      ["a", 1],
      ["b", 2],
      ["c", 3],
    ]);
  });

  it("takes the versions a change left for the records picked by hand, and keeps all matching", () => {
    const picked = toggle(toggle(emptySelection, { id: "a", version: 1, name: "Alpha" }), loaded[1]);
    const after = withVersions(
      picked,
      new Map([
        ["a", 4],
        ["z", 9],
      ]),
    );
    expect(after.mode === "ids" && [...after.ids.values()]).toEqual([
      { id: "a", version: 4, name: "Alpha" },
      { id: "b", version: 2, name: undefined },
    ]);
    const all = selectMatching(6);
    expect(withVersions(all, new Map([["a", 4]]))).toBe(all);
  });

  it("keeps a row unchecked under all matching as an exception", () => {
    const selection = toggle(selectMatching(2345), loaded[1]);
    expect(selection).toMatchObject({ mode: "matching", total: 2345 });
    expect(selection.mode === "matching" && [...selection.except]).toEqual(["b"]);
    expect(selectedCount(selection)).toBe(2344);
    expect(selectedCount(toggle(selection, loaded[1]))).toBe(2345);
  });

  it("ranges in either direction from the last row toggled", () => {
    const down = range(toggle(emptySelection, loaded[1]), loaded, loaded[3]);
    const up = range(toggle(emptySelection, loaded[3]), loaded, loaded[1]);
    expect(selectedCount(down)).toBe(3);
    expect(selectedCount(up)).toBe(3);
    // A range without an anchor among the loaded rows is the row alone.
    expect(selectedCount(range(emptySelection, loaded, loaded[2]))).toBe(1);
  });

  it("states the header checkbox over the loaded rows", () => {
    expect(loadedState(emptySelection, loaded)).toBe("none");
    expect(loadedState(toggle(emptySelection, loaded[0]), loaded)).toBe("some");
    expect(loadedState(toggleLoaded(emptySelection, loaded), loaded)).toBe("all");
    expect(loadedState(emptySelection, [])).toBe("none");
  });
});
