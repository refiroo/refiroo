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
}: {
  design: AiTaskDesign;
  names: ModelNames;
  onOpenEditor?: () => void;
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
        <p>No change to the model: the workbook fits it as it is.</p>
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
