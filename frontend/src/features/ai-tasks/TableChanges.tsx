/** The records the latest check would change in one sheet of the design: one row per changed field, a page at a time (0.16 AP6a, AP6). */

import { ai } from "@/api/aiClient";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { InlineError } from "@/ui/InlineError";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { shown } from "./aiTaskText";

export function TableChanges({
  taskId,
  table,
  sheet,
  checkedAt,
}: {
  taskId: string;
  /** The design's source in the check's sheets. */
  table: number;
  sheet: string;
  checkedAt: string;
}) {
  const feed = useCursorFeed((cursor) => ai.taskChanges(taskId, { source: table }, cursor), [taskId, table, checkedAt]);
  if (feed.error) return <InlineError message={feed.error} onRetry={feed.retry} />;
  if (feed.loading && feed.items.length === 0) return <Skeleton label={`Reading the changes of ${sheet}`} lines={3} />;
  if (feed.items.length === 0) return <p className="admin-hint">No stored record changes in this sheet.</p>;
  return (
    <div className="task-changes">
      <SettingsTable label={`Changed records of ${sheet}`} columns={["Record", "What", "Now", "After"]}>
        {feed.items.flatMap((change) =>
          change.fields.map((field) => (
            <tr key={`${change.recordId}-${field.field}`}>
              <th scope="row" data-label="Record">
                {change.name ?? change.recordId}
              </th>
              <td data-label="What">{field.label}</td>
              <td data-label="Now">{shown(field.now)}</td>
              <td data-label="After">{shown(field.after)}</td>
            </tr>
          )),
        )}
      </SettingsTable>
      {feed.hasMore && (
        <button type="button" className="load-more" disabled={feed.loading} onClick={feed.loadMore}>
          Show more
        </button>
      )}
    </div>
  );
}
