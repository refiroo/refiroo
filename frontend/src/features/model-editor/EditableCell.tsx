/**
 * A cell of an editor table edited in place, as a record's fields are (`ui/EditInPlace`; the user's
 * request after A4a): the value with its pencil, a click or Enter opens a one-field form in the cell,
 * and saving is one step. Cardinality, required, value type, a group's label: whatever the column
 * says (`CellEdit`). A refusal stays in the form with the server's reason (D39).
 */

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import type { DraftOperation, ModelDraftOutline } from "@/types";
import { EditInPlaceValue, InlineEditForm } from "@/ui/EditInPlace";
import { Notice } from "@/ui/Notice";
import { refusalText, type RunStep } from "@/features/model-editor/OperationDialog";

/** How a cell is edited: what it is called, its control and the step a new value makes. */
export type CellEdit = {
  label: string;
  value: string;
  /** Choices for a select; a text field without. */
  options?: { value: string; label: string }[];
  operations: (value: string) => DraftOperation[];
};

export const YES_NO = [
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];

export function EditableCell({
  edit,
  outline,
  run,
  children,
}: {
  edit: CellEdit;
  outline: ModelDraftOutline;
  run: RunStep;
  /** The value as the cell shows it. */
  children: ReactNode;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const control = useRef<HTMLButtonElement>(null);
  const wasEditing = useRef(false);

  useEffect(() => {
    if (wasEditing.current && !editing) requestAnimationFrame(() => control.current?.focus());
    wasEditing.current = editing;
  }, [editing]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = String(new FormData(event.currentTarget).get("value") ?? "").trim();
    if (next === edit.value || (!edit.options && !next)) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError("");
    try {
      await run(edit.operations(next));
      setEditing(false);
    } catch (cause) {
      setError(refusalText(cause, outline));
    } finally {
      setSaving(false);
    }
  }

  if (!editing)
    return (
      <EditInPlaceValue controlRef={control} layout="row" name={edit.label} onEdit={() => setEditing(true)}>
        <span className="attribute-value">{children}</span>
      </EditInPlaceValue>
    );
  return (
    <div className="field-editor field-editor-row cell-editor">
      <InlineEditForm
        label={`Edit ${edit.label}`}
        saving={saving}
        onSubmit={submit}
        onClose={() => {
          setError("");
          setEditing(false);
        }}
        notices={
          error && (
            <Notice tone="error" title="Not saved" focusOnMount>
              {error}
            </Notice>
          )
        }
      >
        <label className="cell-editor-field">
          <span className="visually-hidden">{edit.label}</span>
          {edit.options ? (
            <select name="value" defaultValue={edit.value} autoFocus>
              {edit.options.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          ) : (
            <input name="value" defaultValue={edit.value} required autoFocus />
          )}
        </label>
      </InlineEditForm>
    </div>
  );
}
