/**
 * Layout editing in the model editor's preview (0.10 A4b, D46, D50): each change to a detail page or a
 * table view as the operations the server applies (A2's view verbs, D19), so one choice is one step.
 *
 * Panels are addressed by the page (`applicationKey`, `detail`: the page's type) and their key, a
 * table view by its key. A panel's `order` counts within its region and the server keeps it between
 * its neighbours when a panel moves (D35), so a move is a position in the page's declared list.
 */

import { attributeName } from "@/model/fields";
import type { DetailViewDefinition, DraftOperation, EngineModel, PanelDefinition, TableViewDefinition } from "@/types";
import { keyFromLabel } from "@/features/model-editor/outline";
import type { FieldValues, OperationField, OperationSpec } from "@/features/model-editor/operations";

export type Region = "main" | "side";

/** Where the page and the view stand: the application and the type they show. */
export interface LayoutPlace {
  applicationKey: string;
  objectTypeKey: string;
}

const page = (place: LayoutPlace) => ({ applicationKey: place.applicationKey, detail: place.objectTypeKey });

/** A region's panels in the order the record screen shows them. */
export function regionPanels(detail: DetailViewDefinition, region: Region): PanelDefinition[] {
  return detail.panels.filter((panel) => panel.region === region).sort((a, b) => a.order - b.order);
}

/** Move a panel up or down within its region. */
export function movePanel(
  place: LayoutPlace,
  detail: DetailViewDefinition,
  key: string,
  direction: -1 | 1,
): DraftOperation[] {
  const panel = detail.panels.find((item) => item.key === key);
  if (!panel) return [];
  const siblings = regionPanels(detail, panel.region);
  const neighbour = siblings[siblings.findIndex((item) => item.key === key) + direction];
  if (!neighbour) return [];
  const position = detail.panels.findIndex((item) => item.key === neighbour.key);
  return [{ kind: "moveViewItem", ...page(place), list: "panels", item: key, position }];
}

/**
 * Move a panel to the other region, after that region's last panel (or, with `before`, ahead of
 * that panel): one request, the region set and then the place in the list.
 */
export function panelToRegion(
  place: LayoutPlace,
  detail: DetailViewDefinition,
  key: string,
  region: Region,
  before?: string,
): DraftOperation[] {
  const panel = detail.panels.find((item) => item.key === key);
  if (!panel) return [];
  const others = detail.panels.filter((item) => item.key !== key);
  const anchor = before ? others.findIndex((item) => item.key === before) : -1;
  const last = regionPanels({ ...detail, panels: others }, region).at(-1);
  const position = anchor >= 0 ? anchor : last ? others.findIndex((item) => item.key === last.key) + 1 : others.length;
  const operations: DraftOperation[] = [];
  if (panel.region !== region)
    operations.push({ kind: "setViewProperty", ...page(place), panel: key, property: "region", value: region });
  operations.push({ kind: "moveViewItem", ...page(place), list: "panels", item: key, position });
  return operations;
}

export function setPanelVisible(place: LayoutPlace, key: string, visible: boolean): DraftOperation[] {
  return [{ kind: "setViewProperty", ...page(place), panel: key, property: "visible", value: visible }];
}

export function removePanel(place: LayoutPlace, key: string): DraftOperation[] {
  return [{ kind: "removeViewItem", ...page(place), list: "panels", item: key }];
}

/** Move a field up or down within its attributes panel. */
export function moveField(place: LayoutPlace, panel: PanelDefinition, field: string, direction: -1 | 1) {
  if (panel.type !== "attributes") return [];
  const position = panel.config.fields.indexOf(field) + direction;
  if (position < 0 || position >= panel.config.fields.length) return [];
  return [{ kind: "moveViewItem", ...page(place), panel: panel.key, list: "fields", item: field, position }];
}

/** Move a field into another attributes panel (a field group, D50), at its end: one step. */
export function fieldToPanel(place: LayoutPlace, from: string, to: string, field: string, position?: number) {
  return [
    { kind: "removeViewItem", ...page(place), panel: from, list: "fields", item: field },
    {
      kind: "insertViewItem",
      ...page(place),
      panel: to,
      list: "fields",
      item: field,
      ...(position === undefined ? {} : { position }),
    },
  ];
}

export function removeField(place: LayoutPlace, panel: string, field: string): DraftOperation[] {
  return [{ kind: "removeViewItem", ...page(place), panel, list: "fields", item: field }];
}

/** Move a table column left or right. */
export function moveColumn(
  place: LayoutPlace,
  view: TableViewDefinition,
  column: string,
  direction: -1 | 1,
): DraftOperation[] {
  const position = view.config.columns.indexOf(column) + direction;
  if (position < 0 || position >= view.config.columns.length) return [];
  return [
    {
      kind: "moveViewItem",
      applicationKey: place.applicationKey,
      view: view.key,
      list: "columns",
      item: column,
      position,
    },
  ];
}

export function removeColumn(place: LayoutPlace, view: TableViewDefinition, column: string): DraftOperation[] {
  return [
    { kind: "removeViewItem", applicationKey: place.applicationKey, view: view.key, list: "columns", item: column },
  ];
}

/**
 * The operations that make a list hold `chosen`: the items left out removed, the new ones added at
 * the end, so the items kept keep their order.
 */
export function chooseList(
  target: Record<string, unknown>,
  list: string,
  current: readonly string[],
  chosen: readonly string[],
): DraftOperation[] {
  return [
    ...current
      .filter((item) => !chosen.includes(item))
      .map((item) => ({ kind: "removeViewItem", ...target, list, item })),
    ...chosen
      .filter((item) => !current.includes(item))
      .map((item) => ({ kind: "insertViewItem", ...target, list, item })),
  ];
}

/** The fields a panel's columns may show: the name and the attributes of the types it lists. */
export function columnChoices(model: EngineModel, place: LayoutPlace, panel: PanelDefinition): string[] {
  const types =
    panel.type === "children"
      ? panel.config.objectTypeKeys
      : panel.type === "table"
        ? [panel.config.objectTypeKey]
        : panel.type === "relations"
          ? model.objectTypeRelations
              .filter((binding) => panel.config.relationTypeKeys.includes(binding.relationTypeKey))
              .flatMap((binding) => {
                const out = binding.fromObjectTypeKey === place.objectTypeKey ? [binding.toObjectTypeKey] : [];
                const back = binding.toObjectTypeKey === place.objectTypeKey ? [binding.fromObjectTypeKey] : [];
                return panel.config.direction === "outgoing"
                  ? out
                  : panel.config.direction === "incoming"
                    ? back
                    : [...out, ...back];
              })
          : [];
  const keys = types.flatMap(
    (key) => model.objectTypes.find((item) => item.key === key)?.attributes.map((item) => item.attributeTypeKey) ?? [],
  );
  return ["name", ...new Set(keys)];
}

/** A panel's current columns, where its type has them. */
export function panelColumns(panel: PanelDefinition): string[] | undefined {
  if (panel.type === "children" || panel.type === "table" || panel.type === "relations") return panel.config.columns;
  return undefined;
}

/** The type's attributes that no attributes panel of the page shows. */
export function fieldsNotOnPage(model: EngineModel, detail: DetailViewDefinition): string[] {
  const shown = new Set(detail.panels.flatMap((panel) => (panel.type === "attributes" ? panel.config.fields : [])));
  const type = model.objectTypes.find((item) => item.key === detail.objectTypeKey);
  return (type?.attributes ?? [])
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((item) => item.attributeTypeKey)
    .filter((key) => !shown.has(key));
}

// --- the dialogs, as descriptors the editor's one OperationDialog renders (D38) ---

const options = (model: EngineModel, keys: readonly string[]) =>
  keys.map((key) => ({ value: key, label: attributeName(model, key) }));

function spec(
  id: string,
  title: string,
  fields: OperationField[],
  initial: FieldValues,
  build: (values: FieldValues) => DraftOperation[],
): OperationSpec {
  return {
    id,
    on: "objectType",
    label: () => `${title}…`,
    title: () => title,
    fields: () => fields,
    initial: () => initial,
    build: (values) => build(values),
  };
}

const list = (value: unknown) => (Array.isArray(value) ? (value as string[]) : []);
const text = (value: unknown) => (typeof value === "string" ? value : "");

export function renamePanelSpec(place: LayoutPlace, panel: PanelDefinition): OperationSpec {
  return spec(
    "layout-rename-panel",
    `Rename ${panel.title}`,
    [{ name: "title", label: "Title", type: "text", required: true }],
    { title: panel.title },
    (values) => [
      { kind: "setViewProperty", ...page(place), panel: panel.key, property: "title", value: text(values.title) },
    ],
  );
}

/** A new field group: an attributes panel in `main`, with the fields chosen moved into it (D50). */
export function newFieldGroupSpec(model: EngineModel, place: LayoutPlace, detail: DetailViewDefinition): OperationSpec {
  const fields = detail.panels.flatMap((panel) =>
    panel.type === "attributes" ? panel.config.fields.map((field) => ({ field, panel: panel.key })) : [],
  );
  const notShown = fieldsNotOnPage(model, detail);
  return spec(
    "layout-new-field-group",
    "New field group",
    [
      { name: "title", label: "Title", type: "text", required: true },
      {
        name: "fields",
        label: "Fields",
        type: "checkboxes",
        options: options(model, [...fields.map((item) => item.field), ...notShown]),
        hint: "Chosen fields move into the group from where they are now.",
      },
    ],
    { title: "", fields: [] },
    (values) => {
      const taken = new Set(detail.panels.map((panel) => panel.key));
      const key = keyFromLabel(text(values.title) || "group", taken);
      const chosen = list(values.fields);
      return [
        {
          kind: "insertViewItem",
          ...page(place),
          list: "panels",
          item: { key, title: text(values.title), type: "attributes", region: "main", config: { fields: [] } },
        },
        ...chosen.flatMap((field) => {
          const from = fields.find((item) => item.field === field);
          return from
            ? fieldToPanel(place, from.panel, key, field)
            : [{ kind: "insertViewItem", ...page(place), panel: key, list: "fields", item: field }];
        }),
      ];
    },
  );
}

export function addFieldSpec(
  model: EngineModel,
  place: LayoutPlace,
  panel: PanelDefinition,
  detail: DetailViewDefinition,
) {
  return spec(
    "layout-add-field",
    `Add fields to ${panel.title}`,
    [
      {
        name: "fields",
        label: "Fields not on the page",
        type: "checkboxes",
        options: options(model, fieldsNotOnPage(model, detail)),
      },
    ],
    { fields: [] },
    (values) =>
      list(values.fields).map((field) => ({
        kind: "insertViewItem",
        ...page(place),
        panel: panel.key,
        list: "fields",
        item: field,
      })),
  );
}

export function panelColumnsSpec(model: EngineModel, place: LayoutPlace, panel: PanelDefinition): OperationSpec {
  const current = panelColumns(panel) ?? [];
  return spec(
    "layout-panel-columns",
    `Columns of ${panel.title}`,
    [
      {
        name: "columns",
        label: "Columns",
        type: "checkboxes",
        options: options(model, [...new Set([...current, ...columnChoices(model, place, panel)])]),
      },
    ],
    { columns: current },
    (values) => chooseList({ ...page(place), panel: panel.key }, "columns", current, list(values.columns)),
  );
}

/** A relations panel's default sort among its sort fields (schema 0.7). */
export function panelSortSpec(
  model: EngineModel,
  place: LayoutPlace,
  panel: PanelDefinition,
): OperationSpec | undefined {
  if (panel.type !== "relations" || !panel.config.sortFields?.length) return undefined;
  return spec(
    "layout-panel-sort",
    `Sort ${panel.title}`,
    [
      {
        name: "sort",
        label: "Sorted by",
        type: "select",
        required: true,
        options: options(model, panel.config.sortFields),
      },
    ],
    { sort: (panel.config.defaultSort ?? panel.config.sortFields[0]).replace(/^-/, "") },
    (values) => [
      { kind: "setViewProperty", ...page(place), panel: panel.key, property: "defaultSort", value: text(values.sort) },
    ],
  );
}

const viewTarget = (place: LayoutPlace, view: TableViewDefinition) => ({
  applicationKey: place.applicationKey,
  view: view.key,
});

/** The fields a table view may list: the name and the type's attributes, with what it lists now. */
function viewChoices(model: EngineModel, view: TableViewDefinition, current: readonly string[]) {
  const type = model.objectTypes.find((item) => item.key === view.objectTypeKey);
  return [...new Set([...current, "name", ...(type?.attributes.map((item) => item.attributeTypeKey) ?? [])])];
}

export function tableColumnsSpec(model: EngineModel, place: LayoutPlace, view: TableViewDefinition): OperationSpec {
  const current = view.config.columns;
  return spec(
    "layout-table-columns",
    `Columns of ${view.name}`,
    [
      {
        name: "columns",
        label: "Columns",
        type: "checkboxes",
        options: options(model, viewChoices(model, view, current)),
      },
    ],
    { columns: current },
    (values) => chooseList(viewTarget(place, view), "columns", current, list(values.columns)),
  );
}

export function tableFiltersSpec(model: EngineModel, place: LayoutPlace, view: TableViewDefinition): OperationSpec {
  const current = view.config.filterFields;
  return spec(
    "layout-table-filters",
    `Filters of ${view.name}`,
    [
      {
        name: "filters",
        label: "Filters",
        type: "checkboxes",
        options: options(model, viewChoices(model, view, current)),
      },
    ],
    { filters: current },
    (values) => chooseList(viewTarget(place, view), "filterFields", current, list(values.filters)),
  );
}

/** The default sort, among the view's sort fields; a field not yet sortable joins them first. */
export function tableSortSpec(model: EngineModel, place: LayoutPlace, view: TableViewDefinition): OperationSpec {
  return spec(
    "layout-table-sort",
    `Default sort of ${view.name}`,
    [
      {
        name: "sort",
        label: "Sorted by",
        type: "select",
        required: true,
        options: options(model, view.config.sortFields),
      },
      { name: "descending", label: "Descending", type: "checkbox" },
    ],
    { sort: view.config.defaultSort.replace(/^-/, ""), descending: view.config.defaultSort.startsWith("-") },
    (values) => [
      {
        kind: "setViewProperty",
        ...viewTarget(place, view),
        property: "defaultSort",
        value: `${values.descending ? "-" : ""}${text(values.sort)}`,
      },
    ],
  );
}
