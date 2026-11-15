/** "What happens to the records" (0.16 AP12, board 2): the types the proposal turns into others, with the
 * records the workspace holds of each, from the engine's own figures. */

import type { ReactElement } from "react";
import { count, counted, plural } from "@/lib/count";
import type { AiTask, AiTaskMove } from "@/types";
import { Card } from "@/ui/Card";
import { SettingsTable } from "@/ui/SettingsTable";

/** A move that only changes the application of a type, which keeps its key. */
function onlyApplication(move: AiTaskMove): boolean {
  return move.from === move.to && !!move.toApplication;
}

/** What a move does to the type: it becomes another type, goes to another application, or both. */
export function moveWords(move: AiTaskMove): ReactElement {
  const where = move.toApplicationName ?? move.toApplication;
  if (onlyApplication(move)) {
    return (
      <>
        moves to <strong>{where}</strong>
      </>
    );
  }
  return (
    <>
      becomes <strong>{move.toName}</strong>
      {where ? <> in {where}</> : null}
    </>
  );
}

/** The sentence over a proposal's moves, or nothing when it moves no whole type. */
export function movesSentence(task: Pick<AiTask, "design">): string | undefined {
  const moves = task.design?.moves ?? [];
  if (moves.length === 0) return undefined;
  const records = moves.reduce((total, move) => total + move.records, 0);
  const kept = `${counted(records, "record keeps", "records keep")} ${plural(records, "its", "their")} IDs, history and relationships.`;
  const across = moves.filter(onlyApplication);
  const apps = [...new Set(across.map((move) => move.toApplicationName ?? move.toApplication))];
  if (across.length === 0 || apps.length !== 1) return kept;
  const here = across.reduce((total, move) => total + move.records, 0);
  return `${counted(across.length, "type moves", "types move")} to ${apps[0]}, ${counted(here, "record")}. ${kept}`;
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
    const parts = (
      [
        [lost.records, "record", "records"],
        [lost.values, "value", "values"],
        [lost.relationships, "relationship", "relationships"],
      ] as const
    ).flatMap(([n, one, many]) => (typeof n === "number" && n > 0 ? [counted(n, one, many)] : []));
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
            <td data-label="Becomes">
              {onlyApplication(move)
                ? `${move.toName}, in ${move.toApplicationName ?? move.toApplication}`
                : move.toName}
            </td>
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
