import { describe, expect, it } from "vitest";
import { criteriaFromFilters } from "@/features/jobs/exportRequest";
import { relationFilterEntries, relationFilterMode, relationFilterText } from "@/features/objects/RelationFilter";
import { testModel } from "@/test/fixtures";

const field = "related:codelist-belongs-to-domain";

describe("a relationship filter's entries (0.9 K6, D153, D158)", () => {
  it("stores one eq per chosen record, or one isNull, and reads its mode back", () => {
    const chosen = [
      { id: "a", name: "Alpha" },
      { id: "b", name: "Bravo" },
    ];
    expect(relationFilterEntries(field, "any", chosen)).toEqual([
      { field, operator: "eq", value: "a" },
      { field, operator: "eq", value: "b" },
    ]);
    expect(relationFilterEntries(field, "none", chosen)).toEqual([{ field, operator: "isNull", value: "true" }]);
    expect(relationFilterEntries(field, "some", [])).toEqual([{ field, operator: "isNull", value: "false" }]);
    expect(relationFilterMode(relationFilterEntries(field, "none", []))).toBe("none");
    expect(relationFilterMode(relationFilterEntries(field, "any", chosen))).toBe("any");
    const names = new Map([["a", { id: "a", name: "Alpha", objectTypeKey: "domain" }]]);
    expect(relationFilterText(relationFilterEntries(field, "any", chosen), names)).toBe("is any of Alpha, …");
    expect(relationFilterText(relationFilterEntries(field, "some", []), names)).toBe("has any");
  });

  it("becomes the query's related hop in an export, as the list applies it", () => {
    const criteria = criteriaFromFilters(testModel, [
      { field: "code", operator: "eq", value: "X" },
      ...relationFilterEntries(field, "any", [
        { id: "a", name: "Alpha" },
        { id: "b", name: "Bravo" },
      ]),
    ]);
    expect(criteria).toEqual([
      {
        related: {
          relationTypeKey: "domain-contains-codelist",
          direction: "incoming",
          where: [
            { field: "id", op: "eq", value: "a" },
            { field: "id", op: "eq", value: "b" },
          ],
        },
      },
      { field: "code", op: "eq", value: "X" },
    ]);
    expect(criteriaFromFilters(testModel, relationFilterEntries(field, "none", []))).toEqual([
      { related: { relationTypeKey: "domain-contains-codelist", direction: "incoming", where: [] }, not: true },
    ]);
  });
});
