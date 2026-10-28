/**
 * A list's cells edited in place (0.10 A9, D131–D138), for `ui/ObjectTable`: a collection and a
 * record's table panel. A value cell (the name or a bound attribute) edits through `EditableField`'s
 * `cell` layout and removes through `RemoveValueDialog`; a relation cell where the row holds at
 * most one sets or changes it through `RelationFormDialog` and deletes it through
 * `DeleteRelationDialog`; where it holds several, `RelatedRecordsDialog`. Ancestor and containment
 * columns, computed fields, read-only bindings and a read-only list show no icons. One cell edits at
 * a time. A save reloads the list where it is and says where it went in a toast.
 *
 * `renderCell` changes only with what the cells show (the cell being edited, whether editing is
 * possible, the model and the permissions); its handlers read the rest through a ref, so the table's
 * rows draw again only then (0.12 LS1, D373).
 */

import { useCallback, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { useDataApi, useRecordWrites, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { holds, recordWrites } from "@/features/security/permissions";
import type { CursorWindow } from "@/lib/hooks/useCursorWindow";
import { attributeName, relatedRecords } from "@/model/fields";
import { RELATED_FIELD_PREFIX, relatedCellEdit, type RelatedCellEdit } from "@/model/lookup";
import type { AttributeTypeDefinition, EngineModel, ObjectItem, RelationItem, RelationPage } from "@/types";
import { EditInPlaceCell } from "@/ui/EditInPlace";
import { useToast } from "@/ui/Toast";
import { EditableField, fieldEditing } from "./EditableField";
import { DeleteRelationDialog } from "./DeleteRelationDialog";
import { RelatedRecordsDialog } from "./RelatedRecordsDialog";
import { RemoveValueDialog } from "./RemoveValueDialog";
import { RelationFormDialog } from "./panels/RelationFormDialog";

/** What a table cell shows, given the row, the column and the value as the list renders it. */
export type CellRenderer = (item: ObjectItem, column: string, shown: ReactNode) => ReactNode;

type Open =
  | { kind: "value"; id: string; field: string }
  | { kind: "remove"; item: ObjectItem; attribute: AttributeTypeDefinition }
  | { kind: "set"; item: ObjectItem; edit: RelatedCellEdit }
  | { kind: "change"; item: ObjectItem; edit: RelatedCellEdit; held: RelationItem }
  | { kind: "delete"; item: ObjectItem; held: RelationItem }
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
  const [open, setOpen] = useState<Open>();
  const [reading, setReading] = useState(false);

  function saved(what: string, item: ObjectItem) {
    setOpen(undefined);
    list.reload();
    onChanged?.();
    toast(warning || `${what} of “${item.name}” saved to ${changeSet ? `change set “${changeSet.name}”` : "Live"}`);
  }

  const heldOne = (item: ObjectItem, edit: RelatedCellEdit) => heldRelation(api.relations, item, edit);

  async function openSingle(item: ObjectItem, edit: RelatedCellEdit, removing: boolean) {
    setReading(true);
    try {
      const held = await heldOne(item, edit);
      if (removing) setOpen(held ? { kind: "delete", item, held } : undefined);
      else setOpen(held ? { kind: "change", item, edit, held } : { kind: "set", item, edit });
      if (!held && removing) list.reload();
    } catch (cause) {
      toast(errorMessage(cause), { tone: "info" });
    } finally {
      setReading(false);
    }
  }

  const busy = Boolean(open) || reading || Boolean(warning);
  const latest = useRef({ openSingle, saved, list });
  useLayoutEffect(() => {
    latest.current = { openSingle, saved, list };
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
          disabled={busy && !editing}
          onEdit={() => setOpen({ kind: "value", id: item.id, field: column })}
          onClose={() => setOpen(undefined)}
          onSaved={() => latest.current.saved(attributeName(model, column), item)}
          onConflict={async () => latest.current.list.reload()}
          onRemove={
            editable.isName ? undefined : () => setOpen({ kind: "remove", item, attribute: editable.attribute })
          }
        />
      );
    },
    [model, writes, permissions, batches, open, busy],
  );

  const dialogs = open && (
    <>
      {open.kind === "remove" && (
        <RemoveValueDialog
          object={open.item}
          attribute={open.attribute}
          reload={async () => list.reload()}
          onChanged={onChanged}
          onCancel={() => setOpen(undefined)}
          onRemoved={() => saved(open.attribute.name, open.item)}
        />
      )}
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
      {open.kind === "delete" && (
        <DeleteRelationDialog
          relation={open.held}
          workspaceKey={open.item.workspaceKey}
          onCancel={() => setOpen(undefined)}
          onDeleted={() => saved(relationName(model, open.held), open.item)}
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
  const definition = model.relationTypes.find((relation) => relation.key === held.relation.relationTypeKey);
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
  let cursor: string | undefined;
  do {
    const page = await read(item.id, {
      workspaceKey: item.workspaceKey,
      direction: edit.direction,
      relationTypeKey: edit.relationTypeKey,
      pageSize: 100,
      cursor,
    });
    const held = page.items.find((found) => types.includes(found.object.objectTypeKey));
    if (held) return held;
    cursor = page.nextCursor ?? undefined;
  } while (cursor);
  return undefined;
}
