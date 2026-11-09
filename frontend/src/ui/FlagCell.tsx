/**
 * A yes/no value in a table cell that is the control itself (the relation matrix cell's table): one
 * click flips it and saves, so no editor opens. The word beside the box says the value ("Yes",
 * "No"); the box is disabled while the save runs; "Saved" follows it as a status. A refused save
 * puts its notice in a layer over the cell (`FloatingCellEditor`), where Dismiss closes it.
 */

import type { ReactNode } from "react";
import { FloatingCellEditor } from "@/ui/FloatingCellEditor";

export function FlagCell({
  label,
  checked,
  saving,
  saved,
  notice,
  onDismiss,
  onToggle,
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
        <span>{checked ? "Yes" : "No"}</span>
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
