/**
 * The inspector's **Connected** list (ADR-040, UA4): the record's declared relations panels, one row
 * each, labelled by the panel's title, with the related records as chips in their types' colours.
 * Reading and opening only; relationships are added, edited and deleted in the panels' tables on the
 * record's full page, which `onManage` opens.
 *
 * A row reads the first page of its relation, by name, and appends further pages on request. When the
 * panel declares an `ancestor:<type>` column, a chip names that ancestor before the record, since the
 * panel's author chose it as what tells the related records apart (a value's system, a language).
 */

import { useState } from "react";
import { useDataApi } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { objectTypeHue } from "@/model/hues";
import type { EngineModel, ObjectItem, RelationItem, RelationsPanelDefinition } from "@/types";
import { InlineError } from "@/ui/InlineError";
import { RecordChip } from "@/ui/RecordChip";

const PAGE_SIZE = 12;
const ANCESTOR = "ancestor:";

export function ConnectedList({
  model,
  object,
  panels,
  onOpen,
  onManage,
}: {
  model: EngineModel;
  object: ObjectItem;
  panels: RelationsPanelDefinition[];
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
  /** Opens the record's full page, where the relationships are managed. */
  onManage?: () => void;
}) {
  return (
    <section className="panel connected-panel" aria-labelledby={`connected-${object.id}`}>
      <h2 id={`connected-${object.id}`}>Connected</h2>
      <dl className="connected-list">
        {panels.map((panel) => (
          <ConnectedRow key={panel.key} model={model} object={object} panel={panel} onOpen={onOpen} />
        ))}
      </dl>
      {onManage && (
        <button type="button" className="ghost connected-manage" onClick={onManage}>
          Manage relationships on the full page
        </button>
      )}
    </section>
  );
}

function ConnectedRow({
  model,
  object,
  panel,
  onOpen,
}: {
  model: EngineModel;
  object: ObjectItem;
  panel: RelationsPanelDefinition;
  onOpen: (objectTypeKey: string, objectId: string, applicationKey?: string) => void;
}) {
  const api = useDataApi();
  const [total, setTotal] = useState<number>();
  const relationTypeKeys = panel.config.relationTypeKeys;
  const relationTypeKey = relationTypeKeys.length === 1 ? relationTypeKeys[0] : undefined;
  const ancestorType = panel.config.columns.find((column) => column.startsWith(ANCESTOR))?.slice(ANCESTOR.length);
  const feed = useCursorFeed<RelationItem>(
    (cursor) =>
      api
        .relations(object.id, {
          workspaceKey: object.workspaceKey,
          direction: panel.config.direction,
          ...(relationTypeKey ? { relationTypeKey } : {}),
          sort: "name",
          pageSize: PAGE_SIZE,
          ...(cursor ? { cursor } : { includeTotal: true }),
        })
        .then((page) => {
          if (!cursor) setTotal(page.totalCount);
          return page;
        }),
    [object.id, object.workspaceKey, object.version, panel.key],
    // Several relation types are read together and kept to the panel's own, as its table does.
    (previous, incoming) => [
      ...previous,
      ...incoming.filter((item) => relationTypeKeys.includes(item.relation.relationTypeKey)),
    ],
  );
  // The total counts every relation the request read, so it is shown only for one relation type.
  const remaining = relationTypeKey && total !== undefined ? total - feed.items.length : undefined;

  return (
    <div className="connected-row">
      <dt>{panel.title}</dt>
      <dd>
        {feed.error && <InlineError message={feed.error} onRetry={feed.retry} />}
        {feed.loading && feed.items.length === 0 ? (
          <span className="connected-state">Loading…</span>
        ) : !feed.error && feed.items.length === 0 ? (
          <span className="connected-state">None</span>
        ) : (
          <ul className="connected-chips">
            {feed.items.map((item) => {
              const ancestor = ancestorType
                ? item.object.path.find((part) => part.objectTypeKey === ancestorType)
                : undefined;
              return (
                <li key={item.relation.id}>
                  <RecordChip
                    hue={objectTypeHue(model, item.object.objectTypeKey)}
                    onOpen={() => onOpen(item.object.objectTypeKey, item.object.id, item.object.applicationKey)}
                  >
                    {ancestor && <span className="record-chip-context">{ancestor.name}</span>}
                    {item.object.name}
                  </RecordChip>
                </li>
              );
            })}
          </ul>
        )}
        {feed.hasMore && !feed.error && (
          <button type="button" className="ghost connected-more" disabled={feed.loading} onClick={feed.loadMore}>
            {feed.loading ? "Loading…" : remaining && remaining > 0 ? `Show ${remaining} more` : "Show more"}
          </button>
        )}
      </dd>
    </div>
  );
}
