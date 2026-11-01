import { describe, expect, it } from "vitest";
import {
  candidateHint,
  candidateScope,
  describeCriteria,
  ownEndReason,
  ownEndReasonParts,
  ownEndScope,
} from "@/model/candidates";
import { testModel } from "@/test/fixtures";
import type { EngineModel, ObjectTypeRelationDefinition } from "@/types";

const binding: ObjectTypeRelationDefinition = {
  relationTypeKey: "domain-contains-codelist",
  fromObjectTypeKey: "domain",
  toObjectTypeKey: "codelist",
  cardinality: "one-to-many",
  candidates: { to: [{ field: "name", op: "contains", value: "Res" }] },
};

describe("which records a relationship may choose (0.9 K7)", () => {
  it("scopes the far end's picker by the key read from the anchor, and only where it is limited", () => {
    expect(candidateScope(testModel, binding, "outgoing", "domain")).toEqual({
      candidateFor: "domain-contains-codelist",
      anchorTypeKey: "domain",
    });
    expect(candidateScope(testModel, binding, "incoming", "codelist")).toBeUndefined();
    expect(ownEndScope(testModel, binding, "incoming")).toEqual({
      candidateFor: "domain-contains-codelist",
      anchorTypeKey: "domain",
    });
    expect(ownEndScope(testModel, binding, "outgoing")).toBeUndefined();
  });

  it("says the criteria in words, an ancestor's, a flag's and alternatives included", () => {
    const model: EngineModel = {
      ...testModel,
      attributeTypes: [
        ...testModel.attributeTypes,
        { key: "flag", name: "Flag", valueType: "boolean", features: {} },
      ] as EngineModel["attributeTypes"],
    };
    expect(
      describeCriteria(model, [
        { field: "ancestor:domain.name", op: "contains", value: "Reserved" },
        { field: "flag", op: "eq", value: true },
        { field: "name", op: "eq", value: "A" },
        { field: "name", op: "eq", value: "B" },
      ]),
    ).toBe("under a Domain whose name contains “Reserved”, with Flag: Yes, whose name is “A” or whose name is “B”");
    expect(candidateHint(testModel, binding, "outgoing")).toBe("Offers only codelists whose name contains “Res”.");
  });

  it("marks the parent and the value in a reason's pieces", () => {
    const limited: ObjectTypeRelationDefinition = {
      ...binding,
      candidates: { from: [{ field: "ancestor:domain.name", op: "eq", value: "Reserved" }] },
    };
    const parts = ownEndReasonParts(testModel, limited, "outgoing");
    expect(parts?.filter((part) => part.mark)).toEqual([
      { text: "under a Domain", mark: "parent" },
      { text: "“Reserved”", mark: "value" },
    ]);
    expect(ownEndReason(testModel, limited, "outgoing")).toBe(parts?.map((part) => part.text).join(""));
  });
});
