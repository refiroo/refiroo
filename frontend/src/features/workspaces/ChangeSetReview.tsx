/**
 * A change set's review (Base 0.8 P2b): what it adds, changes and removes against its source, as
 * two continuous lists over the change lists API (P2a), records and relationships.
 *
 * Every label comes from the change set's pinned model. Engine-maintained parent links are hidden
 * from the relationships by default (D32), because the moved record's Parent change shows the move.
 * The screen only reads: publishing stays on the change set bar.
 */

import { useId, useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { attributeName } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import type {
  ChangeKind,
  EngineModel,
  ObjectChange,
  ObjectChangeState,
  ObjectPathPart,
  RelationChange,
  RouteState,
} from "@/types";
import { ControlPopover } from "@/ui/ControlPopover";
import { formatValue } from "@/ui/formatValue";
import { Icon } from "@/ui/Icon";
import { InlineError } from "@/ui/InlineError";
import { ScrollWindow } from "@/ui/ScrollWindow";
import { Tabs } from "@/ui/Tabs";

type ReviewRoute = Extract<RouteState, { kind: "changeSetChanges" }>;

const PAGE_SIZE = 50;
const KINDS: { key: ChangeKind; label: string }[] = [
  { key: "added", label: "Added" },
  { key: "changed", label: "Changed" },
  { key: "removed", label: "Removed" },
];

export function ChangeSetReview({
  model,
  route,
  refreshToken,
  onRouteChange,
  onAnchorChange,
  onOpenRecord,
  onBack,
}: {
  /** The change set's pinned model. */
  model: EngineModel;
  route: ReviewRoute;
  refreshToken?: number;
  onRouteChange: (next: ReviewRoute) => void;
  onAnchorChange: (anchor: string | undefined) => void;
  onOpenRecord: (change: ObjectChange) => void;
  onBack: () => void;
}) {
  const { changeSet } = useWorkspaceData();
  const records = route.tab === "records";
  // A type from the URL that the pinned model lacks is dropped rather than refused by the API.
  const types = records
    ? model.objectTypes.map((type) => ({ key: type.key, name: type.name }))
    : model.relationTypes.map((type) => ({ key: type.key, name: type.name }));
  const typeKey = types.some((type) => type.key === route.typeKey) ? route.typeKey : undefined;
  const filter = { kinds: route.changeKinds, typeKey, containment: !records && route.containment === true };
  // Showing parent links widens the list; only kinds and a type narrow it.
  const narrowed = filter.kinds.length > 0 || Boolean(typeKey);
  const change = (patch: Partial<ReviewRoute>) => onRouteChange({ ...route, ...patch, anchor: undefined });

  const list = (
    <section className="surface collection-surface">
      <div className="collection-toolbar change-review-toolbar">
        <ControlPopover
          label="Filter"
          icon="filter"
          count={(filter.kinds.length ? 1 : 0) + (typeKey ? 1 : 0) + (filter.containment ? 1 : 0)}
          className="change-review-filter"
        >
          <fieldset>
            <legend>Kind of change</legend>
            {KINDS.map((kind) => {
              const checked = filter.kinds.includes(kind.key);
              return (
                <label className="checkbox" key={kind.key}>
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() =>
                      change({
                        changeKinds: KINDS.map((item) => item.key).filter((key) =>
                          key === kind.key ? !checked : filter.kinds.includes(key),
                        ),
                      })
                    }
                  />
                  <span>{kind.label}</span>
                </label>
              );
            })}
          </fieldset>
          <label>
            {records ? "Record type" : "Relationship type"}
            <select value={typeKey ?? ""} onChange={(event) => change({ typeKey: event.target.value || undefined })}>
              <option value="">All types</option>
              {[...types]
                .sort((left, right) => left.name.localeCompare(right.name))
                .map((type) => (
                  <option key={type.key} value={type.key}>
                    {type.name}
                  </option>
                ))}
            </select>
          </label>
          {!records && (
            <label className="checkbox">
              <input
                type="checkbox"
                checked={filter.containment}
                onChange={() => change({ containment: filter.containment ? undefined : true })}
              />
              <span>Show parent links</span>
            </label>
          )}
        </ControlPopover>
        {(narrowed || filter.containment) && (
          <button
            type="button"
            className="ghost"
            onClick={() => change({ changeKinds: [], typeKey: undefined, containment: undefined })}
          >
            Clear filters
          </button>
        )}
        {!records && !filter.containment && (
          <span className="muted-text change-review-note">
            Parent links are hidden: a move shows as a Parent change.
          </span>
        )}
      </div>
      {records ? (
        <ObjectChanges
          model={model}
          changeSetId={route.changeSetId}
          kinds={filter.kinds}
          typeKey={typeKey}
          filtered={narrowed}
          anchor={route.anchor}
          refreshToken={refreshToken}
          onAnchorChange={onAnchorChange}
          onOpenRecord={onOpenRecord}
        />
      ) : (
        <RelationChanges
          model={model}
          changeSetId={route.changeSetId}
          kinds={filter.kinds}
          typeKey={typeKey}
          containment={filter.containment}
          filtered={narrowed}
          anchor={route.anchor}
          refreshToken={refreshToken}
          onAnchorChange={onAnchorChange}
        />
      )}
    </section>
  );

  return (
    <section className="context-page change-review">
      <header className="page-header collection-header">
        <div className="page-title">
          <div>
            <h1 tabIndex={-1}>Review changes</h1>
            <p>
              What {changeSet?.name ? `“${changeSet.name}”` : "this change set"} adds, changes and removes compared with
              its source. Nothing here is live until the change set is published.
            </p>
          </div>
        </div>
        <div className="collection-header-actions">
          <button type="button" className="secondary" onClick={onBack}>
            Back to change set
          </button>
        </div>
      </header>
      <Tabs
        label="Changes"
        selected={route.tab}
        onChange={(tab) =>
          tab !== route.tab &&
          onRouteChange({
            ...route,
            tab: tab === "relationships" ? "relationships" : "records",
            typeKey: undefined,
            containment: undefined,
            anchor: undefined,
          })
        }
        tabs={[
          { id: "records", label: "Records", content: records ? list : null },
          { id: "relationships", label: "Relationships", content: records ? null : list },
        ]}
      />
    </section>
  );
}

function KindBadge({ kind }: { kind: ChangeKind }) {
  return <span className={`change-kind change-kind-${kind}`}>{KINDS.find((item) => item.key === kind)?.label}</span>;
}

function fieldLabel(model: EngineModel, field: string) {
  return field === "parent" ? "Parent" : attributeName(model, field);
}

/** Ancestors of a record, root first, as the record screen's breadcrumb names them. */
function location(path: ObjectPathPart[]) {
  const ancestors = path.slice(0, -1);
  return ancestors.length ? ancestors.map((part) => part.name).join(" / ") : "Top level";
}

function objectValue(field: string, side: ObjectChangeState | null, path: ObjectPathPart[] | null | undefined) {
  if (!side) return formatValue(undefined);
  if (field === "name") return side.name;
  if (field === "parent") return !side.parentObjectId ? "Top level" : path ? location(path) : side.parentObjectId;
  return formatValue(side.attributes.find((attribute) => attribute.attributeTypeKey === field)?.value);
}

function EmptyState({
  filtered,
  what,
  parentLinksHidden = false,
}: {
  filtered: boolean;
  what: "record" | "relationship";
  parentLinksHidden?: boolean;
}) {
  return (
    <div className="empty-panel">
      <strong>{filtered ? "Nothing matches" : "No changes yet"}</strong>
      <p>
        {filtered
          ? `No ${what} changes match these filters.`
          : `This change set does not add, change or remove any ${what}s${parentLinksHidden ? " besides parent links" : ""}.`}
      </p>
    </div>
  );
}

/** One expandable row: a summary line, then a before/after table on request. */
function ChangeRow({
  index,
  rowKey,
  name,
  summary,
  children,
}: {
  index: number;
  rowKey: string;
  name: string;
  summary: ReactNode;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const detail = useId();
  return (
    <li className={`change-row${open ? " is-open" : ""}`} data-row-key={rowKey} data-row-index={index}>
      <div className="change-row-summary">
        <button
          type="button"
          className="icon-button change-row-toggle"
          data-row-focus
          aria-expanded={open}
          aria-controls={detail}
          aria-label={`Details of ${name}`}
          onClick={() => setOpen((value) => !value)}
        >
          <Icon name={open ? "chevron-down" : "chevron-right"} size={16} />
        </button>
        {summary}
      </div>
      <div id={detail} className="change-row-detail" hidden={!open}>
        {open && children}
      </div>
    </li>
  );
}

function DiffTable({
  caption,
  rows,
}: {
  caption: string;
  rows: { key: string; label: string; before: ReactNode; after: ReactNode }[];
}) {
  return (
    <table className="change-diff">
      <caption className="visually-hidden">{caption}</caption>
      <thead>
        <tr>
          <th scope="col">Field</th>
          <th scope="col">Before</th>
          <th scope="col">After</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.key}>
            <th scope="row">{row.label}</th>
            <td>{row.before}</td>
            <td>{row.after}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

/** A changed entry naming no field was saved back to its source values; publishing still claims it. */
function unchangedNote(noun: "record" | "relationship") {
  return `No field differs from the source. The ${noun} was saved again, so publishing still checks its version against live data.`;
}

function ObjectChanges({
  model,
  changeSetId,
  kinds,
  typeKey,
  filtered,
  anchor,
  refreshToken,
  onAnchorChange,
  onOpenRecord,
}: {
  model: EngineModel;
  changeSetId: string;
  kinds: ChangeKind[];
  typeKey?: string;
  filtered: boolean;
  anchor?: string;
  refreshToken?: number;
  onAnchorChange: (anchor: string | undefined) => void;
  onOpenRecord: (change: ObjectChange) => void;
}) {
  const list = useCursorWindow<ObjectChange>(
    (selector) =>
      api.objectChanges(changeSetId, {
        kinds,
        objectTypeKeys: typeKey ? [typeKey] : undefined,
        ...selector,
        pageSize: PAGE_SIZE,
      }),
    [changeSetId, kinds.join(","), typeKey],
    { anchor, refreshToken },
  );
  return (
    <>
      {list.error && <InlineError message={list.error} onRetry={list.retry} />}
      {(!list.error || list.items.length > 0) && (
        <ScrollWindow
          list={list}
          label="Record changes"
          noun={["record change", "record changes"]}
          pageSize={PAGE_SIZE}
          className="change-list"
          onAnchorChange={onAnchorChange}
        >
          {list.items.length > 0 && (
            <ul className="change-rows" aria-busy={list.loading || undefined}>
              {list.items.map((item, position) => {
                const name = item.after?.name ?? item.before?.name ?? item.objectId;
                const type = objectTypeFor(model, item.objectTypeKey)?.name ?? item.objectTypeKey;
                const where = location(item.path);
                return (
                  <ChangeRow
                    key={item.objectId}
                    rowKey={item.objectId}
                    index={list.startIndex + position}
                    name={name}
                    summary={
                      <>
                        <KindBadge kind={item.kind} />
                        <span className="change-row-main">
                          <span className="change-row-title">
                            {item.kind === "removed" ? (
                              <span className="change-row-name">{name}</span>
                            ) : (
                              <button type="button" className="cell-link" onClick={() => onOpenRecord(item)}>
                                {name}
                              </button>
                            )}
                            <span className="change-row-type">{type}</span>
                          </span>
                          <span className="change-row-meta">
                            <span className="change-row-path">{where}</span>
                            <ChangedFields model={model} fields={item.changedFields} kind={item.kind} />
                          </span>
                        </span>
                      </>
                    }
                  >
                    {item.changedFields.length === 0 ? (
                      <p className="muted-text">{unchangedNote("record")}</p>
                    ) : (
                      <DiffTable
                        caption={`Changes to ${name}`}
                        rows={item.changedFields.map((field) => ({
                          key: field,
                          label: fieldLabel(model, field),
                          before: objectValue(
                            field,
                            item.before,
                            item.kind === "removed" ? item.path : item.beforePath,
                          ),
                          after: objectValue(field, item.after, item.path),
                        }))}
                      />
                    )}
                  </ChangeRow>
                );
              })}
            </ul>
          )}
          {list.loading && !list.items.length && <p className="candidate-state">Loading changes…</p>}
          {!list.loading && !list.error && !list.items.length && <EmptyState filtered={filtered} what="record" />}
        </ScrollWindow>
      )}
    </>
  );
}

function ChangedFields({ model, fields, kind }: { model: EngineModel; fields: string[]; kind: ChangeKind }) {
  if (kind !== "changed") return null;
  return (
    <span className="change-row-fields">
      {fields.length ? `Changed: ${fields.map((field) => fieldLabel(model, field)).join(", ")}` : "Saved unchanged"}
    </span>
  );
}

function RelationChanges({
  model,
  changeSetId,
  kinds,
  typeKey,
  containment,
  filtered,
  anchor,
  refreshToken,
  onAnchorChange,
}: {
  model: EngineModel;
  changeSetId: string;
  kinds: ChangeKind[];
  typeKey?: string;
  containment: boolean;
  filtered: boolean;
  anchor?: string;
  refreshToken?: number;
  onAnchorChange: (anchor: string | undefined) => void;
}) {
  const list = useCursorWindow<RelationChange>(
    (selector) =>
      api.relationChanges(changeSetId, {
        kinds,
        relationTypeKeys: typeKey ? [typeKey] : undefined,
        // Hidden by default (D32); shown, they list beside every other relationship.
        containment: containment ? undefined : false,
        ...selector,
        pageSize: PAGE_SIZE,
      }),
    [changeSetId, kinds.join(","), typeKey, containment],
    { anchor, refreshToken },
  );
  return (
    <>
      {list.error && <InlineError message={list.error} onRetry={list.retry} />}
      {(!list.error || list.items.length > 0) && (
        <ScrollWindow
          list={list}
          label="Relationship changes"
          noun={["relationship change", "relationship changes"]}
          pageSize={PAGE_SIZE}
          className="change-list"
          onAnchorChange={onAnchorChange}
        >
          {list.items.length > 0 && (
            <ul className="change-rows" aria-busy={list.loading || undefined}>
              {list.items.map((item, position) => {
                const type = model.relationTypes.find((relation) => relation.key === item.relationTypeKey);
                const from = item.fromObject.name ?? item.fromObject.objectId;
                const to = item.toObject.name ?? item.toObject.objectId;
                const name = `${from} → ${to}`;
                const attributes = [
                  ...new Set([
                    ...Object.keys(item.before?.attributes ?? {}),
                    ...Object.keys(item.after?.attributes ?? {}),
                  ]),
                ];
                const fields = item.kind === "changed" ? item.changedFields : attributes;
                return (
                  <ChangeRow
                    key={item.relationId}
                    rowKey={item.relationId}
                    index={list.startIndex + position}
                    name={`${type?.name ?? item.relationTypeKey} ${name}`}
                    summary={
                      <>
                        <KindBadge kind={item.kind} />
                        <span className="change-row-main">
                          <span className="change-row-title">
                            <span className="change-row-name">
                              {from} <span aria-hidden="true">→</span>
                              <span className="visually-hidden"> to </span> {to}
                            </span>
                            <span className="change-row-type">{type?.name ?? item.relationTypeKey}</span>
                            {item.containment && <span className="pill">Parent link</span>}
                          </span>
                          <span className="change-row-meta">
                            <span className="change-row-path">
                              {endType(model, item.fromObject.objectTypeKey)} →{" "}
                              {endType(model, item.toObject.objectTypeKey)}
                            </span>
                            <ChangedFields model={model} fields={item.changedFields} kind={item.kind} />
                          </span>
                        </span>
                      </>
                    }
                  >
                    {fields.length === 0 ? (
                      <p className="muted-text">
                        {item.kind === "changed"
                          ? unchangedNote("relationship")
                          : `${item.kind === "added" ? "Added" : "Removed"} with no attributes.`}
                      </p>
                    ) : (
                      <DiffTable
                        caption={`Changes to ${name}`}
                        rows={fields.map((field) => ({
                          key: field,
                          label: attributeName(model, field),
                          before: formatValue(item.before?.attributes[field]),
                          after: formatValue(item.after?.attributes[field]),
                        }))}
                      />
                    )}
                  </ChangeRow>
                );
              })}
            </ul>
          )}
          {list.loading && !list.items.length && <p className="candidate-state">Loading changes…</p>}
          {!list.loading && !list.error && !list.items.length && (
            <EmptyState filtered={filtered} what="relationship" parentLinksHidden={!containment} />
          )}
        </ScrollWindow>
      )}
    </>
  );
}

function endType(model: EngineModel, objectTypeKey: string | null) {
  return objectTypeKey ? (objectTypeFor(model, objectTypeKey)?.name ?? objectTypeKey) : "Unknown type";
}
