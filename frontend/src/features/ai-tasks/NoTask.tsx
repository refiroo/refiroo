/** A task that is not here (0.16 AP13, AP-D60): expired, discarded long ago, or a link that is wrong. */

import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";

export function NoTask({ onWorkspaces }: { onWorkspaces: () => void }) {
  return (
    <Section title="This task is no longer here">
      <Notice tone="info">
        A task is kept for a number of days after it ends, and this one is past that, or the link is wrong. What it
        loaded or published is unchanged.
      </Notice>
      <div className="task-actions">
        <button type="button" className="primary" onClick={onWorkspaces}>
          Go to the workspaces
        </button>
      </div>
    </Section>
  );
}
