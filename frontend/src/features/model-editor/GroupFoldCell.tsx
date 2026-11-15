/**
 * Whether a navigation group starts folded, as a table cell that is its own control (`ui/FlagCell`,
 * as a record's yes/no cell is): one click sends the step and "Saved" follows. A refused step's
 * reason stays over the cell until it is dismissed.
 */

import type { ModelDraftOutline } from "@/types";
import { FlagCell } from "@/ui/FlagCell";
import { refusalText, type RunStep } from "@/features/model-editor/OperationDialog";

export function GroupFoldCell({
  applicationKey,
  group,
  label,
  folded,
  outline,
  run,
}: {
  applicationKey: string;
  group: string;
  /** The group's name, for the box's label. */
  label: string;
  folded: boolean;
  outline: ModelDraftOutline;
  run: RunStep;
}) {
  return (
    <FlagCell
      label={`Starts folded: ${label}`}
      checked={folded}
      words={null}
      failureTitle="Not saved"
      onSave={async (collapsed) => {
        await run([{ kind: "setNavigationGroup", applicationKey, group, collapsed }]);
      }}
      describeFailure={(cause) => ({ message: refusalText(cause, outline) })}
    />
  );
}
