/**
 * Whether a navigation group starts folded, as a table cell that is its own control (`ui/FlagCell`,
 * as a record's yes/no cell is): one click sends the step and "Saved" follows. A refused step's
 * reason stays over the cell until it is dismissed.
 */

import { useEffect, useState } from "react";
import type { ModelDraftOutline } from "@/types";
import { FlagCell } from "@/ui/FlagCell";
import { Notice } from "@/ui/Notice";
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
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [failure, setFailure] = useState("");
  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), 2500);
    return () => clearTimeout(timer);
  }, [saved]);
  async function toggle(collapsed: boolean) {
    setSaving(true);
    setSaved(false);
    setFailure("");
    try {
      await run([{ kind: "setNavigationGroup", applicationKey, group, collapsed }]);
      setSaved(true);
    } catch (cause) {
      setFailure(refusalText(cause, outline));
    } finally {
      setSaving(false);
    }
  }
  return (
    <FlagCell
      label={`Starts folded: ${label}`}
      checked={folded}
      saving={saving}
      saved={saved}
      words={null}
      notice={
        failure && (
          <Notice tone="error" title="Not saved">
            {failure}
          </Notice>
        )
      }
      onDismiss={() => setFailure("")}
      onToggle={(next) => void toggle(next)}
    />
  );
}
