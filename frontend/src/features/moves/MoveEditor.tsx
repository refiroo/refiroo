/**
 * The move editor (0.11 X4, the approved boards MoveEditor, MoveStart and PhoneMove): records of one
 * workspace copied or moved into a workspace whose model differs. The header names the two
 * workspaces and the mapping's version, with undo, redo and Start the move…; the band says what
 * moves and copy or move; the figures are the dry run of every item, run again after every step
 * (D140); then the source's types, the mapping by type (each row a step, marked Proposed while it is
 * as proposed, D141) and the reason pane with the target's types. The report lists what cannot move
 * (D143) and starts the move into a change set of the target (D144). At phone width the parts are
 * tabs (D147). Without background jobs or model administration the editor reads only (D146).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError, isVersionConflict } from "@/api/errors";
import { count, counted, plural } from "@/lib/count";
import { PHONE_WIDTH, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { attributeTypeFor, typeName } from "@/model/lookup";
import { workspaceModel } from "@/model/workspaceModels";
import { routePath } from "@/routing/routes";
import type {
  EngineModel,
  MappingOperation,
  MappingProblem,
  MappingProposal,
  ModelMapping,
  ModelMappingOperationEntry,
  MoveAddress,
  MoveRequest,
  RouteState,
  Workspace,
} from "@/types";
import { canRedo, historySteps, undoable } from "@/features/model-editor/history";
import { useCapabilities } from "@/state/useSystem";
import { Trail } from "@/ui/Trail";
import { Notice } from "@/ui/Notice";
import { ProposalNote } from "@/ui/ProposalNote";
import { RouteLink } from "@/ui/RouteLink";
import { Skeleton } from "@/ui/Skeleton";
import { StalePreviewDialog } from "@/ui/StalePreviewDialog";
import { Tabs } from "@/ui/Tabs";
import { MappingPane, rowId, type RowNote } from "./MappingPane";
import { MoveReport } from "./MoveReport";
import { MoveStatus } from "./MoveStatus";
import { SelectionDialog } from "./SelectionDialog";
import { StartMoveDialog } from "./StartMoveDialog";
import { alternativeText, evidenceText, mappingBlocks, unmappedTypes, type MappingBlock } from "./mappingRows";
import {
  difference,
  figuresOf,
  modeWords,
  type ModeWords,
  movesAnything,
  reasonCards,
  selectionFor,
  type Figures,
} from "@/model/moveRun";
import { moveAbility } from "@/lib/moveAbility";
import { useMoveDryRun } from "./useMoveDryRun";
import { allWorkspaces } from "@/api/allWorkspaces";

const MOVES: RouteState = { kind: "settings", page: "moves" };

/** The row a problem points at: `/types/{i}/…` within that type's block. */
function problemRow(mapping: ModelMapping, problem: MappingProblem): string | undefined {
  const found = /^\/types\/(\d+)(?:\/([^/]+)(?:\/([^/]+))?)?/.exec(problem.pointer);
  const entry = found ? mapping.types[Number(found[1])] : undefined;
  if (!found || !entry) return undefined;
  const [, , part, index] = found;
  if (part === "attributes" && index !== undefined)
    return rowId(entry.source, `attribute:${entry.attributes[Number(index)]?.source}`);
  if (part === "relations" && index !== undefined)
    return rowId(entry.source, `relation:${entry.relations[Number(index)]?.source}`);
  if (part === "defaults" && index !== undefined)
    return rowId(entry.source, `default:${index.replaceAll("~1", "/").replaceAll("~0", "~")}`);
  if (part === "parent" || part === "match") return rowId(entry.source, part);
  return rowId(entry.source, "type");
}

/** Whether the latest step can be undone, and an undo redone, by the history's rules (D32). */
function undoState(history: ModelMappingOperationEntry[]) {
  const steps = historySteps(history);
  return { canUndo: steps.some(undoable), canRedo: canRedo(steps) };
}

export function MoveEditor({
  address,
  onAddress,
  onNavigate,
  onOpenChangeSet,
}: {
  address: MoveAddress;
  /** A new address for the editor; `replace` keeps the browser's history to one entry. */
  onAddress: (next: MoveAddress, replace?: boolean) => void;
  onNavigate: (route: RouteState) => void;
  onOpenChangeSet: (workspaceKey: string, changeSetId: string) => void;
}) {
  const { mappingKey, from, to } = address;
  const phone = useMediaQuery(PHONE_WIDTH);
  const { capabilities } = useCapabilities();
  const ability = moveAbility(capabilities);
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  const [models, setModels] = useState<{ source: EngineModel; target: EngineModel }>();
  const [mapping, setMapping] = useState<ModelMapping>();
  const [proposals, setProposals] = useState<MappingProposal[]>([]);
  const [history, setHistory] = useState<ModelMappingOperationEntry[]>([]);
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [stepError, setStepError] = useState("");
  const [refused, setRefused] = useState<Record<string, string>>({});
  const [choosing, setChoosing] = useState(false);
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState("");
  const [stale, setStale] = useState<"mapping" | "release">();
  const [renameTo, setRenameTo] = useState<string>();
  // The name the start dialog gave the change set, which the status names.
  const [changeSetName, setChangeSetName] = useState<string>();
  const [tab, setTab] = useState("mapping");

  const fetchMapping = useCallback(async () => {
    const [next, found, steps] = await Promise.all([
      api.modelMapping(mappingKey, { source: from, target: to }),
      api.mappingProposals(mappingKey).catch((cause) => {
        if (isApiError(cause, "INFERENCE_NOT_FOUND")) return [] as MappingProposal[];
        throw cause;
      }),
      api.mappingHistory(mappingKey),
    ]);
    return { next, found, steps };
  }, [mappingKey, from, to]);
  const show = ({ next, found, steps }: Awaited<ReturnType<typeof fetchMapping>>) => {
    setMapping(next);
    setProposals(found);
    setHistory(steps);
    return next;
  };
  const readMapping = async () => show(await fetchMapping());

  useEffect(() => {
    let active = true;
    Promise.all([allWorkspaces({ status: "all" }), workspaceModel(from), workspaceModel(to), fetchMapping()])
      .then(([items, source, target, read]) => {
        if (!active) return;
        setWorkspaces(items);
        setModels({ source, target });
        setMapping(read.next);
        setProposals(read.found);
        setHistory(read.steps);
      })
      .catch((cause) => active && setLoadError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [from, to, fetchMapping]);

  const source = workspaces?.find((item) => item.key === from);
  const target = workspaces?.find((item) => item.key === to);
  const sourceLabel = source?.label ?? from;
  const targetLabel = target?.label ?? to;
  const mode = address.mode ?? "copy";
  // A copy is never called a move: every label follows the chosen operation.
  const w = modeWords(mode);
  const repointed =
    mapping && source && target
      ? mapping.sourceReleaseId !== source.model.releaseId || mapping.targetReleaseId !== target.model.releaseId
      : false;

  const request = useMemo<MoveRequest | undefined>(() => {
    if (!mapping || !models || !ability.canMove || mapping.problems.length) return undefined;
    return {
      sourceWorkspaceKey: from,
      targetWorkspaceKey: to,
      mapping: { key: mapping.key, expectedVersion: mapping.version },
      selection: selectionFor(mapping, address.selection, models.source),
      mode,
    };
  }, [mapping, models, ability.canMove, from, to, address.selection, mode]);

  const dryRun = useMoveDryRun(
    request,
    address.jobId,
    (jobId) => onAddress({ ...address, jobId }, true),
    (finished) => {
      // The change set takes the name the start dialog gave it, once the load has opened it.
      const name = renameTo;
      const changeSetId = finished.move?.targetChangeSetId;
      setRenameTo(undefined);
      if (!name || !changeSetId || finished.state !== "completed") return;
      void api
        .changeSet(changeSetId)
        .then((changeSet) => api.renameChangeSet(changeSetId, name, changeSet.version))
        .catch(() => undefined);
    },
  );
  const job = dryRun.job;
  const summary = job?.move ?? undefined;
  const waiting = job?.state === "awaiting_confirmation";

  const blocks = useMemo<MappingBlock[]>(
    () => (mapping && models ? mappingBlocks(mapping, models.source, models.target, proposals) : []),
    [mapping, models, proposals],
  );
  const selectedRow = address.row;
  const selectedProposal = useMemo(() => {
    for (const block of blocks)
      for (const row of block.rows) if (rowId(block.sourceType, row.key) === selectedRow) return row.proposal;
    return undefined;
  }, [blocks, selectedRow]);

  const notes = useMemo<RowNote>(() => {
    const reported: Record<string, string> = {};
    if (summary) {
      for (const item of summary.types) {
        const cannot = item.counts.refused + item.counts.notMoved;
        if (cannot) reported[rowId(item.sourceType, "type")] = `${count(cannot)} ${w.cannot.toLowerCase()}`;
      }
      for (const item of summary.attributesNotCarried) {
        const key = rowId(item.sourceType, `attribute:${item.attributeTypeKey}`);
        reported[key] = `${count(item.count)} ${plural(item.count, "value")} not carried`;
      }
      for (const block of blocks)
        for (const relation of summary.relationships) {
          const dropped = relation.counts.refused + relation.counts.notMoved;
          const key = rowId(block.sourceType, `relation:${relation.relationTypeKey}`);
          if (dropped && block.rows.some((row) => rowId(block.sourceType, row.key) === key))
            reported[key] = `${count(dropped)} dropped`;
        }
    }
    return { refused, reported };
  }, [summary, blocks, refused, w.cannot]);

  async function step(row: string | undefined, send: () => Promise<unknown>) {
    setBusy(true);
    setStepError("");
    try {
      await send();
      setRefused({});
      await readMapping();
    } catch (cause) {
      if (isApiError(cause, "INVALID_OPERATION") && row) {
        setRefused({ [row]: errorMessage(cause) });
      } else if (isVersionConflict(cause, ["VERSION_CONFLICT"])) {
        setStepError(
          "The mapping was changed in another session; it was read again. Make the change again if it is still needed.",
        );
        await readMapping().catch(() => undefined);
      } else if (isApiError(cause, "NOTHING_TO_UNDO") || isApiError(cause, "NOTHING_TO_REDO")) {
        await readMapping().catch(() => undefined);
      } else setStepError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }
  const run = (row: string | undefined, operations: MappingOperation[]) =>
    mapping && step(row, () => api.mappingOperations(mapping.key, mapping.version, operations));

  async function confirm(name: string) {
    if (!job) return;
    setBusy(true);
    setStartError("");
    try {
      const next = await api.confirmJob(job.id);
      setRenameTo(name);
      setChangeSetName(name || undefined);
      setStarting(false);
      dryRun.setJob(next);
    } catch (cause) {
      if (isApiError(cause, "MOVE_MAPPING_CHANGED")) {
        setStarting(false);
        setStale("mapping");
      } else if (isApiError(cause, "MODEL_RELEASE_CHANGED")) {
        setStarting(false);
        setStale("release");
      } else setStartError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  }

  async function runAgain() {
    setStale(undefined);
    const before = mapping?.version;
    const next = await readMapping().catch(() => undefined);
    // A new version starts its own dry run; a release changed under the same version needs a nudge.
    if (next && next.version === before) dryRun.rerun();
  }

  const select = (row: string) => {
    if (row !== address.row) onAddress({ ...address, row }, true);
  };
  // Stable for the mapping's rows, so a dry run's new figures redraw only the rows they change.
  const handlers = useRef({ select, run });
  useEffect(() => {
    handlers.current = { select, run };
  });
  const selectRow = useCallback((row: string) => handlers.current.select(row), []);
  const stepRow = useCallback(
    (row: string, operations: MappingOperation[]) => void handlers.current.run(row, operations),
    [],
  );
  const openReport = (start = false) => {
    onAddress({ ...address, view: "report" });
    if (start) {
      setStartError("");
      setStarting(true);
    }
  };

  if (loadError)
    return (
      <div className="move-editor">
        <Notice tone="error" title="The editor could not open" focusOnMount>
          {loadError}
        </Notice>
        <RouteLink href={routePath(MOVES)} onNavigate={() => onNavigate(MOVES)}>
          Back to Copy and move
        </RouteLink>
      </div>
    );
  if (!mapping || !models || !workspaces) return <Skeleton lines={6} label="Opening the editor" />;

  const { canUndo, canRedo: redoable } = undoState(history);
  const readOnly = !ability.canMap;
  const canStart = Boolean(waiting && summary && movesAnything(summary) && !dryRun.checking && ability.canMove);
  const startWhy = !ability.canMove
    ? ability.reason
    : mapping.problems.length
      ? "The mapping has problems to fix first."
      : dryRun.checking || !summary
        ? "Waiting for the dry run."
        : summary && !movesAnything(summary)
          ? "Nothing would be created or updated."
          : "";
  const figures = dryRun.figures;
  const previous = dryRun.previous;
  const unmapped = unmappedTypes(mapping, models.source);
  const report = address.view === "report";

  const header = (
    <header className="move-head">
      <Trail
        items={[
          {
            key: "moves",
            content: (
              <RouteLink href={routePath(MOVES)} onNavigate={() => onNavigate(MOVES)}>
                Copy and move
              </RouteLink>
            ),
          },
          report
            ? {
                key: "editor",
                content: (
                  <RouteLink
                    href={routePath({ kind: "settings", page: "moves", move: { ...address, view: undefined } })}
                    onNavigate={() => onAddress({ ...address, view: undefined })}
                  >
                    Mapping
                  </RouteLink>
                ),
              }
            : { key: "editor", content: "Mapping", current: true },
          ...(report ? [{ key: "report", content: w.whatCannot, current: true }] : []),
        ]}
      />
      <div className="move-head-row">
        <h1>
          {w.Verb} from {sourceLabel} to {targetLabel}
        </h1>
        <div className="move-head-actions">
          {!report && !readOnly && (
            <>
              <button
                type="button"
                className="secondary"
                disabled={busy || !canUndo}
                onClick={() => void step(undefined, () => api.undoMapping(mapping.key, mapping.version))}
              >
                Undo
              </button>
              <button
                type="button"
                className="secondary"
                disabled={busy || !redoable}
                onClick={() => void step(undefined, () => api.redoMapping(mapping.key, mapping.version))}
              >
                Redo
              </button>
            </>
          )}
          {!phone && ability.canMove && (
            <button
              type="button"
              className="primary"
              disabled={!canStart}
              title={startWhy || undefined}
              onClick={() => openReport(true)}
            >
              Start the {w.verb}…
            </button>
          )}
        </div>
      </div>
    </header>
  );

  const band = (
    <div className="move-band">
      <div className="move-side">
        <span className="muted">From</span>
        <span>
          <strong>{sourceLabel}</strong> · {source?.model.releaseName}{" "}
          <span className="mono">{source?.model.releaseVersion}</span> · live at the dry run
        </span>
      </div>
      <span className="move-band-arrow" aria-hidden="true">
        →
      </span>
      <div className="move-side">
        <span className="muted">To</span>
        <span>
          <strong>{targetLabel}</strong> · {target?.model.releaseName}{" "}
          <span className="mono">{target?.model.releaseVersion}</span> · a new change set
        </span>
      </div>
      <div className="move-side">
        <span className="muted">Mapping</span>
        <span className="move-head-mapping" title="The version rises with every step, undo and redo included">
          “{mapping.name}” · version {mapping.version}
        </span>
      </div>
      <div className="move-side move-what">
        <span className="muted">{w.what}</span>
        <span className="move-what-chips">
          <SelectionChips address={address} source={models.source} mappedCount={mapping.types.length} />
          {ability.canMove && (
            <button type="button" className="secondary move-chip-change" onClick={() => setChoosing(true)}>
              Change…
            </button>
          )}
        </span>
      </div>
      {ability.canMove && (
        <div role="radiogroup" aria-label="Copy or move" className="theme-choice move-mode">
          {(["copy", "move"] as const).map((value) => (
            <label key={value} className={mode === value ? "selected" : undefined}>
              <input
                type="radio"
                name="move-mode"
                checked={mode === value}
                onChange={() => onAddress({ ...address, mode: value === "move" ? "move" : undefined })}
              />
              {value === "copy" ? "Copy" : "Move"}
            </label>
          ))}
        </div>
      )}
    </div>
  );

  const figureBand = mapping.problems.length ? (
    <section className="move-figures-waiting" aria-label="Dry run of every item">
      <Notice tone="warning" title="The dry run waits for the mapping">
        <p>
          The mapping names what the releases the two workspaces run lack or do not allow. Fix each, then the dry run
          starts.
        </p>
        <ul className="move-problems">
          {mapping.problems.map((problem) => {
            const row = problemRow(mapping, problem);
            return (
              <li key={`${problem.pointer}:${problem.code}`}>
                {row ? (
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => onAddress({ ...address, row, view: undefined })}
                  >
                    {problem.message}
                  </button>
                ) : (
                  problem.message
                )}{" "}
                <span className="mono">{problem.code}</span>
              </li>
            );
          })}
        </ul>
      </Notice>
    </section>
  ) : (
    <FigureBand
      figures={figures}
      previous={previous}
      checking={dryRun.checking}
      phone={phone}
      readOnly={!ability.canMove}
      words={w}
      onCannot={() => openReport()}
    />
  );

  const notices = (
    <>
      {!ability.canMap && capabilities && (
        <Notice tone="info" title="This editor reads only">
          {ability.reason}
        </Notice>
      )}
      {repointed && (
        <Notice
          tone="warning"
          title="The mapping names other releases than the workspaces run"
          actions={
            !readOnly && (
              <button
                type="button"
                className="secondary"
                disabled={busy}
                onClick={() =>
                  void run(undefined, [
                    {
                      kind: "setReleases",
                      sourceReleaseId: source!.model.releaseId,
                      targetReleaseId: target!.model.releaseId,
                    },
                  ])
                }
              >
                Use the releases the workspaces run
              </button>
            )
          }
        >
          The dry run reads {sourceLabel} and {targetLabel} under the releases they run; what the mapping lacks is
          listed as its problems.
        </Notice>
      )}
      {stepError && (
        <Notice tone="error" focusOnMount>
          {stepError}
        </Notice>
      )}
      {dryRun.error && (
        <Notice
          tone="error"
          title="The dry run did not run"
          actions={
            <button type="button" className="secondary" onClick={dryRun.rerun}>
              Dry run again
            </button>
          }
        >
          {dryRun.error}
        </Notice>
      )}
    </>
  );

  const sourcePane = (
    <section className="move-source" aria-labelledby="move-source-h">
      <h2 id="move-source-h" className="move-pane-title">
        Source · {models.source.release.name}
      </h2>
      {models.source.objectTypes.map((type) => {
        const entry = mapping.types.find((item) => item.source === type.key);
        const counted = summary?.types.find((item) => item.sourceType === type.key);
        const chosen = request?.selection;
        const inSelection =
          !chosen || (!chosen.types && !chosen.parentObjectId) || Boolean(chosen.parentObjectId)
            ? true
            : chosen.types!.some((item) => item.objectTypeKey === type.key);
        const total = counted
          ? Object.values(counted.counts).reduce((sum, value) => sum + value, 0)
          : summary && inSelection
            ? 0
            : undefined;
        return (
          <div key={type.key} className="move-type-card">
            <span className="move-type-card-head">
              <strong>{type.pluralName}</strong>
              <span className="muted">{total === undefined ? "Not selected" : `${count(total)} selected`}</span>
            </span>
            <span className="muted move-type-card-fields">
              {type.attributes
                .map(
                  (binding) =>
                    attributeTypeFor(models.source, binding.attributeTypeKey)?.name ?? binding.attributeTypeKey,
                )
                .join(" · ") || "Name only"}
            </span>
            <span className={entry ? "move-type-state is-mapped" : "move-type-state"}>
              {entry ? `Mapped to ${typeName(models.target, entry.target, { plural: true })}` : "Not mapped"}
            </span>
          </div>
        );
      })}
    </section>
  );

  const targetList = (
    <div className="move-target">
      <h2 className="move-pane-title">Target · {models.target.release.name}</h2>
      <ul>
        {models.target.objectTypes.map((type) => {
          const fromTypes = mapping.types
            .filter((entry) => entry.target === type.key)
            .map((entry) => typeName(models.source, entry.source, { plural: true }));
          return (
            <li key={type.key}>
              <span>{type.pluralName}</span>
              <span className="muted">{fromTypes.length ? `from ${fromTypes.join(", ")}` : "untouched"}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );

  const reasonPane = (
    <aside className="move-reason" aria-label="Why this step">
      {selectedProposal ? (
        <ProposalNote
          subtitle="Change the row to make it yours"
          summary={selectedProposal.summary}
          evidence={selectedProposal.evidence.map(evidenceText)}
          alternatives={
            readOnly
              ? []
              : selectedProposal.alternatives.map((alternative) => ({
                  label: alternativeText(alternative, selectedProposal, models.source, models.target),
                  onSelect: () => void run(selectedRow, alternative.operations),
                }))
          }
          busy={busy}
        />
      ) : (
        <p className="muted move-reason-empty">
          {selectedRow
            ? "This row is yours: set by hand, or nothing proposed it. Undo brings back what was proposed."
            : "Select a row to see why it was proposed and its alternatives."}
        </p>
      )}
      {targetList}
    </aside>
  );

  const mappingPane = (
    <section className="move-centre" aria-labelledby="move-mapping-h">
      <h2 id="move-mapping-h" className={phone ? "visually-hidden" : "move-centre-title"}>
        Mapping
      </h2>
      {blocks.length === 0 && unmapped.length === 0 ? (
        <p className="muted">The source model has no types.</p>
      ) : (
        <MappingPane
          blocks={blocks}
          unmapped={unmapped}
          target={models.target}
          selected={selectedRow}
          notes={notes}
          busy={busy}
          readOnly={readOnly}
          onSelect={selectRow}
          onStep={stepRow}
        />
      )}
      {phone && selectedRow && reasonPane}
    </section>
  );

  const reportBody =
    job && summary ? (
      <MoveReport
        jobId={job.id}
        summary={summary}
        source={models.source}
        target={models.target}
        reason={address.reason}
        onReason={(reason) => onAddress({ ...address, reason }, true)}
        onFix={(row) => onAddress({ ...address, view: undefined, row })}
      />
    ) : (
      <Skeleton lines={4} label="Waiting for the dry run" />
    );

  return (
    <div className={`move-editor${phone ? " is-phone" : ""}`}>
      {header}
      <div className="move-notices" aria-live="polite">
        {notices}
        {!mapping.problems.length && ability.canMove && (
          <MoveStatus
            job={job}
            checking={dryRun.checking}
            mode={mode}
            what={selectionWords(address, models.source, mapping.types.length)}
            sourceLabel={sourceLabel}
            targetLabel={targetLabel}
            mappingVersion={mapping.version}
            changeSetName={changeSetName}
            onOpenTarget={(id) => onOpenChangeSet(to, id)}
            onOpenSource={(id) => onOpenChangeSet(from, id)}
            onReport={() => openReport()}
          />
        )}
      </div>
      {band}
      {figureBand}
      {report ? (
        <section className="move-report-page" aria-labelledby="move-report-h">
          <h2 id="move-report-h" className="move-centre-title">
            {w.whatCannot}
          </h2>
          <p className="muted">
            {job?.confirmedAt
              ? `What the ${w.verb} loaded, mapping version ${summary?.mapping.version ?? mapping.version}: the items below were not ${w.past}, or were ${w.past} without a value.`
              : `Dry run of every item, mapping version ${summary?.mapping.version ?? mapping.version}: ${
                  summary
                    ? `${count(figuresOf(summary).create + figuresOf(summary).update)} records are created or updated in ${targetLabel}; the items below cannot be ${w.past}, or are ${w.past} without a value.`
                    : "running."
                } Nothing has changed in either workspace.`}
          </p>
          {reportBody}
        </section>
      ) : phone ? (
        <Tabs
          label={`${w.Verb} editor`}
          selected={tab}
          onChange={setTab}
          tabs={[
            { id: "mapping", label: "Mapping", content: mappingPane },
            { id: "source", label: "Source", content: sourcePane },
            { id: "target", label: "Target", content: targetList },
            {
              id: "report",
              label: `Not ${w.past}`,
              content:
                summary && reasonCards(summary).length ? (
                  <ul className="move-phone-reasons">
                    {reasonCards(summary).map((card) => (
                      <li key={card.code}>
                        <button
                          type="button"
                          className="link-button"
                          onClick={() => onAddress({ ...address, view: "report", reason: card.code })}
                        >
                          {count(card.count)} · {card.label}
                        </button>
                        <span className="muted">{card.fix}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">{summary ? "Everything selected moves." : "Waiting for the dry run."}</p>
                ),
            },
          ]}
        />
      ) : (
        <div className="move-panes">
          {sourcePane}
          {mappingPane}
          {reasonPane}
        </div>
      )}
      {phone && ability.canMove && (
        <div className="move-phone-start">
          <button type="button" className="primary" disabled={!canStart} onClick={() => openReport(true)}>
            Start the {w.verb}…
          </button>
          {startWhy && <small className="muted">{startWhy}</small>}
        </div>
      )}
      {choosing && (
        <SelectionDialog
          mode={mode}
          source={models.source}
          sourceWorkspaceKey={from}
          mapped={mapping.types.map((entry) => entry.source)}
          chosen={address.selection}
          onClose={() => setChoosing(false)}
          onChoose={(selection) => {
            setChoosing(false);
            onAddress({ ...address, selection });
          }}
        />
      )}
      {starting && report && summary && (
        <StartMoveDialog
          summary={summary}
          sourceLabel={sourceLabel}
          targetLabel={targetLabel}
          busy={busy}
          error={startError}
          onClose={() => setStarting(false)}
          onConfirm={(name) => void confirm(name)}
        />
      )}
      {stale && (
        <StalePreviewDialog
          title={
            stale === "mapping"
              ? "The mapping changed after this dry run"
              : "A workspace's release changed after this dry run"
          }
          reason={
            stale === "mapping"
              ? `The mapping was changed, here or in another session, after the dry run you reviewed (version ${summary?.mapping.version ?? mapping.version}).`
              : `${sourceLabel} or ${targetLabel} runs another release than at the dry run you reviewed.`
          }
          past={w.past}
          next="Run the dry run again and review its figures before starting."
          confirmLabel="Dry run again"
          secondary={{
            label: "Open the mapping",
            onClick: () => {
              setStale(undefined);
              onAddress({ ...address, view: undefined });
            },
          }}
          dismissable={false}
          onCancel={() => setStale(undefined)}
          onConfirm={() => void runAgain()}
        />
      )}
    </div>
  );
}

function FigureBand({
  figures,
  previous,
  checking,
  phone,
  readOnly,
  words,
  onCannot,
}: {
  words: ModeWords;
  figures?: Figures;
  previous?: Figures;
  checking: boolean;
  phone: boolean;
  readOnly: boolean;
  onCannot: () => void;
}) {
  if (readOnly) return null;
  const items: { key: keyof Figures; label: string; warn?: boolean; link?: boolean }[] = [
    { key: "create", label: "Create" },
    { key: "update", label: `Update (${words.past} before or found)` },
    { key: "cannot", label: words.cannot, warn: true, link: true },
    ...(phone
      ? []
      : ([
          { key: "carried", label: "Relationships carried" },
          { key: "dropped", label: "Relationships dropped", warn: true, link: true },
        ] as const)),
  ];
  return (
    <section className="move-figures" aria-label="Dry run of every item" aria-busy={checking}>
      {items.map((item) => {
        const value = figures?.[item.key];
        const text = value === undefined ? "…" : count(value);
        const change = value === undefined ? "" : difference(value, previous?.[item.key]);
        return (
          <div key={item.key} className="move-figure">
            <span className="muted">{item.label}</span>
            <span className="move-figure-value">
              {item.link && value ? (
                <button
                  type="button"
                  className={`link-button move-figure-number${item.warn ? " is-warning" : ""}`}
                  onClick={onCannot}
                  aria-label={`${text} ${item.label.toLowerCase()}: ${words.whatCannot.toLowerCase()}`}
                >
                  {text}
                </button>
              ) : (
                <span className={`move-figure-number${item.warn && value ? " is-warning" : ""}`}>{text}</span>
              )}
              {change && <small className="muted">{change}</small>}
            </span>
          </div>
        );
      })}
    </section>
  );
}

/** What moves, in words: the chips' text, and the status's (every mapped type by default). */
function selectionWords(address: MoveAddress, source: EngineModel, mappedCount: number): string {
  return selectionChips(address, source, mappedCount)
    .map((chip) => chip.charAt(0).toLowerCase() + chip.slice(1))
    .join(", ");
}

function selectionChips(address: MoveAddress, source: EngineModel, mappedCount: number): string[] {
  const choice = address.selection;
  return choice?.kind === "all"
    ? ["The whole workspace"]
    : choice?.kind === "subtree"
      ? [`${choice.name ?? "A record"} and everything under it`]
      : choice?.kind === "types"
        ? choice.types.map(
            (item) =>
              `${typeName(source, item.objectTypeKey, { plural: true })}${item.filters.length ? ` (${counted(item.filters.length, "filter")})` : ""}`,
          )
        : [mappedCount ? `Every mapped type (${mappedCount})` : "The whole workspace"];
}

/** What moves, as chips: the default names the mapped types; a choice names itself. */
function SelectionChips({
  address,
  source,
  mappedCount,
}: {
  address: MoveAddress;
  source: EngineModel;
  mappedCount: number;
}) {
  const chips = selectionChips(address, source, mappedCount);
  return (
    <>
      {chips.map((chip) => (
        <span key={chip} className="move-chip">
          {chip}
        </span>
      ))}
    </>
  );
}
