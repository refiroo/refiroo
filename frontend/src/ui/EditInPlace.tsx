/**
 * Editing a value in place (UA4 revision, UA8, U-D18): the value is the control, with a pencil (or a
 * plus where nothing is set) as Settings › Appearance › Edit pencil says, and a click opens a small
 * form in its place; Save or Enter, Escape or Cancel closes it. A record's fields use it
 * (`features/objects/EditableField`, `InlineAttributeEditor`), and so do the model editor's names
 * (0.10 A4a), so a name is edited the same way wherever it is.
 */

import type { FormEvent, ReactNode, Ref } from "react";
import { readEditHint } from "@/lib/editHint";
import { Icon } from "@/ui/Icon";
import { IconButton } from "@/ui/IconButton";

export type EditLayout = "row" | "title" | "subtitle";

/** The value as a control: what it shows, and the pencil that says a click edits it. */
export function EditInPlaceValue({
  layout,
  name,
  empty = false,
  disabled = false,
  controlRef,
  onEdit,
  children,
}: {
  layout: EditLayout;
  /** What is edited, for its accessible name ("Edit Name:") and an empty title's "Add …". */
  name: string;
  /** Nothing is set yet: a plus, and in a title or subtitle "Add {name}" instead of the value. */
  empty?: boolean;
  disabled?: boolean;
  controlRef?: Ref<HTMLButtonElement>;
  onEdit: () => void;
  /** The value as it reads. */
  children: ReactNode;
}) {
  return (
    <button
      ref={controlRef}
      type="button"
      className={`attribute-edit attribute-edit-${layout}`}
      data-edit-hint={readEditHint()}
      disabled={disabled}
      onClick={(event) => {
        // A click that ends a text selection inside the value is left for copying.
        const selection = window.getSelection();
        if (selection?.toString() && event.currentTarget.contains(selection.anchorNode)) return;
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
          {children}
        </>
      )}
      <span className="attribute-edit-hint">
        <Icon name={empty ? "plus" : "pencil"} size={layout === "title" ? 16 : 13} />
      </span>
    </button>
  );
}

/**
 * A list's cell that edits in place (0.10 A9, D133): the value as the list shows it (a click on it
 * opens the record, as anywhere in the row), then a pencil and, given `onRemove`, a trash. The cell
 * shows them while the pointer is over it, always on touch; they are out of the tab order, since the row's Edit record
 * and its menu are the keyboard's way.
 */
export function EditInPlaceCell({
  name,
  record,
  disabled = false,
  cellRef,
  onEdit,
  onRemove,
  children,
}: {
  /** What is edited: "Edit {name} of {record}". */
  name: string;
  record: string;
  disabled?: boolean;
  cellRef?: Ref<HTMLSpanElement>;
  onEdit: () => void;
  onRemove?: () => void;
  /** The value as the list shows it. */
  children: ReactNode;
}) {
  return (
    <span className="cell-edit" ref={cellRef}>
      <span className="cell-edit-value">{children}</span>
      <span className="cell-edit-actions">
        <IconButton
          icon="pencil"
          label={`Edit ${name} of ${record}`}
          tooltip={`Edit ${name}`}
          quiet
          tabIndex={-1}
          disabled={disabled}
          onClick={onEdit}
        />
        {onRemove && (
          <IconButton
            icon="trash"
            label={`Remove ${name} of ${record}`}
            tooltip={`Remove ${name}`}
            tone="danger"
            quiet
            tabIndex={-1}
            disabled={disabled}
            onClick={onRemove}
          />
        )}
      </span>
    </span>
  );
}

/**
 * The form that takes the value's place: its controls, then any notices, then Cancel and Save.
 * Escape cancels unless it is saving; the controls are disabled while it saves.
 */
export function InlineEditForm({
  label,
  saving,
  onSubmit,
  onClose,
  onChange,
  notices,
  extraActions,
  canSave = true,
  children,
}: {
  label: string;
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onClose: () => void;
  onChange?: () => void;
  /** Below the controls: a conflict, a refusal. */
  notices?: ReactNode;
  /** Between Cancel and Save (Reload current value). */
  extraActions?: ReactNode;
  canSave?: boolean;
  children: ReactNode;
}) {
  return (
    <form
      className="inline-attribute-editor"
      aria-label={label}
      onSubmit={onSubmit}
      onChange={onChange}
      onKeyDown={(event) => {
        if (event.key === "Escape" && !saving) {
          event.preventDefault();
          event.stopPropagation();
          onClose();
        }
      }}
    >
      <fieldset disabled={saving}>{children}</fieldset>
      {notices}
      <div className="dialog-actions">
        <button type="button" className="secondary" disabled={saving} onClick={onClose}>
          Cancel
        </button>
        {extraActions}
        <button className="primary" disabled={saving || !canSave}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </form>
  );
}
