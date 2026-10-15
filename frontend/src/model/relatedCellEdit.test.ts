import { describe, expect, it } from "vitest";
import { relatedCellEdit } from "@/model/lookup";
import { testModel } from "@/test/fixtures";
import type { EngineModel, ObjectTypeRelationDefinition } from "@/types";

type Binding = Partial<ObjectTypeRelationDefinition>;

/** The test model with a relation type `cites` (reverse `cited-by`) and the given bindings of it. */
function withCites(...bindings: Binding[]): EngineModel {
  return {
    ...testModel,
    relationTypes: [
      ...testModel.relationTypes,
      { key: "cites", reverseKey: "cited-by", name: "Cites", reverseName: "Cited by", isOriented: true, features: {} },
    ],
    objectTypeRelations: [
      ...testModel.objectTypeRelations,
      ...bindings.map((binding) => ({
        relationTypeKey: "cites",
        fromObjectTypeKey: "domain",
        toObjectTypeKey: "codelist",
        cardinality: "many-to-many" as const,
        ...binding,
      })),
    ],
  };
}

describe("what a list's relation cell edits (0.10 A9, D135–D137)", () => {
  it("a row holding at most one edits it singly, read from either end", () => {
    const model = withCites({ cardinality: "many-to-one" });
    expect(relatedCellEdit(model, "domain", "related:cites")).toMatchObject({
      single: true,
      direction: "outgoing",
      choices: [{ otherObjectTypeKey: "codelist", label: "Cites" }],
    });
    // Read backwards, a codelist is cited by many domains.
    expect(relatedCellEdit(model, "codelist", "related:cited-by")).toMatchObject({
      single: false,
      direction: "incoming",
    });
  });

  it("a column showing a field of the related records edits the relationship as its plain column does", () => {
    const model = withCites({ cardinality: "one-to-one" });
    expect(relatedCellEdit(model, "domain", "related:cites.code")?.single).toBe(true);
  });

  it("a many-valued binding, or several bindings behind one column, edit as a set", () => {
    expect(relatedCellEdit(withCites({}), "domain", "related:cites")?.single).toBe(false);
    const mixed = withCites({ cardinality: "many-to-one" }, { cardinality: "many-to-one", toObjectTypeKey: "domain" });
    const edit = relatedCellEdit(mixed, "domain", "related:cites");
    expect(edit?.single).toBe(false);
    expect(edit?.choices.map((choice) => choice.otherObjectTypeKey)).toEqual(["codelist", "domain"]);
  });

  it("shows no icons for required ownership, containment, or a type with no binding behind the column", () => {
    for (const cardinality of ["one-to-one", "one-to-many"] as const)
      expect(relatedCellEdit(withCites({ cardinality, required: true }), "domain", "related:cites")).toBeUndefined();
    expect(relatedCellEdit(testModel, "domain", "related:domain-contains-codelist")).toBeUndefined();
    expect(relatedCellEdit(withCites({}), "codelist", "related:cites")).toBeUndefined();
    expect(relatedCellEdit(withCites({}), "domain", "code")).toBeUndefined();
  });

  it("a required many-to-many is still edited as a set; the engine refuses taking away what a record needs", () => {
    expect(relatedCellEdit(withCites({ required: true }), "domain", "related:cites")?.single).toBe(false);
  });
});
