/**
 * A cell of an editor table edited in place, as a record's fields are (`ui/EditInPlace`; the user's
 * request after A4a): the value with its pencil, a click or Enter makes it its field in the cell, which
 * saves when it is left, on Enter, or as a choice is made (0.17 UX2), and saving is one step. Cardinality, required, value type, a group's label: whatever the column
 * says (`CellEdit`). A refusal stays in the form with the server's reason (D39).
 */

import type { ReactNode } from "react";
import type { DraftOperation, ModelDraftOutline } from "@/types";
import { EditInPlaceValue, InlineEditForm, useInPlaceEdit } from "@/ui/EditInPlace";
import { Notice } from "@/ui/Notice";
import { refusalText, type RunStep } from "@/features/model-editor/OperationDialog";

/** How a cell is edited: what it is called, its control and the step a new value makes. */
export type CellEdit = {
  label: string;
  value: string;
  /** Choices for a select; a text field without. */
  options?: { value: string; label: string }[];
  /** A text cell that may be emptied (a public name back to its default, a default taken out). */
  optional?: boolean;
  operations: (value: string) => DraftOperation[];
  /** The cell shows a link or button of its own (a group's label opens the group): only the pencil edits. */
  holdsControl?: boolean;
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
  const editor = useInPlaceEdit({
    label: edit.label,
    current: edit.value,
    required: !edit.options && !edit.optional,
    save: (next) => run(edit.operations(next)),
    describe: (cause) => refusalText(cause, outline),
  });
  const { editing, saving, error } = editor;

  if (!editing)
    return (
      <EditInPlaceValue
        controlRef={editor.controlRef}
        layout="row"
        name={edit.label}
        holdsControl={edit.holdsControl}
        onEdit={editor.open}
      >
        <span className="attribute-value">{children}</span>
      </EditInPlaceValue>
    );
  return (
    <div className="field-editor field-editor-row cell-editor">
      <InlineEditForm
        label={`Edit ${edit.label}`}
        saving={saving}
        onSubmit={editor.submit}
        onClose={editor.close}
        notices={
          error && (
            <Notice tone="error" title="Not saved">
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
            <input name="value" defaultValue={edit.value} required={!edit.optional} autoFocus />
          )}
        </label>
      </InlineEditForm>
    </div>
  );
}
