import { useCallback, useMemo, useRef, useState, type MouseEvent } from "react";
import { useDataApi, useRecordWrites, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { useCursorWindow } from "@/lib/hooks/useCursorWindow";
import { useDebouncedValue } from "@/lib/hooks/useDebouncedValue";
import { errorMessage, isApiError } from "@/api/errors";
import { InlineError } from "@/ui/InlineError";
import { DataTable, type DataColumn } from "@/ui/DataTable";
import { ScrollWindow, WindowPlaceholder, WindowSpacer } from "@/ui/ScrollWindow";
import { useTableDisplay } from "@/ui/TableDisplay";
import { Icon } from "@/ui/Icon";
import { PageHeader } from "@/ui/PageHeader";
import { HueTile } from "@/ui/HueTile";
import { RecordChip } from "@/ui/RecordChip";
import { objectTypeHue, objectTypeTile, type Hue } from "@/model/hues";
import { Candidate } from "@/ui/Candidate";
import { Modal } from "@/ui/Modal";
import { Notice } from "@/ui/Notice";
import { formatValue } from "@/ui/formatValue";
import { attributeName } from "@/model/fields";
import { holdsOne, listingApplication, objectTypeFor } from "@/model/lookup";
import { ObjectFormDialog } from "@/features/objects/ObjectFormDialog";
import { ScopeBanner } from "@/features/objects/CollectionScope";
import { MappingProposalDialog } from "@/features/objects/MappingProposalDialog";
import { useWorkspaceAiOffer } from "@/features/settings/useWorkspaceAiOffer";
import { AiOriginMark } from "@/ui/AiOriginMark";
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
import { DebouncedSearchField } from "@/ui/SearchField";
import { StatusPill, type StatusTone } from "@/ui/StatusPill";
import { Card } from "@/ui/Card";

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
  readOnly: contextReadOnly,
  onChanged,
  query,
  onQueryChange,
  onAnchorChange,
  onShowProposed,
  refreshToken = 0,
  lenses,
  onOpen,
}: ViewComponentProps) {
  const view = rawView as MappingGridViewDefinition;
  const api = useDataApi();
  const { changeSet } = useWorkspaceData();
  const root = useRef<HTMLDivElement>(null);
  const [internalRefresh, setInternalRefresh] = useState(0);
  const [editingId, setEditingId] = useState<string>();
  const [proposing, setProposing] = useState(false);

  const { config } = view;
  const sourceTypeKey = config.direction === "outgoing" ? config.fromObjectTypeKey : config.toObjectTypeKey;
  const targetTypeKey = config.direction === "outgoing" ? config.toObjectTypeKey : config.fromObjectTypeKey;
  const sourceType = objectTypeFor(model, sourceTypeKey);
  const targetType = objectTypeFor(model, targetTypeKey);
  const relationType = model.relationTypes.find((rt) => rt.key === config.relationTypeKey);
  // Several targets are ambiguous only where a source holds at most one; elsewhere they are mapped.
  const binding = model.objectTypeRelations.find(
    (b) =>
      b.relationTypeKey === config.relationTypeKey &&
      b.fromObjectTypeKey === config.fromObjectTypeKey &&
      b.toObjectTypeKey === config.toObjectTypeKey,
  );
  const sourceHoldsOne = binding ? holdsOne(binding, config.direction === "outgoing" ? "from" : "to") : true;
  // A mapping is a relationship: written where either end's type may be (0.12 Z5, D291, D329).
  const writes = useRecordWrites();
  const readOnly =
    contextReadOnly || !(writes.permits(application.key, sourceTypeKey) || writes.permitsType(targetTypeKey));

  const combinedRefresh = refreshToken + internalRefresh;
  // The AI's proposals are read in a change set; the button is offered where the AI may be asked (0.16 AP2).
  const proposed = Boolean(query.mappingProposed && changeSet);
  const assistant = useWorkspaceAiOffer();
  const canPropose = Boolean(assistant && !readOnly);
  const proposalScope = useMemo(
    () => ({
      workspaceKey,
      applicationKey: application.key,
      viewKey: view.key,
      viewName: view.name,
      coverage: {
        relationTypeKey: config.relationTypeKey,
        fromObjectTypeKey: config.fromObjectTypeKey,
        toObjectTypeKey: config.toObjectTypeKey,
        direction: config.direction,
      },
      search: query.search || undefined,
      parentObjectId: query.parentObjectId,
      sources: (sourceType?.pluralName ?? "").toLowerCase(),
      targets: (targetType?.pluralName ?? "").toLowerCase(),
      targetName: (targetType?.name ?? "").toLowerCase(),
    }),
    [
      workspaceKey,
      application.key,
      view.key,
      view.name,
      config,
      query.search,
      query.parentObjectId,
      sourceType,
      targetType,
    ],
  );

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
        changeSetId: changeSet?.id,
        search: query.search || undefined,
        parentObjectId: query.parentObjectId,
        state: proposed ? undefined : query.mappingState,
        proposed: proposed || undefined,
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
      proposed,
      changeSet?.id,
    ],
    { anchor: query.anchor, refreshToken: combinedRefresh },
  );
  const { error } = pages;

  const refreshCoverage = useCallback(() => {
    setInternalRefresh((n) => n + 1);
    onChanged?.();
  }, [onChanged]);

  // The columns keep their widths per view on this device, as every table's do (ui/TableDisplay).
  const sourceColumns = config.sourceColumns.filter((column) => column !== "name");
  const targetColumns = config.targetDisplayColumns.filter((column) => column !== "name");
  const display = useTableDisplay(["name", ...sourceColumns, "state", "targets"], `${application.key}:${view.key}`);
  const rowAttributes = useCallback(
    (row: MappingCoverageRow) => ({
      tabIndex: -1,
      className: `mapping-row mapping-state-${row.state}${readOnly ? "" : " clickable-row"}`,
      onClick: readOnly
        ? undefined
        : (event: MouseEvent<HTMLTableRowElement>) => {
            // The row button is the keyboard path; the row is a larger pointer target.
            if ((event.target as HTMLElement).closest("button, a, input, select, textarea, summary")) return;
            if (window.getSelection()?.toString()) return;
            setEditingId(row.source.id);
          },
    }),
    [readOnly],
  );

  if (!sourceType || !targetType) {
    return (
      <div className="empty-state">
        <h2>{view.name}</h2>
        <p>This mapping view references an object type that does not exist in the active model.</p>
      </div>
    );
  }

  const directionLabel = config.direction === "outgoing" ? relationType?.name : relationType?.reverseName;
  const sourceApplicationKey = listingApplication(model, application.key, sourceTypeKey);
  const targetApplicationKey = listingApplication(model, application.key, targetTypeKey);
  const targetHue = objectTypeHue(model, targetType.key);
  const editingIndex = pages.items.findIndex((row) => row.source.id === editingId);
  const editingRow = editingIndex >= 0 ? pages.items[editingIndex] : undefined;
  const nextRow = editingIndex >= 0 ? pages.items[editingIndex + 1] : undefined;

  const openRecord = (record: MappingObjectSummary, applicationKey: string) =>
    onOpen({ id: record.id, objectTypeKey: record.objectTypeKey, applicationKey, workspaceKey });
  const openTarget = (record: MappingObjectSummary) => openRecord(record, targetApplicationKey);
  const columns: DataColumn<MappingCoverageRow>[] = [
    {
      key: "name",
      label: sourceType.name,
      alwaysShown: true,
      cell: (row) => (
        <button className="cell-link mapping-source-name" onClick={() => openRecord(row.source, sourceApplicationKey)}>
          {row.source.name}
        </button>
      ),
    },
    ...sourceColumns.map((column): DataColumn<MappingCoverageRow> => ({
      key: column,
      label: attributeName(model, column),
      cell: (row) => <SourceValue model={model} field={column} value={row.source.fields[column]} />,
    })),
    {
      key: "state",
      label: "Status",
      alwaysShown: true,
      cell: (row) => (
        <StatusPill tone={STATE_TONES[row.state]}>
          {STATE_LABELS[row.state]}
          {row.targetCount > 1 && ` (${row.targetCount})`}
        </StatusPill>
      ),
    },
    {
      key: "targets",
      label: targetType.name,
      alwaysShown: true,
      className: "mapping-targets-cell",
      cell: (row) => (
        <TargetsCell
          row={row}
          targetColumns={targetColumns}
          targetHue={targetHue}
          workspaceKey={workspaceKey}
          applicationKey={application.key}
          viewKey={view.key}
          config={config}
          changeSetId={changeSet?.id}
          onOpenTarget={openTarget}
        />
      ),
    },
  ];

  return (
    <div ref={root}>
      <PageHeader
        focusTitle
        icon={<HueTile hue={objectTypeHue(model, sourceType.key)} icon={sourceType.icon} size={40} />}
        title={view.name}
        descriptionClassName="mapping-direction"
        description={
          <>
            <span>{sourceType.name}</span>
            <Icon name="arrow-right" size={14} />
            <span>{directionLabel ?? "maps to"}</span>
            <Icon name="arrow-right" size={14} />
            <span>{targetType.name}</span>
          </>
        }
      />
      <ScopeBanner
        model={model}
        workspaceKey={workspaceKey}
        query={query}
        onQueryChange={onQueryChange}
        pluralName={sourceType.pluralName}
      />
      {lenses}
      <Card as="section" flush className="collection-surface">
        <div className="collection-toolbar object-toolbar">
          <DebouncedSearchField
            appliedValue={query.search}
            onApply={(search) => onQueryChange({ ...query, search, anchor: undefined })}
            placeholder={`Search ${sourceType.pluralName.toLowerCase()}`}
          />
          <div className="segmented" role="group" aria-label="Mapping status">
            {STATE_FILTERS.filter((option) => option.value !== "ambiguous" || sourceHoldsOne).map((option) => (
              <button
                key={option.value || "all"}
                aria-pressed={!proposed && (query.mappingState ?? "") === option.value}
                onClick={() =>
                  onQueryChange({
                    ...query,
                    mappingState: option.value || undefined,
                    mappingProposed: undefined,
                    anchor: undefined,
                  })
                }
              >
                {option.value && <span className={`state-dot state-${option.value}`} aria-hidden="true" />}
                {option.label}
              </button>
            ))}
            {changeSet && (
              <button
                aria-pressed={proposed}
                onClick={() =>
                  onQueryChange({ ...query, mappingState: undefined, mappingProposed: true, anchor: undefined })
                }
              >
                <Icon name="sparkle" size={14} />
                Proposed
              </button>
            )}
          </div>
          {canPropose && (
            <div className="mapping-propose-end">
              <button type="button" className="secondary" onClick={() => setProposing(true)}>
                <Icon name="sparkle" size={16} />
                Propose targets
              </button>
            </div>
          )}
        </div>
        {error && <InlineError message={error} onRetry={pages.retry} />}
        {(!error || pages.items.length > 0) && (
          <DataTable<MappingCoverageRow>
            columns={columns}
            list={pages}
            rowKey={(row) => row.source.id}
            rowAttributes={rowAttributes}
            actions={
              readOnly
                ? undefined
                : {
                    header: "Action",
                    width: 96,
                    className: "mapping-actions-col",
                    cell: (row) => (
                      <button
                        data-row-focus
                        className={row.state === "unmapped" ? "secondary accent-outline" : "secondary"}
                        onClick={() => setEditingId(row.source.id)}
                        aria-label={`Change mapping for ${row.source.name}`}
                      >
                        {row.state === "unmapped" ? "Map" : "Change"}
                      </button>
                    ),
                  }
            }
            columnWidths={display.widths}
            onColumnWidths={display.setWidths}
            label={`${view.name} mapping grid`}
            noun={["row", "rows"]}
            pageSize={pageSize}
            onAnchorChange={onAnchorChange}
            className="mapping-table"
            oneLine
            emptyMessage={
              proposed
                ? "No targets proposed by the AI in this change set"
                : query.mappingState
                  ? "No results match these filters"
                  : query.search
                    ? "No results match this search"
                    : `No ${sourceType.pluralName.toLowerCase()} in this workspace yet`
            }
          />
        )}
      </Card>
      {proposing && assistant && !readOnly && (
        <MappingProposalDialog
          scope={proposalScope}
          offer={assistant}
          onClose={() => setProposing(false)}
          onShowProposed={(changeSetId) => {
            if (changeSetId === changeSet?.id) {
              onQueryChange({ ...query, mappingState: undefined, mappingProposed: true, anchor: undefined });
              refreshCoverage();
            } else onShowProposed?.(changeSetId);
          }}
        />
      )}
      {editingRow && !readOnly && (
        <MappingActionDialog
          key={editingRow.source.id}
          model={model}
          workspaceKey={workspaceKey}
          applicationKey={application.key}
          viewKey={view.key}
          config={config}
          changeSetId={changeSet?.id}
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

const STATE_TONES: Record<MappingCoverageRow["state"], StatusTone> = {
  mapped: "success",
  unmapped: "neutral",
  ambiguous: "warning",
};

const STATE_LABELS: Record<string, string> = {
  mapped: "Mapped",
  unmapped: "Unmapped",
  ambiguous: "Ambiguous",
};

/** A source's own value; the name of the record above it (`ancestor:<type>`) is a chip in that type's colour. */
function SourceValue({ model, field, value }: { model: EngineModel; field: string; value: unknown }) {
  if (field.startsWith("ancestor:") && typeof value === "string" && value)
    return <RecordChip hue={objectTypeHue(model, field.slice("ancestor:".length))}>{value}</RecordChip>;
  return <>{formatValue(value)}</>;
}

function TargetsCell({
  row,
  targetColumns,
  targetHue,
  workspaceKey,
  applicationKey,
  viewKey,
  config,
  changeSetId,
  onOpenTarget,
}: {
  row: MappingCoverageRow;
  targetColumns: string[];
  targetHue: Hue | undefined;
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  config: MappingGridViewDefinition["config"];
  changeSetId?: string;
  onOpenTarget: (target: MappingObjectSummary) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const inlineTargets = row.targets;
  const hasMore = row.targetCount > inlineTargets.length;

  if (row.state === "unmapped") return <span className="muted">—</span>;
  if (row.state === "mapped" && inlineTargets.length === 1)
    return <TargetDisplay target={inlineTargets[0]} hue={targetHue} columns={targetColumns} onOpen={onOpenTarget} />;
  return (
    <div className="mapping-targets-list">
      {(expanded ? inlineTargets : inlineTargets.slice(0, 3)).map((target) => (
        <TargetDisplay
          key={target.relationId}
          target={target}
          hue={targetHue}
          columns={targetColumns}
          onOpen={onOpenTarget}
        />
      ))}
      {expanded && hasMore && (
        <TargetContinuation
          workspaceKey={workspaceKey}
          applicationKey={applicationKey}
          viewKey={viewKey}
          config={config}
          changeSetId={changeSetId}
          sourceObjectId={row.source.id}
          mappingVersion={row.mappingVersion}
          nextCursor={row.targetsNextCursor}
          targetColumns={targetColumns}
          targetHue={targetHue}
          onOpenTarget={onOpenTarget}
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
  );
}

function MappingActionDialog({
  model,
  workspaceKey,
  applicationKey,
  viewKey,
  config,
  changeSetId,
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
  changeSetId?: string;
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
        changeSetId: changeSetId,
        search: debouncedSearch || undefined,
        ...selector,
        pageSize: 20,
      }),
    [workspaceKey, applicationKey, viewKey, targetTypeKey, changeSetId, debouncedSearch],
  );
  // A target created here is shown first until the list reads it; it has no place in the list yet.
  const unlisted = created && !candidates.items.some((item) => item.id === created.id) ? created : undefined;

  function candidateRow(candidate: MappingObjectSummary, index?: number, measure?: (element: Element | null) => void) {
    const details = [
      ...new Set(
        Object.values(candidate.fields)
          .filter((value) => value != null && value !== "" && value !== candidate.name)
          .map(String),
      ),
    ];
    return (
      <Candidate
        key={candidate.id}
        ref={measure}
        data-row-key={candidate.id}
        data-row-index={index}
        selected={selectedId === candidate.id}
        control={
          <input
            type="radio"
            name="mapping-target"
            value={candidate.id}
            checked={selectedId === candidate.id}
            onChange={() => setSelectedId(candidate.id)}
          />
        }
        type={objectTypeTile(model, candidate.objectTypeKey)}
        name={candidate.name}
        detail={details.length > 0 && details.join(" · ")}
      >
        {currentTargets.some((target) => target.object.id === candidate.id) && (
          <StatusPill tone="neutral" marker={false}>
            Current
          </StatusPill>
        )}
      </Candidate>
    );
  }

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
      if (isApiError(cause, "MAPPING_VERSION_CONFLICT")) {
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
              <>
                {currentTargets.map((target) => (
                  <RecordChip key={target.relationId} hue={objectTypeHue(model, targetType.key)}>
                    {target.object.name}
                  </RecordChip>
                ))}
                {targetCount > currentTargets.length && <span>and {targetCount - currentTargets.length} more</span>}
              </>
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
              {(drawn) => (
                <>
                  {unlisted && candidateRow(unlisted)}
                  <WindowSpacer as="div" edge="before" height={drawn.before} />
                  {drawn.rows.map(({ index, item, size }) =>
                    item === undefined ? (
                      <WindowPlaceholder
                        key={`placeholder-${index}`}
                        as="div"
                        index={index}
                        size={size}
                        className="candidate"
                      />
                    ) : (
                      candidateRow(item, index, drawn.measure)
                    ),
                  )}
                  <WindowSpacer as="div" edge="after" height={drawn.after} />
                  {candidates.loading && !candidates.items.length && <p className="candidate-state">Loading…</p>}
                  {!candidates.loading && !candidates.error && !unlisted && candidates.items.length === 0 && (
                    <p className="candidate-state">
                      No {targetType.pluralName.toLowerCase()} match{debouncedSearch ? ` “${debouncedSearch}”` : ""}.
                    </p>
                  )}
                </>
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

/** A mapped record: a chip in its type's colour (ADR-040), its display fields beside it. */
function TargetDisplay({
  target,
  hue,
  columns,
  onOpen,
}: {
  target: MappingTargetSummary;
  hue: Hue | undefined;
  columns: string[];
  onOpen: (target: MappingObjectSummary) => void;
}) {
  return (
    <div className="mapping-target-block">
      <div className="mapping-target">
        <RecordChip hue={hue} onOpen={() => onOpen(target.object)}>
          {target.object.name}
        </RecordChip>
        {columns.map((col) => (
          <span key={col} className="mapping-target-field mobile-secondary-column">
            {formatValue(target.object.fields[col])}
          </span>
        ))}
      </div>
      {target.origin && <AiOriginMark origin={target.origin} variant="target" />}
    </div>
  );
}

function TargetContinuation({
  workspaceKey,
  applicationKey,
  viewKey,
  config,
  changeSetId,
  sourceObjectId,
  mappingVersion,
  nextCursor,
  targetColumns,
  targetHue,
  onOpenTarget,
}: {
  workspaceKey: string;
  applicationKey: string;
  viewKey: string;
  config: MappingGridViewDefinition["config"];
  changeSetId?: string;
  sourceObjectId: string;
  mappingVersion: number;
  nextCursor: string | null;
  targetColumns: string[];
  targetHue: Hue | undefined;
  onOpenTarget: (target: MappingObjectSummary) => void;
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
        changeSetId: changeSetId,
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
  }, [
    api,
    workspaceKey,
    applicationKey,
    viewKey,
    config,
    changeSetId,
    sourceObjectId,
    mappingVersion,
    cursor,
    loading,
  ]);

  return (
    <>
      {targets.map((target) => (
        <TargetDisplay
          key={target.relationId}
          target={target}
          hue={targetHue}
          columns={targetColumns}
          onOpen={onOpenTarget}
        />
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
