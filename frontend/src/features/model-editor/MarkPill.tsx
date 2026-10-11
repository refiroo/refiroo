import type { OutlineMark } from "@/types";
import { StatusPill, type StatusTone } from "@/ui/StatusPill";
import { MARK_LABELS } from "@/features/model-editor/outline";

const TONES: Record<OutlineMark, StatusTone> = { new: "success", changed: "warning", released: "neutral" };

/** Whether an element is new in the draft, changed from its base release, or released as it is. */
export function MarkPill({ mark }: { mark: OutlineMark }) {
  return (
    <StatusPill tone={TONES[mark]} className="mark-pill">
      {MARK_LABELS[mark]}
    </StatusPill>
  );
}
