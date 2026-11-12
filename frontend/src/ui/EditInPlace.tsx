/**
 * Editing a value in place (UA4 revision, UA8, U-D18): the value is the control, with a pencil (or a
 * plus where nothing is set) as Settings › Appearance › Edit pencil says, and a click makes the value
 * its field, which saves when it is left (`InlineEditForm`). A record's fields use it
 * (`features/objects/EditableField`, `InlineAttributeEditor`), and so do the model editor's names
 * (0.10 A4a), so a name is edited the same way wherever it is.
 */

import {
  useContext,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
  type Ref,
} from "react";
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
 * Focus goes back to the value when its field closes, unless the person already took it elsewhere (a
 * field left by Tab or by a click on another control keeps focus where it went).
 */
export function focusValue(target: HTMLElement | null | undefined) {
  if (!document.activeElement || document.activeElement === document.body) target?.focus();
}

/** What the field's controls hold now, to tell a changed input from an untouched one. */
function fieldSnapshot(form: HTMLFormElement): string {
  return JSON.stringify([...new FormData(form).entries()].map(([name, value]) => [name, String(value)]));
}

/**
 * One field edited where it stands (0.17 UX2, PP-D68): the value becomes its control, and leaving it
 * saves. There are no Cancel and Save buttons. Enter saves (in a text of several lines Enter is a new
 * line, and Ctrl or Cmd with Enter saves); a choice from a list and a tick save as they are made;
 * Escape puts the old value back and saves nothing. An input left as it was opened closes the field
 * and nothing is saved. A refusal stays under the field with the input kept and the field open:
 * leaving it again saves only once the input has changed, and Cancel and Save again stand under the
 * reason for the pointer.
 *
 * The caller's `onSubmit` reads the form and saves; it closes the field itself when the save is done.
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
  /** Between Cancel and Save again (Reload current value). */
  extraActions?: ReactNode;
  canSave?: boolean;
  children: ReactNode;
}) {
  const form = useRef<HTMLFormElement>(null);
  /** The input as the field opened, and as it was last sent and refused. */
  const opened = useRef<string | undefined>(undefined);
  const [refused, setRefused] = useState<string>();
  const busy = useRef(saving);
  const wasSaving = useRef(false);
  useLayoutEffect(() => {
    busy.current = saving;
  });
  useLayoutEffect(() => {
    if (form.current) opened.current = fieldSnapshot(form.current);
  }, []);
  // A text opens with the caret after it, where typing goes on.
  useEffect(() => {
    const control = form.current?.querySelector("fieldset input, fieldset textarea");
    if (
      control === document.activeElement &&
      (control instanceof HTMLTextAreaElement || (control instanceof HTMLInputElement && control.type === "text"))
    )
      control.setSelectionRange(control.value.length, control.value.length);
  }, []);
  // A refused save hands the field back: focus returns to the input, which is kept.
  const focusField = () =>
    form.current?.querySelector<HTMLElement>("fieldset input, fieldset textarea, fieldset select")?.focus();
  useEffect(() => {
    if (wasSaving.current && !saving) focusField();
    wasSaving.current = saving;
  }, [saving]);

  // A press outside the field leaves it: saved at the press, so a click that opens another field (which may take
  // this one off the page) cannot come first, with a mouse or a finger.
  const leave = useRef(() => {});
  useLayoutEffect(() => {
    leave.current = () => save(false);
  });
  useEffect(() => {
    const press = (event: Event) => {
      if (form.current && !form.current.contains(event.target as Node | null)) leave.current();
    };
    document.addEventListener("pointerdown", press, true);
    return () => document.removeEventListener("pointerdown", press, true);
  }, []);

  /** Saves what the field holds; `asked` is Enter, a choice or Save again, otherwise focus left. */
  function save(asked: boolean) {
    const node = form.current;
    if (!node || !node.isConnected || busy.current) return;
    const now = fieldSnapshot(node);
    if (now === opened.current) {
      onClose();
      return;
    }
    if (!asked && now === refused) return;
    if (!canSave) return;
    setRefused(now);
    node.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    // Refused before anything was sent (a required field left empty): the field is still here and not saving.
    setTimeout(() => {
      if (!busy.current) focusField();
    });
  }

  return (
    <form
      ref={form}
      className="inline-attribute-editor"
      aria-label={label}
      noValidate
      onSubmit={onSubmit}
      onChange={(event) => {
        onChange?.();
        const target = event.target as Element;
        if (target instanceof HTMLSelectElement || (target instanceof HTMLInputElement && target.type === "checkbox"))
          save(true);
      }}
      onBlur={(event) => {
        const next = event.relatedTarget as Node | null;
        if (event.currentTarget.contains(next)) return;
        // Focus moved to another control: saved now, before that control acts.
        if (next) save(false);
        // Otherwise where focus went is known once the event is over; a window that lost focus keeps it here.
        else
          setTimeout(() => {
            if (form.current && !form.current.contains(document.activeElement)) save(false);
          });
      }}
      onKeyDown={(event) => {
        if (saving) return;
        if (event.key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          onClose();
        } else if (event.key === "Enter" && !event.nativeEvent.isComposing) {
          const target = event.target as Element;
          const lines = target instanceof HTMLTextAreaElement;
          if (
            (lines && (event.ctrlKey || event.metaKey)) ||
            (target instanceof HTMLInputElement && target.type !== "checkbox")
          ) {
            event.preventDefault();
            save(true);
          }
        }
      }}
    >
      <fieldset disabled={saving}>{children}</fieldset>
      {saving && (
        <span role="status" className="inline-edit-saving">
          Saving…
        </span>
      )}
      {notices}
      {refused !== undefined && !saving && (
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose}>
            Cancel
          </button>
          {extraActions}
          <button type="button" className="primary" disabled={!canSave} onClick={() => save(true)}>
            Save again
          </button>
        </div>
      )}
    </form>
  );
}
