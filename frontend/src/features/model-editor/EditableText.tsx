/**
 * A text of the model editor edited in place, as a record's title and fields are (`ui/EditInPlace`,
 * the user's request after A4a): an element's name in its heading, a relation type's reverse name, a
 * group's label. The text with its pencil; a click makes it its field, which saves when it is left or
 * on Enter (0.17 UX2), and saving is one step. A refusal stays in the form; a stale draft closes it, as the editor then asks what to do
 * with the change (D41).
 */

import type { ReactNode } from "react";
import type { AttributeTypeDefinition, ModelDraftOutline, ObjectTypeAttributeDefinition } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { EditInPlaceValue, InlineEditForm, useInPlaceEdit } from "@/ui/EditInPlace";
import { Notice } from "@/ui/Notice";
import { refusalText, type StepOutcome } from "@/features/model-editor/OperationDialog";

const field = (name: string): AttributeTypeDefinition => ({
  key: "value",
  name,
  valueType: "text",
  features: {},
  validation: {},
  ui: {},
});
const REQUIRED: ObjectTypeAttributeDefinition = {
  attributeTypeKey: "value",
  required: true,
  readOnly: false,
  order: 0,
  ui: {},
};

export function EditableText({
  value: name,
  label = "Name",
  heading = false,
  outline,
  onSave,
  after,
}: {
  value: string;
  /** What is edited, for the control's name ("Edit Reverse name:") and the field's label. */
  label?: string;
  /** The element's heading (`h2`, the title's size); otherwise an inline value. */
  heading?: boolean;
  outline: ModelDraftOutline;
  /** Saves the new text as one step. */
  onSave: (value: string) => Promise<StepOutcome>;
  /** Beside the text (a heading's mark). */
  after?: ReactNode;
}) {
  const edit = useInPlaceEdit({
    label,
    current: name,
    save: onSave,
    describe: (cause) => refusalText(cause, outline),
  });
  const { editing, saving, error, controlRef } = edit;

  if (editing)
    return (
      <div className={`field-editor field-editor-${heading ? "title" : "row"}`}>
        <InlineEditForm
          label={`Edit ${label}`}
          saving={saving}
          onSubmit={edit.submit}
          onClose={edit.close}
          notices={
            error && (
              <Notice tone="error" title={`The ${label.toLowerCase()} was not saved`}>
                {error}
              </Notice>
            )
          }
        >
          <AttributeField attribute={field(label)} binding={REQUIRED} value={name} autoFocus />
        </InlineEditForm>
      </div>
    );
  const control = (
    <EditInPlaceValue controlRef={controlRef} layout={heading ? "title" : "row"} name={label} onEdit={edit.open}>
      <span className="attribute-value">{name}</span>
    </EditInPlaceValue>
  );
  if (!heading)
    return (
      <>
        {control}
        {after}
      </>
    );
  return (
    <h2 id="element-title" aria-label={name}>
      {control}
      {after}
    </h2>
  );
}
