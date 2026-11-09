import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import { matchOptions, relatedFieldOptions } from "@/features/model-editor/consumer";

describe("an XREF rule's fields (found 2026-10-19)", () => {
  it("lists a field several exposed types share once, under no one type's name", () => {
    const options = matchOptions(outlineFixture(), {}, { verb: "under", types: ["area", "shelf"] });
    expect(options.filter((option) => option.value === "code")).toEqual([
      { value: "code", label: "Code", group: "Attributes of the exposed types" },
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
