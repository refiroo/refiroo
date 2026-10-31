/**
 * "Relationships to make" (0.16 AP6, AP-D17/D18): the design's rules that relate stored records where a
 * condition holds, each one sentence in the model's names with the engine's count of pairs; a rule the
 * engine refuses shows why. Nothing is written until the person confirms.
 */

import type { AiTaskDesign } from "@/types";
import { Card } from "@/ui/Card";
import { Notice } from "@/ui/Notice";
import { describeLink, type ModelNames } from "./aiTaskDesign";

export function DesignLinks({ design, names }: { design: AiTaskDesign; names: ModelNames }) {
  const links = design.links ?? [];
  if (links.length === 0) return null;
  const found = design.outcome?.links ?? [];
  return (
    <Card as="section" title="Relationships to make" className="task-table">
      <ul className="task-sheet-list" aria-label="Rules for relationships">
        {links.map((rule, index) => {
          const check = found[index];
          return (
            <li key={index}>
              {describeLink(rule, names, check)}
              {rule.reason && <span className="task-reason"> {rule.reason}</span>}
              {check?.refused && (
                <Notice tone="warning" title="The engine refuses this rule">
                  {check.refused}
                </Notice>
              )}
            </li>
          );
        })}
      </ul>
      <p className="task-reason">They are written into the same change set, after the load.</p>
    </Card>
  );
}
