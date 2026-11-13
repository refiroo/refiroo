import { describe, expect, it } from "vitest";
import { testModel } from "@/test/fixtures";
import type { CollectionQueryState, RelationTableViewDefinition, ViewDefinition } from "@/types";
import { exportViewStart, exportViewState, identifyingFields } from "./exportRequest";

const application = testModel.applications[0];
const query: CollectionQueryState = {
  search: "station",
  sort: "name",
  pageSize: 20,
  filters: [],
};

const relationTable = (layout: "rows" | "grid"): RelationTableViewDefinition => ({
  key: "links",
  name: "Links",
  type: "relationTable",
  config: {
    relationTypeKey: "domain-contains-codelist",
    fromObjectTypeKey: "domain",
    toObjectTypeKey: "codelist",
    fromColumns: ["name"],
    toColumns: ["name"],
    attributeColumns: [],
    filterFields: [],
    sortFields: ["from:name"],
    defaultSort: "from:name",
    layout,
    pageSize: 20,
  },
});

describe("exportViewStart (0.17 EX1)", () => {
  it("hands a table's search, filters, parent and columns, and the type its rows are of", () => {
    const view = testModel.applications[0].views[0] as ViewDefinition;
    const start = exportViewStart(
      application,
      view,
      { ...query, filters: [{ field: "active", operator: "eq", value: "true" }], parentObjectId: "p1" },
      ["name", "code"],
    );
    expect(start).toMatchObject({
      applicationKey: "test-app",
      viewKey: "domains",
      kind: "table",
      typeKey: "domain",
      search: "station",
      parentObjectId: "p1",
      columns: ["name", "code"],
    });
    expect(exportViewState(testModel, start)).toEqual({
      search: "station",
      where: [{ field: "active", op: "eq", value: true }],
      parentObjectId: "p1",
      columns: ["name", "code"],
    });
  });

  it("splits a relationships table's filters by the end they name and says what it cannot carry", () => {
    const start = exportViewStart(application, relationTable("grid"), {
      ...query,
      filters: [
        { field: "from:name", operator: "contains", value: "a" },
        { field: "to:name", operator: "contains", value: "b" },
        { field: "relation:weight", operator: "eq", value: "3" },
      ],
      gridColumnIds: ["c1"],
      gridSearch: "x",
    });
    expect(start.filters).toEqual([{ field: "name", operator: "contains", value: "a" }]);
    expect(start.toFilters).toEqual([{ field: "name", operator: "contains", value: "b" }]);
    expect(start).toMatchObject({ columnIds: ["c1"], toSearch: "x" });
    expect(start.notCarried).toMatch(/relationship's own values/);
    const rows = exportViewStart(application, relationTable("rows"), { ...query, gridColumnIds: ["c1"] });
    expect(rows.columnIds).toBeUndefined();
  });
});

describe("identifyingFields (PP-D27)", () => {
  it("offers the name, then every text field of the type, not only the unique ones", () => {
    // `code` is a text attribute that is not declared unique; `active` is a boolean.
    expect(identifyingFields(testModel, "codelist")).toEqual([
      { key: "name", label: "Name" },
      { key: "code", label: "Code" },
    ]);
  });

  it("is empty for a type the model lacks", () => {
    expect(identifyingFields(testModel, "nothing")).toEqual([]);
  });
});
