import { useCallback, useEffect, useRef, useState } from "react";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorPages } from "@/lib/hooks/useCursorPages";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { errorMessage, isApiError } from "@/api/errors";
import { InlineError } from "@/ui/InlineError";
import { Pagination } from "@/ui/Pagination";
import { Icon } from "@/ui/Icon";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { formatValue } from "@/ui/formatValue";
import { attributeName } from "@/model/fields";
import { objectTypeFor } from "@/model/lookup";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { CollectionScope } from "@/features/objects/CollectionScope";
import type {
  EngineModel,
  MappingCoverageRow,
  MappingGridViewDefinition,
  MappingObjectSummary,
  MappingTargetSummary,
  ObjectItem,
  ObjectTypeDefinition,
} from "@/types";
import type { ViewComponentProps } from "./views/types";

export function MappingGridView({
  model,
  application,
  view: rawView,
  workspaceKey,
  readOnly,
  onChanged,
  query,
  onQueryChange,
  refreshToken = 0,
}: ViewComponentProps) {
  const view = rawView as MappingGridViewDefinition;
  const api = useDataApi();
  const { draft } = useWorkspaceData();
  const root = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState(query.search);
  const [internalRefresh, setInternalRefresh] = useState(0);

  const { config } = view;
  const sourceTypeKey = config.direction === "outgoing" ? config.fromObjectTypeKey : config.toObjectTypeKey;
  const targetTypeKey = config.direction === "outgoing" ? config.toObjectTypeKey : config.fromObjectTypeKey;
  const sourceType = objectTypeFor(model, sourceTypeKey);
  const targetType = objectTypeFor(model, targetTypeKey);
  const relationType = model.relationTypes.find((rt) => rt.key === config.relationTypeKey);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const trimmed = search.trim();
      if (trimmed !== query.search) onQueryChange({ ...query, search: trimmed, cursors: undefined });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search, query, onQueryChange]);

  const combinedRefresh = refreshToken + internalRefresh;

  const pages = useCursorPages<MappingCoverageRow>(
    (cursor) =>
      api.mappingCoverage({
        workspaceKey,
        applicationKey: application.key,
        viewKey: view.key,
        relationTypeKey: config.relationTypeKey,
        fromObjectTypeKey: config.fromObjectTypeKey,
        toObjectTypeKey: config.toObjectTypeKey,
        direction: config.direction,
        workspaceDraftId: draft?.id,
        search: query.search || undefined,
        parentObjectId: query.parentObjectId,
        state: query.mappingState,
        cursor,
        pageSize: query.pageSize || config.pageSize,
      }),
    [
      application.key,
      view.key,
      workspaceKey,
      query.search,
      query.pageSize,
      query.parentObjectId,
      query.mappingState,
      draft?.id,
    ],
    { cursors: query.cursors ?? [], onChange: (cursors) => onQueryChange({ ...query, cursors }) },
    combinedRefresh,
  );
  const { loading, error } = pages;

  useEffect(() => {
    if (!loading && !error && pages.items.length === 0 && pages.pageNumber > 1) pages.previous();
  }, [loading, error, pages]);

  const refreshCoverage = useCallback(() => {
    setInternalRefresh((n) => n + 1);
    onChanged?.();
  }, [onChanged]);

  if (!sourceType || !targetType) {
    return (
      <div className="empty-state">
        <h2>{view.name}</h2>
        <p>This mapping view references an object type that does not exist in the active model.</p>
      </div>
    );
  }

  const directionLabel = config.direction === "outgoing" ? relationType?.name : relationType?.reverseName;
  const sourceColumns = config.sourceColumns.filter((column) => column !== "name");
  const targetColumns = config.targetDisplayColumns.filter((column) => column !== "name");
  const columnCount = (readOnly ? 3 : 4) + sourceColumns.length;

  return (
    <div ref={root}>
      <header className="page-header collection-header">
        <div>
          <h1 tabIndex={-1}>{view.name}</h1>
          <CollectionScope
            model={model}
            workspaceKey={workspaceKey}
            parentObjectId={query.parentObjectId}
            parentObjectTypeKey={query.parentObjectTypeKey}
          />
          <p>
            {sourceType.name} {directionLabel ? `→ ${directionLabel} → ` : "→ "}
            {targetType.name}
          </p>
        </div>
        {query.parentObjectId && (
          <button
            className="secondary"
            onClick={() =>
              onQueryChange({ ...query, parentObjectId: undefined, parentObjectTypeKey: undefined, cursors: undefined })
            }
          >
            Show all {sourceType.pluralName.toLowerCase()}
          </button>
        )}
      </header>
      <section className="surface collection-surface">
        <div className="collection-toolbar object-toolbar">
          <label className="search-box">
            <Icon name="search" />
            <input
              aria-label="Search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder={`Search ${sourceType.pluralName.toLowerCase()}`}
            />
          </label>
          <label className="toolbar-field mapping-state-filter">
            Mapping status
            <select
              value={query.mappingState ?? ""}
              onChange={(event) =>
                onQueryChange({
                  ...query,
                  mappingState: (event.target.value || undefined) as typeof query.mappingState,
                  cursors: undefined,
                })
              }
            >
              <option value="">All statuses</option>
              <option value="unmapped">No target</option>
              <option value="mapped">One target</option>
              <option value="ambiguous">Multiple targets</option>
            </select>
          </label>
        </div>
        <div className="collection-meta">
          <span role="status">
            {loading
              ? "Loading coverage…"
              : !error
                ? `${pages.items.length} on this page`
                : pages.items.length > 0
                  ? "Showing previously loaded data"
                  : "Coverage unavailable"}
          </span>
        </div>
        {error && <InlineError message={error} onRetry={pages.retry} />}
        {(!error || pages.items.length > 0) && (
          <div className="table-wrap mapping-table" role="region" aria-label={`${view.name} mapping grid`} tabIndex={0}>
            <table aria-busy={loading || undefined}>
              <caption className="visually-hidden">{view.name}</caption>
              <thead>
                <tr>
                  <th scope="col">{sourceType.name}</th>
                  {sourceColumns.map((col) => (
                    <th key={col} scope="col" className="mobile-secondary-column">
                      {attributeName(model, col)}
                    </th>
                  ))}
                  <th scope="col">Status</th>
                  <th scope="col">{targetType.name}</th>
                  {!readOnly && (
                    <th scope="col" className="mapping-actions-col">
                      Action
                    </th>
                  )}
                </tr>
              </thead>
              <tbody>
                {loading && pages.items.length === 0 ? (
                  <tr>
                    <td colSpan={columnCount} className="empty-row">
                      Loading…
                    </td>
                  </tr>
                ) : pages.items.length === 0 ? (
                  <tr>
                    <td colSpan={columnCount} className="empty-row">
                      {query.mappingState
                        ? "No results match these filters"
                        : query.search
                          ? "No results match this search"
                          : `No ${sourceType.pluralName.toLowerCase()} in this workspace yet`}
                    </td>
                  </tr>
                ) : (
                  pages.items.map((row) => (
                    <CoverageRow
                      key={row.source.id}
                      row={row}
                      model={model}
                      sourceColumns={sourceColumns}
                      targetColumns={targetColumns}
                      targetType={targetType}
                      workspaceKey={workspaceKey}
                      applicationKey={application.key}
                      viewKey={view.key}
                      config={config}
                      draftId={draft?.id}
                      readOnly={readOnly}
                      onSaved={refreshCoverage}
                    />
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
        {!error && (
          <Pagination
            disabled={loading}
            page={pages.pageNumber}
            hasNext={pages.hasNext}
            onPrevious={pages.previous}
            onNext={pages.next}
          />
        )}
      </section>
    </div>
  );
}

const STATE_LABELS: Record<string, string> = {
  mapped: "Mapped",
  unmapped: "Unmapped",
  ambiguous: "Ambiguous",
};

function CoverageRow({
  row,
  model,
  sourceColumns,
  targetColumns,
  targetType,
  workspaceKey,
  applicationKey,
  viewKey,
  config,
  draftId,
  readOnly,
  onSaved,
}: {
  row: MappingCoverageRow;
  model: EngineModel;
  sourceColumns: string[];
  targetColumns: string[];
  targetType: ObjectTypeDefinition;
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  config: MappingGridViewDefinition["config"];
  draftId?: string;
  readOnly?: boolean;
  onSaved: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const inlineTargets = row.targets;
  const hasMore = row.targetCount > inlineTargets.length;

  return (
    <>
      <tr className={`mapping-row mapping-state-${row.state}`}>
        <td>
          <span className="mapping-source-name">{row.source.name}</span>
        </td>
        {sourceColumns.map((col) => (
          <td key={col} className="mobile-secondary-column">
            {formatValue(row.source.fields[col])}
          </td>
        ))}
        <td>
          <span className={`mapping-state-badge state-${row.state}`}>
            {STATE_LABELS[row.state]}
            {row.state === "ambiguous" && ` (${row.targetCount})`}
          </span>
        </td>
        <td className="mapping-targets-cell">
          {row.state === "unmapped" ? (
            <span className="muted">—</span>
          ) : row.state === "mapped" && inlineTargets.length === 1 ? (
            <TargetDisplay target={inlineTargets[0]} columns={targetColumns} />
          ) : (
            <div className="mapping-targets-list">
              {(expanded ? inlineTargets : inlineTargets.slice(0, 3)).map((target) => (
                <TargetDisplay key={target.relationId} target={target} columns={targetColumns} />
              ))}
              {expanded && hasMore && (
                <TargetContinuation
                  workspaceKey={workspaceKey}
                  applicationKey={applicationKey}
                  viewKey={viewKey}
                  config={config}
                  draftId={draftId}
                  sourceObjectId={row.source.id}
                  mappingVersion={row.mappingVersion}
                  nextCursor={row.targetsNextCursor}
                  targetColumns={targetColumns}
                />
              )}
              {!expanded && (inlineTargets.length > 3 || hasMore) && (
                <button
                  className="secondary mapping-expand"
                  onClick={() => setExpanded(true)}
                  aria-label={`Show all ${row.targetCount} targets for ${row.source.name}`}
                >
                  {hasMore ? `Show all ${row.targetCount}…` : `Show all ${inlineTargets.length}`}
                </button>
              )}
              {expanded && (
                <button className="secondary mapping-expand" onClick={() => setExpanded(false)}>
                  Show fewer
                </button>
              )}
            </div>
          )}
        </td>
        {!readOnly && (
          <td className="mapping-actions-col">
            <button
              className="secondary"
              onClick={() => setEditing(true)}
              aria-label={`Change mapping for ${row.source.name}`}
            >
              Change
            </button>
          </td>
        )}
      </tr>
      {editing && (
        <MappingActionDialog
          model={model}
          workspaceKey={workspaceKey}
          applicationKey={applicationKey}
          viewKey={viewKey}
          config={config}
          draftId={draftId}
          source={row.source}
          currentTargets={row.targets}
          mappingVersion={row.mappingVersion}
          targetType={targetType}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            onSaved();
          }}
        />
      )}
    </>
  );
}

function MappingActionDialog({
  model,
  workspaceKey,
  applicationKey,
  viewKey,
  config,
  draftId,
  source,
  currentTargets,
  mappingVersion,
  targetType,
  onClose,
  onSaved,
}: {
  model: EngineModel;
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  config: MappingGridViewDefinition["config"];
  draftId?: string;
  source: MappingObjectSummary;
  currentTargets: MappingTargetSummary[];
  mappingVersion: number;
  targetType: ObjectTypeDefinition;
  onClose: () => void;
  onSaved: () => void;
}) {
  const api = useDataApi();
  const targetTypeKey = config.direction === "outgoing" ? config.toObjectTypeKey : config.fromObjectTypeKey;
  const [selectedId, setSelectedId] = useState<string | null>(
    currentTargets.length === 1 ? currentTargets[0].object.id : null,
  );
  const [selectedName, setSelectedName] = useState(currentTargets.length === 1 ? currentTargets[0].object.name : "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [conflictVersion, setConflictVersion] = useState<number | null>(null);
  const [conflictTargets, setConflictTargets] = useState<MappingTargetSummary[]>([]);
  const [conflictTargetCount, setConflictTargetCount] = useState(0);
  const [conflictAcknowledged, setConflictAcknowledged] = useState(false);
  const [currentMappingVersion, setCurrentMappingVersion] = useState(mappingVersion);
  const [candidateSearch, setCandidateSearch] = useState("");
  const debouncedSearch = useDebouncedValue(candidateSearch.trim());
  const [showCreate, setShowCreate] = useState(false);
  const dirty = selectedId !== (currentTargets.length === 1 ? currentTargets[0].object.id : null);

  const candidates = useCursorFeed<MappingObjectSummary>(
    (cursor) =>
      api.mappingCandidates({
        workspaceKey,
        applicationKey,
        viewKey,
        objectTypeKey: targetTypeKey,
        workspaceDraftId: draftId,
        search: debouncedSearch || undefined,
        cursor,
        pageSize: 20,
      }),
    [workspaceKey, applicationKey, viewKey, targetTypeKey, draftId, debouncedSearch],
  );

  async function save() {
    setSaving(true);
    setError("");
    setConflictVersion(null);
    setConflictAcknowledged(false);
    try {
      await api.replaceMapping(workspaceKey, {
        relationTypeKey: config.relationTypeKey,
        fromObjectTypeKey: config.fromObjectTypeKey,
        toObjectTypeKey: config.toObjectTypeKey,
        direction: config.direction,
        sourceObjectId: source.id,
        targetObjectId: selectedId,
        expectedMappingVersion: currentMappingVersion,
      });
      onSaved();
    } catch (cause) {
      if (isApiError(cause, "mapping_version_conflict")) {
        const details = cause.details as
          { mappingVersion?: number; targetCount?: number; targets?: MappingTargetSummary[] } | undefined;
        const newVersion = details?.mappingVersion ?? currentMappingVersion;
        setConflictVersion(newVersion);
        setCurrentMappingVersion(newVersion);
        setConflictTargets(details?.targets ?? []);
        setConflictTargetCount(details?.targetCount ?? 0);
        setError(
          "The mapping was changed by another operation. Review the latest state before applying your selection.",
        );
      } else {
        setError(errorMessage(cause));
      }
      setSaving(false);
    }
  }

  function handleCreated(item: ObjectItem) {
    setShowCreate(false);
    setSelectedId(item.id);
    setSelectedName(item.name);
    candidates.reload();
  }

  return (
    <>
      <Modal title={`Change mapping — ${source.name}`} eyebrow="Mapping" busy={saving} dirty={dirty} onClose={onClose}>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          <label>
            Target {targetType.name}
            <div className="object-lookup">
              <input
                aria-label={`Search ${targetType.pluralName.toLowerCase()}`}
                value={candidateSearch}
                onChange={(e) => setCandidateSearch(e.target.value)}
                placeholder={`Search ${targetType.pluralName.toLowerCase()}…`}
                autoFocus
              />
              <select
                aria-label={`Select ${targetType.name.toLowerCase()}`}
                value={selectedId ?? ""}
                onChange={(e) => {
                  const id = e.target.value || null;
                  setSelectedId(id);
                  if (id) {
                    const found = candidates.items.find((c) => c.id === id);
                    setSelectedName(found?.name ?? "");
                  } else {
                    setSelectedName("");
                  }
                }}
              >
                <option value="">
                  {candidates.loading && !candidates.items.length ? "Loading…" : "No target (clear mapping)"}
                </option>
                {selectedId && !candidates.items.some((c) => c.id === selectedId) && (
                  <option value={selectedId}>{selectedName || `Selected (${selectedId})`}</option>
                )}
                {candidates.items.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                    {Object.keys(c.fields).length > 0 &&
                      ` — ${Object.values(c.fields)
                        .filter((v) => v != null && v !== "")
                        .join(", ")}`}
                  </option>
                ))}
              </select>
              {candidates.error && <InlineError message={candidates.error} onRetry={candidates.retry} />}
              {candidates.hasMore && !candidates.error && (
                <button
                  type="button"
                  className="load-more inline"
                  disabled={candidates.loading}
                  onClick={candidates.loadMore}
                >
                  Load more candidates
                </button>
              )}
            </div>
            <small>
              <button type="button" className="secondary mapping-create-target" onClick={() => setShowCreate(true)}>
                Create new {targetType.name.toLowerCase()}
              </button>
            </small>
          </label>

          {conflictVersion !== null && (
            <Notice tone="warning" title="Mapping conflict" focusOnMount>
              <p>{error}</p>
              <p>
                Current mapping:{" "}
                {conflictTargetCount === 0
                  ? "Unmapped"
                  : conflictTargets.map((target) => target.object.name).join(", ")}
                {conflictTargetCount > conflictTargets.length
                  ? ` and ${conflictTargetCount - conflictTargets.length} more`
                  : ""}
                .
              </p>
              {!conflictAcknowledged && (
                <button type="button" className="secondary" onClick={() => setConflictAcknowledged(true)}>
                  Continue with my selection
                </button>
              )}
            </Notice>
          )}
          {error && conflictVersion === null && (
            <Notice tone="error" title="Save failed" focusOnMount>
              {error}
            </Notice>
          )}

          <div className="dialog-actions">
            <button type="button" className="secondary" disabled={saving} onClick={onClose}>
              Cancel
            </button>
            <button className="primary" disabled={saving || (conflictVersion !== null && !conflictAcknowledged)}>
              {saving ? "Saving…" : selectedId ? "Save mapping" : "Clear mapping"}
            </button>
          </div>
        </form>
      </Modal>
      {showCreate && (
        <ObjectFormDialog
          model={model}
          applicationKey={applicationKey}
          workspaceKey={workspaceKey}
          objectType={targetType}
          onClose={() => setShowCreate(false)}
          onSaved={handleCreated}
        />
      )}
    </>
  );
}

function TargetDisplay({ target, columns }: { target: MappingTargetSummary; columns: string[] }) {
  return (
    <div className="mapping-target">
      <span className="mapping-target-name">{target.object.name}</span>
      {columns.map((col) => (
        <span key={col} className="mapping-target-field mobile-secondary-column">
          {formatValue(target.object.fields[col])}
        </span>
      ))}
    </div>
  );
}

function TargetContinuation({
  workspaceKey,
  applicationKey,
  viewKey,
  config,
  draftId,
  sourceObjectId,
  mappingVersion,
  nextCursor,
  targetColumns,
}: {
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  config: MappingGridViewDefinition["config"];
  draftId?: string;
  sourceObjectId: string;
  mappingVersion: number;
  nextCursor: string | null;
  targetColumns: string[];
}) {
  const api = useDataApi();
  const [targets, setTargets] = useState<MappingTargetSummary[]>([]);
  const [cursor, setCursor] = useState(nextCursor);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const loadMore = useCallback(async () => {
    if (!cursor || loading) return;
    setLoading(true);
    setError("");
    try {
      const page = await api.mappingTargets({
        workspaceKey,
        applicationKey,
        viewKey,
        relationTypeKey: config.relationTypeKey,
        fromObjectTypeKey: config.fromObjectTypeKey,
        toObjectTypeKey: config.toObjectTypeKey,
        direction: config.direction,
        workspaceDraftId: draftId,
        sourceObjectId,
        mappingVersion,
        cursor,
      });
      setTargets((prev) => [...prev, ...page.items]);
      setCursor(page.nextCursor);
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setLoading(false);
    }
  }, [api, workspaceKey, applicationKey, viewKey, config, draftId, sourceObjectId, mappingVersion, cursor, loading]);

  return (
    <>
      {targets.map((target) => (
        <TargetDisplay key={target.relationId} target={target} columns={targetColumns} />
      ))}
      {loading && <span className="muted">Loading more targets…</span>}
      {error && (
        <span className="mapping-target-error">
          Could not load targets.{" "}
          <button className="secondary" onClick={loadMore}>
            Retry
          </button>
        </span>
      )}
      {cursor && !loading && !error && (
        <button className="secondary mapping-expand" onClick={loadMore}>
          Load more…
        </button>
      )}
    </>
  );
}
