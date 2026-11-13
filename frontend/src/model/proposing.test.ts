import { describe, expect, it } from "vitest";
import { evidenceLines } from "@/ui/ProposedBecause";
import { columnElements, elementOfSelection, patternLabel } from "@/model/proposing";

describe("what the inference proposed (0.10 A6b)", () => {
  it("reads a proposal's evidence in lines: each column, then the pattern's own facts", () => {
    const lines = evidenceLines({
      columns: [
        {
          column: "Category",
          letter: "C",
          rows: 200,
          filled: 200,
          distinct: 13,
          values: [{ value: "Category 01", count: 19 }],
        },
      ],
      groups: 13,
      dependents: [{ column: "Category order", constantIn: 13 }],
      key: null,
      share: 0.333,
    });
    expect(lines).toEqual([
      "Category (C): 200 of 200 filled · 13 distinct · Category 01 ×19",
      "Groups: 13",
      "Dependents: Category order: constant in 13",
      "Share: 33%",
    ]);
  });

  it("names a selection's and a column's elements as the inference does", () => {
    expect(elementOfSelection({ show: "type", key: "item" })).toBe("objectType:item");
    expect(elementOfSelection({ show: "matrix" })).toBeUndefined();
    const profile = {
      key: "k",
      name: "k",
      valueMaps: {},
      sources: [
        { id: "items", sheet: "Items", headerRow: 1, applicationKey: null, objectTypeKey: "item", columns: [] },
        { id: "names", sheet: "Names", headerRow: 1, applicationKey: null, objectTypeKey: "item", columns: [] },
      ],
    };
    expect(columnElements(profile, "Items", "Code")).toEqual(["column:items/Code"]);
    expect(patternLabel("repeatedParent")).toBe("Repeated parent");
    expect(patternLabel("somethingNew")).toBe("somethingNew");
  });

  it("reads what differs from the stored records and a list to be defined (0.10 A7)", () => {
    const lines = evidenceLines({
      acrossFiles: true,
      drift: [{ code: "C2", stored: "Navy", names: [{ value: "Navy blue", count: 3 }] }],
      missing: [{ value: "Bamboo", rows: 12 }],
      toBeDefined: false,
    });
    expect(lines).toEqual([
      "Across files: yes",
      "Drift: C2: stored Navy, here Navy blue ×3",
      "Missing: Bamboo (12 rows)",
      "To be defined: no",
    ]);
    expect(patternLabel("modelDescription")).toBe("Model description");
  });
});
