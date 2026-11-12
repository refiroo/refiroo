/**
 * What `useDraftEditing` opens and says, drawn once for every page that edits a draft (0.17 CE1, PP-D3):
 * `DraftEditingDialogs` (the operation form or question, Move to…, the dependants of an undo) and
 * `DraftEditingNotices` (a step held back because the draft moved on, and the last notice).
 */

import type { ReactNode } from "react";
import { DependantsDialog } from "@/features/model-editor/DependantsDialog";
import { describeOperation } from "@/features/model-editor/history";
import { MoveToDialog } from "@/features/model-editor/MoveToDialog";
import { OperationDialog } from "@/features/model-editor/OperationDialog";
import { applicationOf, nameOf } from "@/features/model-editor/outline";
import type { DraftEditing } from "@/features/model-editor/useDraftEditing";
import { Notice } from "@/ui/Notice";

export function DraftEditingDialogs({ editing, busy }: { editing: DraftEditing; busy?: boolean }) {
  const { outline, dialog } = editing;
  if (!outline || !dialog) return null;
  if (dialog.kind === "operation")
    return (
      <OperationDialog
        operation={dialog.operation}
        target={dialog.target}
        outline={outline}
        preset={dialog.preset}
        anchor={dialog.anchor}
        run={editing.run}
        onClose={editing.closeDialog}
      />
    );
  if (dialog.kind === "move")
    return (
      <MoveToDialog
        subject={dialog.subject}
        outline={outline}
        initialTarget={dialog.target}
        run={editing.run}
        onClose={editing.closeDialog}
      />
    );
  return (
    <DependantsDialog
      steps={dialog.steps}
      dependants={dialog.dependants}
      pending={busy ?? editing.working}
      onCancel={editing.closeDialog}
      onConfirm={(together) => {
        editing.closeDialog();
        void editing.undo(together);
      }}
    />
  );
}

export function DraftEditingNotices({
  editing,
  busy,
  onOpenApplication,
}: {
  editing: DraftEditing;
  busy?: boolean;
  /** Opens an application of the draft's model, in the workspace the notice names. */
  onOpenApplication?: (applicationKey: string, workspaceKey?: string) => void;
}) {
  const { outline, stale, notice } = editing;
  if (!outline) return null;
  const names = nameOf(outline);
  const disabled = busy ?? editing.working;
  const actions: ReactNode =
    notice?.applications && onOpenApplication ? (
      notice.applications.map((key) => (
        <button
          key={key}
          type="button"
          className="secondary"
          onClick={() => onOpenApplication(key, notice.workspaceKey)}
        >
          Open {applicationOf(outline, key)?.name ?? key}
        </button>
      ))
    ) : (
      <button type="button" className="secondary" onClick={() => editing.setNotice(undefined)}>
        Dismiss
      </button>
    );
  return (
    <>
      {stale && (
        <Notice
          tone="warning"
          title="Another change came first"
          focusOnMount
          actions={
            <>
              <button
                type="button"
                className="primary"
                disabled={disabled}
                onClick={() => void editing.guarded(() => editing.step(stale.send))}
              >
                Apply mine again
              </button>
              <button type="button" className="secondary" disabled={disabled} onClick={editing.clearStale}>
                Discard mine
              </button>
            </>
          }
        >
          Your change was not applied: the draft changed since you opened it.{" "}
          {stale.since.length > 0 && (
            <>
              Applied since:{" "}
              {stale.since
                .map((entry) => describeOperation(entry.kind, entry.parameters, names, entry.inverse))
                .join("; ")}
              {stale.more ? " and more" : ""}.
            </>
          )}{" "}
          The model below shows the newer version.
        </Notice>
      )}
      {notice && (
        <Notice tone={notice.tone} actions={actions}>
          {notice.text}
        </Notice>
      )}
    </>
  );
}
