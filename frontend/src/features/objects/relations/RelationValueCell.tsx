/**
 * One attribute of one relationship as a table cell (0.13 RV): its value, and where it can be written
 * an edit that makes the value its field, which saves when it is left or Enter is pressed (a flag as it
 * is toggled), as every single field does (`ui/EditInPlace`'s `InlineEditForm`, 0.17 UX2). A conflict stays on the row with the relationship as it is saved now. A
 * relationships table and a relation matrix cell's dialog draw their attribute columns with it, so
 * a value is edited the same way in both.
 */

import { useEffect, useRef, useState } from "react";
import type { AttributeTypeDefinition } from "@/types";
import { EditInPlaceCell, InlineEditForm, focusValue } from "@/ui/EditInPlace";
import { FlagCell } from "@/ui/FlagCell";
import { FloatingCellEditor } from "@/ui/FloatingCellEditor";
import { formatValue } from "@/ui/formatValue";
import { RelationAttributes, RelationConflictNotice } from "./RelationAttributes";
import { useRelationValueSave, type StoredRelation } from "./RelationValueField";

export function RelationValueCell({
  attribute,
  relation,
  label,
  editable,
  workspaceKey,
  onSaved,
  onDirty,
  floating = false,
  saved = false,
  tabbable = false,
}: {
  attribute: AttributeTypeDefinition;
  relation: StoredRelation;
  /** What the cell's edit button says the value belongs to. */
  label: string;
  editable: boolean;
  workspaceKey: string;
  onSaved: () => void;
  /** Tells a dialog whether the open form holds input that is not saved. */
  onDirty?: (dirty: boolean) => void;
  /** The form floats over the cell, which keeps its value, so nothing in the table moves. */
  floating?: boolean;
  /** A yes/no value in a floating cell is the control itself; the parent says one was just saved. */
  saved?: boolean;
  /** The edit pencil is a tab stop (a table with no row action to edit by). */
  tabbable?: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [changed, setChanged] = useState(false);
  const edit = useRelationValueSave(attribute, relation, workspaceKey);
  const row = useRef<Element | null>(null);
  const dirty = editing && changed;
  useEffect(() => {
    onDirty?.(dirty);
    return () => onDirty?.(false);
    // The parent's callback is only told what changed.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dirty]);
  const wasEditing = useRef(false);
  useEffect(() => {
    // A floating editor's cell has no control to return to; the row's own does, as a record's cells do.
    if (floating && wasEditing.current && !editing)
      requestAnimationFrame(() => focusValue(row.current?.querySelector<HTMLElement>("[data-row-focus]")));
    wasEditing.current = editing;
  }, [editing, floating]);
  async function save(form: HTMLFormElement) {
    const result = await edit.saveValue(form, onSaved);
    if (result) {
      setEditing(false);
      setChanged(false);
      if (result === "saved") onSaved();
    }
  }
  if (floating && editable && attribute.valueType === "boolean") {
    const stored = relation.attributes[attribute.key] === true;
    return (
      <FlagCell
        label={`${attribute.name} of ${label}`}
        checked={stored}
        saving={edit.saving}
        saved={saved}
        notice={
          (edit.error || edit.current) && (
            <>
              {edit.current && <RelationConflictNotice attributes={[attribute]} current={edit.current} />}
              {edit.error && (
                <span role="alert" className="field-error">
                  {edit.error}
                </span>
              )}
            </>
          )
        }
        onDismiss={edit.reset}
        onToggle={(next) => {
          edit.reset();
          void edit.save({ ...relation.attributes, [attribute.key]: next }).then((done) => done && onSaved());
        }}
      />
    );
  }
  if (!editing)
    return editable ? (
      <EditInPlaceCell
        name={attribute.name}
        record={label}
        tabbable={tabbable}
        onEdit={() => {
          edit.reset();
          setChanged(false);
          setEditing(true);
        }}
      >
        {formatValue(relation.attributes[attribute.key])}
      </EditInPlaceCell>
    ) : (
      <span className="relation-attribute-cell">{formatValue(relation.attributes[attribute.key])}</span>
    );
  const form = (
    <div
      ref={(node) => {
        row.current = node?.closest("tr") ?? row.current;
      }}
      className="relation-attribute-cell is-editing"
    >
      <InlineEditForm
        label={`Edit ${attribute.name}`}
        saving={edit.saving}
        onSubmit={(event) => {
          event.preventDefault();
          void save(event.currentTarget);
        }}
        onClose={() => setEditing(false)}
        onChange={() => setChanged(true)}
        notices={
          (edit.error || edit.current) && (
            <>
              {edit.error && (
                <span role="alert" className="field-error">
                  {edit.error}
                </span>
              )}
              {edit.current && <RelationConflictNotice attributes={[attribute]} current={edit.current} />}
            </>
          )
        }
      >
        <RelationAttributes attributes={[attribute]} relation={relation} mode="edit" legend={false} autoFocus />
      </InlineEditForm>
    </div>
  );
  return floating ? (
    <FloatingCellEditor value={formatValue(relation.attributes[attribute.key])}>{form}</FloatingCellEditor>
  ) : (
    form
  );
}
