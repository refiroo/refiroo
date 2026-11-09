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
 *
 * In a list's cell (`cell`, 0.10 A9, D133) a click on the value opens the record, so the value is
 * not the control: the cell shows what the caller gives it, and a pencil (and, given `onRemove`, a
 * trash) beside it, out of the tab order, which the cell shows on hover. The editor opens in the
 * cell, above its neighbours; when it closes, focus goes to the row's link.
 */

import { useEffect, useRef, useState, type ReactNode } from "react";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { attributeName, fieldValue } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { formatValue } from "@/ui/formatValue";
import { EditInPlaceCell, EditInPlaceValue } from "@/ui/EditInPlace";
import { FlagCell } from "@/ui/FlagCell";
import { FloatingCellEditor } from "@/ui/FloatingCellEditor";
import { errorMessage, isApiError } from "@/api/errors";
import { Notice } from "@/ui/Notice";
import type {
  AttributeTypeDefinition,
  EngineModel,
  ObjectAttributeValue,
  ObjectItem,
  ObjectTypeAttributeDefinition,
} from "@/types";
import { InlineAttributeEditor } from "./panels/InlineAttributeEditor";

export type FieldLayout = "row" | "title" | "subtitle" | "cell";

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
  display,
  onRemove,
  describeError,
  floating = false,
  onOutside,
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
  /** In a cell: the value as the list shows it. */
  display?: ReactNode;
  /** In a cell: removes the value (the caller confirms); offered where one is set and not required. */
  onRemove?: () => void;
  /** Words a refused save in the caller's terms (see `InlineAttributeEditor`). */
  describeError?: (cause: unknown) => { message: string; action?: ReactNode } | undefined;
  /** In a cell: the editor floats over the cell, which keeps its value, so nothing in the table moves. */
  floating?: boolean;
  /** A floating editor: a press outside it (the caller closes it where nothing is unsaved). */
  onOutside?: () => void;
}) {
  const api = useDataApi();
  const { changeSet, warning } = useWorkspaceData();
  const control = useRef<HTMLButtonElement>(null);
  const cell = useRef<HTMLSpanElement>(null);
  const wasEditing = useRef(editing);
  const [saved, setSaved] = useState(false);
  const editable = fieldEditing(model, object, field, readOnly);

  useEffect(() => {
    if (focusOnMount) control.current?.focus();
    // Only on mount: the parent asks once, when the value takes the editor's place.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (wasEditing.current && !editing)
      requestAnimationFrame(() =>
        layout === "cell"
          ? cell.current?.closest("tr")?.querySelector<HTMLElement>("[data-row-focus]")?.focus()
          : control.current?.focus(),
      );
    wasEditing.current = editing;
  }, [editing, layout]);

  if (editing && editable) {
    const editor = (
      <div className={`field-editor field-editor-${layout}${layout === "cell" ? " cell-editor" : ""}`}>
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
          describeError={describeError}
        />
      </div>
    );
    return floating && layout === "cell" ? (
      <FloatingCellEditor value={display} onOutside={onOutside}>
        {editor}
      </FloatingCellEditor>
    ) : (
      editor
    );
  }

  const status = saved && (
    <span role="status" className={layout === "row" ? "inline-save-status" : "visually-hidden"}>
      {warning || (changeSet ? `Saved to change set “${changeSet.name}”` : "Saved to Live")}
    </span>
  );
  if (!editable)
    return (
      <>
        {layout === "cell" ? display : shownValue(model, object, field)}
        {status}
      </>
    );

  const name = editable.isName ? "Name" : attributeName(model, field);
  if (floating && layout === "cell" && !editable.isName && editable.attribute.valueType === "boolean")
    return (
      <RecordFlagCell
        object={object}
        attribute={editable.attribute}
        label={`${name} of ${object.name}`}
        stored={editable.stored?.value === true}
        exists={Boolean(editable.stored)}
        onSaved={onSaved}
        onConflict={onConflict}
        describeError={describeError}
      />
    );
  const empty = !editable.isName && !editable.stored;
  if (layout === "cell")
    return (
      <EditInPlaceCell
        cellRef={cell}
        name={name}
        record={object.name}
        disabled={disabled || !!warning}
        onEdit={onEdit}
        onRemove={onRemove && !empty && !editable.binding.required ? onRemove : undefined}
      >
        {display}
      </EditInPlaceCell>
    );
  return (
    <>
      <EditInPlaceValue
        controlRef={control}
        layout={layout}
        name={name}
        empty={empty}
        disabled={disabled || !!warning}
        onEdit={() => {
          setSaved(false);
          onEdit();
        }}
      >
        {shownValue(model, object, field)}
      </EditInPlaceValue>
      {status}
    </>
  );
}

/** A yes/no attribute of a record in a floating cell: one click saves it against the record's version. */
function RecordFlagCell({
  object,
  attribute,
  label,
  stored,
  exists,
  onSaved,
  onConflict,
  describeError,
}: {
  object: ObjectItem;
  attribute: AttributeTypeDefinition;
  label: string;
  stored: boolean;
  exists: boolean;
  onSaved: (object: ObjectItem) => void;
  onConflict: () => Promise<void>;
  describeError?: (cause: unknown) => { message: string; action?: ReactNode } | undefined;
}) {
  const api = useDataApi();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [failure, setFailure] = useState<{ message: string; action?: ReactNode }>();
  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), 2500);
    return () => clearTimeout(timer);
  }, [saved]);
  async function toggle(next: boolean) {
    setSaving(true);
    setFailure(undefined);
    setSaved(false);
    try {
      const result = exists
        ? await api.updateAttribute(object.objectTypeKey, object.id, attribute.key, next, object.version)
        : await api.createAttribute(object.objectTypeKey, object.id, attribute.key, next, object.version);
      setSaved(true);
      onSaved(result);
    } catch (cause) {
      const described = describeError?.(cause);
      setFailure({ message: described?.message ?? errorMessage(cause), action: described?.action });
      if (isApiError(cause, "VERSION_CONFLICT") || isApiError(cause, "CHANGE_SET_VERSION_CONFLICT"))
        await onConflict().catch(() => undefined);
    } finally {
      setSaving(false);
    }
  }
  return (
    <FlagCell
      label={label}
      checked={stored}
      saving={saving}
      saved={saved}
      notice={
        failure && (
          <Notice tone="error" title="The value was not saved">
            {failure.message}
            {failure.action}
          </Notice>
        )
      }
      onDismiss={() => setFailure(undefined)}
      onToggle={(next) => void toggle(next)}
    />
  );
}
