import { describe, expect, it } from "vitest";
import type { ImportProfileSource } from "@/types";
import { ignoreColumn, renameColumn, setMissing } from "./profileEdits";

// A source as GET /import-profiles/{key} answers it: defaults and nulls included.
const source: ImportProfileSource = {
  sheet: "Shelves",
  headerRow: 1,
  block: null,
  applicationKey: "store",
  objectTypeKey: "shelf",
  record: "upsert",
  key: { attributeTypeKey: "code", column: null, versionColumn: null, nameColumn: null },
  missing: null,
  columns: [
    { column: "Code", attributeTypeKey: "code" },
    { column: "Area", parent: { objectTypeKey: "area", matchBy: { field: "name" } } },
    {
      columns: ["Cold", "Dry"],
      relationFlags: {
        relationTypeKey: "kept",
        objectTypeKey: "zone",
        targets: { Cold: "Cold store", Dry: "Dry store" },
      },
    },
  ],
};

describe("a profile changed from its check (0.10 A5c)", () => {
  it("renames every member naming a column, and nothing else", () => {
    const [renamed] = renameColumn([source], 0, "Cold", "Chilled");
    expect(renamed.columns[2]).toEqual({
      columns: ["Chilled", "Dry"],
      relationFlags: {
        relationTypeKey: "kept",
        objectTypeKey: "zone",
        targets: { Chilled: "Cold store", Dry: "Dry store" },
      },
    });
    expect(renameColumn([source], 0, "Area", "Aisle")[0].columns[1].column).toBe("Aisle");
    expect(source.columns[1].column).toBe("Area");
  });

  it("ignores a new column and sets what a load does with missing records", () => {
    expect(ignoreColumn([source], 0, "Notes")[0].columns.at(-1)).toEqual({ column: "Notes", ignore: true });
    const deleting = setMissing([source], 0, "delete");
    expect(deleting[0].missing).toBe("delete");
    expect("missing" in setMissing(deleting, 0, "report")[0]).toBe(false);
  });
});
