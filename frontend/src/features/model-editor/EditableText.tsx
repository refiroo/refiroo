/**
 * A text of the model editor edited in place, as a record's title and fields are (`ui/EditInPlace`,
 * the user's request after A4a): an element's name in its heading, a relation type's reverse name, a
 * group's label. The text with its pencil; a click opens the form in its place, and saving is one
 * step. A refusal stays in the form; a stale draft closes it, as the editor then asks what to do
 * with the change (D41).
 */

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import type { AttributeTypeDefinition, ModelDraftOutline, ObjectTypeAttributeDefinition } from "@/types";
import { AttributeField } from "@/ui/AttributeField";
import { EditInPlaceValue, InlineEditForm } from "@/ui/EditInPlace";
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
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const controlRef = useRef<HTMLButtonElement>(null);
  const wasEditing = useRef(false);

  // Focus returns to the name when its form closes.
  useEffect(() => {
    if (wasEditing.current && !editing) requestAnimationFrame(() => controlRef.current?.focus());
    wasEditing.current = editing;
  }, [editing]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = String(new FormData(event.currentTarget).get("value") ?? "").trim();
    if (!next || next === name) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError("");
    try {
      await onSave(next);
      setEditing(false);
    } catch (cause) {
      setError(refusalText(cause, outline));
    } finally {
      setSaving(false);
    }
  }

  if (editing)
    return (
      <div className={`field-editor field-editor-${heading ? "title" : "row"}`}>
        <InlineEditForm
          label={`Edit ${label}`}
          saving={saving}
          onSubmit={submit}
          onClose={() => {
            setError("");
            setEditing(false);
          }}
          notices={
            error && (
              <Notice tone="error" title={`The ${label.toLowerCase()} was not saved`} focusOnMount>
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
    <EditInPlaceValue
      controlRef={controlRef}
      layout={heading ? "title" : "row"}
      name={label}
      onEdit={() => setEditing(true)}
    >
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
