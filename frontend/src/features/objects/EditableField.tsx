/**
 * One field of one record, shown and edited in place (UA4 revision; UA8, U-D18). The details panel
 * renders its rows with it and the record header its title and subtitle, so a field looks and
 * behaves the same wherever it is: the value is the control, with a pencil (or a plus where nothing
 * is set) as Settings › Appearance › Edit pencil says, and a click opens the editor; Save or Enter,
 * Escape cancels, focus returns to the value, a conflict reloads and says so.
 *
 * What can be edited is read from the model: the built-in `name`, saved by the record update with
 * its version, and an attribute the type binds and does not mark read-only, saved by the attribute
 * routes. Any other field (a computed or built-in one), and every field when read-only, is text.
 * Which field is open is the parent's state, so it can keep one editor open at a time.
 */

import { useEffect, useRef, useState } from "react";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { attributeName, fieldValue } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { readEditHint } from "@/lib/editHint";
import { formatValue } from "@/ui/formatValue";
import { Icon } from "@/ui/Icon";
import type {
  AttributeTypeDefinition,
  EngineModel,
  ObjectAttributeValue,
  ObjectItem,
  ObjectTypeAttributeDefinition,
} from "@/types";
import { InlineAttributeEditor } from "./panels/InlineAttributeEditor";

export type FieldLayout = "row" | "title" | "subtitle";

/** The record's name as the editor takes a field: required text. */
const NAME_ATTRIBUTE: AttributeTypeDefinition = {
  key: "name",
  name: "Name",
  valueType: "text",
  features: {},
  validation: {},
  ui: {},
};
const NAME_BINDING: ObjectTypeAttributeDefinition = {
  attributeTypeKey: "name",
  required: true,
  readOnly: false,
  order: 0,
  ui: {},
};

export interface FieldEditing {
  binding: ObjectTypeAttributeDefinition;
  attribute: AttributeTypeDefinition;
  /** The value stored now: an attribute's, or the name's; none where the attribute is not set. */
  stored?: Pick<ObjectAttributeValue, "value">;
  /** The attribute value as stored, which the details panel's remove names. */
  attributeValue?: ObjectAttributeValue;
  isName: boolean;
}

/** How `field` of `object` is edited in place, or `undefined` where it is shown as text. */
export function fieldEditing(
  model: EngineModel,
  object: ObjectItem,
  field: string,
  readOnly: boolean,
): FieldEditing | undefined {
  if (readOnly) return undefined;
  if (field === "name")
    return { binding: NAME_BINDING, attribute: NAME_ATTRIBUTE, stored: { value: object.name }, isName: true };
  const binding = objectTypeFor(model, object.objectTypeKey)?.attributes.find(
    (item) => item.attributeTypeKey === field,
  );
  const attribute = model.attributeTypes.find((item) => item.key === field);
  if (!binding || !attribute || binding.readOnly) return undefined;
  const attributeValue = object.attributes.find((item) => item.attributeTypeKey === field);
  return { binding, attribute, stored: attributeValue, attributeValue, isName: false };
}

/** A field's value as it reads, telling not set, null and empty text apart. */
function shownValue(model: EngineModel, object: ObjectItem, field: string) {
  if (field === "name") return <span className="attribute-value">{object.name}</span>;
  const isAttribute = model.attributeTypes.some((item) => item.key === field);
  if (!isAttribute) return <span className="attribute-value">{formatValue(fieldValue(object, field, model))}</span>;
  const stored = object.attributes.find((item) => item.attributeTypeKey === field);
  if (!stored) return <span className="unset-value">Not set</span>;
  if (stored.value === null) return <span className="unset-value">Null</span>;
  if (stored.value === "") return <span className="unset-value">Empty text</span>;
  return <span className="attribute-value">{formatValue(stored.value)}</span>;
}

export function EditableField({
  model,
  object,
  field,
  layout,
  readOnly = false,
  editing,
  disabled = false,
  focusOnMount = false,
  onEdit,
  onClose,
  onSaved,
  onConflict,
}: {
  model: EngineModel;
  object: ObjectItem;
  field: string;
  layout: FieldLayout;
  readOnly?: boolean;
  /** Whether this field's editor is open (the parent's state). */
  editing: boolean;
  /** Another field is being edited or removed. */
  disabled?: boolean;
  /** Focus the value when it appears: the header's title returns here after its editor closes. */
  focusOnMount?: boolean;
  onEdit: () => void;
  onClose: () => void;
  onSaved: (object: ObjectItem) => void;
  onConflict: () => Promise<void>;
}) {
  const api = useDataApi();
  const { changeSet, warning } = useWorkspaceData();
  const control = useRef<HTMLButtonElement>(null);
  const wasEditing = useRef(editing);
  const [saved, setSaved] = useState(false);
  const editable = fieldEditing(model, object, field, readOnly);

  useEffect(() => {
    if (focusOnMount) control.current?.focus();
    // Only on mount: the parent asks once, when the value takes the editor's place.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (wasEditing.current && !editing) requestAnimationFrame(() => control.current?.focus());
    wasEditing.current = editing;
  }, [editing]);

  if (editing && editable)
    return (
      <div className={`field-editor field-editor-${layout}`}>
        <InlineAttributeEditor
          object={object}
          binding={editable.binding}
          attribute={editable.attribute}
          stored={editable.stored}
          save={
            editable.isName
              ? (value) =>
                  api.updateObject(object.objectTypeKey, object.id, {
                    name: String(value ?? ""),
                    expectedVersion: object.version,
                  })
              : undefined
          }
          onClose={onClose}
          onSaved={(next) => {
            setSaved(true);
            onSaved(next);
          }}
          onConflict={onConflict}
        />
      </div>
    );

  const status = saved && (
    <span role="status" className={layout === "row" ? "inline-save-status" : "visually-hidden"}>
      {warning || (changeSet ? `Saved to change set “${changeSet.name}”` : "Saved to Live")}
    </span>
  );
  if (!editable)
    return (
      <>
        {shownValue(model, object, field)}
        {status}
      </>
    );

  const name = editable.isName ? "Name" : attributeName(model, field);
  const empty = !editable.isName && !editable.stored;
  return (
    <>
      <button
        ref={control}
        type="button"
        className={`attribute-edit attribute-edit-${layout}`}
        data-edit-hint={readEditHint()}
        disabled={disabled || !!warning}
        onClick={(event) => {
          // A click that ends a text selection inside the value is left for copying.
          const selection = window.getSelection();
          if (selection?.toString() && event.currentTarget.contains(selection.anchorNode)) return;
          setSaved(false);
          onEdit();
        }}
      >
        {empty && layout !== "row" ? (
          <span className="unset-value">Add {name}</span>
        ) : (
          <>
            <span className="visually-hidden">
              {empty ? "Add" : "Edit"} {name}:
            </span>{" "}
            {shownValue(model, object, field)}
          </>
        )}
        <span className="attribute-edit-hint">
          <Icon name={empty ? "plus" : "pencil"} size={layout === "title" ? 16 : 13} />
        </span>
      </button>
      {status}
    </>
  );
}
