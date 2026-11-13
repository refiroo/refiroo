import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import type { DraftProfile, SourceColumn } from "@/types";
import {
  NEW_ATTRIBUTE,
  columnState,
  columnsOfType,
  describeMappingOperation,
  dropChoice,
  feedWords,
  issuesByColumn,
  likelyValueType,
  mapOperations,
  mapTargets,
  relationValue,
  usesOf,
} from "@/features/model-editor/mapping";
import { nameOf } from "@/model/outline";

const outline = outlineFixture();
const stores = { relationType: "stores", from: "shelf", to: "bin" };

/** A sheet of shelves mapped by hand: its key, name, parent, a split lookup, an ignored column and
 * a column a model step left unmapped. */
const draft: DraftProfile = {
  version: 9,
  profile: {
    key: "shelves",
    name: "shelves",
    sources: [
      {
        id: "shelves-shelf",
        sheet: "Shelves",
        headerRow: 1,
        applicationKey: "shop",
        objectTypeKey: "shelf",
        key: { attributeTypeKey: "code" },
        columns: [
          { column: "Shelf code", attributeTypeKey: "code" },
          { column: "Shelf", field: "name" },
          { column: "Area", parent: { objectTypeKey: "area", matchBy: { field: "name" } } },
          {
            column: "Bins",
            relation: { relationTypeKey: "stores", objectTypeKey: "bin", matchBy: { field: "name" }, split: ";" },
          },
          { column: "Note", ignore: true },
        ],
      },
    ],
    valueMaps: {},
    unmapped: [
      { id: "u1", sheet: "Shelves", source: "shelves-shelf", column: "Depth", because: { kind: "detachAttribute" } },
    ],
  },
  definition: null,
  valid: true,
  diagnostics: [
    { severity: "warning", code: "COLUMN_UNMAPPED", path: "/profile/unmapped/0", message: "Depth is no longer mapped" },
  ],
  sourceFile: { id: "f1", name: "shelves.xlsx", profile: "completed" },
};

const column = (part: Partial<SourceColumn>): SourceColumn => ({
  sheet: "Shelves",
  letter: "A",
  header: "Width",
  block: 0,
  rows: 10,
  filled: 10,
  distinct: 10,
  valueTypes: { text: 10 },
  candidateKey: false,
  delimiters: [],
  placeholders: [],
  overlaps: [],
  ...part,
});

describe("a column of the draft's source file in the editor (0.10 A5b)", () => {
  it("has the status the source pane shows: its source's key, mapped, ignored, not mapped or with an issue", () => {
    const issues = issuesByColumn(draft);
    const status = (header: string) => columnState(draft, issues, "Shelves", header).status;
    expect(["Shelf code", "Shelf", "Bins", "Note", "Width", "Depth"].map(status)).toEqual([
      "key",
      "mapped",
      "mapped",
      "ignored",
      "unmapped",
      "issue",
    ]);
    expect(columnState(draft, issues, "Shelves", "Depth").issues.map((item) => item.code)).toEqual(["COLUMN_UNMAPPED"]);
  });

  it("says what it feeds by the draft's names, and marks the columns feeding a type", () => {
    const words = (header: string) => feedWords(outline, usesOf(draft.profile, "Shelves", header)[0], header);
    expect(words("Shelf code")).toBe("Shelf · Code");
    expect(words("Area")).toBe("Shelf’s parent · Area");
    expect(words("Bins")).toBe("Shelf · Stores → Bin");
    expect([...columnsOfType(draft.profile, "bin")]).toEqual(["Shelves\u0000Bins"]);
    expect(columnsOfType(draft.profile, "area").has("Shelves\u0000Area")).toBe(true);
  });

  it("offers a type's attributes, its parents and its relations both ways as targets", () => {
    expect(mapTargets("attribute", "shelf", outline).map((item) => item.value)).toEqual([
      "code",
      "depth",
      NEW_ATTRIBUTE,
    ]);
    expect(mapTargets("parent", "shelf", outline).map((item) => item.name)).toEqual(["Area"]);
    // The containment relation is the parent's; seen from the bin, the relation reads in reverse.
    expect(mapTargets("lookup", "shelf", outline).map((item) => item.name)).toEqual(["Stores → Bin"]);
    expect(mapTargets("lookup", "bin", outline).map((item) => item.name)).toEqual(["Stored on → Shelf"]);
  });
});

describe("Map to… as one request", () => {
  it("creates an attribute, starts the sheet's source keyed by it and maps the column, in that order", () => {
    const operations = mapOperations(
      {
        sheet: "Bins",
        header: "Bin code",
        rowType: "bin",
        kind: "attribute",
        target: NEW_ATTRIBUTE,
        newAttribute: { name: "Bin code", valueType: "text", unique: true },
        useAsKey: true,
      },
      draft.profile,
      outline,
    );
    expect(operations).toEqual([
      { kind: "addAttributeType", key: "bin-code", name: "Bin code", valueType: "text", features: { unique: true } },
      { kind: "attachAttribute", objectType: "bin", attributeType: "bin-code" },
      { kind: "addSource", id: "bins-bin", sheet: "Bins", objectType: "bin", key: { attributeTypeKey: "bin-code" } },
      { kind: "mapColumn", source: "bins-bin", column: "Bin code", binding: { attributeTypeKey: "bin-code" } },
    ]);
  });

  it("keys a source that exists with a step after the mapping", () => {
    expect(
      mapOperations(
        { sheet: "Shelves", header: "Depth", rowType: "shelf", kind: "attribute", target: "depth", useAsKey: true },
        draft.profile,
        outline,
      ),
    ).toEqual([
      { kind: "mapColumn", source: "shelves-shelf", column: "Depth", binding: { attributeTypeKey: "depth" } },
      { kind: "setSource", source: "shelves-shelf", key: { attributeTypeKey: "depth" } },
    ]);
  });

  it("reads a lookup from either end, split and creating what it names, and a flag of a relation", () => {
    const [lookup] = mapOperations(
      {
        sheet: "Shelves",
        header: "Bins",
        rowType: "shelf",
        kind: "lookup",
        target: relationValue(stores),
        split: ";",
        create: true,
      },
      draft.profile,
      outline,
    );
    expect(lookup.binding).toEqual({
      relation: {
        relationTypeKey: "stores",
        objectTypeKey: "bin",
        matchBy: { field: "name" },
        split: ";",
        missing: "create",
      },
    });
    const reverse = mapOperations(
      { sheet: "Bins", header: "Shelf", rowType: "bin", kind: "lookup", target: relationValue(stores) },
      draft.profile,
      outline,
    );
    expect(reverse[1].binding).toEqual({
      relation: {
        relationTypeKey: "stores",
        objectTypeKey: "shelf",
        direction: "incoming",
        matchBy: { field: "name" },
      },
    });
    const [flag] = mapOperations(
      { sheet: "Shelves", header: "Top bin", rowType: "shelf", kind: "flag", target: relationValue(stores) },
      draft.profile,
      outline,
    );
    expect(flag).toEqual({
      kind: "setColumnReading",
      source: "shelves-shelf",
      column: "Top bin",
      reading: "relationFlag",
      relationTypeKey: "stores",
      objectTypeKey: "bin",
      target: "Top bin",
    });
  });

  it("maps a column dropped on a type to that type's source, the parent, a related record or a new source's name", () => {
    expect(dropChoice(draft.profile, outline, "Shelves", "shelf")).toEqual({ rowType: "shelf", kind: "attribute" });
    expect(dropChoice(draft.profile, outline, "Shelves", "area")).toEqual({
      rowType: "shelf",
      kind: "parent",
      target: "area",
    });
    expect(dropChoice(draft.profile, outline, "Shelves", "bin")).toEqual({
      rowType: "shelf",
      kind: "lookup",
      target: relationValue(stores),
    });
    expect(dropChoice(draft.profile, outline, "Bins", "bin")).toEqual({ rowType: "bin", kind: "name" });
  });

  it("proposes a new attribute's value type from the cells a column's placeholders leave", () => {
    expect(
      likelyValueType(column({ valueTypes: { text: 10, integer: 8 }, placeholders: [{ value: "-", count: 2 }] })),
    ).toBe("integer");
    expect(likelyValueType(column({ valueTypes: { text: 10, integer: 7 } }))).toBe("text");
  });
});

describe("the source and mapping kinds in the history", () => {
  const names = nameOf(outline);
  it("says each step in words by the draft's names", () => {
    const say = (kind: string, p: Record<string, unknown>) => describeMappingOperation(kind, p, names);
    expect(say("addSource", { sheet: "Shelves", objectType: "shelf" })).toBe(
      "Started loading Shelf from sheet Shelves",
    );
    expect(say("mapColumn", { column: "Area", binding: { parent: { objectTypeKey: "area" } } })).toBe(
      "Mapped Area to the parent Area",
    );
    expect(
      say("mapColumn", { column: "Bins", binding: { relation: { relationTypeKey: "stores", objectTypeKey: "bin" } } }),
    ).toBe("Mapped Bins to Stores → Bin");
    expect(say("splitColumn", { column: "Bins", delimiter: "\n" })).toBe("Split Bins on line break");
    expect(say("addValuesToList", { column: "Bins" })).toBe("Values of Bins that do not exist are created");
    expect(say("setValueMap", { name: "bins", entries: null })).toBe("Removed value map bins");
    expect(say("setSource", { source: "shelves-shelf", key: { attributeTypeKey: "code" } })).toBe(
      "Made Code the key of source shelves-shelf",
    );
    expect(say("setMissing", { source: "shelves-shelf", missing: "delete" })).toBe(
      "Records missing from the file are deleted from source shelves-shelf in a change set",
    );
    expect(say("addObjectType", {})).toBeUndefined();
  });
});

describe("Map to… a related record (0.10 A6b)", () => {
  const base = { sheet: "Shelves", header: "Bins", rowType: "shelf", target: relationValue(stores) } as const;

  it("matches by a unique attribute without creating what it does not find", () => {
    const [operation] = mapOperations(
      { ...base, kind: "lookup", matchAttribute: "code", create: true },
      draft.profile,
      outline,
    );
    expect(operation.binding).toEqual({
      relation: { relationTypeKey: "stores", objectTypeKey: "bin", matchBy: { attributeTypeKey: "code" } },
    });
  });

  it("fills a related record's name under the parent a column names, created when it does not exist", () => {
    const [operation] = mapOperations(
      {
        ...base,
        kind: "related",
        related: { fills: "name", parentType: "area", parentColumn: "Area", createParent: true },
      },
      draft.profile,
      outline,
    );
    expect(operation).toMatchObject({ kind: "mapColumn", source: "shelves-shelf", column: "Bins" });
    expect(operation.binding).toEqual({
      relatedRecord: {
        relationTypeKey: "stores",
        objectTypeKey: "bin",
        applicationKey: "shop",
        parent: { objectTypeKey: "area", matchBy: { field: "name" }, column: "Area", missing: "create" },
        field: "name",
      },
    });
  });
});
