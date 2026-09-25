import { useCallback, useEffect, useRef, useState } from "react";
import { useDataApi, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { errorMessage, isApiError } from "@/api/errors";
import { InlineError } from "@/ui/InlineError";
import { ScrollWindow } from "@/ui/ScrollWindow";
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

const STATE_FILTERS: { value: "" | "unmapped" | "mapped" | "ambiguous"; label: string }[] = [
  { value: "", label: "All" },
  { value: "unmapped", label: "Unmapped" },
  { value: "mapped", label: "Mapped" },
  { value: "ambiguous", label: "Ambiguous" },
];

export function MappingGridView({
  model,
  application,
  view: rawView,
  workspaceKey,
  readOnly,
  onChanged,
  query,
  onQueryChange,
  onAnchorChange,
  refreshToken = 0,
  lenses,
}: ViewComponentProps) {
  const view = rawView as MappingGridViewDefinition;
  const api = useDataApi();
  const { draft } = useWorkspaceData();
  const root = useRef<HTMLDivElement>(null);
  const [search, setSearch] = useState(query.search);
  const [internalRefresh, setInternalRefresh] = useState(0);
  const [editingId, setEditingId] = useState<string>();

  const { config } = view;
  const sourceTypeKey = config.direction === "outgoing" ? config.fromObjectTypeKey : config.toObjectTypeKey;
  const targetTypeKey = config.direction === "outgoing" ? config.toObjectTypeKey : config.fromObjectTypeKey;
  const sourceType = objectTypeFor(model, sourceTypeKey);
  const targetType = objectTypeFor(model, targetTypeKey);
  const relationType = model.relationTypes.find((rt) => rt.key === config.relationTypeKey);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const trimmed = search.trim();
      if (trimmed !== query.search) onQueryChange({ ...query, search: trimmed, anchor: undefined });
    }, 250);
    return () => window.clearTimeout(timer);
  }, [search, query, onQueryChange]);

  const combinedRefresh = refreshToken + internalRefresh;

  const pageSize = query.pageSize || config.pageSize;
  const pages = useCursorWindow<MappingCoverageRow>(
    (selector) =>
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
        ...selector,
        pageSize,
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
    { anchor: query.anchor, refreshToken: combinedRefresh },
  );
  const { loading, error } = pages;

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
  const editingIndex = pages.items.findIndex((row) => row.source.id === editingId);
  const editingRow = editingIndex >= 0 ? pages.items[editingIndex] : undefined;
  const nextRow = editingIndex >= 0 ? pages.items[editingIndex + 1] : undefined;

  return (
    <div ref={root}>
      <header className="page-header collection-header">
        <div className="page-title">
          <span className="page-icon" aria-hidden="true">
            <Icon name="mapping" size={20} />
          </span>
          <div>
            <h1 tabIndex={-1}>{view.name}</h1>
            <p className="mapping-direction">
              <span>{sourceType.name}</span>
              <Icon name="arrow-right" size={14} />
              <span>{directionLabel ?? "maps to"}</span>
              <Icon name="arrow-right" size={14} />
              <span>{targetType.name}</span>
            </p>
          </div>
        </div>
      </header>
      {query.parentObjectId && (
        <div className="scope-banner">
          <CollectionScope
            model={model}
            workspaceKey={workspaceKey}
            parentObjectId={query.parentObjectId}
            parentObjectTypeKey={query.parentObjectTypeKey}
          />
          <button
            className="ghost"
            onClick={() =>
              onQueryChange({ ...query, parentObjectId: undefined, parentObjectTypeKey: undefined, anchor: undefined })
            }
          >
            Show all {sourceType.pluralName.toLowerCase()}
          </button>
        </div>
      )}
      {lenses}
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
          <div className="segmented" role="group" aria-label="Mapping status">
            {STATE_FILTERS.map((option) => (
              <button
                key={option.value || "all"}
                aria-pressed={(query.mappingState ?? "") === option.value}
                onClick={() =>
                  onQueryChange({
                    ...query,
                    mappingState: option.value || undefined,
                    anchor: undefined,
                  })
                }
              >
                {option.value && <span className={`state-dot state-${option.value}`} aria-hidden="true" />}
                {option.label}
              </button>
            ))}
          </div>
        </div>
        {error && <InlineError message={error} onRetry={pages.retry} />}
        {(!error || pages.items.length > 0) && (
          <ScrollWindow
            list={pages}
            label={`${view.name} mapping grid`}
            noun={["row", "rows"]}
            pageSize={pageSize}
            onAnchorChange={onAnchorChange}
            className="table-wrap mapping-table"
          >
            <table
              aria-busy={loading || undefined}
              aria-rowcount={pages.totalCount !== null && pages.items.length > 0 ? pages.totalCount + 1 : undefined}
            >
              <caption className="visually-hidden">{view.name}</caption>
              <thead>
                <tr aria-rowindex={1}>
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
                  pages.items.map((row, position) => (
                    <CoverageRow
                      key={row.source.id}
                      index={pages.startIndex + position}
                      row={row}
                      sourceColumns={sourceColumns}
                      targetColumns={targetColumns}
                      workspaceKey={workspaceKey}
                      applicationKey={application.key}
                      viewKey={view.key}
                      config={config}
                      draftId={draft?.id}
                      readOnly={readOnly}
                      onEdit={() => setEditingId(row.source.id)}
                    />
                  ))
                )}
              </tbody>
            </table>
          </ScrollWindow>
        )}
      </section>
      {editingRow && !readOnly && (
        <MappingActionDialog
          key={editingRow.source.id}
          model={model}
          workspaceKey={workspaceKey}
          applicationKey={application.key}
          viewKey={view.key}
          config={config}
          draftId={draft?.id}
          source={editingRow.source}
          currentTargets={editingRow.targets}
          targetCount={editingRow.targetCount}
          mappingVersion={editingRow.mappingVersion}
          targetType={targetType}
          nextName={nextRow?.source.name}
          onClose={() => setEditingId(undefined)}
          onSaved={(continueToNext) => {
            setEditingId(continueToNext ? nextRow?.source.id : undefined);
            refreshCoverage();
          }}
        />
      )}
    </div>
  );
}

const STATE_LABELS: Record<string, string> = {
  mapped: "Mapped",
  unmapped: "Unmapped",
  ambiguous: "Ambiguous",
};

function CoverageRow({
  index,
  row,
  sourceColumns,
  targetColumns,
  workspaceKey,
  applicationKey,
  viewKey,
  config,
  draftId,
  readOnly,
  onEdit,
}: {
  index: number;
  row: MappingCoverageRow;
  sourceColumns: string[];
  targetColumns: string[];
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  config: MappingGridViewDefinition["config"];
  draftId?: string;
  readOnly?: boolean;
  onEdit: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const inlineTargets = row.targets;
  const hasMore = row.targetCount > inlineTargets.length;

  return (
    <tr
      data-row-key={row.source.id}
      data-row-index={index}
      aria-rowindex={index + 2}
      tabIndex={-1}
      className={`mapping-row mapping-state-${row.state}${readOnly ? "" : " clickable-row"}`}
      onClick={
        readOnly
          ? undefined
          : (event) => {
              // The row button is the keyboard path; the row is a larger pointer target.
              if ((event.target as HTMLElement).closest("button, a, input, select, textarea")) return;
              if (window.getSelection()?.toString()) return;
              onEdit();
            }
      }
    >
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
          <span className={`state-dot state-${row.state}`} aria-hidden="true" />
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
                className="ghost mapping-expand"
                onClick={() => setExpanded(true)}
                aria-label={`Show all ${row.targetCount} targets for ${row.source.name}`}
              >
                {hasMore ? `Show all ${row.targetCount}…` : `Show all ${inlineTargets.length}`}
              </button>
            )}
            {expanded && (
              <button className="ghost mapping-expand" onClick={() => setExpanded(false)}>
                Show fewer
              </button>
            )}
          </div>
        )}
      </td>
      {!readOnly && (
        <td className="mapping-actions-col">
          <button
            data-row-focus
            className={row.state === "unmapped" ? "secondary accent-outline" : "secondary"}
            onClick={onEdit}
            aria-label={`Change mapping for ${row.source.name}`}
          >
            {row.state === "unmapped" ? "Map" : "Change"}
          </button>
        </td>
      )}
    </tr>
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
  targetCount,
  mappingVersion,
  targetType,
  nextName,
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
  targetCount: number;
  mappingVersion: number;
  targetType: ObjectTypeDefinition;
  /** The following row on this page, offered as "Save and map next". */
  nextName?: string;
  onClose: () => void;
  onSaved: (continueToNext: boolean) => void;
}) {
  const api = useDataApi();
  const targetTypeKey = config.direction === "outgoing" ? config.toObjectTypeKey : config.fromObjectTypeKey;
  const currentId = currentTargets.length === 1 && targetCount === 1 ? currentTargets[0].object.id : null;
  const [selectedId, setSelectedId] = useState<string | null>(currentId);
  const [created, setCreated] = useState<MappingObjectSummary>();
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
  // Objects belong to one application and candidates are read across all of them, so the user
  // chooses where a target created here lives; the lens's application is the default when it can.
  const ownerChoices = model.applications
    .filter((application) => application.objectTypeKeys.includes(targetTypeKey))
    .map((application) => application.key);
  // The server refuses to clear a required relationship, so removal is offered only where the
  // binding allows an empty mapping (SC-07).
  const clearable = !model.objectTypeRelations.some(
    (binding) =>
      binding.relationTypeKey === config.relationTypeKey &&
      binding.fromObjectTypeKey === config.fromObjectTypeKey &&
      binding.toObjectTypeKey === config.toObjectTypeKey &&
      binding.required,
  );
  const dirty = selectedId !== currentId;
  const blockedByConflict = conflictVersion !== null && !conflictAcknowledged;

  const candidates = useCursorWindow<MappingObjectSummary>(
    (selector) =>
      api.mappingCandidates({
        workspaceKey,
        applicationKey,
        viewKey,
        objectTypeKey: targetTypeKey,
        workspaceDraftId: draftId,
        search: debouncedSearch || undefined,
        ...selector,
        pageSize: 20,
      }),
    [workspaceKey, applicationKey, viewKey, targetTypeKey, draftId, debouncedSearch],
  );
  // A target created here is shown first until the list reads it; it has no place in the list yet.
  const rowIndex = (id: string) => {
    const position = candidates.items.findIndex((item) => item.id === id);
    return position >= 0 ? candidates.startIndex + position : -1;
  };
  const listed = [
    ...(created && !candidates.items.some((item) => item.id === created.id) ? [created] : []),
    ...candidates.items,
  ];

  async function save(targetObjectId: string | null, continueToNext = false) {
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
        targetObjectId,
        expectedMappingVersion: currentMappingVersion,
      });
      onSaved(continueToNext);
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
    setCreated({ id: item.id, objectTypeKey: item.objectTypeKey, name: item.name, fields: {} });
    setSelectedId(item.id);
    candidates.reload();
  }

  return (
    <>
      <Modal title={`Change mapping — ${source.name}`} eyebrow="Mapping" busy={saving} dirty={dirty} onClose={onClose}>
        <form
          className="mapping-dialog"
          onSubmit={(e) => {
            e.preventDefault();
            if (selectedId && dirty) void save(selectedId);
          }}
        >
          <div className="mapping-current">
            <span>Currently</span>
            {targetCount === 0 ? (
              <strong className="muted-strong">Not mapped</strong>
            ) : (
              <strong>
                {currentTargets.map((target) => target.object.name).join(", ")}
                {targetCount > currentTargets.length ? ` and ${targetCount - currentTargets.length} more` : ""}
              </strong>
            )}
          </div>
          <label className="search-box candidate-search">
            <Icon name="search" />
            <input
              aria-label={`Search ${targetType.pluralName.toLowerCase()}`}
              value={candidateSearch}
              onChange={(e) => setCandidateSearch(e.target.value)}
              placeholder={`Search ${targetType.pluralName.toLowerCase()}…`}
              autoFocus
            />
          </label>
          <fieldset className="candidate-list" aria-busy={candidates.loading || undefined}>
            <legend className="visually-hidden">Select {targetType.name.toLowerCase()}</legend>
            <ScrollWindow
              list={candidates}
              label={`${targetType.pluralName} to choose from`}
              noun={[targetType.name.toLowerCase(), targetType.pluralName.toLowerCase()]}
              pageSize={20}
              rowNavigation={false}
              footer={false}
              className="candidate-scroll"
            >
              {listed.map((candidate) => {
                const details = [
                  ...new Set(
                    Object.values(candidate.fields)
                      .filter((value) => value != null && value !== "" && value !== candidate.name)
                      .map(String),
                  ),
                ];
                return (
                  <label
                    key={candidate.id}
                    data-row-key={candidate.id}
                    data-row-index={rowIndex(candidate.id) >= 0 ? rowIndex(candidate.id) : undefined}
                    className={selectedId === candidate.id ? "candidate selected" : "candidate"}
                  >
                    <input
                      type="radio"
                      name="mapping-target"
                      value={candidate.id}
                      checked={selectedId === candidate.id}
                      onChange={() => setSelectedId(candidate.id)}
                    />
                    <span className="candidate-text">
                      <span className="candidate-name">{candidate.name}</span>
                      {details.length > 0 && <small>{details.join(" · ")}</small>}
                    </span>
                    {currentTargets.some((target) => target.object.id === candidate.id) && (
                      <span className="pill">Current</span>
                    )}
                  </label>
                );
              })}
              {candidates.loading && !candidates.items.length && <p className="candidate-state">Loading…</p>}
              {!candidates.loading && !candidates.error && listed.length === 0 && (
                <p className="candidate-state">
                  No {targetType.pluralName.toLowerCase()} match{debouncedSearch ? ` “${debouncedSearch}”` : ""}.
                </p>
              )}
            </ScrollWindow>
            {candidates.error && <InlineError message={candidates.error} onRetry={candidates.retry} />}
          </fieldset>
          <button type="button" className="ghost mapping-create-target" onClick={() => setShowCreate(true)}>
            <Icon name="plus" size={15} /> Create new {targetType.name.toLowerCase()}
          </button>

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
            {targetCount > 0 && !clearable && (
              <span className="muted">This mapping is required; choose a replacement to change it.</span>
            )}
            {targetCount > 0 && clearable && (
              <button
                type="button"
                className="danger-ghost"
                disabled={saving || blockedByConflict}
                onClick={() => void save(null)}
              >
                Remove mapping
              </button>
            )}
            <span className="dialog-actions-spacer" />
            <button type="button" className="secondary" disabled={saving} onClick={onClose}>
              Cancel
            </button>
            {nextName && (
              <button
                type="button"
                className="secondary"
                disabled={saving || !selectedId || !dirty || blockedByConflict}
                title={`Save, then map ${nextName}`}
                onClick={() => selectedId && void save(selectedId, true)}
              >
                Save and next
              </button>
            )}
            <button className="primary" disabled={saving || !selectedId || !dirty || blockedByConflict}>
              {saving ? "Saving…" : "Save mapping"}
            </button>
          </div>
        </form>
      </Modal>
      {showCreate && (
        <ObjectFormDialog
          model={model}
          applicationKey={ownerChoices.includes(applicationKey) ? applicationKey : ownerChoices[0]}
          applicationChoices={ownerChoices}
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
