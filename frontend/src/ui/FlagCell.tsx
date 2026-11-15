/**
 * A yes/no value in a table cell that is the control itself (the relation matrix cell's table): one
 * click flips it and saves, so no editor opens. The word beside the box says the value ("Yes",
 * "No", or the `words` a caller gives it); the box is disabled while the save runs; "Saved" follows it as a status. A refused save
 * puts its notice in a layer over the cell (`FloatingCellEditor`), where Dismiss closes it.
 *
 * `FlagCell` owns the whole cycle (SR5): `onSave` makes the write and rejects to refuse it; the cell shows
 * saving, "Saved" for `SAVED_FLASH_MS` and the refusal. A cell that is drawn anew by its save (the matrix's) keeps
 * the cycle outside and draws `FlagCellView`.
 */

import { useState, type ReactNode } from "react";
import { errorMessage } from "@/api/errors";
import { FloatingCellEditor } from "@/ui/FloatingCellEditor";
import { Notice } from "@/ui/Notice";
import { useFlashSaved } from "@/ui/useFlashSaved";

type Words = { on: string; off: string } | null;

export function FlagCellView({
  label,
  checked,
  saving,
  saved,
  notice,
  onDismiss,
  onToggle,
  words = { on: "Yes", off: "No" },
}: {
  /** What the box edits: "Requires driver of Riverside". */
  label: string;
  checked: boolean;
  saving: boolean;
  saved: boolean;
  /** A refused save's notice; shown over the cell. */
  notice?: ReactNode;
  onDismiss: () => void;
  onToggle: (next: boolean) => void;
  /** The word beside the box for each value; `null` shows the box alone, where the column header says it. */
  words?: Words;
}) {
  return (
    <span className="flag-cell">
      <label className="checkbox">
        <input
          type="checkbox"
          aria-label={label}
          checked={checked}
          disabled={saving}
          onChange={(event) => onToggle(event.target.checked)}
        />
        {words && <span>{checked ? words.on : words.off}</span>}
      </label>
      {saved && (
        <span role="status" className="flag-cell-saved">
          Saved
        </span>
      )}
      {notice && (
        <FloatingCellEditor onOutside={onDismiss}>
          {notice}
          <div className="dialog-actions">
            <button type="button" className="secondary" onClick={onDismiss}>
              Dismiss
            </button>
          </div>
        </FloatingCellEditor>
      )}
    </span>
  );
}

export function FlagCell({
  label,
  checked,
  words,
  failureTitle,
  onSave,
  describeFailure,
}: {
  label: string;
  checked: boolean;
  words?: Words;
  /** The title of the notice over the cell when the save is refused. */
  failureTitle: string;
  /** Writes the value; rejects when the write is refused. */
  onSave: (next: boolean) => Promise<void>;
  /** Words a refusal, with a step if it has one; the server's message by default. */
  describeFailure?: (cause: unknown) => { message: string; action?: ReactNode };
}) {
  const [saving, setSaving] = useState(false);
  const [failure, setFailure] = useState<{ message: string; action?: ReactNode }>();
  const flash = useFlashSaved();
  async function toggle(next: boolean) {
    setSaving(true);
    setFailure(undefined);
    flash.clear();
    try {
      await onSave(next);
      flash.flash();
    } catch (cause) {
      setFailure(describeFailure?.(cause) ?? { message: errorMessage(cause) });
    } finally {
      setSaving(false);
    }
  }
  return (
    <FlagCellView
      label={label}
      checked={checked}
      saving={saving}
      saved={Boolean(flash.saved)}
      words={words}
      notice={
        failure && (
          <Notice tone="error" title={failureTitle}>
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
