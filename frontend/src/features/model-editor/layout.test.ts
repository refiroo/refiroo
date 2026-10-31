import { fieldOptions } from "@/features/model-editor/operations";
import { describe, expect, it } from "vitest";
import {
  chooseList,
  fieldToPanel,
  fieldsNotOnPage,
  moveColumn,
  moveField,
  movePanel,
  newFieldGroupSpec,
  panelToRegion,
  tableColumnsSpec,
  tableFiltersSpec,
  tableSortSpec,
} from "@/features/model-editor/layout";
import type { DetailViewDefinition, EngineModel, PanelDefinition, TableViewDefinition } from "@/types";

const place = { applicationKey: "catalogue", objectTypeKey: "item" };
const target = { applicationKey: "catalogue", detail: "item" };

const panel = (key: string, region: "main" | "side", order: number, fields?: string[]): PanelDefinition =>
  (fields
    ? { key, title: key, type: "attributes", region, order, visible: true, config: { fields } }
    : {
        key,
        title: key,
        type: "hierarchy",
        region,
        order,
        visible: true,
        config: { showParent: true, showAncestors: true },
      }) as PanelDefinition;

// Declared order: details (main 10), hierarchy (side 10), related (main 20), notes (side 20).
const detail: DetailViewDefinition = {
  objectTypeKey: "item",
  breadcrumbs: { showApplication: true, showObjectType: true, showAncestors: true },
  header: { titleField: "name", showObjectType: true },
  panels: [
    panel("details", "main", 10, ["code", "colour"]),
    panel("hierarchy", "side", 10),
    panel("related", "main", 20),
    panel("notes", "side", 20, []),
  ],
};

const model = {
  attributeTypes: [
    { key: "code", name: "Code" },
    { key: "colour", name: "Colour" },
    { key: "price", name: "Price" },
  ],
  objectTypes: [
    {
      key: "item",
      attributes: ["code", "colour", "price"].map((attributeTypeKey, order) => ({ attributeTypeKey, order })),
    },
  ],
  objectTypeRelations: [],
} as unknown as EngineModel;

describe("layout operations", () => {
  it("moves a panel past its region's neighbour, by its place in the declared list", () => {
    expect(movePanel(place, detail, "related", -1)).toEqual([
      { kind: "moveViewItem", ...target, list: "panels", item: "related", position: 0 },
    ]);
    expect(movePanel(place, detail, "details", 1)).toEqual([
      { kind: "moveViewItem", ...target, list: "panels", item: "details", position: 2 },
    ]);
    expect(movePanel(place, detail, "details", -1)).toEqual([]);
  });

  it("moves a panel to the other region in one request: its region, then its place", () => {
    expect(panelToRegion(place, detail, "related", "side")).toEqual([
      { kind: "setViewProperty", ...target, panel: "related", property: "region", value: "side" },
      { kind: "moveViewItem", ...target, list: "panels", item: "related", position: 3 },
    ]);
    expect(panelToRegion(place, detail, "related", "side", "hierarchy")).toEqual([
      { kind: "setViewProperty", ...target, panel: "related", property: "region", value: "side" },
      { kind: "moveViewItem", ...target, list: "panels", item: "related", position: 1 },
    ]);
  });

  it("moves a field within its group, and into another group in one step (D50)", () => {
    expect(moveField(place, detail.panels[0], "colour", -1)).toEqual([
      { kind: "moveViewItem", ...target, panel: "details", list: "fields", item: "colour", position: 0 },
    ]);
    expect(moveField(place, detail.panels[0], "colour", 1)).toEqual([]);
    expect(fieldToPanel(place, "details", "notes", "code")).toEqual([
      { kind: "removeViewItem", ...target, panel: "details", list: "fields", item: "code" },
      { kind: "insertViewItem", ...target, panel: "notes", list: "fields", item: "code" },
    ]);
  });

  it("makes a list hold what was chosen, keeping the order of what stays", () => {
    expect(
      chooseList(
        { applicationKey: "catalogue", view: "items" },
        "columns",
        ["name", "code", "colour"],
        ["name", "colour", "price"],
      ),
    ).toEqual([
      { kind: "removeViewItem", applicationKey: "catalogue", view: "items", list: "columns", item: "code" },
      { kind: "insertViewItem", applicationKey: "catalogue", view: "items", list: "columns", item: "price" },
    ]);
  });

  it("lists the attributes no group of the page shows", () => {
    expect(fieldsNotOnPage(model, detail)).toEqual(["price"]);
  });

  it("adds a field group and moves the chosen fields into it, a field not on the page added", () => {
    const operations = newFieldGroupSpec(model, place, detail).build(
      { title: "Pricing", fields: ["colour", "price"] },
      undefined as never,
      undefined as never,
    );
    expect(operations).toEqual([
      {
        kind: "insertViewItem",
        ...target,
        list: "panels",
        item: { key: "pricing", title: "Pricing", type: "attributes", region: "main", config: { fields: [] } },
      },
      { kind: "removeViewItem", ...target, panel: "details", list: "fields", item: "colour" },
      { kind: "insertViewItem", ...target, panel: "pricing", list: "fields", item: "colour" },
      { kind: "insertViewItem", ...target, panel: "pricing", list: "fields", item: "price" },
    ]);
  });

  it("moves a column and sets the default sort, descending with a minus", () => {
    const view = {
      key: "items",
      name: "Items",
      type: "table",
      objectTypeKey: "item",
      config: {
        columns: ["name", "code"],
        filterFields: ["name"],
        sortFields: ["name", "code"],
        defaultSort: "name",
        pageSize: 50,
      },
    } as TableViewDefinition;
    expect(moveColumn(place, view, "code", -1)).toEqual([
      { kind: "moveViewItem", applicationKey: "catalogue", view: "items", list: "columns", item: "code", position: 0 },
    ]);
    expect(
      tableSortSpec(model, place, view).build(
        { sort: "code", descending: true },
        undefined as never,
        undefined as never,
      ),
    ).toEqual([
      { kind: "setViewProperty", applicationKey: "catalogue", view: "items", property: "defaultSort", value: "-code" },
    ]);
  });

  it("offers a table view the relationships its records hold, the one to their parent first (D358)", () => {
    const related = {
      attributeTypes: [{ key: "code", name: "Code" }],
      objectTypes: [
        { key: "group", attributes: [] },
        { key: "item", attributes: [{ attributeTypeKey: "code", order: 0 }] },
        { key: "tag", attributes: [] },
        {
          key: "entry",
          attributes: [],
          behavior: { parentRelationTypeKeys: ["group-contains-entry"] },
        },
      ],
      relationTypes: [
        { key: "entry-tagged", name: "Tagged", reverseKey: "tag-of", reverseName: "Tag of" },
        { key: "group-contains-entry", name: "Contains entry", reverseKey: "entry-in-group", reverseName: "In group" },
      ],
      objectTypeRelations: [
        { relationTypeKey: "entry-tagged", fromObjectTypeKey: "entry", toObjectTypeKey: "tag" },
        { relationTypeKey: "group-contains-entry", fromObjectTypeKey: "group", toObjectTypeKey: "entry" },
      ],
    } as unknown as EngineModel;
    const view = {
      key: "entries",
      name: "Entries",
      type: "table",
      objectTypeKey: "entry",
      config: { columns: ["name"], filterFields: ["name"], sortFields: ["name"], defaultSort: "name", pageSize: 20 },
    } as TableViewDefinition;
    const choices = (operation: ReturnType<typeof tableColumnsSpec>) =>
      operation
        .fields?.(undefined as never, undefined as never)
        .flatMap((field) => (field.type === "checkboxes" ? fieldOptions(field, {}) : []));
    const offered = [
      { value: "name", label: "Name" },
      { value: "related:entry-in-group", label: "In group" },
      { value: "related:entry-tagged", label: "Tagged" },
    ];
    expect(choices(tableColumnsSpec(related, place, view))).toEqual(offered);
    expect(choices(tableFiltersSpec(related, place, view))).toEqual(offered);
    expect(
      tableFiltersSpec(related, place, view).build(
        { filters: ["name", "related:entry-in-group"] },
        undefined as never,
        undefined as never,
      ),
    ).toEqual([
      {
        kind: "insertViewItem",
        applicationKey: "catalogue",
        view: "entries",
        list: "filterFields",
        item: "related:entry-in-group",
      },
    ]);
  });
});
