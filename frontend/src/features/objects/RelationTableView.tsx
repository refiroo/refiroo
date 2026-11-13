/**
 * A relationships table (0.13 RV): one binding's relationships as rows, with both records' columns
 * and the relationship's own attributes as columns. Filters, sorting and paging are the server's
 * (`GET /workspaces/{key}/relations` through the view); the rows scroll in a `ScrollWindow` over a
 * cursor window. A grouped table heads its rows by their `from` or `to` record with the group's
 * count. An attribute cell edits where it stands and saves as it is left, through the same
 * `RelationAttributes` and save the Edit values dialog uses (`RelationValueCell`); ticked rows get one attribute set to
 * one value in one request (`POST /relations/batch`), all or none. Where the data cannot be written
 * (a publication, a read-only view, no permission) no control is offered.
 */

import { useState, type FormEvent } from "react";
import { errorMessage, isApiError } from "@/api/errors";
import { useDataApi, useRecordWrites, useWorkspaceData } from "@/state/WorkspaceDataContext";
import { RELATION_ATTRIBUTES_LABEL, relationAttributeTypes } from "@/features/objects/relations/RelationAttributes";
import { RelationValueCell } from "@/features/objects/relations/RelationValueCell";
import { relationAttributeColumn } from "@/features/objects/relations/relationAttributeColumns";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { attributeName } from "@/model/fields";
import { objectTypeHue, objectTypeTile } from "@/model/hues";
import { isManagedRelation, listingApplication, objectTypeFor } from "@/model/lookup";
import type {
  AttributeTypeDefinition,
  CollectionFilter,
  EngineModel,
  RelationTableRow,
  RelationTableViewDefinition,
} from "@/types";
import { Card } from "@/ui/Card";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { Icon } from "@/ui/Icon";
import { HueTile } from "@/ui/HueTile";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { pageTitle } from "@/model/collections";
import { PageHeader } from "@/ui/PageHeader";
import { DebouncedSearchField } from "@/ui/SearchField";
import { SelectionCheckbox } from "@/ui/SelectionCheckbox";
import { TableDisplay, useTableDisplay } from "@/ui/TableDisplay";
import { SortMenu, useTableSort } from "@/ui/TableSort";
import { formatValue } from "@/ui/formatValue";
import { parseAttributeValue } from "@/ui/attributeForm";
import type { ViewComponentProps } from "./views/types";
import { useExportExtra, windowTotal } from "./views/useViewExport";

type End = "from" | "to";

export function RelationTableView({
  model,
  application,
  view: rawView,
  workspaceKey,
  readOnly: contextReadOnly,
  onChanged,
  query,
  onQueryChange,
  onAnchorChange,
  refreshToken = 0,
  lenses,
  onOpen,
  exportExtraRef,
}: ViewComponentProps) {
  const view = rawView as RelationTableViewDefinition;
  const { config } = view;
  const api = useDataApi();
  const { changeSet } = useWorkspaceData();
  const writes = useRecordWrites();
  const [internalRefresh, setInternalRefresh] = useState(0);
  const [counts, setCounts] = useState<{ key: string; byGroup: Record<string, number> }>({ key: "", byGroup: {} });
  const [selection, setSelection] = useState<{ key: string; rows: Map<string, { version: number; label: string }> }>({
    key: "",
    rows: new Map(),
  });
  const [bulk, setBulk] = useState<{ attribute?: string; raw: string; error?: string; failed?: string[] }>({
    raw: "",
  });
  const [applying, setApplying] = useState(false);

  const fromType = objectTypeFor(model, config.fromObjectTypeKey);
  const toType = objectTypeFor(model, config.toObjectTypeKey);
  const binding = model.objectTypeRelations.find(
    (item) =>
      item.relationTypeKey === config.relationTypeKey &&
      item.fromObjectTypeKey === config.fromObjectTypeKey &&
      item.toObjectTypeKey === config.toObjectTypeKey,
  );
  const declared = relationAttributeTypes(model, binding);
  const attributes = config.attributeColumns.flatMap((key) => declared.filter((item) => item.key === key));
  const fromApplicationKey = listingApplication(model, application.key, config.fromObjectTypeKey);
  const toApplicationKey = listingApplication(model, application.key, config.toObjectTypeKey);
  // A relationship is written where either end's type may be (0.12 Z5, D291, D329); none in a publication.
  const readOnly =
    contextReadOnly ||
    !(writes.permits(fromApplicationKey, config.fromObjectTypeKey) || writes.permitsType(config.toObjectTypeKey));
  const editable = !readOnly && attributes.length > 0 && !(binding && isManagedRelation(model, binding));

  const grouped = config.groupBy ?? null;
  const pageSize = query.pageSize || config.pageSize;
  const sort = query.sort || config.defaultSort;
  const filters = query.filters;
  const queryKey = JSON.stringify([view.key, query.search, sort, filters, changeSet?.id]);
  const chosen = selection.key === queryKey ? selection.rows : new Map<string, { version: number; label: string }>();

  const list = useCursorWindow<RelationTableRow>(
    (selector) =>
      api
        .relationTable({
          workspaceKey,
          applicationKey: application.key,
          viewKey: view.key,
          search: query.search || undefined,
          sort,
          filters: filters.map(({ field, value }) => ({ field, value })),
          ...selector,
          pageSize,
        })
        .then((page) => {
          if (page.groupCounts)
            setCounts((current) => ({
              key: queryKey,
              byGroup: { ...(current.key === queryKey ? current.byGroup : {}), ...page.groupCounts },
            }));
          return page;
        }),
    [application.key, view.key, workspaceKey, query.search, sort, JSON.stringify(filters), pageSize, changeSet?.id],
    { anchor: query.anchor, refreshToken: refreshToken + internalRefresh },
  );
  useExportExtra(exportExtraRef, { size: { rows: windowTotal(list) } });
  const groupCounts = counts.key === queryKey ? counts.byGroup : {};

  function reload() {
    setInternalRefresh((value) => value + 1);
    onChanged?.();
  }

  const sortFields = config.sortFields;
  const fieldLabel = (end: End, field: string) => {
    const type = end === "from" ? fromType : toType;
    return field === "name" ? (type?.name ?? field) : `${attributeName(model, field)} (${type?.name ?? end})`;
  };
  const refLabel = (ref: string) => {
    const [place, ...rest] = ref.split(":");
    const field = rest.join(":");
    return place === "relation" ? attributeName(model, field) : fieldLabel(place as End, field);
  };
  const sorting = useTableSort({
    sort,
    fields: sortFields,
    onSort: (next) => onQueryChange({ ...query, sort: next, anchor: undefined }),
    labelFor: refLabel,
  });

  const openRecord = (end: End, record: RelationTableRow["source"]) =>
    onOpen({
      id: record.id,
      objectTypeKey: record.objectTypeKey,
      applicationKey: end === "from" ? fromApplicationKey : toApplicationKey,
      workspaceKey,
    });

  /** A record's column; the name links to the record. */
  function recordColumn(end: End, field: string): DataColumn<RelationTableRow> {
    return {
      key: `${end}:${field}`,
      label: fieldLabel(end, field),
      cell: (row) => {
        const record = end === "from" ? row.source : row.target;
        return field === "name" ? (
          <button className="cell-link" data-row-focus onClick={() => openRecord(end, record)}>
            {record.name}
          </button>
        ) : (
          formatValue(record.fields[field])
        );
      },
    };
  }

  function attributeColumn(attribute: AttributeTypeDefinition): DataColumn<RelationTableRow> {
    return {
      key: relationAttributeColumn(attribute.key),
      label: attribute.name,
      cell: (row) => (
        <RelationValueCell
          key={`${row.relationId}:${row.relationVersion}`}
          attribute={attribute}
          relation={{ id: row.relationId, version: row.relationVersion, attributes: row.attributes }}
          label={`${row.source.name} · ${row.target.name}`}
          editable={editable}
          workspaceKey={workspaceKey}
          onSaved={reload}
        />
      ),
    };
  }

  const endColumns = [
    ...(grouped !== "from" ? config.fromColumns.map((field) => recordColumn("from", field)) : []),
    ...(grouped !== "to" ? config.toColumns.map((field) => recordColumn("to", field)) : []),
  ];
  const attributeColumns = attributes.map(attributeColumn);
  const allKeys = [...endColumns, ...attributeColumns].map((column) => column.key);
  const display = useTableDisplay(allKeys, `${application.key}:${view.key}`);
  const shown = new Set(display.columns);
  const dataColumns = [...endColumns, ...attributeColumns].filter((column) => shown.has(column.key));
  const columns: DataColumn<RelationTableRow>[] = dataColumns.map((column, position) =>
    position === 0 && grouped
      ? {
          ...column,
          cell: (row, index) => (
            <>
              <GroupBand
                row={row}
                index={index}
                end={grouped}
                columns={grouped === "from" ? config.fromColumns : config.toColumns}
                count={groupCounts[(grouped === "from" ? row.source : row.target).id]}
                previous={list.itemAt(index - 1)}
                first={index === list.startIndex}
                model={model}
                onOpen={(record) => openRecord(grouped, record)}
              />
              {column.cell(row, index)}
            </>
          ),
        }
      : column,
  );

  // --- the ticked rows ---
  const tick = (row: RelationTableRow) =>
    setSelection((current) => {
      const rows = new Map(current.key === queryKey ? current.rows : []);
      if (rows.has(row.relationId)) rows.delete(row.relationId);
      else rows.set(row.relationId, { version: row.relationVersion, label: `${row.source.name} · ${row.target.name}` });
      return { key: queryKey, rows };
    });
  const bulkAttribute = attributes.find((item) => item.key === (bulk.attribute ?? attributes[0]?.key));
  async function applyBulk(event: FormEvent) {
    event.preventDefault();
    if (!bulkAttribute || chosen.size === 0) return;
    const value =
      bulkAttribute.valueType === "boolean"
        ? bulk.raw === "true"
        : bulk.raw === ""
          ? null
          : safeValue(bulkAttribute, bulk.raw);
    if (value === undefined) {
      setBulk((current) => ({ ...current, error: `That is not a valid ${bulkAttribute.valueType} value.` }));
      return;
    }
    // The versions as the rows were last read, newer than when they were ticked after a cell's save.
    const fresh = new Map(list.items.map((row) => [row.relationId, row.relationVersion]));
    setApplying(true);
    setBulk((current) => ({ ...current, error: undefined, failed: undefined }));
    try {
      await api.updateRelationBatch({
        workspaceKey,
        items: [...chosen].map(([id, held]) => ({
          id,
          expectedVersion: fresh.get(id) ?? held.version,
          attributes: { [bulkAttribute.key]: value },
        })),
      });
      setSelection({ key: queryKey, rows: new Map() });
      setBulk({ attribute: bulk.attribute, raw: "" });
      reload();
    } catch (cause) {
      const refused = isApiError(cause, "RELATION_BATCH_REFUSED")
        ? (cause.details as { items?: { relationId: string; message: string }[] } | undefined)?.items
        : undefined;
      setBulk((current) => ({
        ...current,
        error: errorMessage(cause),
        failed: refused?.map((item) => `${chosen.get(item.relationId)?.label ?? item.relationId}: ${item.message}`),
      }));
      // A stale version is cured by reading the rows again.
      if (isApiError(cause, "RELATION_BATCH_REFUSED") && refused?.some((item) => /changed/i.test(item.message)))
        reload();
    } finally {
      setApplying(false);
    }
  }

  if (!fromType || !toType) {
    return (
      <div className="empty-state">
        <h2>{view.name}</h2>
        <p>This relationships table shows a record type that does not exist in the current model.</p>
      </div>
    );
  }
  const relationType = model.relationTypes.find((item) => item.key === config.relationTypeKey);
  const noun: [string, string] = ["relationship", "relationships"];

  const selectionColumn = editable
    ? {
        header: <span className="visually-hidden">Select</span>,
        width: 44,
        cell: (row: RelationTableRow) => (
          <SelectionCheckbox
            label={`Select ${row.source.name} · ${row.target.name}`}
            state={chosen.has(row.relationId) ? "all" : "none"}
            onSelect={() => tick(row)}
          />
        ),
      }
    : undefined;

  return (
    <div>
      <PageHeader
        focusTitle
        icon={<HueTile hue={objectTypeHue(model, fromType.key)} icon={fromType.icon} size={40} />}
        title={pageTitle(model, application, view)}
        descriptionClassName="mapping-direction"
        description={
          <>
            <span>{fromType.name}</span>
            <Icon name="arrow-right" size={14} />
            <span>{relationType?.name ?? config.relationTypeKey}</span>
            <Icon name="arrow-right" size={14} />
            <span>{toType.name}</span>
          </>
        }
      />
      {lenses}
      <Card as="section" flush className="collection-surface">
        <div className="collection-toolbar object-toolbar">
          <DebouncedSearchField
            appliedValue={query.search}
            onApply={(search) => onQueryChange({ ...query, search, anchor: undefined })}
            placeholder={`Search ${fromType.pluralName.toLowerCase()} and ${toType.pluralName.toLowerCase()}`}
          />
          <RelationTableFilters
            model={model}
            fields={config.filterFields}
            filters={filters}
            label={refLabel}
            onChange={(next) => onQueryChange({ ...query, filters: next, anchor: undefined })}
          />
          <TableDisplay
            model={model}
            columns={endColumns.map((column) => column.key)}
            extraColumns={{ legend: RELATION_ATTRIBUTES_LABEL, columns: attributeColumns.map((column) => column.key) }}
            columnLabel={(key) =>
              [...endColumns, ...attributeColumns].find((column) => column.key === key)?.label ?? key
            }
            display={display}
            pageSize={pageSize}
            defaultPageSize={config.pageSize}
            onPageSize={(size) => onQueryChange({ ...query, pageSize: size, anchor: undefined })}
            urlBacked
          />
          <SortMenu sorting={sorting} />
        </div>
        {chosen.size > 0 && (
          <form
            className="selection-bar relation-bulk"
            onSubmit={applyBulk}
            aria-label="Change the ticked relationships"
          >
            <strong>{chosen.size === 1 ? "1 relationship ticked" : `${chosen.size} relationships ticked`}</strong>
            <label>
              <span className="visually-hidden">Attribute to set</span>
              <select
                value={bulkAttribute?.key}
                onChange={(event) => setBulk({ attribute: event.target.value, raw: "" })}
              >
                {attributes.map((item) => (
                  <option key={item.key} value={item.key}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            {bulkAttribute && (
              <BulkValue
                attribute={bulkAttribute}
                raw={bulk.raw}
                onChange={(raw) => setBulk((current) => ({ ...current, raw, error: undefined }))}
              />
            )}
            <button className="primary" disabled={applying || !bulkAttribute}>
              {applying
                ? "Setting…"
                : `Set ${bulkAttribute?.name ?? ""} to ${bulk.raw === "" && bulkAttribute?.valueType !== "boolean" ? "empty" : bulkAttribute?.valueType === "boolean" ? (bulk.raw === "true" ? "Yes" : "No") : bulk.raw}`}
            </button>
            <button type="button" className="ghost" onClick={() => setSelection({ key: queryKey, rows: new Map() })}>
              Clear
            </button>
            {bulk.error && (
              <Notice tone="error" title="Nothing was changed" focusOnMount>
                <p>{bulk.error}</p>
                {bulk.failed && (
                  <ul>
                    {bulk.failed.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                )}
              </Notice>
            )}
          </form>
        )}
        {list.error && <InlineError message={list.error} onRetry={list.retry} />}
        {(!list.error || list.items.length > 0) && (
          <DataTable<RelationTableRow>
            columns={columns}
            list={list}
            rowKey={(row) => row.relationId}
            rowHue={(row) => objectTypeHue(model, row.target.objectTypeKey)}
            selection={selectionColumn}
            sorting={sorting}
            columnWidths={display.widths}
            onColumnWidths={display.setWidths}
            label={view.name}
            noun={noun}
            pageSize={pageSize}
            onAnchorChange={onAnchorChange}
            compact={display.compact}
            emptyMessage={
              query.search || filters.length ? "No relationships match these filters." : "No relationships yet."
            }
          />
        )}
      </Card>
    </div>
  );
}

/** A value as a form yields it, or `undefined` when it is not one of the attribute's type. */
export function safeValue(attribute: AttributeTypeDefinition, raw: string) {
  try {
    const value = parseAttributeValue(attribute, raw);
    return typeof value === "number" && Number.isNaN(value) ? undefined : value;
  } catch {
    return undefined;
  }
}

export function BulkValue({
  attribute,
  raw,
  onChange,
}: {
  attribute: AttributeTypeDefinition;
  raw: string;
  onChange: (raw: string) => void;
}) {
  if (attribute.valueType === "boolean")
    return (
      <label>
        <span className="visually-hidden">Value</span>
        <select value={raw || "false"} onChange={(event) => onChange(event.target.value)}>
          <option value="true">Yes</option>
          <option value="false">No</option>
        </select>
      </label>
    );
  return (
    <label>
      <span className="visually-hidden">Value</span>
      <input
        value={raw}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Value"
        type={
          attribute.valueType === "integer" || attribute.valueType === "decimal"
            ? "number"
            : attribute.valueType === "date"
              ? "date"
              : "text"
        }
        step={attribute.valueType === "decimal" ? "any" : undefined}
      />
    </label>
  );
}

/** A filter's equality control: yes/no for a flag, otherwise the value typed. Empty takes the filter off. */
function RelationTableFilters({
  model,
  fields,
  filters,
  label,
  onChange,
}: {
  model: EngineModel;
  fields: string[];
  filters: CollectionFilter[];
  label: (ref: string) => string;
  onChange: (filters: CollectionFilter[]) => void;
}) {
  if (fields.length === 0) return null;
  const set = (field: string, value: string) =>
    onChange([
      ...filters.filter((item) => item.field !== field),
      ...(value === "" ? [] : [{ field, operator: "eq", value }]),
    ]);
  return (
    <div className="relation-table-filters" role="group" aria-label="Filters">
      {fields.map((field) => {
        const current = filters.find((item) => item.field === field)?.value ?? "";
        const key = field.slice(field.indexOf(":") + 1);
        const attribute = model.attributeTypes.find((item) => item.key === key);
        return attribute?.valueType === "boolean" ? (
          <label key={field} className="toolbar-field">
            {label(field)}
            <select value={current} onChange={(event) => set(field, event.target.value)}>
              <option value="">Any</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </label>
        ) : (
          <FilterText
            key={field}
            label={label(field)}
            value={current}
            numeric={attribute?.valueType === "integer" || attribute?.valueType === "decimal"}
            onApply={(value) => set(field, value)}
          />
        );
      })}
    </div>
  );
}

function FilterText({
  label,
  value,
  numeric,
  onApply,
}: {
  label: string;
  value: string;
  numeric: boolean;
  onApply: (value: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  return (
    <label className="toolbar-field">
      {label}
      <input
        type={numeric ? "number" : "text"}
        value={draft}
        placeholder="Equals"
        onChange={(event) => setDraft(event.target.value)}
        onBlur={() => draft.trim() !== value && onApply(draft.trim())}
        onKeyDown={(event) => event.key === "Enter" && onApply(draft.trim())}
      />
    </label>
  );
}

/**
 * The heading of a group, drawn in the first cell of the group's first row: the group's record, its
 * other columns and how many relationships it holds. A list scrolled into a group's middle shows it
 * above the first row it holds.
 */
function GroupBand({
  row,
  index,
  end,
  columns,
  count,
  previous,
  first,
  model,
  onOpen,
}: {
  row: RelationTableRow;
  index: number;
  end: End;
  columns: string[];
  count: number | undefined;
  previous: RelationTableRow | undefined;
  first: boolean;
  model: EngineModel;
  onOpen: (record: RelationTableRow["source"]) => void;
}) {
  const record = end === "from" ? row.source : row.target;
  const before = previous ? (end === "from" ? previous.source : previous.target) : undefined;
  if (index !== 0 && !first && before?.id === record.id) return null;
  const others = columns.filter((column) => column !== "name" && record.fields[column] != null);
  return (
    <div className="relation-group-band">
      <HueTile {...objectTypeTile(model, record.objectTypeKey)} size={18} />
      <button className="cell-link" onClick={() => onOpen(record)}>
        {record.name}
      </button>
      {others.map((column) => (
        <span key={column} className="muted">
          {formatValue(record.fields[column])}
        </span>
      ))}
      {count !== undefined && (
        <span className="relation-group-count">{count === 1 ? "1 relationship" : `${count} relationships`}</span>
      )}
    </div>
  );
}
