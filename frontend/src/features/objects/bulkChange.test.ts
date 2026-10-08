import { describe, expect, it } from "vitest";
import { emptySelection, selectMatching, toggle } from "@/lib/recordSelection";
import { testModel } from "@/test/fixtures";
import type { EngineModel } from "@/types";
import { bulkFields, bulkItems, recordsToChange, refFor, versionsAfter } from "./bulkChange";

/** The test model with a read-only, a hidden and a required binding added to its domains. */
const model: EngineModel = {
  ...testModel,
  attributeTypes: [
    ...testModel.attributeTypes,
    { key: "origin", name: "Origin", valueType: "text", features: {}, validation: {}, ui: {} },
    { key: "secret", name: "Secret", valueType: "text", features: {}, validation: {}, ui: { hidden: true } },
    { key: "note", name: "Note", valueType: "longText", features: {}, validation: {}, ui: {} },
  ],
  objectTypes: testModel.objectTypes.map((type) =>
    type.key === "domain"
      ? {
          ...type,
          attributes: [
            { attributeTypeKey: "note", required: false, readOnly: false, order: 5, ui: {} },
            ...type.attributes,
            { attributeTypeKey: "origin", required: false, readOnly: true, order: 30, ui: {} },
            { attributeTypeKey: "secret", required: false, readOnly: false, order: 40, ui: {} },
          ],
        }
      : type,
  ),
};
const domain = model.objectTypes.find((type) => type.key === "domain")!;

describe("what a bulk change offers and sends (0.9 K2)", () => {
  it("offers the bound fields in order, but not read-only or hidden ones, and never clears a required one", () => {
    expect(bulkFields(model, domain).map((field) => [field.attribute.key, field.clearable])).toEqual([
      ["note", true],
      ["code", false],
      ["active", true],
    ]);
  });

  it("sends the hand-picked records with the versions their rows showed, named by their names", () => {
    const selection = toggle(toggle(emptySelection, { id: "a", version: 3, name: "Alpha" }), {
      id: "b",
      version: 7,
      name: "x".repeat(250),
    });
    const items = bulkItems(recordsToChange(selection), [
      { attributeTypeKey: "note", value: "Checked" },
      { attributeTypeKey: "active", value: null },
    ]);
    expect(items[0]).toEqual({
      op: "update",
      ref: "Alpha",
      target: { id: "a" },
      expectedVersion: 3,
      attributes: [
        { attributeTypeKey: "note", value: "Checked" },
        { attributeTypeKey: "active", value: null },
      ],
    });
    expect(items[1].ref).toHaveLength(200);
    expect(items[1].expectedVersion).toBe(7);
    expect(refFor({ id: "c", version: 1 })).toBe("c");
  });

  it("sends the records read for all matching, leaving out its exceptions", () => {
    const read = ["a", "b", "c"].map((id, index) => ({ id, version: index + 1, name: id.toUpperCase() }));
    const selection = toggle(selectMatching(3), read[1]);
    expect(recordsToChange(selection, read).map((row) => row.id)).toEqual(["a", "c"]);
  });

  it("keeps the versions applied outcomes left, and none of refused or deleted ones", () => {
    expect(
      versionsAfter([
        { index: 0, ref: "A", status: "applied", action: "updated", id: "a", objectTypeKey: "domain", version: 4 },
        { index: 1, ref: "B", status: "applied", action: "unchanged", id: "b", objectTypeKey: "domain", version: 7 },
        { index: 2, ref: "C", status: "rejected", error: { code: "VERSION_CONFLICT", message: "…" } },
        { index: 3, ref: "D", status: "applied", action: "deleted", id: "d", objectTypeKey: "domain" },
      ]),
    ).toEqual(
      new Map([
        ["a", 4],
        ["b", 7],
      ]),
    );
  });
});
