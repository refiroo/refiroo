import { useState, type ReactNode } from "react";
import { attributeName } from "@/model/fields";
import type { CollectionQueryState, EngineModel, TableViewDefinition, ValueType } from "@/types";
import { Icon } from "@/ui/Icon";
import { ControlPopover } from "@/ui/ControlPopover";
import { DebouncedSearchField } from "@/ui/SearchField";

const OPERATOR_LABELS: Record<string, string> = {
  eq: "is",
  contains: "contains",
  startsWith: "starts with",
  lt: "is less than",
  lte: "is at most",
  gt: "is greater than",
  gte: "is at least",
  isNull: "is null",
  isUnset: "is unset",
};

export function ObjectToolbar({
  model,
  view,
  query,
  placeholder,
  onChange,
  display,
  sortMenu,
}: {
  display: ReactNode;
  /** The sort menu, when a declared sort field has no visible column header. */
  sortMenu?: ReactNode;
  model: EngineModel;
  view: TableViewDefinition;
  query: CollectionQueryState;
  placeholder: string;
  onChange: (query: CollectionQueryState) => void;
}) {
  function applyFilter(field: string, input: { operator: string; value: string }) {
    const remaining = query.filters.filter((filter) => filter.field !== field);
    const filters = input.value === "" ? remaining : [...remaining, { field, ...input }];
    onChange({ ...query, filters });
  }

  return (
    <>
      <div className="collection-toolbar object-toolbar">
        <DebouncedSearchField
          key={query.search}
          appliedValue={query.search}
          placeholder={placeholder}
          onApply={(search) => onChange({ ...query, search })}
        />
        {view.config.filterFields.length > 0 && (
          <ControlPopover label="Filter" icon="filter" count={query.filters.length}>
            <div className="filter-fields">
              {view.config.filterFields.map((field) => {
                const type = valueType(model, field);
                const current = query.filters.find((filter) => filter.field === field);
                return (
                  <FilterControl
                    key={field}
                    label={attributeName(model, field)}
                    type={type}
                    attribute={!isBuiltIn(field)}
                    initial={current ?? { operator: defaultOperator(type), value: "" }}
                    onApply={(input) => applyFilter(field, input)}
                  />
                );
              })}
            </div>
            {query.filters.length > 0 && (
              <button type="button" className="ghost" onClick={() => onChange({ ...query, filters: [] })}>
                Clear all filters
              </button>
            )}
          </ControlPopover>
        )}
        {display}
        {sortMenu}
      </div>
      <div className="filter-chips" aria-label="Applied filters">
        {query.filters.map((filter, index) => (
          <button
            className="filter-chip"
            key={`${filter.field}:${filter.operator}:${index}`}
            aria-label={`Remove ${attributeName(model, filter.field)} ${OPERATOR_LABELS[filter.operator] ?? filter.operator} ${filter.value}`}
            onClick={() => onChange({ ...query, filters: query.filters.filter((_, position) => position !== index) })}
          >
            <span>
              {attributeName(model, filter.field)} <em>{OPERATOR_LABELS[filter.operator] ?? filter.operator}</em>{" "}
              {filter.value}
            </span>
            <Icon name="close" size={13} />
          </button>
        ))}
        {(query.search !== "" || query.filters.length > 0) && (
          <button className="ghost" onClick={() => onChange({ ...query, search: "", filters: [] })}>
            Clear filters
          </button>
        )}
      </div>
    </>
  );
}

function FilterControl({
  label,
  type,
  attribute,
  initial,
  onApply,
}: {
  label: string;
  type: ValueType;
  attribute: boolean;
  initial: { operator: string; value: string };
  onApply: (input: { operator: string; value: string }) => void;
}) {
  const [input, setInput] = useState(initial);
  const [applied, setApplied] = useState(initial);
  if (applied.operator !== initial.operator || applied.value !== initial.value) {
    setApplied(initial);
    setInput(initial);
  }
  const operators = filterOperators(type, attribute);
  const booleanValue = type === "boolean" || input.operator === "isNull" || input.operator === "isUnset";
  return (
    <div className="toolbar-filter">
      <span>{label}</span>
      <select
        aria-label={`${label} operator`}
        value={input.operator}
        onChange={(event) => {
          const next = { operator: event.target.value, value: "" };
          setInput(next);
        }}
      >
        {operators.map((operator) => (
          <option key={operator} value={operator}>
            {OPERATOR_LABELS[operator]}
          </option>
        ))}
      </select>
      {booleanValue ? (
        <select
          aria-label={`${label} value`}
          value={input.value}
          onChange={(event) => {
            const next = { ...input, value: event.target.value };
            setInput(next);
            onApply(next);
          }}
        >
          <option value="">Any</option>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      ) : (
        <input
          aria-label={`${label} value`}
          type={inputType(type)}
          value={input.value}
          onChange={(event) => setInput({ ...input, value: event.target.value })}
          onBlur={(event) => onApply({ ...input, value: event.target.value.trim() })}
          onKeyDown={(event) => {
            if (event.key === "Enter") onApply({ ...input, value: event.currentTarget.value.trim() });
          }}
        />
      )}
    </div>
  );
}

function isBuiltIn(field: string) {
  return ["id", "name", "createdAt", "updatedAt"].includes(field);
}

function valueType(model: EngineModel, field: string): ValueType {
  if (["createdAt", "updatedAt"].includes(field)) return "dateTime";
  return model.attributeTypes.find((attribute) => attribute.key === field)?.valueType ?? "text";
}

function defaultOperator(type: ValueType) {
  return type === "text" || type === "longText" ? "contains" : "eq";
}

function filterOperators(type: ValueType, attribute: boolean) {
  const unset = attribute ? ["isUnset"] : [];
  if (type === "text" || type === "longText") return ["eq", "contains", "startsWith", "isNull", ...unset];
  if (["integer", "decimal", "date", "dateTime"].includes(type))
    return ["eq", "lt", "lte", "gt", "gte", "isNull", ...unset];
  return ["eq", "isNull", ...unset];
}

function inputType(type: ValueType) {
  if (type === "integer" || type === "decimal") return "number";
  if (type === "date") return "date";
  if (type === "dateTime") return "datetime-local";
  return "text";
}
