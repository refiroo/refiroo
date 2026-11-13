import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import { cardsOf, linesOf } from "./canvasModel";
import {
  ZOOM_MAX,
  ZOOM_MIN,
  centredScroll,
  clampZoom,
  findIn,
  fitZoom,
  pickOf,
  renameFieldOperations,
  renameListOperations,
  moveAttributeDropOperations,
  reorderAttributeOperations,
  stepAttributeOperations,
  scrollAfterZoom,
  selectionOfPick,
  stepZoom,
  targetOfField,
  targetOfLine,
  targetOfSelection,
  editorSelectionOf,
  wheelZoom,
} from "./canvasView";

const outline = outlineFixture();
const cards = cardsOf(outline, undefined, new Set(), undefined, { scope: "model" });
const lines = linesOf(outline, cards);

describe("zoom (0.17 CE1)", () => {
  it("keeps the zoom between a quarter and double, in whole percents", () => {
    expect(clampZoom(0.1)).toBe(ZOOM_MIN);
    expect(clampZoom(5)).toBe(ZOOM_MAX);
    expect(clampZoom(Number.NaN)).toBe(1);
    expect(stepZoom(1, -1)).toBe(0.9);
    expect(stepZoom(0.3, -1)).toBe(ZOOM_MIN);
    expect(stepZoom(1.95, 1)).toBe(ZOOM_MAX);
  });

  it("turns the wheel into a smooth zoom that a flick of the other way undoes", () => {
    const out = wheelZoom(1, 100);
    expect(out).toBeLessThan(1);
    expect(wheelZoom(out, -100)).toBeCloseTo(1, 1);
  });

  it("fits the whole board in the viewport, never larger than it is", () => {
    expect(fitZoom({ width: 2000, height: 1000 }, { width: 1000, height: 800 })).toBe(0.5);
    expect(fitZoom({ width: 400, height: 300 }, { width: 1000, height: 800 })).toBe(1);
    expect(fitZoom({ width: 100000, height: 100 }, { width: 1000, height: 800 })).toBe(ZOOM_MIN);
    expect(fitZoom({ width: 0, height: 0 }, { width: 1000, height: 800 })).toBe(1);
  });

  it("keeps the point under the pointer where it is while zooming, and the box in the middle when centred", () => {
    // Under the pointer at (100, 50) of a view scrolled to (200, 0): board point (300, 50) stays put at double.
    const next = scrollAfterZoom({ x: 200, y: 0 }, { x: 100, y: 50 }, 1, 2);
    expect(next).toEqual({ x: 500, y: 50 });
    expect(centredScroll({ x: 1000, y: 800, width: 300, height: 100 }, 1, { width: 800, height: 600 })).toEqual({
      x: 750,
      y: 550,
    });
    expect(centredScroll({ x: 0, y: 0, width: 300, height: 100 }, 1, { width: 800, height: 600 })).toEqual({
      x: 0,
      y: 0,
    });
  });
});

describe("find (0.17 CE1)", () => {
  it("finds lists and fields by part of a name, names that start with it first", () => {
    const hits = findIn(outline, "de");
    expect(hits[0]).toMatchObject({ typeKey: "shelf", fieldId: "attribute:depth", label: "Depth" });
    expect(findIn(outline, "shelf")[0]).toMatchObject({ typeKey: "shelf", label: "Shelf", hint: "Shop" });
    expect(findIn(outline, "stor")).toEqual([
      expect.objectContaining({ typeKey: "shelf", fieldId: "relation:stores:bin", label: "Stores" }),
    ]);
    expect(findIn(outline, "  ")).toEqual([]);
    expect(findIn(outline, "zzz")).toEqual([]);
  });
});

describe("by hand: what the editor's table builds for the gestures (0.17 CE1)", () => {
  it("a rename is the editor's heading rename, the name alone, and the editor's Rename… of a field", () => {
    const bin = cards.find((card) => card.typeKey === "bin")!;
    expect(renameListOperations(bin, " Crate ")).toEqual([
      { kind: "setLabel", element: { objectType: "bin" }, name: "Crate" },
    ]);
    const shelf = cards.find((card) => card.typeKey === "shelf")!;
    const depth = shelf.fields.find((field) => field.id === "attribute:depth")!;
    expect(renameFieldOperations(shelf, depth, "Deepness", outline)).toEqual([
      { kind: "setLabel", element: { attributeType: "depth" }, name: "Deepness" },
    ]);
    const stores = shelf.fields.find((field) => field.kind === "relation")!;
    expect(renameFieldOperations(shelf, stores, "Keeps", outline)[0]).toMatchObject({
      kind: "setLabel",
      element: { relationType: "stores" },
      name: "Keeps",
      reverseName: "Stored on",
    });
    expect(renameFieldOperations(shelf, shelf.fields[0], "Title", outline)).toEqual([]);
  });
});

describe("attributes dragged on the board: what the editor's operations build (0.17 CE1)", () => {
  const shelf = cards.find((card) => card.typeKey === "shelf")!;
  const field = (id: string) => shelf.fields.find((item) => item.id === id)!;

  it("an attribute dropped on another object type's card is the editor's Move to…", () => {
    expect(moveAttributeDropOperations(shelf, field("attribute:depth"), "bin")).toEqual([
      { kind: "moveAttribute", attributeType: "depth", from: "shelf", to: "bin" },
    ]);
    expect(moveAttributeDropOperations(shelf, field("attribute:depth"), "shelf")).toEqual([]);
    expect(moveAttributeDropOperations(shelf, field("name"), "bin")).toEqual([]);
    expect(
      moveAttributeDropOperations(
        shelf,
        shelf.fields.find((item) => item.kind === "relation")!,
        "bin",
      ),
    ).toEqual([]);
  });

  it("an attribute dropped beside another of its card takes that place; the place it already holds sends nothing", () => {
    expect(reorderAttributeOperations(outline, "shelf", "depth", "code", false)).toEqual([
      { kind: "setAttributeBinding", objectType: "shelf", attributeType: "depth", position: 0 },
    ]);
    expect(reorderAttributeOperations(outline, "shelf", "code", "depth", true)).toEqual([
      { kind: "setAttributeBinding", objectType: "shelf", attributeType: "code", position: 1 },
    ]);
    expect(reorderAttributeOperations(outline, "shelf", "code", "depth", false)).toEqual([]);
    expect(reorderAttributeOperations(outline, "shelf", "depth", "code", true)).toEqual([]);
    expect(reorderAttributeOperations(outline, "shelf", "depth", "depth", true)).toEqual([]);
  });

  it("Alt+Arrow is the editor's Move up and Move down, only where they are offered", () => {
    expect(stepAttributeOperations(shelf, field("attribute:depth"), -1, outline)).toEqual([
      { kind: "setAttributeBinding", objectType: "shelf", attributeType: "depth", position: 0 },
    ]);
    expect(stepAttributeOperations(shelf, field("attribute:depth"), 1, outline)).toEqual([]);
    expect(stepAttributeOperations(shelf, field("attribute:code"), -1, outline)).toEqual([]);
  });
});

describe("what each thing on the board is to the operation table", () => {
  it("names a card, a field and a line by their targets", () => {
    const shelf = cards.find((card) => card.typeKey === "shelf")!;
    expect(
      targetOfField(
        shelf,
        shelf.fields.find((f) => f.id === "attribute:depth")!,
        outline,
      ),
    ).toEqual({
      on: "attribute",
      objectType: "shelf",
      attributeType: "depth",
    });
    expect(
      targetOfField(
        shelf,
        shelf.fields.find((f) => f.kind === "relation")!,
        outline,
      ),
    ).toEqual({
      on: "relation",
      relationType: "stores",
      from: "shelf",
      to: "bin",
    });
    // A parent field and a containment line are the relationship that places the child.
    const expected = { on: "relation", relationType: "holds", from: "area", to: "shelf" };
    expect(
      targetOfField(
        shelf,
        shelf.fields.find((f) => f.kind === "parent")!,
        outline,
      ),
    ).toEqual(expected);
    expect(
      targetOfLine(
        lines.find((line) => line.kind === "contains")!,
        outline,
      ),
    ).toEqual(expected);
    expect(
      targetOfLine(
        lines.find((line) => line.kind === "relates")!,
        outline,
      ),
    ).toMatchObject({ relationType: "stores" });
  });

  it("maps a canvas selection to a target and to the editor's panel", () => {
    expect(targetOfSelection({ show: "canvas", element: "type", key: "bin" }, cards, lines, outline)).toEqual({
      on: "objectType",
      objectType: "bin",
    });
    expect(targetOfSelection({ show: "canvas", element: "application", key: "shop" }, cards, lines, outline)).toEqual({
      on: "application",
      applicationKey: "shop",
    });
    expect(
      editorSelectionOf(
        { show: "canvas", element: "field", key: "shelf", field: "attribute:depth" },
        cards,
        lines,
        outline,
      ),
    ).toEqual({
      show: "attributeType",
      key: "depth",
    });
    expect(
      editorSelectionOf({ show: "canvas", element: "line", key: "relates:stores:shelf:bin" }, cards, lines, outline),
    ).toEqual({
      show: "relationType",
      key: "stores",
    });
    expect(
      editorSelectionOf({ show: "canvas", element: "group", application: "shop", key: "lists" }, cards, lines, outline),
    ).toEqual({
      show: "group",
      application: "shop",
      key: "lists",
    });
    expect(editorSelectionOf({ show: "canvas" }, cards, lines, outline)).toEqual({});
  });

  it("keeps the part of the selection the address holds", () => {
    const selection = { show: "canvas", element: "field", key: "shelf", field: "attribute:depth" } as const;
    expect(pickOf(selection)).toEqual({ element: "field", key: "shelf", field: "attribute:depth" });
    expect(selectionOfPick(pickOf(selection))).toEqual(selection);
    expect(pickOf({ show: "canvas" })).toBeUndefined();
  });
});
