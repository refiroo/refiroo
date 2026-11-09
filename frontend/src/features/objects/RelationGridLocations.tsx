/**
 * Which related records a relationships grid shows as column groups (0.13 RG): the filter bar of
 * their type's main collection (`ObjectToolbar`: its search, its filters and their operators, and
 * asking in words), and a pick by name from the records of the type (the relation matrix's column
 * chooser). The choices live in the address with the grid's filters.
 */

import { ObjectToolbar } from "@/features/objects/ObjectToolbar";
import { ColumnChooser } from "@/features/objects/RelationMatrixFilter";
import { GRID_MAX_COLUMNS } from "@/routing/routes";
import type { CollectionQueryState, EngineModel, ObjectTypeDefinition, TableViewDefinition } from "@/types";
import { ControlPopover } from "@/ui/ControlPopover";

type Query = Pick<CollectionQueryState, "filters" | "gridColumnIds" | "gridSearch">;

export function RelationGridLocations({
  model,
  toType,
  filterView,
  applicationKey,
  query,
  workspaceKey,
  countDraft,
  onChange,
}: {
  model: EngineModel;
  toType: ObjectTypeDefinition;
  /** The table view the column records are filtered by, as their collection does. */
  filterView: TableViewDefinition;
  /** The application of that collection, for asking in words; none where the grid has no main view for the type. */
  applicationKey?: string;
  query: Query;
  workspaceKey: string;
  countDraft: (filters: { field: string; operator: string; value: string }[]) => Promise<number | undefined>;
  onChange: (next: Query) => void;
}) {
  const picked = query.gridColumnIds ?? [];
  const toFilters = query.filters.filter((filter) => filter.field.startsWith("to:"));
  const count = (picked.length ? 1 : 0) + toFilters.length + (query.gridSearch ? 1 : 0);
  const plural = toType.pluralName.toLowerCase();
  return (
    <ControlPopover label={toType.pluralName} icon="filter" count={count} className="matrix-filter">
      <p className="muted-text">
        Only these {plural} are shown as columns, filtered and changed by a bulk edit. At most {GRID_MAX_COLUMNS} at
        once.
      </p>
      <ObjectToolbar
        display={null}
        model={model}
        view={filterView}
        query={{
          search: query.gridSearch ?? "",
          sort: "",
          pageSize: 20,
          filters: toFilters.map((filter) => ({ ...filter, field: filter.field.slice(3) })),
        }}
        onChange={(next) =>
          onChange({
            ...query,
            gridSearch: next.search || undefined,
            filters: [
              ...query.filters.filter((filter) => !filter.field.startsWith("to:")),
              ...next.filters.map((filter) => ({ ...filter, field: `to:${filter.field}` })),
            ],
          })
        }
        placeholder={`Search ${plural}`}
        workspaceKey={workspaceKey}
        applicationKey={applicationKey}
        noun={[toType.name, toType.pluralName]}
        countDraft={countDraft}
      />
      <fieldset className="matrix-filter-columns">
        <legend>{toType.pluralName} to show</legend>
        <ColumnChooser
          model={model}
          workspaceKey={workspaceKey}
          columnType={toType}
          labelField="name"
          chosen={picked}
          max={GRID_MAX_COLUMNS}
          onChange={(ids) => onChange({ ...query, gridColumnIds: ids.length ? ids : undefined })}
        />
        {count > 0 && (
          <button
            type="button"
            className="ghost"
            onClick={() =>
              onChange({
                filters: query.filters.filter((filter) => !filter.field.startsWith("to:")),
                gridColumnIds: undefined,
                gridSearch: undefined,
              })
            }
          >
            Show all {plural}
          </button>
        )}
      </fieldset>
    </ControlPopover>
  );
}
