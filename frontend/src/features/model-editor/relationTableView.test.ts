import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import {
  addTable,
  attributeOptions,
  bindingOptions,
  endColumnOptions,
  followTable,
  newTableValues,
} from "@/features/model-editor/relationTableView";
import type { ModelDraftOutline } from "@/types";

const attribute = (key: string, extra = {}) => ({
  attributeType: key,
  name: key,
  valueType: "text",
  required: false,
  readOnly: false,
  unique: false,
  sharedWith: [],
  mark: "released" as const,
  ...extra,
});

function worded(): ModelDraftOutline {
  const base = outlineFixture();
  const type = (key: string, attributes: ReturnType<typeof attribute>[]) => ({
    key,
    name: key,
    pluralName: `${key}s`,
    rootCreatable: true,
    parents: [],
    attributes,
    mark: "released" as const,
  });
  return {
    ...base,
    applications: [{ ...base.applications[0], key: "a", name: "A", objectTypeKeys: ["item"], views: [] }],
    objectTypes: [type("item", [attribute("code", { unique: true })]), type("place", [attribute("label")])],
    attributeTypes: [
      {
        key: "weight",
        name: "Weight",
        valueType: "integer",
        features: { filterable: true },
        boundBy: [],
        mark: "released",
      },
      { key: "note", name: "Note", valueType: "text", features: {}, boundBy: [], mark: "released" },
    ],
    relationTypes: [
      { key: "at", name: "At", reverseName: "Has", containment: false, mark: "released" },
      { key: "in", name: "In", containment: true, mark: "released" },
    ],
    relations: [
      {
        relationType: "at",
        from: "item",
        to: "place",
        required: false,
        containment: false,
        attributeTypeKeys: ["weight", "note"],
        mark: "released",
      },
      { relationType: "in", from: "place", to: "item", required: false, containment: true, mark: "released" },
    ],
  };
}

describe("a relationships table in the dialog (0.13 RV)", () => {
  const outline = worded();

  it("offers the bindings that are not containments, and each end's name and scalar attributes", () => {
    expect(bindingOptions(outline).map((item) => item.value)).toEqual(["at|item|place"]);
    expect(endColumnOptions(outline, "at|item|place", "from").map((item) => item.value)).toEqual(["name", "code"]);
    expect(attributeOptions(outline, "at|item|place").map((item) => item.label)).toEqual(["Weight", "Note"]);
  });

  it("starts from the first binding with its identifying columns and all its attributes", () => {
    const values = newTableValues<Record<string, unknown>>(outline);
    expect(values).toMatchObject({
      binding: "at|item|place",
      fromColumns: ["name", "code"],
      toColumns: ["name"],
      attributeColumns: ["weight", "note"],
    });
    expect(
      followTable<Record<string, unknown>>(outline, { ...values, binding: "" }, values, "binding").attributeColumns,
    ).toEqual([]);
  });

  it("adds the view with filters and sorts that follow its columns, and lists the types it needs", () => {
    const values = { ...newTableValues<Record<string, unknown>>(outline), name: "Item places", groupBy: "from" };
    const [list, add] = addTable(outline, "a", values);
    expect(list).toEqual({ kind: "listObjectType", applicationKey: "a", objectType: "place" });
    expect(add).toMatchObject({
      kind: "addView",
      view: {
        key: "item-places",
        type: "relationTable",
        config: {
          relationTypeKey: "at",
          groupBy: "from",
          filterFields: ["relation:weight"],
          sortFields: ["from:name", "from:code", "to:name", "relation:weight", "relation:note"],
          defaultSort: "from:name",
        },
      },
    });
  });
});
