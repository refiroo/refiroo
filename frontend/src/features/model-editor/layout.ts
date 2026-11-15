/**
 * Layout editing in the model editor's preview (0.10 A4b, D46, D50): each change to a detail page or a
 * table view as the operations the server applies (A2's view verbs, D19), so one choice is one step.
 *
 * Panels are addressed by the page (`applicationKey`, `detail`: the page's type) and their key, a
 * table view by its key. A panel's `order` counts within its region and the server keeps it between
 * its neighbours when a panel moves (D35), so a move is a position in the page's declared list.
 */

import { stringList, text } from "@/lib/coerce";
import { containedTypes, heldRelations, relationsPanelConfig, relationshipTitle } from "@/model/defaults";
import type { HeldRelation } from "@/model/defaults";
import { attributeName } from "@/model/fields";
import {
  attributeTypeFor,
  objectTypeFor,
  RELATED_FIELD_PREFIX,
  relatedAncestorTypes,
  relatedColumn,
  relatedTargetTypes,
  relationTypeFor,
} from "@/model/lookup";
import { ancestorObjectTypeKeys } from "@/model/placements";
import type { DetailViewDefinition, DraftOperation, EngineModel, PanelDefinition, TableViewDefinition } from "@/types";
import type { ChoiceOption } from "@/features/model-editor/ChoiceListField";
import { keyFromLabel } from "@/model/outline";
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

/** The types a panel lists. */
function panelTypes(model: EngineModel, place: LayoutPlace, panel: PanelDefinition): string[] {
  if (panel.type === "children") return panel.config.objectTypeKeys;
  if (panel.type === "table") return [panel.config.objectTypeKey];
  if (panel.type !== "relations") return [];
  return [
    ...new Set(
      model.objectTypeRelations
        .filter((binding) => panel.config.relationTypeKeys.includes(binding.relationTypeKey))
        .flatMap((binding) => {
          const out = binding.fromObjectTypeKey === place.objectTypeKey ? [binding.toObjectTypeKey] : [];
          const back = binding.toObjectTypeKey === place.objectTypeKey ? [binding.fromObjectTypeKey] : [];
          return panel.config.direction === "outgoing"
            ? out
            : panel.config.direction === "incoming"
              ? back
              : [...out, ...back];
        }),
    ),
  ];
}

/** The fields a panel's columns may show: the name and the attributes of the types it lists. */
export function columnChoices(model: EngineModel, place: LayoutPlace, panel: PanelDefinition): string[] {
  const keys = panelTypes(model, place, panel).flatMap(
    (key) => objectTypeFor(model, key)?.attributes.map((item) => item.attributeTypeKey) ?? [],
  );
  return ["name", ...new Set(keys)];
}

/**
 * Where the listed records sit (0.13 RL): `ancestor:<type>` for each type they can stand under, at any
 * depth (a panel takes the ancestor's name; a field of the ancestor is a related column's), and `objectType`
 * when the panel lists several types.
 */
export function whereItSits(model: EngineModel, place: LayoutPlace, panel: PanelDefinition): string[] {
  const types = panelTypes(model, place, panel);
  const ancestors = [...new Set(types.flatMap((key) => ancestorObjectTypeKeys(model, key)))];
  return [...ancestors.map((key) => `ancestor:${key}`), ...(types.length > 1 ? ["objectType"] : [])];
}

/** A panel's current columns, where its type has them. */
export function panelColumns(panel: PanelDefinition): string[] | undefined {
  if (panel.type === "children" || panel.type === "table" || panel.type === "relations") return panel.config.columns;
  return undefined;
}

/** The type's attributes that no attributes panel of the page shows. */
export function fieldsNotOnPage(model: EngineModel, detail: DetailViewDefinition): string[] {
  const shown = new Set(detail.panels.flatMap((panel) => (panel.type === "attributes" ? panel.config.fields : [])));
  const type = objectTypeFor(model, detail.objectTypeKey);
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
  follow?: (next: FieldValues, previous: FieldValues, changed: string) => FieldValues,
): OperationSpec {
  return {
    id,
    on: "objectType",
    label: () => `${title}…`,
    title: () => title,
    fields: () => fields,
    initial: () => initial,
    build: (values) => build(values),
    ...(follow ? { follow } : {}),
  };
}

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

/** The operations of a field group: an attributes panel with the fields chosen moved into it (D50). */
function fieldGroupOperations(
  place: LayoutPlace,
  detail: DetailViewDefinition,
  title: string,
  chosen: string[],
  region: Region,
): DraftOperation[] {
  const fields = detail.panels.flatMap((panel) =>
    panel.type === "attributes" ? panel.config.fields.map((field) => ({ field, panel: panel.key })) : [],
  );
  const taken = new Set(detail.panels.map((panel) => panel.key));
  const key = keyFromLabel(title || "group", taken);
  return [
    {
      kind: "insertViewItem",
      ...page(place),
      list: "panels",
      item: { key, title, type: "attributes", region, config: { fields: [] } },
    },
    ...chosen.flatMap((field) => {
      const from = fields.find((item) => item.field === field);
      return from
        ? fieldToPanel(place, from.panel, key, field)
        : [{ kind: "insertViewItem", ...page(place), panel: key, list: "fields", item: field }];
    }),
  ];
}

/** The fields a field group may take: the ones on the page and the ones not on it. */
function fieldGroupOptions(model: EngineModel, detail: DetailViewDefinition) {
  const fields = detail.panels.flatMap((panel) => (panel.type === "attributes" ? panel.config.fields : []));
  return options(model, [...fields, ...fieldsNotOnPage(model, detail)]);
}

/** A new field group: an attributes panel in `main`, with the fields chosen moved into it (D50). */
export function newFieldGroupSpec(model: EngineModel, place: LayoutPlace, detail: DetailViewDefinition): OperationSpec {
  return spec(
    "layout-new-field-group",
    "New field group",
    [
      { name: "title", label: "Title", type: "text", required: true },
      {
        name: "fields",
        label: "Fields",
        type: "checkboxes",
        options: fieldGroupOptions(model, detail),
        hint: "Chosen fields move into the group from where they are now.",
      },
    ],
    { title: "", fields: [] },
    (values) => fieldGroupOperations(place, detail, text(values.title), stringList(values.fields), "main"),
  );
}

const heldValue = (held: HeldRelation) => `${held.direction}:${held.relationTypeKey}`;
const heldOf = (value: unknown): HeldRelation | undefined => {
  const [direction, ...rest] = text(value).split(":");
  return direction === "outgoing" || direction === "incoming"
    ? { direction, relationTypeKey: rest.join(":") }
    : undefined;
};

/** Whether the page has a panel listing the relationship in that direction. */
function onThePage(detail: DetailViewDefinition, held: HeldRelation): boolean {
  return detail.panels.some(
    (panel) =>
      panel.type === "relations" &&
      panel.config.relationTypeKeys.includes(held.relationTypeKey) &&
      (panel.config.direction === held.direction || panel.config.direction === "both"),
  );
}

/**
 * Add panel… (0.13 RL): what the panel shows (the records of one of the type's relationships, the
 * records it contains, or a group of its fields), where, and its title. The server builds a related or
 * contained panel with the rule a new page follows (`addPanel`); its columns change afterwards with the
 * panel's Columns….
 */
export function addPanelSpec(model: EngineModel, place: LayoutPlace, detail: DetailViewDefinition): OperationSpec {
  const application = model.applications.find((item) => item.key === place.applicationKey);
  const held = heldRelations(model, place.objectTypeKey);
  const contained = containedTypes(model, place.objectTypeKey).filter((type) =>
    application?.objectTypeKeys.includes(type.key),
  );
  const kinds = [
    ...(held.length ? [{ value: "relations", label: "Related records" }] : []),
    ...(contained.length ? [{ value: "children", label: "Contained records" }] : []),
    { value: "fields", label: "Fields" },
  ];
  const relationOptions = held.map((item) => ({
    value: heldValue(item),
    label: `${relationshipTitle(model, item)}${onThePage(detail, item) ? " (on the page)" : ""}`,
  }));
  const firstRelation = held.find((item) => !onThePage(detail, item)) ?? held[0];
  const titleFor = (values: FieldValues) => {
    if (values.kind === "relations") {
      const choice = heldOf(values.relation);
      return choice ? relationshipTitle(model, choice) : "";
    }
    if (values.kind === "children") {
      const first = contained.find((type) => stringList(values.objectTypes).includes(type.key)) ?? contained[0];
      return first?.pluralName ?? "";
    }
    return "";
  };
  const initial: FieldValues = {
    kind: kinds[0].value,
    relation: firstRelation ? heldValue(firstRelation) : "",
    objectTypes: contained.map((type) => type.key),
    fields: [],
    region: "main",
    title: "",
  };
  initial.title = titleFor(initial);
  return spec(
    "layout-add-panel",
    "Add panel",
    [
      { name: "kind", label: "What the panel shows", type: "select", required: true, options: kinds },
      {
        name: "relation",
        label: "Relationship",
        type: "select",
        required: true,
        options: relationOptions,
        when: (values) => values.kind === "relations",
        hint: (values) => {
          const choice = heldOf(values.relation);
          if (!choice) return undefined;
          const columns = relationsPanelConfig(model, place.objectTypeKey, choice).columns;
          return `Columns: ${columns.map((column) => attributeName(model, column)).join(", ")}. Change them afterwards with the panel's Columns….`;
        },
      },
      {
        name: "objectTypes",
        label: "Contained types",
        type: "checkboxes",
        options: options(
          model,
          contained.map((type) => type.key),
        ).map((option) => ({ ...option, label: objectTypeFor(model, option.value)?.pluralName ?? option.label })),
        when: (values) => values.kind === "children",
      },
      {
        name: "fields",
        label: "Fields",
        type: "checkboxes",
        options: fieldGroupOptions(model, detail),
        hint: "Chosen fields move into the group from where they are now.",
        when: (values) => values.kind === "fields",
      },
      {
        name: "region",
        label: "Region",
        type: "select",
        required: true,
        options: [
          { value: "main", label: "Main" },
          { value: "side", label: "Side" },
        ],
      },
      { name: "title", label: "Title", type: "text", required: true },
    ],
    initial,
    (values) => {
      const region = values.region === "side" ? "side" : "main";
      const title = text(values.title);
      if (values.kind === "fields")
        return fieldGroupOperations(place, detail, title, stringList(values.fields), region);
      const show =
        values.kind === "children"
          ? { children: { objectTypeKeys: stringList(values.objectTypes) } }
          : (() => {
              const choice = heldOf(values.relation);
              return { relations: { relation: choice?.relationTypeKey, direction: choice?.direction } };
            })();
      return [{ kind: "addPanel", ...page(place), show, region, title }];
    },
    (next, previous, changed) => {
      // The title follows the choice while it is still the one the previous choice gave.
      if (
        ["kind", "relation", "objectTypes"].includes(changed) &&
        (!previous.title || previous.title === titleFor(previous))
      )
        return { ...next, title: titleFor(next) };
      return next;
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
      stringList(values.fields).map((field) => ({
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
  const sits = whereItSits(model, place, panel);
  // The panel's own columns first, then "Where it sits": a containing type already chosen (Language on Name translations)
  // stays in its group, so the columns after it are not drawn under that heading (found 2026-11-12).
  const all = [...new Set([...current, ...columnChoices(model, place, panel), ...sits])];
  const offered = [...all.filter((key) => !sits.includes(key)), ...all.filter((key) => sits.includes(key))];
  return spec(
    "layout-panel-columns",
    `Columns of ${panel.title}`,
    [
      {
        name: "columns",
        label: "Columns",
        type: "checkboxes",
        options: offered.map((key) => ({
          value: key,
          label: attributeName(model, key),
          ...(sits.includes(key) ? { group: "Where it sits" } : {}),
        })),
        hint: sits.length ? "Where it sits shows what the listed records stand under, and their type." : undefined,
      },
    ],
    { columns: current },
    (values) => chooseList({ ...page(place), panel: panel.key }, "columns", current, stringList(values.columns)),
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

/**
 * The relationships a type's records hold, as `related:` fields read from their side (0.12 TV1,
 * D358): the ones to a parent first, then the others in the model's order.
 */
function relatedChoices(model: EngineModel, objectTypeKey: string): string[] {
  const parents = objectTypeFor(model, objectTypeKey)?.behavior?.parentRelationTypeKeys ?? [];
  const fields = model.objectTypeRelations.flatMap((binding) => {
    const type = relationTypeFor(model, binding.relationTypeKey);
    if (!type) return [];
    return [
      ...(binding.fromObjectTypeKey === objectTypeKey ? [{ key: type.key, parent: false }] : []),
      ...(binding.toObjectTypeKey === objectTypeKey && type.reverseKey
        ? [{ key: type.reverseKey, parent: parents.includes(type.key) }]
        : []),
    ];
  });
  const ordered = [...fields.filter((item) => item.parent), ...fields.filter((item) => !item.parent)];
  return [...new Set(ordered.map((item) => `${RELATED_FIELD_PREFIX}${item.key}`))];
}

/** The fields a table view may list: the name, the type's attributes and relationships, with what it lists now. */
function viewChoices(model: EngineModel, view: TableViewDefinition, current: readonly string[]) {
  const type = objectTypeFor(model, view.objectTypeKey);
  return [
    ...new Set([
      ...current,
      "name",
      ...(type?.attributes.map((item) => item.attributeTypeKey) ?? []),
      ...relatedChoices(model, view.objectTypeKey),
    ]),
  ];
}

/**
 * The fields of the records a relationship reaches, as the columns `related:<key>.<field>` (Base 0.9
 * K5a): their attributes, and where they sit (0.13 RL): each type they can stand under, its name and its
 * attributes (`related:<key>.ancestor:<type>.<field>`). A JSON attribute cannot be one.
 */
export function relatedFieldChoices(model: EngineModel, objectTypeKey: string, field: string): ChoiceOption[] {
  const readable = (attributeKey: string) => attributeTypeFor(model, attributeKey)?.valueType !== "json";
  const attributesOf = (types: { attributes: { attributeTypeKey: string; order: number }[] }[]) => [
    ...new Set(
      types.flatMap((type) =>
        type.attributes
          .slice()
          .sort((a, b) => a.order - b.order)
          .map((binding) => binding.attributeTypeKey)
          .filter(readable),
      ),
    ),
  ];
  const direct = attributesOf(relatedTargetTypes(model, objectTypeKey, field)).map((key) => ({
    value: `${field}.${key}`,
    label: attributeName(model, key),
    under: field,
  }));
  const sitting = relatedAncestorTypes(model, objectTypeKey, field).flatMap((ancestor) => [
    {
      value: `${field}.ancestor:${ancestor.key}.name`,
      label: "Name",
      group: `Where they sit · ${ancestor.name}`,
      under: field,
    },
    ...attributesOf([ancestor]).map((key) => ({
      value: `${field}.ancestor:${ancestor.key}.${key}`,
      label: attributeName(model, key),
      group: `Where they sit · ${ancestor.name}`,
      under: field,
    })),
  ]);
  return [...direct, ...sitting];
}

/**
 * The table's Columns choices: each relationship unfolds into the fields of its records and where they
 * sit; a related column the view has that no relationship offers stands among the others.
 */
function columnOptions(model: EngineModel, view: TableViewDefinition, current: readonly string[]): ChoiceOption[] {
  const choices = viewChoices(model, view, current);
  const unfolded = choices
    .filter((key) => key.startsWith(RELATED_FIELD_PREFIX) && !relatedColumn(model, key)?.field)
    .flatMap((key) => relatedFieldChoices(model, view.objectTypeKey, key));
  const known = new Set(unfolded.map((option) => option.value));
  return [
    ...choices.filter((key) => !known.has(key)).map((key) => ({ value: key, label: attributeName(model, key) })),
    ...unfolded,
  ];
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
        options: columnOptions(model, view, current),
        hint: "Open a relationship to show a field of its records as a column of its own, such as the language code of a translation.",
      },
    ],
    { columns: current },
    (values) => chooseList(viewTarget(place, view), "columns", current, stringList(values.columns)),
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
    (values) => chooseList(viewTarget(place, view), "filterFields", current, stringList(values.filters)),
  );
}

/**
 * A table's availability field (0.13 LB): optionally one boolean attribute of the type. A record with
 * it set to No stays in its place, marked Inactive, and the toolbar gains a switch that hides them.
 */
export function tableAvailabilitySpec(
  model: EngineModel,
  place: LayoutPlace,
  view: TableViewDefinition,
): OperationSpec {
  const booleans = (objectTypeFor(model, view.objectTypeKey)?.attributes ?? [])
    .map((item) => item.attributeTypeKey)
    .filter((key) => attributeTypeFor(model, key)?.valueType === "boolean");
  const current = view.config.availabilityField ?? "";
  return spec(
    "layout-table-availability",
    `Inactive records of ${view.name}`,
    [
      {
        name: "availability",
        label: "A record is inactive when this is No",
        type: "select",
        options: [{ value: "", label: "None" }, ...options(model, booleans)],
        hint: "Inactive records keep their place with an Inactive mark, and the table offers a switch that hides them. Values stay editable as usual.",
      },
    ],
    { availability: current },
    (values) =>
      changed(viewTarget(place, view), [
        { property: "availabilityField", now: current || null, next: text(values.availability) || null },
      ]),
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

// --- the settings a page, a table and a panel hold beyond their contents (0.13 ED) ---

const sortableFields = (model: EngineModel, typeKeys: readonly string[], keep: readonly string[]) => {
  const sortable = new Set(model.attributeTypes.filter((item) => item.features?.sortable).map((item) => item.key));
  const attributes = typeKeys.flatMap(
    (key) => objectTypeFor(model, key)?.attributes.map((item) => item.attributeTypeKey) ?? [],
  );
  return [...new Set(["name", ...keep, ...attributes.filter((key) => sortable.has(key))])];
};

const PAGE_SIZES = [10, 20, 25, 50, 100].map((size) => ({ value: String(size), label: String(size) }));
const pageSizeOptions = (current: number) =>
  PAGE_SIZES.some((item) => item.value === String(current))
    ? PAGE_SIZES
    : [...PAGE_SIZES, { value: String(current), label: String(current) }].sort(
        (a, b) => Number(a.value) - Number(b.value),
      );

/** The operations that set the properties of `values` that differ from what is held now. */
const changed = (
  target: Record<string, unknown>,
  properties: { property: string; now: unknown; next: unknown }[],
): DraftOperation[] =>
  properties
    .filter((item) => JSON.stringify(item.now ?? null) !== JSON.stringify(item.next ?? null))
    .map((item) => ({ kind: "setViewProperty", ...target, property: item.property, value: item.next ?? null }));

/**
 * The page's header and breadcrumbs: which field titles a record and which sits under it, whether the
 * header names the type, and which of the application, the type and the ancestors lead the breadcrumbs.
 */
export function pageHeaderSpec(model: EngineModel, place: LayoutPlace, detail: DetailViewDefinition): OperationSpec {
  const fields = options(model, [
    "name",
    ...(objectTypeFor(model, place.objectTypeKey)?.attributes ?? []).map((item) => item.attributeTypeKey),
  ]);
  const { header, breadcrumbs } = detail;
  // `breadcrumbs.showApplication` stays in the model but draws nothing since 0.17 SH1, so it is not offered here.
  return spec(
    "layout-page-header",
    "Header and breadcrumbs",
    [
      { name: "title", label: "Title of the record", type: "select", required: true, options: fields },
      {
        name: "subtitle",
        label: "Line under the title",
        type: "select",
        options: [{ value: "", label: "None" }, ...fields],
      },
      { name: "headerType", label: "Show the type's name in the header", type: "checkbox" },
      { name: "crumbType", label: "Breadcrumbs name the type", type: "checkbox" },
      { name: "crumbAncestors", label: "Breadcrumbs name the records above it", type: "checkbox" },
    ],
    {
      title: header.titleField,
      subtitle: header.subtitleField ?? "",
      headerType: header.showObjectType,
      crumbType: breadcrumbs.showObjectType,
      crumbAncestors: breadcrumbs.showAncestors,
    },
    (values) =>
      changed(page(place), [
        { property: "header.titleField", now: header.titleField, next: text(values.title) },
        { property: "header.subtitleField", now: header.subtitleField, next: text(values.subtitle) || null },
        { property: "header.showObjectType", now: header.showObjectType, next: values.headerType === true },
        { property: "breadcrumbs.showObjectType", now: breadcrumbs.showObjectType, next: values.crumbType === true },
        { property: "breadcrumbs.showAncestors", now: breadcrumbs.showAncestors, next: values.crumbAncestors === true },
      ]),
  );
}

/** A table's sort menu (the fields a reader may sort by) and the number of rows on a page. */
export function tableMenuSpec(model: EngineModel, place: LayoutPlace, view: TableViewDefinition): OperationSpec {
  const current = view.config.sortFields;
  return spec(
    "layout-table-menu",
    `Sort menu and page size of ${view.name}`,
    [
      {
        name: "sortFields",
        label: "Fields a reader can sort by",
        type: "checkboxes",
        options: options(model, sortableFields(model, [view.objectTypeKey], current)),
        hint: "Only fields set to be sortable are offered. The default sort stays one of them.",
      },
      {
        name: "pageSize",
        label: "Rows on a page",
        type: "select",
        required: true,
        options: pageSizeOptions(view.config.pageSize),
      },
    ],
    { sortFields: current, pageSize: String(view.config.pageSize) },
    (values) => {
      const chosen = stringList(values.sortFields);
      const defaultField = view.config.defaultSort.replace(/^-/, "");
      const target = viewTarget(place, view);
      const keeps = chosen.includes(defaultField);
      return [
        // A default sort the new list no longer holds moves to its first field before the list changes.
        ...(keeps || !chosen.length
          ? []
          : [{ kind: "setViewProperty", ...target, property: "defaultSort", value: chosen[0] } as DraftOperation]),
        ...changed(target, [
          { property: "sortFields", now: current, next: chosen.length ? chosen : current },
          { property: "pageSize", now: view.config.pageSize, next: Number(values.pageSize) },
        ]),
      ];
    },
  );
}

/**
 * The settings of one panel: which relationships a relations panel lists, their direction, the
 * relationship column and the sort menu; a hierarchy panel's parent and ancestors; a table panel's
 * parent filter; a page size. Undefined for a panel with none (an attributes panel).
 */
export function panelSettingsSpec(
  model: EngineModel,
  place: LayoutPlace,
  panel: PanelDefinition,
): OperationSpec | undefined {
  const target = { ...page(place), panel: panel.key };
  if (panel.type === "relations") {
    const config = panel.config;
    const held = [
      ...new Set(
        model.objectTypeRelations
          .filter(
            (item) => item.fromObjectTypeKey === place.objectTypeKey || item.toObjectTypeKey === place.objectTypeKey,
          )
          .map((item) => item.relationTypeKey),
      ),
    ];
    const related = panelTypes(model, place, panel);
    return spec(
      "layout-panel-settings",
      `Settings of ${panel.title}`,
      [
        {
          name: "relations",
          label: "Relationships listed",
          type: "checkboxes",
          options: held.map((key) => ({
            value: key,
            label: relationTypeFor(model, key)?.name ?? key,
          })),
        },
        {
          name: "direction",
          label: "Listed from",
          type: "select",
          required: true,
          options: [
            { value: "outgoing", label: "This record to the others" },
            { value: "incoming", label: "The others to this record" },
            { value: "both", label: "Both ways" },
          ],
        },
        { name: "relationshipColumn", label: "Show which relationship joins each record", type: "checkbox" },
        {
          name: "sortFields",
          label: "Fields a reader can sort by",
          type: "checkboxes",
          options: options(model, sortableFields(model, related, config.sortFields ?? [])),
          hint: "Leave all unchecked to list by name.",
        },
      ],
      {
        relations: config.relationTypeKeys,
        direction: config.direction,
        relationshipColumn: config.showRelationshipColumn === true,
        sortFields: config.sortFields ?? [],
      },
      (values) => {
        const chosen = stringList(values.sortFields);
        const defaultField = config.defaultSort?.replace(/^-/, "");
        return [
          ...(config.defaultSort && !chosen.includes(defaultField ?? "")
            ? [
                {
                  kind: "setViewProperty",
                  ...target,
                  property: "defaultSort",
                  value: chosen[0] ?? null,
                } as DraftOperation,
              ]
            : []),
          ...changed(target, [
            { property: "relationTypeKeys", now: config.relationTypeKeys, next: stringList(values.relations) },
            { property: "direction", now: config.direction, next: text(values.direction) },
            {
              property: "showRelationshipColumn",
              now: config.showRelationshipColumn === true,
              next: values.relationshipColumn === true,
            },
            // The schema has no empty sort list (`min_length=1`): none is "absent", so unchecking all of none saves no step.
            {
              property: "sortFields",
              now: config.sortFields?.length ? config.sortFields : null,
              next: chosen.length ? chosen : null,
            },
          ]),
        ];
      },
    );
  }
  if (panel.type === "hierarchy") {
    const config = panel.config;
    return spec(
      "layout-panel-settings",
      `Settings of ${panel.title}`,
      [
        { name: "showParent", label: "Show the parent", type: "checkbox" },
        { name: "showAncestors", label: "Show the records above the parent", type: "checkbox" },
      ],
      { showParent: config.showParent, showAncestors: config.showAncestors },
      (values) =>
        changed(target, [
          { property: "showParent", now: config.showParent, next: values.showParent === true },
          { property: "showAncestors", now: config.showAncestors, next: values.showAncestors === true },
        ]),
    );
  }
  if (panel.type === "table" || panel.type === "children") {
    const config = panel.config;
    return spec(
      "layout-panel-settings",
      `Settings of ${panel.title}`,
      [
        ...(panel.type === "table"
          ? [
              {
                name: "filterByParent",
                label: "List only the records under this one",
                type: "checkbox",
              } as OperationField,
            ]
          : []),
        {
          name: "pageSize",
          label: "Rows on a page",
          type: "select",
          required: true,
          options: pageSizeOptions(config.pageSize),
        },
      ],
      {
        ...(panel.type === "table" ? { filterByParent: panel.config.filterByParent } : {}),
        pageSize: String(config.pageSize),
      },
      (values) =>
        changed(target, [
          ...(panel.type === "table"
            ? [{ property: "filterByParent", now: panel.config.filterByParent, next: values.filterByParent === true }]
            : []),
          { property: "pageSize", now: config.pageSize, next: Number(values.pageSize) },
        ]),
    );
  }
  return undefined;
}
