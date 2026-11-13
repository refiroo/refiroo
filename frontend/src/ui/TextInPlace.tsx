/**
 * A name or a short text of a settings page changed where it stands (0.17 UX1, PP-D40): the value with its
 * pencil, a click makes it the field, and leaving the field or Enter saves; Escape puts the old text back
 * (`InlineEditForm`, 0.17 UX2). A saved change says so with a toast and, where `onSave` hands back the call that
 * puts the old value back, offers Undo. A refusal, and a required text left empty, stay under the field.
 */

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { errorMessage } from "@/api/errors";
import { EditInPlaceValue, InlineEditForm, focusValue } from "@/ui/EditInPlace";
import { Notice } from "@/ui/Notice";
import { useToast } from "@/ui/Toast";

export function TextInPlace({
  value,
  label,
  heading = false,
  headingLevel = 2,
  optional = false,
  maxLength,
  savedText = "Saved.",
  disabled = false,
  onSave,
  children,
}: {
  value: string;
  /** What is edited: the control's name ("Edit Name:") and the field's. */
  label: string;
  /** The page's title (`h2`, the title's size); otherwise a line. */
  heading?: boolean;
  /** The heading's level: 1 where it is the title of an opened item's page (0.17 ST1). */
  headingLevel?: 1 | 2;
  /** May be left empty (a description): an empty value shows "Add {label}". */
  optional?: boolean;
  maxLength?: number;
  /** The toast a saved change shows. */
  savedText?: string;
  disabled?: boolean;
  /** Saves the new text. A refusal is thrown and shown under the field; the result, where there is one, puts the old text back; false means nothing was saved (the draft moved on) and is said elsewhere, so no saved message. */
  onSave: (next: string) => Promise<void | false | (() => Promise<unknown>)>;
  /** The value as it reads (default: the text). */
  children?: ReactNode;
}) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const controlRef = useRef<HTMLButtonElement>(null);
  const wasEditing = useRef(false);
  const toast = useToast();

  // Focus returns to the value when its field closes.
  useEffect(() => {
    if (wasEditing.current && !editing) requestAnimationFrame(() => focusValue(controlRef.current));
    wasEditing.current = editing;
  }, [editing]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = String(new FormData(event.currentTarget).get("value") ?? "").trim();
    if (next === value) {
      setEditing(false);
      return;
    }
    if (!next && !optional) {
      setError(`${label} needs a value.`);
      return;
    }
    setSaving(true);
    setError("");
    try {
      const undo = await onSave(next);
      setEditing(false);
      if (undo === false) return;
      toast(
        savedText,
        undo
          ? {
              actions: [
                {
                  label: "Undo",
                  onPress: () =>
                    void undo().then(
                      () => toast("Change undone."),
                      (cause) => toast(`Not undone: ${errorMessage(cause)}`, { tone: "info" }),
                    ),
                },
              ],
            }
          : undefined,
      );
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setSaving(false);
    }
  }

  const shown = children ?? <span className="attribute-value">{value}</span>;
  const Heading = headingLevel === 1 ? "h1" : "h2";
  const wrapper = (content: ReactNode) =>
    heading ? (
      <Heading className="text-in-place text-in-place-heading" aria-label={value || label}>
        {content}
      </Heading>
    ) : (
      <div className="text-in-place">{content}</div>
    );

  if (editing)
    return wrapper(
      <InlineEditForm
        label={`Edit ${label}`}
        saving={saving}
        onSubmit={(event) => void submit(event)}
        onClose={() => {
          setError("");
          setEditing(false);
        }}
        notices={
          error && (
            <Notice tone="error" title="Not saved">
              {error}
            </Notice>
          )
        }
      >
        <label>
          <span className="visually-hidden">{label}</span>
          <input name="value" autoFocus maxLength={maxLength} defaultValue={value} required={!optional} />
        </label>
      </InlineEditForm>,
    );
  return wrapper(
    <EditInPlaceValue
      controlRef={controlRef}
      layout={heading ? "title" : optional && !value ? "subtitle" : "row"}
      name={label}
      empty={optional && !value}
      disabled={disabled}
      onEdit={() => setEditing(true)}
    >
      {shown}
    </EditInPlaceValue>,
  );
}
