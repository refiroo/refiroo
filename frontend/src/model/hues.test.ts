import { describe, expect, it } from "vitest";
import starter from "../../../model/rdm-starter.json";
import { testModel } from "@/test/fixtures";
import { applicationHue, HUE_SLOTS, objectTypeHue } from "@/model/hues";
import type { EngineModel } from "@/types";

const starterModel = starter as unknown as EngineModel;

/** A model of `count` object types and applications with generated keys. */
function generatedModel(count: number): EngineModel {
  return {
    ...testModel,
    objectTypes: Array.from({ length: count }, (_, index) => ({ ...testModel.objectTypes[0], key: `type-${index}` })),
    applications: Array.from({ length: count }, (_, index) => ({ ...testModel.applications[0], key: `app-${index}` })),
  };
}

describe("type and application hues", () => {
  for (const [name, model] of [
    ["the starter model", starterModel],
    ["a generated model", generatedModel(19)],
  ] as const) {
    it(`gives every object type and application of ${name} its slot by position`, () => {
      model.objectTypes.forEach((type, index) => expect(objectTypeHue(model, type.key)).toBe((index % HUE_SLOTS) + 1));
      model.applications.forEach((application, index) =>
        expect(applicationHue(model, application.key)).toBe((index % HUE_SLOTS) + 1),
      );
    });
  }

  it("gives consecutive types different hues and wraps after the eighth", () => {
    const model = generatedModel(10);
    const hues = model.objectTypes.map((type) => objectTypeHue(model, type.key));
    expect(hues).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 1, 2]);
  });

  it("follows the model's order, not the key", () => {
    const model = generatedModel(3);
    const reordered = { ...model, objectTypes: [...model.objectTypes].reverse() };
    expect(objectTypeHue(reordered, "type-0")).toBe(3);
  });

  it("gives no hue to a key the model does not declare", () => {
    expect(objectTypeHue(starterModel, "missing")).toBeUndefined();
    expect(applicationHue(starterModel, "missing")).toBeUndefined();
  });
});
