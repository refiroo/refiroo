import { describe, expect, it } from "vitest";
import { outlineFixture } from "@/test/draftOutline";
import {
  actionOptions,
  addMatrix,
  cellOptions,
  changeMatrix,
  followMatrix,
  matrixValues,
  newMatrixValues,
  rowOptions,
} from "@/features/model-editor/matrixView";
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
  const type = (key: string, parents: string[], attributes = [attribute("label")]) => ({
    key,
    name: key,
    pluralName: `${key}s`,
    rootCreatable: !parents.length,
    parents,
    attributes,
    mark: "released" as const,
  });
  return {
    ...base,
    applications: [
      { ...base.applications[0], key: "a", name: "A", objectTypeKeys: ["item"], views: [] },
      { ...base.applications[0], key: "b", name: "B", objectTypeKeys: ["tongue", "word"], views: [] },
    ],
    objectTypes: [
      type("item", [], [attribute("code", { unique: true })]),
      type("tongue", [], [attribute("iso", { unique: true })]),
      type("word", ["tongue"], [attribute("text", { required: true }), attribute("active")]),
      type("loose", []),
    ],
    relationTypes: [{ key: "has", name: "Has", reverseName: "Of", containment: false, mark: "released" }],
    relations: [
      { relationType: "has", from: "item", to: "word", required: true, containment: false, mark: "released" },
      { relationType: "has", from: "item", to: "loose", required: false, containment: false, mark: "released" },
    ],
  };
}

describe("a relation matrix in the dialog", () => {
  const outline = worded();

  it("offers only rows and cells that give columns, read from either end", () => {
    expect(rowOptions(outline).map((option) => option.value)).toEqual(["item"]);
    expect(cellOptions(outline, "item").map((option) => option.value)).toEqual(["has|outgoing|word"]);
    const incoming = { ...outline, relations: [{ ...outline.relations[0], from: "word", to: "item" }] };
    expect(cellOptions(incoming, "item").map((option) => option.value)).toEqual(["has|incoming|word"]);
  });

  it("starts from defaults the server accepts and hides what cannot succeed", () => {
    const values = newMatrixValues<Record<string, unknown>>(outline);
    expect(values).toMatchObject({
      row: "item",
      cell: "has|outgoing|word",
      column: "tongue",
      columnLabel: "iso",
      cellFields: ["text", "active"],
      rowColumns: ["name", "code"],
      actions: ["create", "edit"],
      name: "item words",
    });
    // Required, so no unlink; a cell without its required field cannot be created.
    expect(actionOptions(outline, values).map((option) => option.value)).toEqual(["create", "edit", "link"]);
    const without = followMatrix<Record<string, unknown>>(
      outline,
      { ...values, cellFields: ["active"] },
      values,
      "cellFields",
    );
    expect(without.actions).toEqual(["edit"]);
  });

  it("lists what the application lacks with the view, in one step", () => {
    const operations = addMatrix(outline, "b", newMatrixValues(outline));
    expect(operations.map((item) => item.kind)).toEqual(["listObjectType", "addView"]);
    expect(operations[0]).toMatchObject({ applicationKey: "b", objectType: "item" });
    expect(operations[1]).toMatchObject({
      view: { key: "item-words", type: "relationMatrix", config: { relationTypeKey: "has", direction: "outgoing" } },
    });
  });

  it("changes only the properties that moved, keeping a name that was typed", () => {
    const start = newMatrixValues<Record<string, unknown>>(outline);
    const [, view] = addMatrix(outline, "b", start);
    const declared = (view as unknown as { view: { key: string; name: string; config: Record<string, unknown> } }).view;
    const matrix = {
      key: declared.key,
      name: declared.name,
      type: "relationMatrix",
      shows: [],
      matrix: declared.config,
      mark: "new" as const,
    };
    const withView: ModelDraftOutline = {
      ...outline,
      applications: outline.applications.map((item) =>
        item.key === "b" ? { ...item, objectTypeKeys: [...item.objectTypeKeys, "item"], views: [matrix] } : item,
      ),
    };
    const values = { ...matrixValues<Record<string, unknown>>(matrix), cellFields: ["text"], name: "Words" };
    expect(changeMatrix(withView, "b", declared.key, values)).toEqual([
      { kind: "setViewProperty", applicationKey: "b", view: declared.key, property: "name", value: "Words" },
      { kind: "setViewProperty", applicationKey: "b", view: declared.key, property: "cellFields", value: ["text"] },
    ]);
    expect(followMatrix(outline, { ...values, column: "tongue" }, values, "column").name).toBe("Words");
  });
});
