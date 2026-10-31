/** "Records the structure needs" (0.16 AP6, board 8): the design's records by type, created in the same change set. */

import type { AiTaskDesign } from "@/types";
import { Card } from "@/ui/Card";
import { recordGroups, type ModelNames } from "./aiTaskDesign";

export function DesignRecords({ design, names }: { design: AiTaskDesign; names: ModelNames }) {
  if (design.records.length === 0) return null;
  return (
    <Card as="section" title="Records the structure needs" className="task-table">
      <ul className="task-sheet-list" aria-label="Records by type">
        {recordGroups(design.records, names).map((group) => (
          <li key={group.typeKey}>
            <strong>{group.label}:</strong> {group.names.join(", ")}
          </li>
        ))}
      </ul>
      <p className="task-reason">They are created in the same change set as the load.</p>
    </Card>
  );
}
