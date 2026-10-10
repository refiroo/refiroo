import type { ReactNode } from "react";
import { FilterBar, filterFields } from "@/features/objects/filters/FilterBar";
import { useRelationFilterNames } from "@/features/objects/RelationFilter";
import type { CollectionFilter, CollectionQueryState, EngineModel, TableViewDefinition } from "@/types";
import { DebouncedSearchField } from "@/ui/SearchField";

export function ObjectToolbar({
  model,
  view,
  query,
  placeholder,
  onChange,
  display,
  sortMenu,
  workspaceKey,
  noun,
  countDraft,
}: {
  display: ReactNode;
  /** The sort menu, when a declared sort field has no visible column header. */
  sortMenu?: ReactNode;
  model: EngineModel;
  view: TableViewDefinition;
  query: CollectionQueryState;
  placeholder: string;
  onChange: (query: CollectionQueryState) => void;
  /** Where a relationship filter's record picker searches. */
  workspaceKey?: string;
  /** The listed records' names, singular and plural, for the phone sheet's Show N. */
  noun: readonly [string, string];
  /** How many records the list shows with these filters, for the phone sheet (D163). */
  countDraft: (filters: CollectionFilter[]) => Promise<number | undefined>;
}) {
  const objectTypeKey = view.objectTypeKey ?? "";
  const names = useRelationFilterNames(model, objectTypeKey, query.filters, workspaceKey);
  return (
    <>
      <div className="collection-toolbar object-toolbar">
        <DebouncedSearchField
          key={query.search}
          appliedValue={query.search}
          placeholder={placeholder}
          onApply={(search) => onChange({ ...query, search })}
        />
        <FilterBar
          model={model}
          objectTypeKey={objectTypeKey}
          fields={filterFields(model, view.config.filterFields)}
          filters={query.filters}
          names={names}
          workspaceKey={workspaceKey}
          noun={noun}
          countDraft={countDraft}
          onChange={(filters) => onChange({ ...query, filters })}
        />
        <div className="object-toolbar-end">
          {display}
          {sortMenu}
        </div>
      </div>
      {query.search !== "" && query.filters.length > 0 && (
        <div className="filter-chips" aria-label="Applied search">
          <button className="ghost" onClick={() => onChange({ ...query, search: "", filters: [] })}>
            Clear search and filters
          </button>
        </div>
      )}
    </>
  );
}
