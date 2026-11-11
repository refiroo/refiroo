import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import {
  blockNames,
  earlierVersionsOf,
  ensureParentObject,
  includeNames,
  matchOptions,
  parentFieldOptions,
  parentSpecOf,
  relatedFieldOptions,
  relatedOf,
  writeParent,
} from "@/features/model-editor/consumer";

describe("an XREF rule's fields (found 2026-10-19)", () => {
  it("lists a field several exposed types share once, under no one type's name", () => {
    const options = matchOptions(outlineFixture(), {}, { verb: "under", types: ["area", "shelf"] });
    expect(options.filter((option) => option.value === "code")).toEqual([
      { value: "code", label: "Code", group: "Attributes of the exposed types" },
    ]);
  });
});

describe("the earlier versions a definition keeps (0.13 DF3)", () => {
  it("lists them as written with their days, and none for a definition that keeps none", () => {
    expect(earlierVersionsOf({ contractVersion: 2 })).toEqual([]);
    const kept = { contractVersion: 1, deprecated: "2026-11-01", sunset: "2027-06-30", exposes: ["shelf"] };
    expect(earlierVersionsOf({ contractVersion: 2, earlierVersions: [kept, { contractVersion: "x" }] })).toEqual([
      { index: 0, version: 1, deprecated: "2026-11-01", sunset: "2027-06-30", value: kept },
    ]);
  });
});

describe("a related block's attributes of the relationship", () => {
  const base = outlineFixture();
  const outline = {
    ...base,
    relations: base.relations.map((item) =>
      item.relationType === "stores" ? { ...item, attributeTypeKeys: ["depth", "colour"] } : item,
    ),
  };

  it("lists the binding's attributes beside the other groups, forward and backward", () => {
    const forward = relatedFieldOptions(outline, ["bin"], [], { via: "stores", exposes: ["shelf"] });
    expect(forward.filter((option) => option.group === "Attributes of the relationship")).toEqual([
      { value: "relation:depth", label: "Depth · decimal", group: "Attributes of the relationship" },
      { value: "relation:colour", label: "Colour · text", group: "Attributes of the relationship" },
    ]);
    expect(forward.some((option) => option.group === "Built in")).toBe(true);
    const backward = relatedFieldOptions(outline, ["shelf"], [], { via: "stored-on", exposes: ["bin"] });
    expect(backward.filter((option) => option.value.startsWith("relation:"))).toHaveLength(2);
  });

  it("offers none for a route whose binding carries none, and shows a written source by its name", () => {
    expect(relatedFieldOptions(outline, ["shelf"], [], { via: "holds", exposes: ["area"] })).not.toContainEqual(
      expect.objectContaining({ group: "Attributes of the relationship" }),
    );
    const written = relatedFieldOptions(outline, ["shelf"], ["relation:colour"], { via: "holds", exposes: ["area"] });
    expect(written).toContainEqual({ value: "relation:colour", label: "Colour", group: "Written by hand" });
  });
});

describe("a related filter's matchOn offers the relationship's attributes", () => {
  it("lists them beside the block's fields", () => {
    const base = outlineFixture();
    const outline = {
      ...base,
      relations: base.relations.map((item) =>
        item.relationType === "stores" ? { ...item, attributeTypeKeys: ["colour"] } : item,
      ),
    };
    const definition = {
      exposes: ["shelf"],
      object: { related: { items: { via: "stores", fields: { name: "name" } } } },
    };
    const options = matchOptions(outline, definition, { verb: "onRelated", related: "items", types: [] });
    expect(options).toContainEqual({
      value: "relation:colour",
      label: "Colour · text",
      group: "Attributes of the relationship",
    });
  });
});

describe("the parent's fields and related blocks (0.17 CA1)", () => {
  const outline = outlineFixture();
  const written = {
    object: {
      related: {
        bins: { via: "stores", fields: { binName: "name" } },
        notes: { via: "stores", fields: {}, served: "onRequest" },
      },
      parent: {
        output: "category",
        fields: ["objectType", "id", "shelf-code"],
        related: { areaBins: { via: "stores", fields: { binName: "name" }, served: "onRequest" } },
      },
    },
  };

  it("reads the parent in either form, serving a source of the list under its camelCase name, and writes it out in full", () => {
    expect(parentSpecOf(written)).toEqual({
      output: "category",
      short: false,
      fields: [
        { output: "objectType", sources: ["objectType"], value: "objectType" },
        { output: "id", sources: ["id"], value: "id" },
        { output: "shelfCode", sources: ["shelf-code"], value: "shelf-code" },
      ],
    });
    const mapped = {
      object: { parent: { output: "up", fields: { masterId: "master-id", kind: { from: ["objectType"] } } } },
    };
    expect(parentSpecOf(mapped)?.fields.map((field) => [field.output, field.sources])).toEqual([
      ["masterId", ["master-id"]],
      ["kind", ["objectType"]],
    ]);
    const short = {
      object: { fields: { code: { role: "code", from: "x" } }, parent: ["objectType", "code", "master-id"] },
    };
    expect(parentSpecOf(short)?.fields.map((field) => field.output)).toEqual(["objectType", "code", "masterId"]);
    expect(parentSpecOf(short)?.short).toBe(true);
    expect(parentSpecOf({ object: {} })).toBeUndefined();
    expect(writeParent(short, { fields: { masterId: "master-id" } })).toEqual({
      output: "parent",
      fields: { masterId: "master-id" },
    });
    expect(writeParent(written, { output: "up" })).toEqual({
      output: "up",
      fields: { objectType: "objectType", id: "id", shelfCode: "shelf-code" },
      related: written.object.parent.related,
    });
    expect(ensureParentObject("api", short)).toEqual([
      {
        kind: "setConsumerApiPart",
        consumerApi: "api",
        pointer: "/object/parent",
        value: { output: "parent", fields: { objectType: "objectType", code: "code", masterId: "master-id" } },
      },
    ]);
    expect(ensureParentObject("api", written)).toEqual([]);
  });

  it("reads each block's Served, and names the blocks a filter may be on and the names include accepts", () => {
    expect(relatedOf(written).map((row) => [row.output, row.served])).toEqual([
      ["bins", "always"],
      ["notes", "onRequest"],
    ]);
    expect(relatedOf(written, "parent").map((row) => [row.output, row.served])).toEqual([["areaBins", "onRequest"]]);
    expect(blockNames(written).map((option) => option.value)).toEqual(["bins", "notes", "parent.areaBins"]);
    expect(includeNames(written)).toEqual(["notes", "parent.areaBins"]);
  });

  it("offers the parent the built-in fields and the attributes of the types above the exposed ones", () => {
    const values = parentFieldOptions(outline, ["shelf"]).map((option) => option.value);
    expect(values.slice(0, 4)).toEqual(["objectType", "id", "code", "name"]);
    expect(parentFieldOptions(outline, ["shelf"], ["legacy"])).toContainEqual({
      value: "legacy",
      label: "legacy",
      group: "Written by hand",
    });
  });

  it("matches a filter on a parent's block by the block's fields", () => {
    const options = matchOptions(outline, written, { verb: "onRelated", types: [], related: "parent.areaBins" });
    expect(options.map((option) => option.value)).toEqual(expect.arrayContaining(["id", "name"]));
  });

  it("offers a filter on a block every field of the records it reaches, ancestors included, after the block's own", () => {
    const definition = {
      exposes: ["shelf", "bin"],
      object: {
        parent: { output: "parent", fields: { id: "id" } },
        related: { onShelf: { via: "stored-on", fields: { shelfCode: "shelf-code" } } },
      },
    };
    const options = matchOptions(outline, definition, { verb: "onRelated", types: [], related: "onShelf" });
    const values = options.map((option) => option.value);
    expect(values).toContain("shelf-code");
    expect(values).toContain("ancestor:area.name");
    expect(values).not.toContain("objectType");
    expect(options.find((option) => option.value === "shelf-code")?.group).toBe("Fields of onShelf");
    expect(options.find((option) => option.value === "ancestor:area.name")?.label).toBe("Area › Name");
    expect(new Set(values).size).toBe(values.length);
  });
});
