/**
 * A list's cells edited in place (0.10 A9, D131–D138), for `ui/ObjectTable`: a collection and a
 * record's table panel. A value cell (the name or a bound attribute) edits through `EditableField`'s
 * `cell` layout (the value becomes its field and saves when it is left, 0.17 UX2) and removes at once with an Undo toast (`useRemovals`); a relation cell where the row holds at
 * most one sets or changes it through `RelationFormDialog` and removes it at once with an Undo toast; where it holds several, `RelatedRecordsDialog`. Ancestor and containment
 * columns, computed fields, read-only bindings and a read-only list show no icons. One cell edits at
 * a time. A save reloads the list where it is; a value's field says so itself with Undo, a relationship's
 * dialog says where it went in a toast.
 *
 * `renderCell` changes only with what the cells show (the cell being edited, whether editing is
 * possible, the model and the permissions); its handlers read the rest through a ref, so the table's
 * rows draw again only then (0.12 LS1, D373).
 */

import { useCallback, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { useDataApi, useRecordWrites, useWorkspaceData } from "@/state/WorkspaceDataContext";
import { holds, recordWrites } from "@/state/permissions";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import { relatedRecords } from "@/model/fields";
import { RELATED_FIELD_PREFIX, relatedCellEdit, relationTypeFor, type RelatedCellEdit } from "@/model/lookup";
import type { EngineModel, ObjectItem, RelationItem, RelationPage } from "@/types";
import { EditInPlaceCell } from "@/ui/EditInPlace";
import { useToast } from "@/ui/Toast";
import { EditableField, fieldEditing } from "./EditableField";
import { RelatedRecordsDialog } from "./RelatedRecordsDialog";
import { useRemovals } from "./useRemovals";
import { RelationFormDialog } from "./panels/RelationFormDialog";
import { everyPage } from "@/lib/everyPage";

/** What a table cell shows, given the row, the column and the value as the list renders it. */
export type CellRenderer = (item: ObjectItem, column: string, shown: ReactNode) => ReactNode;

type Open =
  | { kind: "value"; id: string; field: string }
  | { kind: "set"; item: ObjectItem; edit: RelatedCellEdit }
  | { kind: "change"; item: ObjectItem; edit: RelatedCellEdit; held: RelationItem }
  | { kind: "many"; item: ObjectItem; edit: RelatedCellEdit };

export function useCellEditing({
  model,
  list,
  readOnly,
  onChanged,
}: {
  model: EngineModel;
  list: CursorWindow<ObjectItem>;
  readOnly: boolean;
  onChanged?: () => void;
}): { renderCell?: CellRenderer; dialogs: ReactNode } {
  const api = useDataApi();
  const { changeSet, warning, permissions } = useWorkspaceData();
  // Each row follows its own type's writes, a relationship either end's (0.12 Z5, D329, D291); a
  // cell holding many records saves as a batch, which needs Bulk and import (D323).
  const writes = useRecordWrites();
  const batches = useMemo(() => (permissions ? recordWrites(permissions, "bulk") : undefined), [permissions]);
  const toast = useToast();
  const { removeRelationship, removeValue } = useRemovals();
  const [open, setOpen] = useState<Open>();
  const [reading, setReading] = useState(false);

  function saved(what: string, item: ObjectItem) {
    setOpen(undefined);
    list.reload();
    onChanged?.();
    toast(warning || `${what} of “${item.name}” saved to ${changeSet ? `change set “${changeSet.name}”` : "Live"}`);
  }

  function reloaded() {
    list.reload();
    onChanged?.();
  }

  const heldOne = (item: ObjectItem, edit: RelatedCellEdit) => heldRelation(api.relations, item, edit);

  async function openSingle(item: ObjectItem, edit: RelatedCellEdit, removing: boolean) {
    setReading(true);
    try {
      const held = await heldOne(item, edit);
      if (removing) {
        // One call puts a relationship back, so removing it asks nothing and offers Undo (0.17 UX1, PP-D40).
        if (held) await removeRelationship(held, relationName(model, held), reloaded);
        else list.reload();
      } else setOpen(held ? { kind: "change", item, edit, held } : { kind: "set", item, edit });
    } catch (cause) {
      toast(errorMessage(cause), { tone: "info" });
    } finally {
      setReading(false);
    }
  }

  // A value's field saves when it is left, so another cell can be opened straight from it; a dialog holds the rest.
  const busy = (open !== undefined && open.kind !== "value") || reading || Boolean(warning);
  /** A value cell closes only itself: the save of a cell left for another ends after that one opened. */
  function closeValue(id: string, field: string) {
    setOpen((now) => (now?.kind === "value" && now.id === id && now.field === field ? undefined : now));
  }
  /** A value saved in its cell: the field's own toast says so with Undo, the list reads the row again. */
  function valueSaved(id: string, field: string) {
    closeValue(id, field);
    reloaded();
  }
  const latest = useRef({ openSingle, valueSaved, closeValue, list, removeValue, reloaded });
  useLayoutEffect(() => {
    latest.current = { openSingle, valueSaved, closeValue, list, removeValue, reloaded };
  });

  const renderCell = useCallback<CellRenderer>(
    (item, column, shown) => {
      const own = writes.permits(item.applicationKey, item.objectTypeKey);
      if (column.startsWith(RELATED_FIELD_PREFIX)) {
        const found = relatedCellEdit(model, item.objectTypeKey, column);
        const choices = found?.choices.filter((choice) => own || writes.permitsType(choice.otherObjectTypeKey));
        if (!found || !choices?.length) return shown;
        const edit = { ...found, choices };
        if (
          !edit.single &&
          (!holds(permissions, "bulk") ||
            (batches &&
              !(
                batches.permits(item.applicationKey, item.objectTypeKey) ||
                choices.some((choice) => batches.permitsType(choice.otherObjectTypeKey))
              )))
        )
          return shown;
        const hasRecords = (relatedRecords(item, column, model)?.count ?? 0) > 0;
        return (
          <EditInPlaceCell
            name={edit.choices[0].label}
            record={item.name}
            disabled={busy}
            onEdit={() =>
              edit.single ? void latest.current.openSingle(item, edit, false) : setOpen({ kind: "many", item, edit })
            }
            onRemove={edit.single && hasRecords ? () => void latest.current.openSingle(item, edit, true) : undefined}
          >
            {shown}
          </EditInPlaceCell>
        );
      }
      const editable = own ? fieldEditing(model, item, column, false) : undefined;
      if (!editable) return shown;
      const editing = open?.kind === "value" && open.id === item.id && open.field === column;
      return (
        <EditableField
          model={model}
          object={item}
          field={column}
          layout="cell"
          display={shown}
          editing={editing}
          disabled={busy}
          onEdit={() => setOpen({ kind: "value", id: item.id, field: column })}
          onClose={() => latest.current.closeValue(item.id, column)}
          onSaved={() => latest.current.valueSaved(item.id, column)}
          onConflict={async () => latest.current.list.reload()}
          onRemove={
            editable.isName
              ? undefined
              : () => void latest.current.removeValue(item, editable.attribute, latest.current.reloaded)
          }
        />
      );
    },
    [model, writes, permissions, batches, open, busy],
  );

  const dialogs = open && (
    <>
      {(open.kind === "set" || open.kind === "change") && (
        <RelationFormDialog
          model={model}
          object={open.item}
          choices={
            open.kind === "change"
              ? open.edit.choices.filter((choice) => choice.otherObjectTypeKey === open.held.object.objectTypeKey)
              : open.edit.choices
          }
          replacing={open.kind === "change" ? open.held : undefined}
          setting={open.kind === "set"}
          onClose={() => setOpen(undefined)}
          onSaved={() => saved(open.edit.choices[0].label, open.item)}
        />
      )}
      {open.kind === "many" && (
        <RelatedRecordsDialog
          model={model}
          object={open.item}
          edit={open.edit}
          onClose={() => setOpen(undefined)}
          onSaved={() => saved(open.edit.choices[0].label, open.item)}
        />
      )}
    </>
  );

  return { renderCell: readOnly ? undefined : renderCell, dialogs };
}

/** A relationship's name as read from the row's end. */
function relationName(model: EngineModel, held: RelationItem): string {
  const definition = relationTypeFor(model, held.relation.relationTypeKey);
  return (held.direction === "outgoing" ? definition?.name : definition?.reverseName) ?? held.relation.relationTypeKey;
}

/** The relationship a row holds in a single-valued column, read with its version. The relation type
 * may also join the record to other types, whose relationships the read cannot leave out, so it
 * reads on until it finds the column's (0.10 R-F4). */
export async function heldRelation(
  read: (objectId: string, options: Parameters<typeof api.relations>[1]) => Promise<RelationPage>,
  item: ObjectItem,
  edit: RelatedCellEdit,
): Promise<RelationItem | undefined> {
  const types = edit.choices.map((choice) => choice.otherObjectTypeKey);
  const ofColumn = (found: RelationItem) => types.includes(found.object.objectTypeKey);
  // Stops at the first page that holds it: later pages are not read.
  const items = await everyPage(
    (cursor) =>
      read(item.id, {
        workspaceKey: item.workspaceKey,
        direction: edit.direction,
        relationTypeKey: edit.relationTypeKey,
        pageSize: 100,
        cursor,
      }),
    { stop: (page) => page.items.some(ofColumn) },
  );
  return items.find(ofColumn);
}
