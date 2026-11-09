/**
 * What a relationships grid filters by (0.13 RG). Its rows are records of the `from` type and its
 * column groups records of the `to` type, so each end is filtered as that type's main collection is:
 * by the filter fields of the table view its collection opens with (and the grid's own `from:` and
 * `to:` ones), through the same filter bar. A relationship's value is one more field of the rows'
 * bar (`relation:<attribute>`). The engine applies the same rule
 * (`engine/model/relation_table.main_view_filter_fields`), so the address, the bar and the read agree.
 */

import { collectionGroups } from "@/model/collections";
import type { ApplicationDefinition, EngineModel, RelationTableViewDefinition, TableViewDefinition } from "@/types";

type Config = RelationTableViewDefinition["config"];
export type End = "from" | "to";

/** The table view a type's collection opens with, and the application that lists it. */
export function mainTableView(
  model: EngineModel,
  applicationKey: string,
  objectTypeKey: string,
): { view: TableViewDefinition; application: ApplicationDefinition } | undefined {
  const applications = [
    ...model.applications.filter((item) => item.key === applicationKey),
    ...model.applications.filter((item) => item.key !== applicationKey),
  ];
  const application = applications.find((item) => item.objectTypeKeys.includes(objectTypeKey));
  const main = application && collectionGroups(application).find((item) => item.objectTypeKey === objectTypeKey);
  return application && main?.defaultView.type === "table" ? { view: main.defaultView, application } : undefined;
}

/**
 * The table view one end's filter bar is built over: the main view's own, with the grid's own fields
 * for that end added (and, for the rows, the relationship's attributes the grid filters by).
 */
export function endFilterView(
  model: EngineModel,
  applicationKey: string,
  gridKey: string,
  config: Config,
  end: End,
): { view: TableViewDefinition; applicationKey?: string } {
  const objectTypeKey = end === "from" ? config.fromObjectTypeKey : config.toObjectTypeKey;
  const main = mainTableView(model, applicationKey, objectTypeKey);
  // The grid's own fields for the end; the rows' bar also filters by every attribute the grid shows.
  const own = [
    ...config.filterFields.flatMap((ref) =>
      ref.startsWith(`${end}:`) || (end === "from" && ref.startsWith("relation:")) ? [ref.replace(`${end}:`, "")] : [],
    ),
    ...(end === "from"
      ? config.attributeColumns
          .filter((key) => model.attributeTypes.find((item) => item.key === key)?.valueType !== "json")
          .map((key) => `relation:${key}`)
      : []),
  ];
  const base: TableViewDefinition = main?.view ?? {
    key: gridKey,
    name: gridKey,
    type: "table",
    objectTypeKey,
    config: { columns: ["name"], filterFields: [], sortFields: ["name"], defaultSort: "name", pageSize: 20 },
  };
  return {
    view: { ...base, config: { ...base.config, filterFields: [...new Set([...base.config.filterFields, ...own])] } },
    applicationKey: main?.application.key,
  };
}

/** Every reference the grid's address and read accept as a filter. */
export function gridFilterFields(model: EngineModel, applicationKey: string, config: Config): string[] {
  return [
    ...new Set([
      ...config.filterFields,
      ...(["from", "to"] as const).flatMap((end) =>
        endFilterView(model, applicationKey, "", config, end).view.config.filterFields.map((field) =>
          field.startsWith("relation:") ? field : `${end}:${field}`,
        ),
      ),
    ]),
  ];
}
