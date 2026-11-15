/**
 * The records of a relation matrix cell as one table (0.13 RV): a row per record, the record's name
 * and the view's `cellFields` under the cell type's name, then the binding's relationship attributes
 * under their own group, then the row's actions. Wherever the cell can be written every value edits
 * where it stands, with the cells the other tables use: a record's field through `EditableField` (the
 * record's version claimed), a relationship's value through `RelationValueCell` (the relationship's).
 * A save re-reads the cell and the dialog stays open. Unlink asks in the row. The table scrolls
 * sideways inside its container, the name and the actions keeping their place.
 */

import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { attributeTypeFor } from "@/model/lookup";
import { StatusPill } from "@/ui/StatusPill";
import { EditableField } from "@/features/objects/EditableField";
import { RelationValueCell } from "@/features/objects/relations/RelationValueCell";
import { RELATION_ATTRIBUTES_LABEL } from "@/features/objects/relations/RelationAttributes";
import type { MatrixBinding } from "@/features/objects/relationMatrixStates";
import { attributeName } from "@/model/fields";
import { objectTypeTile } from "@/model/hues";
import type {
  AttributeTypeDefinition,
  EngineModel,
  ObjectItem,
  ObjectTypeDefinition,
  RelationMatrixCellRecord,
} from "@/types";
import { formatValue } from "@/ui/formatValue";
import { HueTile } from "@/ui/HueTile";
import { Icon } from "@/ui/Icon";
import { IconButton } from "@/ui/IconButton";

/** The cell record as the record edit-in-place takes it: only what saving a field reads. */
function recordItem(
  model: EngineModel,
  cellType: ObjectTypeDefinition,
  record: RelationMatrixCellRecord,
  workspaceKey: string,
  applicationKey: string,
): ObjectItem {
  return {
    id: record.id,
    workspaceKey,
    applicationKey,
    objectTypeKey: cellType.key,
    parentObjectId: null,
    name: record.name,
    path: [],
    attributes: Object.entries(record.fields).flatMap(([key, value]) => {
      const definition = attributeTypeFor(model, key);
      // The read gives every cell field, null where the record holds no value for it.
      return definition && value !== null && value !== undefined
        ? [{ id: "", attributeTypeKey: key, name: definition.name, valueType: definition.valueType, value }]
        : [];
    }),
    version: record.version,
    createdAt: null,
    updatedAt: null,
  };
}

/** Whether a record shows `filter` in its name or in a value of its fields (case does not matter). */
export const recordMatches = (record: RelationMatrixCellRecord, filter: string) => {
  const needle = filter.trim().toLowerCase();
  if (!needle) return true;
  return [record.name, ...Object.values(record.fields).map((value) => formatValue(value))].some(
    (text) => typeof text === "string" && text.toLowerCase().includes(needle),
  );
};

export function RelationMatrixCellTable({
  model,
  cellType,
  applicationKey,
  records,
  fields,
  relationAttributes,
  binding,
  workspaceKey,
  rowName,
  columnName,
  filter,
  history,
  editRecords,
  editValues,
  canUnlink,
  canCreateFrom,
  saving,
  onRefresh,
  onOpenRecord,
  onUnlink,
  onCreateFrom,
  onRecordDirty,
  onValuesDirty,
  describeError,
}: {
  model: EngineModel;
  cellType: ObjectTypeDefinition;
  applicationKey: string;
  records: RelationMatrixCellRecord[];
  /** The view's `cellFields`. */
  fields: string[];
  relationAttributes: AttributeTypeDefinition[];
  binding: MatrixBinding;
  workspaceKey: string;
  rowName: string;
  columnName: string;
  filter: string;
  /** A publication's records: shown, never changed; they can only seed a create. */
  history: boolean;
  /** The records' own fields edit in place. */
  editRecords: boolean;
  /** The relationships' values edit in place. */
  editValues: boolean;
  canUnlink: boolean;
  canCreateFrom: boolean;
  saving: boolean;
  onRefresh: () => Promise<void>;
  onOpenRecord: (record: RelationMatrixCellRecord) => void;
  onUnlink: (record: RelationMatrixCellRecord) => void;
  onCreateFrom: (record: RelationMatrixCellRecord) => void;
  onRecordDirty: (dirty: boolean) => void;
  onValuesDirty: (dirty: boolean) => void;
  /** Words a refused record save in the view's terms. */
  describeError?: (cause: unknown) => { message: string; action?: ReactNode } | undefined;
}) {
  // One record field open at a time; `changed` once its form was touched, which asks before closing.
  const [open, setOpen] = useState<{ id: string; field: string; changed: boolean }>();
  const [confirming, setConfirming] = useState<string>();
  // The relationship value saved last, for a yes/no cell's "Saved" (its cell is drawn anew by the save).
  const [savedValue, setSavedValue] = useState<string>();
  useEffect(() => {
    if (!savedValue) return;
    const timer = setTimeout(() => setSavedValue(undefined), 2500);
    return () => clearTimeout(timer);
  }, [savedValue]);
  const dirtyValues = useRef(new Set<string>());
  const dataFields = fields.filter((field) => field !== "name");
  const shown = records.filter((record) => recordMatches(record, filter));
  const hasActions = !history || canCreateFrom;
  const columnCount = 1 + dataFields.length + relationAttributes.length + (hasActions ? 1 : 0);

  // The widths the first rows laid out are kept, so no column or row moves when an editor opens,
  // saves, fails or closes (as ui/DataTable freezes its columns); new columns lay out anew.
  const table = useRef<HTMLTableElement>(null);
  const layoutKey = [dataFields.join(","), relationAttributes.map((item) => item.key).join(","), hasActions].join("|");
  const [frozen, setFrozen] = useState<{ key: string; widths: number[] }>();
  const widths = frozen?.key === layoutKey ? frozen.widths : undefined;
  useLayoutEffect(() => {
    const head = table.current?.tHead;
    if (widths || !head || head.rows.length < 2 || shown.length === 0) return;
    const cells = [
      ...Array.from(head.rows[1].cells),
      ...(hasActions ? [head.rows[0].cells[head.rows[0].cells.length - 1]] : []),
    ];
    const measured = cells.map((cell) => cell.getBoundingClientRect().width);
    if (measured.length === columnCount && measured.every((width) => width > 0))
      setFrozen({ key: layoutKey, widths: measured });
  }, [widths, shown.length, layoutKey, columnCount, hasActions]);

  const changeOpen = (next: typeof open) => {
    setOpen(next);
    onRecordDirty(Boolean(next?.changed));
  };
  /** A record field closes only itself: the save of a field left for another ends after that one opened. */
  const openNow = useRef(open);
  useLayoutEffect(() => {
    openNow.current = open;
  });
  const closeField = (id: string, field: string) => {
    if (openNow.current?.id === id && openNow.current.field === field) changeOpen(undefined);
  };
  // Several relationship values may hold input at once (one per row); the dialog hears "any".
  const valuesDirty = (key: string) => (dirty: boolean) => {
    if (dirty) dirtyValues.current.add(key);
    else dirtyValues.current.delete(key);
    onValuesDirty(dirtyValues.current.size > 0);
  };

  return (
    <div
      className="matrix-cell-table-wrap"
      tabIndex={0}
      role="region"
      aria-label={`${cellType.pluralName} in this cell`}
    >
      <table
        ref={table}
        className={widths ? "matrix-cell-table is-frozen" : "matrix-cell-table"}
        style={widths ? { width: `${widths.reduce((sum, width) => sum + width, 0)}px` } : undefined}
      >
        {widths && (
          <colgroup>
            {widths.map((width, position) => (
              <col key={position} style={{ width: `${width}px` }} />
            ))}
          </colgroup>
        )}
        <thead>
          <tr className="matrix-cell-groups">
            <th scope="colgroup" colSpan={1 + dataFields.length} className="matrix-cell-sticky-start">
              {cellType.name}
            </th>
            {relationAttributes.length > 0 && (
              <th scope="colgroup" colSpan={relationAttributes.length} className="matrix-cell-relation-group first-rel">
                <span className="matrix-cell-group-label">
                  <Icon name="arrow-right" size={12} />
                  {RELATION_ATTRIBUTES_LABEL}
                </span>
              </th>
            )}
            {hasActions && (
              <th rowSpan={2} className="matrix-cell-sticky-end">
                <span className="visually-hidden">Actions</span>
              </th>
            )}
          </tr>
          <tr>
            <th scope="col" className="matrix-cell-sticky-start">
              Name
            </th>
            {dataFields.map((field) => (
              <th scope="col" key={field}>
                {attributeName(model, field)}
              </th>
            ))}
            {relationAttributes.map((attribute, index) => (
              <th
                scope="col"
                key={attribute.key}
                className={`matrix-cell-relation-group${index === 0 ? " first-rel" : ""}${attribute.valueType === "boolean" ? " is-flag" : ""}`}
              >
                {attribute.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((record) => {
            if (confirming === record.id)
              return (
                <tr key={record.id} className="matrix-cell-confirm">
                  <td colSpan={columnCount}>
                    <div className="matrix-cell-confirm-line">
                      <Icon name="unlink" size={15} />
                      <span>
                        Unlink <strong>{record.name}</strong>? {rowName} will no longer be linked to it in {columnName}.
                        The {cellType.name.toLowerCase()} itself stays.
                      </span>
                      <span className="matrix-cell-spacer" />
                      <button
                        type="button"
                        className="secondary"
                        disabled={saving}
                        onClick={() => setConfirming(undefined)}
                      >
                        Keep
                      </button>
                      <button
                        type="button"
                        className="danger"
                        autoFocus
                        disabled={saving}
                        onClick={() => onUnlink(record)}
                      >
                        {saving ? "Unlinking…" : "Unlink"}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            const item = recordItem(model, cellType, record, workspaceKey, applicationKey);
            const dimmed = binding.conditional && !record.meetsCondition;
            const relation = {
              id: record.relationId,
              version: record.relationVersion,
              attributes: record.relationAttributes ?? {},
            };
            return (
              <tr key={record.id} className={dimmed ? "matrix-cell-inactive" : undefined}>
                <td className="matrix-cell-sticky-start">
                  <span className="matrix-record-name">
                    <HueTile {...objectTypeTile(model, cellType.key)} size={18} />
                    {history ? (
                      record.name
                    ) : (
                      <button type="button" className="cell-link" data-row-focus onClick={() => onOpenRecord(record)}>
                        {record.name}
                      </button>
                    )}
                    {dimmed && (
                      <StatusPill tone="neutral" marker={false}>
                        Does not count
                      </StatusPill>
                    )}
                  </span>
                </td>
                {dataFields.map((field) => {
                  const editing = open?.id === record.id && open.field === field;
                  return (
                    <td key={field}>
                      <div onChange={() => open && !open.changed && changeOpen({ ...open, changed: true })}>
                        <EditableField
                          model={model}
                          object={item}
                          field={field}
                          layout="cell"
                          readOnly={!editRecords}
                          display={formatValue(record.fields[field])}
                          editing={editing}
                          onEdit={() => changeOpen({ id: record.id, field, changed: false })}
                          onClose={() => closeField(record.id, field)}
                          onSaved={() => {
                            closeField(record.id, field);
                            void onRefresh();
                          }}
                          onConflict={onRefresh}
                          describeError={describeError}
                          floating
                          tabbable
                          onOutside={() => {
                            if (open && !open.changed) changeOpen(undefined);
                          }}
                        />
                      </div>
                    </td>
                  );
                })}
                {relationAttributes.map((attribute, index) => (
                  <td
                    key={attribute.key}
                    className={`matrix-cell-relation-group${index === 0 ? " first-rel" : ""}${attribute.valueType === "boolean" ? " is-flag" : ""}`}
                  >
                    <RelationValueCell
                      // A saved value brings a new version, which the cell's save starts from.
                      key={`${record.relationId}:${record.relationVersion}`}
                      attribute={attribute}
                      relation={relation}
                      label={record.name}
                      editable={editValues}
                      workspaceKey={workspaceKey}
                      saved={savedValue === `${record.relationId}:${attribute.key}`}
                      onSaved={() => {
                        setSavedValue(`${record.relationId}:${attribute.key}`);
                        void onRefresh();
                      }}
                      floating
                      tabbable
                      onDirty={valuesDirty(`${record.relationId}:${attribute.key}`)}
                    />
                  </td>
                ))}
                {hasActions && (
                  <td className="matrix-cell-sticky-end">
                    <div className="matrix-cell-row-actions">
                      {!history && (
                        <IconButton
                          icon="arrow-up-right"
                          label={`Open ${record.name}`}
                          tooltip="Open"
                          quiet
                          onClick={() => onOpenRecord(record)}
                        />
                      )}
                      {canUnlink && (
                        <IconButton
                          icon="unlink"
                          label={`Unlink ${record.name}`}
                          tooltip="Unlink"
                          tone="danger"
                          quiet
                          onClick={() => setConfirming(record.id)}
                        />
                      )}
                      {canCreateFrom && (
                        <button type="button" className="secondary" onClick={() => onCreateFrom(record)}>
                          Create from this
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            );
          })}
          {shown.length === 0 && (
            <tr>
              <td colSpan={columnCount} className="matrix-cell-no-match">
                No {cellType.name.toLowerCase()} matches “{filter.trim()}”.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
