/**
 * After a publication (0.16 AP13, AP-D58): "Something not right?", the two ways back to the assistant from the
 * task's own page, the same offers as the workspace's menu (one hook). The model and the records each start a
 * task on the workspace; nothing offered here is unavailable to the person.
 */

import { useState } from "react";
import type { AiTask, RouteState } from "@/types";
import { Card } from "@/ui/Card";
import { LoadWorkbookDialog, type LoadWorkbookStart } from "./LoadWorkbookDialog";
import type { AssistantOffers } from "./useAssistantOffers";

export function WayOnward({
  task,
  workspaceLabel,
  offers,
  onNavigate,
}: {
  task: AiTask;
  workspaceLabel: string;
  offers: AssistantOffers;
  onNavigate: (route: RouteState) => void;
}) {
  const [start, setStart] = useState<LoadWorkbookStart>();
  if (!offers.changeModel && !offers.askRecords) return null;
  return (
    <>
      <div className="task-onward">
        {offers.changeModel && (
          <Card as="section" title="The model" headingLevel={3}>
            <p>
              Say what to change in the types, fields or relations. The assistant starts from this workspace&apos;s
              model.
            </p>
            <div className="task-actions">
              <button
                type="button"
                className="secondary"
                onClick={() => setStart({ workspaceKey: task.workspaceKey, changeModel: true, workspaceLabel })}
              >
                Change this model…
              </button>
            </div>
          </Card>
        )}
        {offers.askRecords && (
          <Card as="section" title="The records" headingLevel={3}>
            <p>
              Say what to change in the data, such as values to fix or records to move. It comes back as a change set to
              review.
            </p>
            <div className="task-actions">
              <button type="button" className="secondary" onClick={() => setStart({ workspaceKey: task.workspaceKey })}>
                Ask about these records…
              </button>
            </div>
          </Card>
        )}
      </div>
      {start && (
        <LoadWorkbookDialog
          start={start}
          onClose={() => setStart(undefined)}
          onStarted={(started) => {
            setStart(undefined);
            onNavigate({ kind: "settings", page: "ai-tasks", taskId: started.id });
          }}
        />
      )}
    </>
  );
}
