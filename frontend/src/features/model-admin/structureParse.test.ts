import { describe, expect, it } from "vitest";
import { parseStructure } from "@/features/model-admin/structureParse";

export const fixture = {
  attributeTypes: [
    { key: "label", name: "Label", valueType: "text" },
    {
      key: "count",
      name: "Count",
      valueType: "integer",
      validation: { minimum: 0, maximum: 9 },
      features: { unique: true },
    },
  ],
  objectTypes: [
    {
      key: "t1",
      name: "Alpha",
      icon: "box",
      attributes: [
        { attributeTypeKey: "count", order: 2 },
        { attributeTypeKey: "label", required: true, order: 1 },
      ],
    },
    { key: "t2", name: "Beta" },
  ],
  relationTypes: [{ key: "r1", name: "links", reverseName: "linked by" }],
  objectTypeRelations: [
    { relationTypeKey: "r1", fromObjectTypeKey: "t1", toObjectTypeKey: "t2" },
    { relationTypeKey: "r1", fromObjectTypeKey: "t2", toObjectTypeKey: "t2" },
  ],
  applications: [
    { key: "a1", name: "One", objectTypeKeys: ["t1", "t2", "gone"], views: [{}, {}] },
    { key: "a2", objectTypeKeys: ["t2"] },
  ],
};

describe("parseStructure", () => {
  it("reads applications, their types, attributes in order and relations", () => {
    const structure = parseStructure(fixture)!;
    expect(structure.applications.map((a) => [a.name, a.viewCount, a.objectTypes.length])).toEqual([
      ["One", 2, 2],
      ["a2", 0, 1],
    ]);
    const alpha = structure.applications[0].objectTypes[0];
    expect(alpha.attributes.map((a) => a.key)).toEqual(["label", "count"]);
    expect(alpha.attributes[0]).toMatchObject({ required: true, valueType: "text" });
    expect(alpha.attributes[1]).toMatchObject({ unique: true, minimum: 0, maximum: 9 });
    expect(alpha.relations).toEqual([
      expect.objectContaining({ name: "links", reverseName: "linked by", direction: "out", otherTypeName: "Beta" }),
    ]);
    const beta = structure.applications[0].objectTypes[1];
    expect(beta.relations.map((r) => [r.direction, r.otherTypeKey])).toEqual([
      ["in", "t1"],
      ["out", "t2"],
    ]);
    expect(structure.objectTypeKeys).toEqual(["t1", "t2"]);
  });

  it("lists a type under every application that uses it", () => {
    const structure = parseStructure(fixture)!;
    expect(structure.applications.map((a) => a.objectTypes.some((t) => t.key === "t2"))).toEqual([true, true]);
  });

  it("tolerates missing and odd fields", () => {
    const odd = parseStructure({
      objectTypes: [null, { key: 3 }, { key: "x", attributes: [{ attributeTypeKey: "ghost" }, "bad"] }],
      applications: [{ key: "a", objectTypeKeys: "nope" }, 5, { key: "b", objectTypeKeys: ["x"], views: "no" }],
      relationTypes: "no",
      objectTypeRelations: [{ fromObjectTypeKey: "x" }],
    })!;
    expect(odd.applications.map((a) => a.objectTypes.length)).toEqual([0, 1]);
    expect(odd.applications[1].objectTypes[0].attributes).toEqual([
      expect.objectContaining({ key: "ghost", name: "ghost", valueType: "text", required: false }),
    ]);
  });

  it("returns undefined for a document of another shape", () => {
    expect(parseStructure(undefined)).toBeUndefined();
    expect(parseStructure({ applications: {}, objectTypes: [] })).toBeUndefined();
    expect(parseStructure([])).toBeUndefined();
  });
});
