/** "What happens to the records" (0.16 AP12, board 2): the types the proposal turns into others, with the
 * records the workspace holds of each, from the engine's own figures. */

import type { AiTask } from "@/types";
import { Card } from "@/ui/Card";
import { SettingsTable } from "@/ui/SettingsTable";
import { count } from "@/features/settings/limits";

/** The sentence over a proposal's moves, or nothing when it moves no whole type. */
export function movesSentence(task: Pick<AiTask, "design">): string | undefined {
  const moves = task.design?.moves ?? [];
  if (moves.length === 0) return undefined;
  const records = moves.reduce((total, move) => total + move.records, 0);
  return `${count(records)} ${records === 1 ? "record keeps" : "records keep"} ${records === 1 ? "its" : "their"} IDs, history and relationships.`;
}

/** What changes for the consumers of the model: each consumer API whose version the proposal raises. */
export function ConsumerChanges({ task }: { task: Pick<AiTask, "design"> }) {
  const raised = task.design?.consumerChanges ?? [];
  if (raised.length === 0) return null;
  return (
    <>
      {raised.map((item) => (
        <p key={item.api} className="task-reason">
          Consumer API {item.name}: version {item.from} → {item.to}.
          {item.changes.length > 0 && ` What changes for its consumers: ${item.changes.join("; ")}.`}
        </p>
      ))}
    </>
  );
}

/** What the migration would drop of each moved type (values, relationships, records), from the engine's check. */
export function MoveLosses({ task }: { task: Pick<AiTask, "design"> }) {
  const lines = (task.design?.moves ?? []).flatMap((move) => {
    const lost = move.lost ?? {};
    const parts = [
      [lost.records, "record", "records"],
      [lost.values, "value", "values"],
      [lost.relationships, "relationship", "relationships"],
    ].flatMap(([n, one, many]) => (typeof n === "number" && n > 0 ? [`${count(n)} ${n === 1 ? one : many}`] : []));
    return parts.length > 0 ? [{ key: move.from, text: `${move.fromName}: ${parts.join(", ")} would be lost.` }] : [];
  });
  return (
    <>
      {lines.map((line) => (
        <p key={line.key} className="task-reason">
          {line.text}
        </p>
      ))}
    </>
  );
}

export function ProposalMoves({ task }: { task: Pick<AiTask, "design"> }) {
  const moves = task.design?.moves ?? [];
  if (moves.length === 0) return <ConsumerChanges task={task} />;
  return (
    <Card as="section" title="What happens to the records" className="task-table">
      <SettingsTable label="Types that become others" columns={["Now", "Becomes", "Records"]}>
        {moves.map((move) => (
          <tr key={move.from}>
            <th scope="row" data-label="Now">
              {move.fromName}
            </th>
            <td data-label="Becomes">{move.toName}</td>
            <td data-label="Records">{count(move.records)}</td>
          </tr>
        ))}
      </SettingsTable>
      <p className="task-reason">
        The counts are the engine&apos;s. {movesSentence(task)} Before anything moves, a preview lists every value
        converted, and anything that would be lost or refused.
      </p>
      <MoveLosses task={task} />
      <ConsumerChanges task={task} />
    </Card>
  );
}
