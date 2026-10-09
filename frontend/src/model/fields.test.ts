import { describe, expect, it } from "vitest";
import { attributeName, isSortableField, listSortFields, relatedKeys } from "@/model/fields";
import { testModel } from "@/test/fixtures";
import type { ObjectTypeDefinition } from "@/types";

const type = (key: string) => testModel.objectTypes.find((item) => item.key === key) as ObjectTypeDefinition;
const forward = "related:domain-contains-codelist";
const backward = "related:codelist-belongs-to-domain";

describe("relation columns (0.9 K5)", () => {
  it("names a column by the relation's name in its direction", () => {
    expect(attributeName(testModel, forward)).toBe("Contains");
    expect(attributeName(testModel, backward)).toBe("Belongs to");
    expect(attributeName(testModel, "related:unknown")).toBe("related:unknown");
  });

  it("sorts by a column only where a row holds at most one (D145)", () => {
    // A domain contains many codelists; a codelist belongs to one domain.
    expect(isSortableField(testModel, [type("domain")], forward, true)).toBe(false);
    expect(isSortableField(testModel, [type("codelist")], backward, true)).toBe(true);
    expect(isSortableField(testModel, [type("codelist")], backward, false)).toBe(true);
    expect(isSortableField(testModel, [type("codelist")], backward, true, { relationList: true })).toBe(false);
    expect(isSortableField(testModel, [type("domain"), type("codelist")], backward, true)).toBe(false);
    expect(isSortableField(testModel, [type("domain")], backward, true)).toBe(false);
    expect(listSortFields(testModel, [type("codelist")], ["name", backward], [], true)).toEqual(["name", backward]);
  });

  it("asks only for the relation columns given, as keys", () => {
    expect(relatedKeys(["name", forward, "code", backward])).toEqual([
      "domain-contains-codelist",
      "codelist-belongs-to-domain",
    ]);
    expect(relatedKeys(["name", "ancestor:domain"])).toEqual([]);
  });
});

describe("a field of the related records (0.9 K5a)", () => {
  it("names the column by the relation and the field, and never sorts it", () => {
    expect(attributeName(testModel, `${forward}.code`)).toBe("Contains · Code");
    expect(attributeName(testModel, `${forward}.ancestor:domain.name`)).toBe("Contains · Domain");
    expect(attributeName(testModel, `${forward}.name`)).toBe("Contains");
    expect(isSortableField(testModel, [type("codelist")], `${backward}.code`, true)).toBe(false);
    expect(relatedKeys([`${forward}.ancestor:domain.code`])).toEqual(["domain-contains-codelist.ancestor:domain.code"]);
  });
});
