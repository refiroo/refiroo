/**
 * Starting the move (0.11 X4, D144): what loads into a new change set of the target, with Move the
 * second change set of the source that deletes what loaded, the change set's name, and the
 * confirmation of the reviewed dry run. Nothing reaches either workspace or its consumers until a
 * change set is published.
 */

import { useState } from "react";
import type { MoveSummary } from "@/types";
import { FormField } from "@/ui/FormField";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { figuresOf } from "@/model/moveRun";

const count = (value: number, one: string, many: string) =>
  `${value.toLocaleString("en-GB")} ${value === 1 ? one : many}`;

export function StartMoveDialog({
  summary,
  sourceLabel,
  targetLabel,
  busy,
  error,
  onClose,
  onConfirm,
}: {
  summary: MoveSummary;
  sourceLabel: string;
  targetLabel: string;
  busy: boolean;
  error: string;
  onClose: () => void;
  onConfirm: (changeSetName: string) => void;
}) {
  const [name, setName] = useState(`${summary.mode === "move" ? "Move" : "Copy"} from ${sourceLabel}`);
  const figures = figuresOf(summary);
  const moving = summary.mode === "move";
  const records = figures.create + figures.update;
  const cannot = figures.cannot + figures.dropped;
  return (
    <Modal
      title={`${moving ? "Move" : "Copy"} ${count(records, "record", "records")} into workspace ${targetLabel}`}
      onClose={onClose}
      busy={busy}
    >
      <form
        className="dialog-body"
        onSubmit={(event) => {
          event.preventDefault();
          onConfirm(name.trim());
        }}
      >
        <ul className="move-start-list">
          <li>
            A new change set of workspace <strong>{targetLabel}</strong>: {count(figures.create, "record", "records")}{" "}
            created, {figures.update.toLocaleString("en-GB")} updated ({moving ? "moved" : "copied"} before or found),{" "}
            {count(figures.carried, "relationship", "relationships")}.
          </li>
          {moving && (
            <li>
              A second change set of workspace <strong>{sourceLabel}</strong> deleting the moved records, reviewed and
              published on its own, after the copy. A record that changed since the dry run, or that a record staying
              depends on, is kept.
            </li>
          )}
          <li>
            {cannot
              ? `${count(cannot, "item", "items")} cannot be ${moving ? "moved" : "copied"} (listed on this page). `
              : `Every selected item can be ${moving ? "moved" : "copied"}. `}
            Nothing reaches either workspace or its consumers until a change set is published.
          </li>
        </ul>
        <FormField label={`Name of the change set of workspace ${targetLabel}`}>
          {(control) => (
            <input {...control} value={name} maxLength={300} onChange={(event) => setName(event.target.value)} />
          )}
        </FormField>
        {error && (
          <Notice tone="error" focusOnMount>
            {error}
          </Notice>
        )}
        <div className="dialog-actions">
          <button type="button" className="secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Starting…" : moving ? "Start the move" : "Start the copy"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
