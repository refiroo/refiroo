/** "The model: what changes" (0.16 AP6, board 8): the design's model operations as a table and a button into the draft's editor. */

import type { AiTaskDesign } from "@/types";
import { Card } from "@/ui/Card";
import { SettingsTable } from "@/ui/SettingsTable";
import { StatusPill } from "@/ui/StatusPill";
import { modelChanges, type ModelNames } from "./aiTaskDesign";

export function DesignModel({
  design,
  names,
  onOpenEditor,
  workbook = true,
  draft = false,
}: {
  design: AiTaskDesign;
  names: ModelNames;
  onOpenEditor?: () => void;
  /** Whether the task has a workbook: only then can it be said to fit the model as it is. */
  workbook?: boolean;
  /** Whether the task has a draft of the model: a change of views or layout lives there, not in this table. */
  draft?: boolean;
}) {
  const changes = modelChanges(
    design.operations.filter((op) => op.kind !== "setRelease"),
    names,
  );
  return (
    <Card
      as="section"
      title={<>The model: what changes {changes.length > 0 && <StatusPill tone="proposed">Proposed</StatusPill>}</>}
      className="task-table"
    >
      {changes.length === 0 ? (
        <>
          {draft ? (
            <p>
              No type, attribute or relationship changes. The draft may change how the model is shown, such as its views
              and layout: open it in the model editor to read them.
            </p>
          ) : workbook ? (
            <p>No change to the model: the workbook fits it as it is.</p>
          ) : (
            <p>No change to the model.</p>
          )}
          {draft && onOpenEditor && (
            <div className="task-actions">
              <button type="button" className="secondary" onClick={onOpenEditor}>
                Open in the model editor
              </button>
            </div>
          )}
        </>
      ) : (
        <>
          <SettingsTable label="Changes to the model" columns={["Change", "Name", "What it is"]}>
            {changes.map((change, index) => (
              <tr key={`${change.change}-${change.name}-${index}`}>
                <th scope="row" data-label="Change">
                  {change.change}
                </th>
                <td data-label="Name">{change.name}</td>
                <td data-label="What it is">{change.detail}</td>
              </tr>
            ))}
          </SettingsTable>
          {onOpenEditor && (
            <div className="task-actions">
              <button type="button" className="secondary" onClick={onOpenEditor}>
                Open in the model editor
              </button>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
