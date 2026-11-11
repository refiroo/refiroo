/**
 * Editing a value in place (UA4 revision, UA8, U-D18): the value is the control, with a pencil (or a
 * plus where nothing is set) as Settings › Appearance › Edit pencil says, and a click opens a small
 * form in its place; Save or Enter, Escape or Cancel closes it. A record's fields use it
 * (`features/objects/EditableField`, `InlineAttributeEditor`), and so do the model editor's names
 * (0.10 A4a), so a name is edited the same way wherever it is.
 */

import { useContext, type FormEvent, type ReactNode, type Ref } from "react";
import { readEditHint } from "@/lib/editHint";
import { Icon } from "@/ui/Icon";
import { editIconsRoom } from "@/ui/chipFit";
import { IconButton } from "@/ui/IconButton";
import { CellRoom, RowActive } from "@/ui/tableCell";

export type EditLayout = "row" | "title" | "subtitle";

/**
 * The value as a control: what it shows, and the pencil that says a click edits it. A value that holds a
 * control of its own (`holdsControl`: a link that opens what the value names) cannot be inside the edit
 * button, since a button holds no other control (and a click on the link would also edit): the value reads
 * as before, its link works as a link, and the pencil is the edit button next to it, which Tab reaches.
 */
export function EditInPlaceValue({
  layout,
  name,
  empty = false,
  disabled = false,
  holdsControl = false,
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
  /** The value holds a link or button of its own: only the pencil edits. */
  holdsControl?: boolean;
  controlRef?: Ref<HTMLButtonElement>;
  onEdit: () => void;
  /** The value as it reads. */
  children: ReactNode;
}) {
  const hint = (
    <span className="attribute-edit-hint">
      <Icon name={empty ? "plus" : "pencil"} size={layout === "title" ? 16 : 13} />
    </span>
  );
  if (holdsControl)
    return (
      <span
        className={`attribute-edit attribute-edit-${layout} attribute-edit-holds-control`}
        data-edit-hint={readEditHint()}
        data-disabled={disabled || undefined}
      >
        {children}
        <button ref={controlRef} type="button" className="attribute-edit-pencil" disabled={disabled} onClick={onEdit}>
          <span className="visually-hidden">
            {empty ? "Add" : "Edit"} {name}:
          </span>
          {hint}
        </button>
      </span>
    );
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
      {hint}
    </button>
  );
}

/**
 * A list's cell that edits in place (0.10 A9, D133): the value as the list shows it (a click on it
 * opens the record, as anywhere in the row), then a pencil and, given `onRemove`, a trash. The cell
 * shows them while the pointer is over it, always on touch; they are out of the tab order, since the row's Edit record
 * and its menu are the keyboard's way, unless `tabbable` (a table that has no such row action).
 *
 * In a table only the active row (pointer over it or focus in it, `RowActive`) draws the buttons; the
 * others keep their room empty, so nothing moves when the row becomes active (0.11 X6). The value is
 * told the width the buttons leave it (`CellRoom`).
 */
export function EditInPlaceCell({
  name,
  record,
  disabled = false,
  tabbable = false,
  cellRef,
  onEdit,
  onRemove,
  children,
}: {
  /** What is edited: "Edit {name} of {record}". */
  name: string;
  record: string;
  disabled?: boolean;
  /** The buttons are tab stops: for a table with no row action of its own to edit by (a matrix cell's dialog). */
  tabbable?: boolean;
  cellRef?: Ref<HTMLSpanElement>;
  onEdit: () => void;
  onRemove?: () => void;
  /** The value as the list shows it. */
  children: ReactNode;
}) {
  const active = useContext(RowActive);
  const room = useContext(CellRoom);
  const icons = onRemove ? 2 : 1;
  const reserved = room === undefined ? undefined : editIconsRoom(icons);
  const value = (
    <CellRoom.Provider value={room === undefined || reserved === undefined ? undefined : room - reserved}>
      <span className="cell-edit-value">{children}</span>
    </CellRoom.Provider>
  );
  if (!active)
    return (
      <span className="cell-edit" ref={cellRef}>
        {value}
        <span className="cell-edit-actions cell-edit-actions-kept" data-icons={icons} aria-hidden="true" />
      </span>
    );
  return (
    <span className="cell-edit" ref={cellRef}>
      {value}
      <span className="cell-edit-actions">
        <IconButton
          icon="pencil"
          label={`Edit ${name} of ${record}`}
          tooltip={`Edit ${name}`}
          quiet
          tabIndex={tabbable ? undefined : -1}
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
            tabIndex={tabbable ? undefined : -1}
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
