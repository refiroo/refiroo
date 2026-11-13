/**
 * What a load does with the records no row names (0.17 CE1, PP-D82; the engine's `setMissing`): on a
 * source's panel, in the model editor and the canvas. The current choice stands where it is changed; Report
 * is the default and Delete asks once, saying what a load will then delete. Not offered for a source that
 * has no key or loads no records of its own, where there is nothing to find.
 */

import { useId, useState } from "react";
import type { DraftOperation, ModelDraftOutline, ProfileSource } from "@/types";
import { canSetMissing, missingOf, setMissingOperation, type MissingChoice } from "@/features/model-editor/lists";
import { typeName } from "@/model/outline";
import { Choice } from "@/ui/Choice";
import { ConfirmDialog } from "@/ui/ConfirmDialog";

export function MissingRecords({
  source,
  outline,
  busy,
  run,
}: {
  source: ProfileSource;
  outline: ModelDraftOutline;
  busy?: boolean;
  /** Sends the step; a refusal is said by the caller (`runGuarded`). */
  run: (operations: DraftOperation[]) => void;
}) {
  const [asking, setAsking] = useState(false);
  const hint = useId();
  if (!canSetMissing(source)) return null;
  const current = missingOf(source);
  const type = typeName(outline, source.objectTypeKey);
  const choose = (next: MissingChoice) => {
    if (next === current) return;
    if (next === "delete") setAsking(true);
    else run([setMissingOperation(source, next)]);
  };
  return (
    <div className="missing-records">
      <fieldset disabled={busy} className="missing-records-choice">
        <legend className="visually-hidden">Records no row names</legend>
        <Choice
          name={`missing-${source.id}`}
          value={current}
          describedBy={hint}
          options={[
            ["report", "Report them"],
            ["delete", "Delete them"],
          ]}
          onChange={choose}
        />
      </fieldset>
      <p id={hint} className="muted">
        {current === "delete"
          ? `A load deletes, in its change set, every ${type} record that no row of the file names.`
          : `A load only reports the ${type} records that no row of the file names.`}
      </p>
      {asking && (
        <ConfirmDialog
          title="Delete the records no row names?"
          confirmLabel="Delete them on load"
          onCancel={() => setAsking(false)}
          onConfirm={() => {
            setAsking(false);
            run([setMissingOperation(source, "delete")]);
          }}
        >
          <p>
            Every time this source is loaded, each <strong>{type}</strong> record that no row of the file names is
            deleted in the change set the load makes. Nothing in the workspace changes until that change set is
            published, and it can be reviewed first. Choosing Report again stops it.
          </p>
        </ConfirmDialog>
      )}
    </div>
  );
}
