import { fieldOptions } from "@/features/model-editor/operations";
import { describe, expect, it } from "vitest";
import example from "../../../../guide/samples/model.json";
import {
  addPanelSpec,
  chooseList,
  fieldToPanel,
  fieldsNotOnPage,
  moveColumn,
  moveField,
  movePanel,
  newFieldGroupSpec,
  pageHeaderSpec,
  panelColumnsSpec,
  panelSettingsSpec,
  panelToRegion,
  tableColumnsSpec,
  tableFiltersSpec,
  tableMenuSpec,
  tableAvailabilitySpec,
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
      applications: [],
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

// The guide's example model: Network lists the stop with its municipality, operator and modes; the
// names application holds the translations under their languages.
const bare = example as unknown as EngineModel;
// The engine serves the placements with the model; here they are read off its containment bindings.
const guide = {
  ...bare,
  placements: {
    applications: bare.applications.map((application) => ({
      applicationKey: application.key,
      topLevelObjectTypeKeys: [],
      parents: application.objectTypeKeys.map((key) => ({
        objectTypeKey: key,
        possibleObjectTypeKeys: [],
        childObjectTypeKeys: application.objectTypeKeys.filter((child) =>
          bare.objectTypeRelations.some(
            (binding) =>
              binding.fromObjectTypeKey === key &&
              binding.toObjectTypeKey === child &&
              bare.objectTypes
                .find((type) => type.key === child)
                ?.behavior?.parentRelationTypeKeys?.includes(binding.relationTypeKey),
          ),
        ),
      })),
    })),
  },
} as unknown as EngineModel;
const stopPlace = { applicationKey: "network", objectTypeKey: "stop" };
const guideOptions = (operation: ReturnType<typeof tableColumnsSpec>) =>
  operation
    .fields?.(undefined as never, undefined as never)
    .flatMap((field) => (field.type === "checkboxes" ? fieldOptions(field, {}) : [])) ?? [];

describe("related columns and panels in the editor (0.13 RL)", () => {
  const stops = guide.applications
    .find((item) => item.key === "network")
    ?.views.find((view) => view.type === "table" && view.objectTypeKey === "stop") as TableViewDefinition;

  it("unfolds a relationship into the fields of its records and where they sit", () => {
    const options = guideOptions(tableColumnsSpec(guide, stopPlace, stops));
    const translation = options.filter((option) => option.under === "related:object-has-translation");
    expect(translation.map((option) => [option.value, option.label, option.group])).toEqual([
      ["related:object-has-translation.translated-name", "Translated name", undefined],
      ["related:object-has-translation.active", "Active", undefined],
      ["related:object-has-translation.ancestor:language.name", "Name", "Where they sit · Language"],
      ["related:object-has-translation.ancestor:language.language-code", "Language code", "Where they sit · Language"],
      ["related:object-has-translation.ancestor:language.description", "Description", "Where they sit · Language"],
      ["related:object-has-translation.ancestor:language.active", "Active", "Where they sit · Language"],
    ]);
    // The relationship stays a column of its own, and the filter offers it alone (K6).
    expect(options.map((option) => option.value)).toContain("related:object-has-translation");
    expect(
      guideOptions(tableFiltersSpec(guide, stopPlace, stops)).filter((option) => option.value.includes(".")),
    ).toEqual([]);
  });

  it("writes a checked field as the column related:<key>.<field>, keeping the others in order", () => {
    const column = "related:object-has-translation.ancestor:language.language-code";
    expect(
      tableColumnsSpec(guide, stopPlace, stops).build(
        { columns: [...stops.config.columns, column] },
        undefined as never,
        undefined as never,
      ),
    ).toEqual([{ kind: "insertViewItem", applicationKey: "network", view: stops.key, list: "columns", item: column }]);
  });

  it("offers a panel where its records sit: their ancestors, and their type when it lists several", () => {
    const detail = guide.applications
      .find((item) => item.key === "network")
      ?.details?.find((item) => item.objectTypeKey === "stop") as DetailViewDefinition;
    const codes = detail.panels.find((item) => item.key === "system-codes") as PanelDefinition;
    const offered = (panelDefinition: PanelDefinition) =>
      panelColumnsSpec(guide, stopPlace, panelDefinition)
        .fields?.(undefined as never, undefined as never)
        .flatMap((field) => (field.type === "checkboxes" ? fieldOptions(field, {}) : []))
        .filter((option) => option.group === "Where it sits")
        .map((option) => option.value);
    expect(offered(codes)).toEqual(["ancestor:system"]);
    const several = {
      ...codes,
      config: { ...codes.config, relationTypeKeys: ["system-code-maps-to", "stop-served-by-mode"], direction: "both" },
    } as PanelDefinition;
    expect(offered(several)).toContain("objectType");
  });

  it("builds Add panel… as the server's addPanel, titled from the relationship read from the type", () => {
    const detail = { objectTypeKey: "stop", panels: [] } as unknown as DetailViewDefinition;
    const operation = addPanelSpec(guide, stopPlace, detail);
    const initial = operation.initial?.(undefined as never, undefined as never) ?? {};
    expect(initial.relation).toBe("outgoing:stop-served-by-mode");
    expect(initial.title).toBe("Served by mode");
    expect(
      operation.build(
        { ...initial, relation: "incoming:system-code-maps-to", title: "System codes", region: "side" },
        undefined as never,
        undefined as never,
      ),
    ).toEqual([
      {
        kind: "addPanel",
        applicationKey: "network",
        detail: "stop",
        show: { relations: { relation: "system-code-maps-to", direction: "incoming" } },
        region: "side",
        title: "System codes",
      },
    ]);
    // The title follows the relationship while it is the one the choice gave.
    const next = operation.follow?.(
      { ...initial, relation: "incoming:system-code-maps-to" },
      initial,
      "relation",
      undefined as never,
    );
    expect(next?.title).toBe("Is represented by system code");
  });

  it("marks the relationships the page already shows", () => {
    const detail = guide.applications
      .find((item) => item.key === "network")
      ?.details?.find((item) => item.objectTypeKey === "stop") as DetailViewDefinition;
    const relation = addPanelSpec(guide, stopPlace, detail)
      .fields?.(undefined as never, undefined as never)
      .find((field) => field.name === "relation");
    const labels = relation && "options" in relation ? fieldOptions(relation, {}).map((option) => option.label) : [];
    expect(labels).toContain("Served by mode (on the page)");
    expect(labels).toContain("Is represented by system code (on the page)");
  });
});

describe("the settings of a page, a table and a panel (0.13 ED)", () => {
  const none = undefined as never;

  it("sets the header and the breadcrumbs, sending only what changed", () => {
    const spec = pageHeaderSpec(model, place, detail);
    const initial = spec.initial?.(none, none) ?? {};
    expect(initial).toMatchObject({ title: "name", subtitle: "", headerType: true, crumbAncestors: true });
    expect(spec.build(initial, none, none)).toEqual([]);
    expect(
      spec.build(
        { ...initial, title: "code", subtitle: "colour", headerType: false, crumbAncestors: false },
        none,
        none,
      ),
    ).toEqual([
      { kind: "setViewProperty", ...target, property: "header.titleField", value: "code" },
      { kind: "setViewProperty", ...target, property: "header.subtitleField", value: "colour" },
      { kind: "setViewProperty", ...target, property: "header.showObjectType", value: false },
      { kind: "setViewProperty", ...target, property: "breadcrumbs.showAncestors", value: false },
    ]);
  });

  const view = {
    key: "items",
    name: "Items",
    type: "table",
    objectTypeKey: "item",
    config: { columns: ["name"], filterFields: [], sortFields: ["name", "code"], defaultSort: "-code", pageSize: 20 },
  } as unknown as TableViewDefinition;
  const sortable = {
    ...model,
    attributeTypes: model.attributeTypes.map((item) => ({ ...item, features: { sortable: item.key !== "price" } })),
  } as unknown as EngineModel;

  it("sets a table's sort menu and page size, moving the default sort off a field that leaves the menu", () => {
    const spec = tableMenuSpec(sortable, place, view);
    const field = spec.fields?.(none, none)[0];
    expect(field && "options" in field ? fieldOptions(field, {}).map((item) => item.value) : []).toEqual([
      "name",
      "code",
      "colour",
    ]);
    expect(spec.build({ sortFields: ["name", "code"], pageSize: "20" }, none, none)).toEqual([]);
    expect(spec.build({ sortFields: ["name", "colour"], pageSize: "50" }, none, none)).toEqual([
      { kind: "setViewProperty", applicationKey: "catalogue", view: "items", property: "defaultSort", value: "name" },
      {
        kind: "setViewProperty",
        applicationKey: "catalogue",
        view: "items",
        property: "sortFields",
        value: ["name", "colour"],
      },
      { kind: "setViewProperty", applicationKey: "catalogue", view: "items", property: "pageSize", value: 50 },
    ]);
  });

  it("sets what a hierarchy panel and a table panel show", () => {
    const hierarchy = panelSettingsSpec(model, place, panel("hierarchy", "side", 10))!;
    expect(hierarchy.build({ showParent: true, showAncestors: false }, none, none)).toEqual([
      { kind: "setViewProperty", ...target, panel: "hierarchy", property: "showAncestors", value: false },
    ]);
    const table = {
      key: "children",
      title: "Children",
      type: "table",
      region: "main",
      order: 30,
      visible: true,
      config: { objectTypeKey: "item", columns: [], filterByParent: false, pageSize: 10 },
    } as unknown as PanelDefinition;
    expect(panelSettingsSpec(model, place, table)!.build({ filterByParent: true, pageSize: "25" }, none, none)).toEqual(
      [
        { kind: "setViewProperty", ...target, panel: "children", property: "filterByParent", value: true },
        { kind: "setViewProperty", ...target, panel: "children", property: "pageSize", value: 25 },
      ],
    );
    expect(panelSettingsSpec(model, place, panel("details", "main", 10, []))).toBeUndefined();
  });

  it("offers a table the boolean attributes of its type as the one that marks a record inactive (0.13 LB)", () => {
    const flagged = {
      attributeTypes: [
        { key: "code", name: "Code", valueType: "text" },
        { key: "live", name: "Live", valueType: "boolean" },
        { key: "stocked", name: "Stocked", valueType: "boolean" },
      ],
      objectTypes: [
        {
          key: "item",
          attributes: ["code", "live"].map((attributeTypeKey, order) => ({ attributeTypeKey, order })),
        },
      ],
    } as unknown as EngineModel;
    const view = {
      key: "items",
      name: "Items",
      type: "table",
      objectTypeKey: "item",
      config: { columns: ["name"], filterFields: ["name"], sortFields: ["name"], defaultSort: "name", pageSize: 50 },
    } as TableViewDefinition;
    const spec = tableAvailabilitySpec(flagged, place, view);
    const field = spec.fields?.(undefined as never, undefined as never)[0] as { options: { value: string }[] };
    expect(field.options.map((option) => option.value)).toEqual(["", "live"]);
    const target = { applicationKey: "catalogue", view: "items" };
    expect(spec.build({ availability: "live" }, undefined as never, undefined as never)).toEqual([
      { kind: "setViewProperty", ...target, property: "availabilityField", value: "live" },
    ]);
    // Nothing changes while it stays as it is, and None takes it away.
    expect(spec.build({ availability: "" }, undefined as never, undefined as never)).toEqual([]);
    const set = { ...view, config: { ...view.config, availabilityField: "live" } };
    expect(
      tableAvailabilitySpec(flagged, place, set).build({ availability: "" }, undefined as never, undefined as never),
    ).toEqual([{ kind: "setViewProperty", ...target, property: "availabilityField", value: null }]);
  });
});
