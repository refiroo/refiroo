/**
 * The relation matrix's Filter popover: which column records to show, chosen from a searchable list
 * of the column type's records, and the cell state rows must have in one of them. Both live in the
 * URL. A state needs named columns (the API decides it over those), so choosing one while the
 * matrix pages its columns names the columns on screen.
 */

import { useState } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { ControlPopover } from "@/ui/ControlPopover";
import { InlineError } from "@/ui/InlineError";
import { ScrollWindow } from "@/ui/ScrollWindow";
import { fieldValue } from "@/model/fields";
import { MATRIX_MAX_COLUMNS } from "@/routing/routes";
import { StateMark, type MatrixStateKey } from "@/features/objects/relationMatrixStates";
import type {
  CollectionQueryState,
  EngineModel,
  ObjectItem,
  ObjectTypeDefinition,
  RelationMatrixColumn,
} from "@/types";
import { SearchField } from "@/ui/SearchField";

type MatrixFilter = Pick<CollectionQueryState, "matrixColumnIds" | "matrixState">;

export function RelationMatrixFilter({
  model,
  workspaceKey,
  columnType,
  labelField,
  shownColumns,
  query,
  states,
  onChange,
}: {
  model: EngineModel;
  workspaceKey: string;
  columnType: ObjectTypeDefinition;
  labelField: string;
  shownColumns: RelationMatrixColumn[];
  query: CollectionQueryState;
  states: { key: MatrixStateKey; label: string }[];
  onChange: (filter: MatrixFilter) => void;
}) {
  const chosen = query.matrixColumnIds ?? [];
  const count = (chosen.length ? 1 : 0) + (query.matrixState ? 1 : 0);
  const columnsPlural = columnType.pluralName.toLowerCase();
  const stateColumns = chosen.length ? chosen : shownColumns.map((column) => column.id).slice(0, MATRIX_MAX_COLUMNS);

  return (
    <ControlPopover label="Filter" icon="filter" count={count} className="matrix-filter">
      <fieldset className="matrix-filter-states">
        <legend>Cell state</legend>
        <p className="muted-text">
          Rows with a cell in this state in any {chosen.length ? "chosen" : "shown"} {columnType.name.toLowerCase()},
          across the whole list.
        </p>
        <label className="radio">
          <input
            type="radio"
            name="matrix-state"
            checked={!query.matrixState}
            onChange={() => onChange({ matrixColumnIds: query.matrixColumnIds, matrixState: undefined })}
          />
          <span>Any state</span>
        </label>
        {states.map((state) => (
          <label className="radio" key={state.key}>
            <input
              type="radio"
              name="matrix-state"
              checked={query.matrixState === state.key}
              disabled={stateColumns.length === 0}
              onChange={() => onChange({ matrixColumnIds: stateColumns, matrixState: state.key })}
            />
            <StateMark state={state.key} />
            <span>{state.label}</span>
          </label>
        ))}
      </fieldset>
      <fieldset className="matrix-filter-columns">
        <legend>{columnType.pluralName} to show</legend>
        <ColumnChooser
          model={model}
          workspaceKey={workspaceKey}
          columnType={columnType}
          labelField={labelField}
          chosen={chosen}
          onChange={(ids) =>
            onChange(
              ids.length
                ? { matrixColumnIds: ids, matrixState: query.matrixState }
                : { matrixColumnIds: undefined, matrixState: undefined },
            )
          }
        />
        {chosen.length > 0 && (
          <button
            type="button"
            className="ghost"
            onClick={() => onChange({ matrixColumnIds: undefined, matrixState: undefined })}
          >
            Show all {columnsPlural}
          </button>
        )}
      </fieldset>
    </ControlPopover>
  );
}

function ColumnChooser({
  model,
  workspaceKey,
  columnType,
  labelField,
  chosen,
  onChange,
}: {
  model: EngineModel;
  workspaceKey: string;
  columnType: ObjectTypeDefinition;
  labelField: string;
  chosen: string[];
  onChange: (ids: string[]) => void;
}) {
  const api = useDataApi();
  const [search, setSearch] = useState("");
  const debounced = useDebouncedValue(search.trim());
  const pageSize = 20;
  const list = useCursorWindow<ObjectItem>(
    (selector) =>
      api.objects(columnType.key, {
        workspaceKey,
        search: debounced || undefined,
        sort: "name",
        ...selector,
        pageSize,
      }),
    [columnType.key, workspaceKey, debounced],
  );
  const full = chosen.length >= MATRIX_MAX_COLUMNS;
  const plural = columnType.pluralName.toLowerCase();
  return (
    <>
      <SearchField value={search} onChange={setSearch} label={`Search ${plural}`} placeholder={`Search ${plural}`} />
      {full && <p className="muted-text">At most {MATRIX_MAX_COLUMNS} can be shown at once.</p>}
      <ScrollWindow
        list={list}
        label={`${columnType.pluralName} to choose from`}
        noun={[columnType.name.toLowerCase(), plural]}
        pageSize={pageSize}
        footer={false}
        edgeMarkers="partial"
        className="matrix-column-choices"
      >
        {list.items.map((item, position) => {
          const label = fieldValue(item, labelField, model);
          const checked = chosen.includes(item.id);
          return (
            <label
              key={item.id}
              className="checkbox matrix-column-choice"
              data-row-key={item.id}
              data-row-index={list.startIndex + position}
            >
              <input
                type="checkbox"
                data-row-focus
                checked={checked}
                disabled={!checked && full}
                onChange={() => onChange(checked ? chosen.filter((id) => id !== item.id) : [...chosen, item.id])}
              />
              <span>
                {label !== undefined && label !== null && label !== "" && label !== item.name ? (
                  <>
                    <strong>{String(label)}</strong> <small>{item.name}</small>
                  </>
                ) : (
                  item.name
                )}
              </span>
            </label>
          );
        })}
        {list.loading && !list.items.length && <p className="candidate-state">Loading…</p>}
        {!list.loading && !list.error && !list.items.length && (
          <p className="candidate-state">
            No {plural} match{debounced ? ` “${debounced}”` : ""}.
          </p>
        )}
      </ScrollWindow>
      {list.error && <InlineError message={list.error} onRetry={list.retry} />}
    </>
  );
}
