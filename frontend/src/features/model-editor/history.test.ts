import { describe, expect, it } from "vitest";
import type { ModelDraftOperationEntry } from "@/types";
import { outlineFixture } from "@/test/draftOutline";
import { canRedo, describeOperation, describeStep, historySteps, undoable } from "@/features/model-editor/history";
import { summarizeChanges } from "@/features/model-editor/InstallDialog";
import { nameOf } from "@/features/model-editor/outline";

const outline = outlineFixture();
const names = nameOf(outline);

let sequence = 0;
function entry(
  step: number,
  kind: string,
  origin: ModelDraftOperationEntry["origin"],
  undone = false,
  parameters = {},
): ModelDraftOperationEntry {
  sequence += 1;
  return {
    sequence,
    step,
    kind,
    parameters,
    inverse: {},
    draftVersion: step,
    author: null,
    at: "2026-10-11T10:00:00Z",
    undone,
    origin,
  };
}

const request = { type: "request" } as const;

describe("the history's steps", () => {
  it("groups entries by step, newest first, in plain words", () => {
    const steps = historySteps([
      entry(1, "addObjectType", request, false, { name: "Box", parent: { objectTypes: ["shelf"] } }),
      entry(1, "attachAttribute", request, false, { objectType: "box", attributeType: "code", required: true }),
      entry(2, "placeCollection", request, false, { applicationKey: "shop", collection: "bin", group: "lists" }),
    ]);
    expect(steps.map((step) => step.step)).toEqual([2, 1]);
    expect(describeStep(steps[0], names)).toBe("Placed Bin in group Lists");
    expect(describeStep(steps[1], names)).toBe("Added type Box under Shelf; Attached Code to box, required");
  });

  it("names undo and redo steps by the steps they took back", () => {
    const [redo, undo] = historySteps([
      entry(3, "removeObjectType", { type: "undo", steps: [1, 2] }, true),
      entry(4, "addObjectType", { type: "redo", step: 3 }),
    ]);
    expect(describeStep(undo, names)).toBe("Undid step 1 and 2");
    expect(describeStep(redo, names)).toBe("Redid step 3");
  });

  it("reads an unknown kind as its name and a released type's key as its name", () => {
    expect(describeOperation("someLaterKind", {}, names)).toBe("someLaterKind");
    expect(describeOperation("setKey", { element: { objectType: "shelf" }, key: "rack" }, names)).toBe(
      "Changed the key of Shelf to rack",
    );
  });

  it("reads a layout change in words: panels, fields, columns and the default sort (A4b)", () => {
    const page = { applicationKey: "shop", detail: "shelf" };
    expect(
      describeOperation("setViewProperty", { ...page, panel: "hierarchy", property: "visible", value: false }, names),
    ).toBe("Hid panel hierarchy on the page of Shelf");
    expect(
      describeOperation("setViewProperty", { ...page, panel: "related", property: "region", value: "side" }, names),
    ).toBe("Moved panel related on the page of Shelf to the side region");
    expect(
      describeOperation("insertViewItem", { ...page, list: "panels", item: { key: "more", title: "More" } }, names),
    ).toBe("Added panel More to the page of Shelf");
    expect(
      describeOperation(
        "moveViewItem",
        { ...page, panel: "details", list: "fields", item: "depth", position: 0 },
        names,
      ),
    ).toBe("Moved Depth to place 1 in the fields of panel details on the page of Shelf");
    expect(
      describeOperation(
        "setViewProperty",
        { applicationKey: "shop", view: "shelves", property: "defaultSort", value: "-depth" },
        names,
      ),
    ).toBe("Sorted view shelves by Depth, descending");
    expect(describeOperation("addDetailPage", { applicationKey: "shop", objectType: "bin" }, names)).toBe(
      "Added a detail page for Bin",
    );
  });

  it("offers undo on a change not undone yet, never on an undo (D32)", () => {
    const [undoStep, change] = historySteps([
      entry(1, "addApplication", request),
      entry(2, "removeApplication", { type: "undo", steps: [1] }),
    ]);
    expect(undoable(change)).toBe(true);
    expect(undoable(undoStep)).toBe(false);
  });

  it.each([
    ["nothing undone", [entry(1, "addApplication", request)], false],
    [
      "an undo is the newest step",
      [entry(1, "addApplication", request, true), entry(2, "removeApplication", { type: "undo", steps: [1] })],
      true,
    ],
    [
      "a change after the undo",
      [
        entry(1, "addApplication", request, true),
        entry(2, "removeApplication", { type: "undo", steps: [1] }),
        entry(3, "addApplication", request),
      ],
      false,
    ],
    [
      "the undo was redone",
      [
        entry(1, "addApplication", request),
        entry(2, "removeApplication", { type: "undo", steps: [1] }, true),
        entry(3, "addApplication", { type: "redo", step: 2 }),
      ],
      false,
    ],
    [
      "two undos, one redone",
      [
        entry(1, "addApplication", request, true),
        entry(2, "addApplication", request),
        entry(3, "removeApplication", { type: "undo", steps: [2] }, true),
        entry(4, "removeApplication", { type: "undo", steps: [1] }),
        entry(5, "addApplication", { type: "redo", step: 3 }),
      ],
      true,
    ],
  ])("says whether redo has something to take back: %s", (_, entries, expected) => {
    expect(canRedo(historySteps(entries))).toBe(expected);
  });
});

describe("the install dialog's differences", () => {
  it("lists elements by collection and kind, a change inside an element as changed", () => {
    expect(
      summarizeChanges(
        [
          { kind: "added", path: "/objectTypes/bin" },
          { kind: "changed", path: "/objectTypes/shelf/attributes/depth/required" },
          { kind: "added", path: "/objectTypeRelations/stores/shelf/bin" },
          { kind: "removed", path: "/attributeTypes/colour" },
          { kind: "changed", path: "/release/version" },
        ],
        outline,
      ),
    ).toEqual([
      { label: "Object types added", names: ["Bin"] },
      { label: "Object types changed", names: ["Shelf"] },
      { label: "Allowed relations added", names: ["Shelf → Bin"] },
      { label: "Attribute types removed", names: ["Colour"] },
    ]);
  });
});
