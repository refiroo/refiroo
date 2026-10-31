/**
 * What the assistant's session has reached while it works: facts read from the calls it made, with
 * how long it has been working. No percentage or time left: it explores, so nothing can say them.
 */

import { StatusPill } from "@/ui/StatusPill";
import { count } from "@/features/settings/limits";
import type { AiTaskDesign } from "@/types";

export function SessionProgress({ progress }: { progress: NonNullable<AiTaskDesign["progress"]> }) {
  const minutes = Math.floor(progress.seconds / 60);
  return (
    <>
      <ul className="task-sheet-list" aria-label="What the assistant has reached">
        {progress.milestones.map((milestone) => (
          <li key={milestone.key}>
            {milestone.done ? <span aria-label="Done">✓</span> : <span aria-label="Not yet">○</span>}{" "}
            {milestone.label}
            {milestone.key === "check" && milestone.done && progress.refused !== null && (
              <>
                {" "}
                <StatusPill tone={progress.refused > 0 ? "warning" : "success"}>
                  {count(progress.refused)} refused
                </StatusPill>
              </>
            )}
          </li>
        ))}
      </ul>
      <p className="admin-hint">
        Working for {minutes > 0 ? `${minutes} min ` : ""}
        {progress.seconds % 60} s
      </p>
    </>
  );
}
