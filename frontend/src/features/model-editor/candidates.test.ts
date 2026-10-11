import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import { cleaned, describeCandidates, fieldsFor, operatorsFor, typedValue } from "@/features/model-editor/candidates";

const outline = outlineFixture();

describe("which records a relationship may choose (0.9 K7) in the editor", () => {
  it("offers an end's name, its type's attributes and every type it can sit under", () => {
    const fields = fieldsFor(outline, "shelf").map((field) => field.value);
    expect(fields).toEqual(["name", "code", "depth", "ancestor:area.name", "ancestor:area.code"]);
    expect(fieldsFor(outline, undefined).map((field) => field.value)).toEqual(["name"]);
  });

  it("offers each value type's operators, and has no value only for an attribute", () => {
    const [name, , depth] = fieldsFor(outline, "shelf");
    expect(operatorsFor(name).map((op) => op.value)).toEqual(["eq", "contains", "startsWith", "isNull"]);
    expect(operatorsFor(depth).map((op) => op.value)).toEqual(["eq", "lt", "lte", "gt", "gte", "isNull", "isUnset"]);
    expect(typedValue(depth, "gt", "2.5")).toBe(2.5);
    expect(typedValue(name, "isNull", "false")).toBe(false);
  });

  it("drops unfinished criteria, and no criteria at all removes the rule", () => {
    expect(cleaned({ to: [{ field: "name", op: "eq", value: "" }] })).toBeNull();
    expect(cleaned({ to: [{ field: "name", op: "startsWith", value: "A" }], from: [] })).toEqual({
      to: [{ field: "name", op: "startsWith", value: "A" }],
    });
  });

  it("says the criteria in words", () => {
    expect(
      describeCandidates(
        outline,
        { to: [{ field: "ancestor:area.name", op: "contains", value: "north" }] },
        { from: "bin", to: "shelf" },
      ),
    ).toBe("To: Area (above) › Name contains “north”");
  });
});
