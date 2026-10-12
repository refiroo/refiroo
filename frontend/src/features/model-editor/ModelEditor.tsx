/**
 * The model editor on a draft (0.10 A4a; MODEL_AUTHORING "The editor"): the model pane, the selected
 * element or the relationship matrix, and the issues and history, under a bar with undo, redo, the
 * JSON workbench and install and activate. Opened from Settings › Model (D7), full width in the
 * shared frame (D37). Below 760px the panes are tabs. The left pane has two tabs, Model and Consumer
 * APIs (0.10 A4c, D59); a selected consumer API opens in the centre (`ConsumerApis`).
 *
 * Every change is an operation step on the server at the draft's version (A2). The editor reads the
 * draft back as its outline after each step (D36), so the browser never works out the model's rules.
 * A step refused because another editor moved the draft on is held, and the editor asks whether to
 * apply it again on the newer version (D41).
 *
 * With a workbook (0.10 A5b, D84), a source pane stands left of the model pane: a selected column
 * shows its mapping in the centre, Map to… and drops onto the model pane map it, the drawer's Dry
 * run tab follows each step, and Load into a change set installs, activates and loads (D81).
 */

import { useCallback, useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type {
  DraftOperation,
  EditorMode,
  EditorSelection,
  EngineModel,
  ModelDraftOperationEntry,
  ModelDraftOutline,
  ModelDraftStep,
  RouteState,
} from "@/types";
import { AddWorkbookDialog } from "@/features/model-editor/AddWorkbookDialog";
import { ColumnPanel } from "@/features/model-editor/ColumnPanel";
import { DryRunPanel, DryRunRowsDialog, dryRunLabel, type DryRunRows } from "@/features/model-editor/DryRunPanel";
import { LoadDialog } from "@/features/model-editor/LoadDialog";
import { MapColumnDialog, type MapStart } from "@/features/model-editor/MapColumnDialog";
import { columnsOfType, dropChoice, typesFed, usesOf, type ColumnUse } from "@/features/model-editor/mapping";
import { DRAG_COLUMN, SourcePane } from "@/features/model-editor/SourcePane";
import { useDraftSource } from "@/features/model-editor/useDraftSource";
import { ValueMapDialog } from "@/features/model-editor/ValueMapDialog";
import { useCursorFeed } from "@/lib/hooks/useCursorFeed";
import { readLocalPreference, useLocalNumberPreference, writeLocalPreference } from "@/lib/localPreference";
import { PageHeader } from "@/ui/PageHeader";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { Facts } from "@/features/model-editor/Facts";
import { PHONE_WIDTH, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { routePath } from "@/routing/routes";
import { ActionMenu } from "@/ui/ActionMenu";
import { ConfirmDialog } from "@/ui/ConfirmDialog";
import { Icon } from "@/ui/Icon";
import { IconButton } from "@/ui/IconButton";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import { Tabs } from "@/ui/Tabs";
import { useToast } from "@/ui/Toast";
import { ElementPanel } from "@/features/model-editor/ElementPanel";
import { canRedo, describeOperation, followKeyChange, historySteps, undoable } from "@/features/model-editor/history";
import { InstallDialog } from "@/features/model-editor/InstallDialog";
import { IssuesAndHistory } from "@/features/model-editor/IssuesAndHistory";
import { droppedColumn, ModelPane, type PaneDrop } from "@/features/model-editor/ModelPane";
import { MoveToDialog, type MoveSubject } from "@/features/model-editor/MoveToDialog";
import { OperationDialog, refusalText, type StepOutcome } from "@/features/model-editor/OperationDialog";
import { type FieldValues, type OperationSpec, type OperationTarget } from "@/features/model-editor/operations";
import {
  applicationOf,
  attributeTypeOf,
  consumerApiOf,
  nameOf,
  relationTypeOf,
  typeName,
} from "@/features/model-editor/outline";
import { ConsumerApiPane, ConsumerApiPanel } from "@/features/model-editor/ConsumerApis";
import { RelationshipMatrix } from "@/features/model-editor/RelationshipMatrix";
import { OperationsMenu } from "@/features/model-editor/OperationsMenu";
import { TypePreview } from "@/features/model-editor/TypePreview";

type Send = (version: number) => Promise<ModelDraftStep>;

/** Whether the reader left the issues and history pane open, remembered in this browser. */
const BOTTOM_KEY = "rdm:model-editor:issues-history-open:v1";

type Dialog =
  | { kind: "operation"; operation: OperationSpec; target: OperationTarget; preset?: FieldValues }
  | { kind: "move"; subject: MoveSubject; target?: string }
  | { kind: "install" }
  | { kind: "dependants"; steps: number[]; dependants: number[] }
  | { kind: "map"; start: MapStart }
  | { kind: "valueMap"; use: ColumnUse; header: string }
  | { kind: "rows"; rows: DryRunRows }
  | { kind: "load" }
  | { kind: "workbook" };

/** A step refused because the draft moved on (D41): what came first, and how to send mine again. */
type Stale = { since: ModelDraftOperationEntry[]; more: boolean; send: Send };

export function ModelEditor({
  draftId,
  selection,
  onSelect,
  onNavigate,
  onActivated,
  onOpenApplication,
  onOpenChangeSet,
  activeModel,
  workspaceKey,
}: {
  draftId: string;
  selection: EditorSelection;
  onSelect: (selection: EditorSelection) => void;
  onNavigate: (route: RouteState) => void;
  /** Reloads the active model after an activation. */
  onActivated: () => Promise<unknown>;
  onOpenApplication: (applicationKey: string) => void;
  /** After a load (0.10 A5b): the change set's review, in the application the profile loads. */
  onOpenChangeSet: (target: { applicationKey: string; workspaceKey: string; changeSetId: string }) => void;
  /** The running model: the preview reads its records through it (0.10 A4b, D44). */
  activeModel: EngineModel;
  /** The workspace the preview reads records from first. */
  workspaceKey: string;
}) {
  const toast = useToast();
  const phone = useMediaQuery(PHONE_WIDTH);
  const [outline, setOutline] = useState<ModelDraftOutline>();
  const [name, setName] = useState("");
  // Whether the draft names a base release of its own; without one, the active release stands in (D17).
  const [ownBase, setOwnBase] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [dialog, setDialog] = useState<Dialog>();
  const [stale, setStale] = useState<Stale>();
  const [notice, setNotice] = useState<{ tone: "error" | "success"; text: string; applications?: string[] }>();
  const [busy, setBusy] = useState(false);
  const [bottomTab, setBottomTab] = useState("issues");
  const [elementTab, setElementTab] = useState("attributes");
  const [phoneTab, setPhoneTab] = useState(selection.show ? "element" : "model");
  // The left pane's tab (0.10 A4c, D59): it follows a selected consumer API, and stays where the reader put it.
  const [paneTab, setPaneTab] = useState(selection.show === "consumerApi" ? "apis" : "model");
  const [menuOpen, setMenuOpen] = useState(false);
  const version = useRef(0);
  // The selection a step's answer is compared with: a changed key of the selected element follows.
  const selected = useRef(selection);
  useEffect(() => {
    selected.current = selection;
  });
  const paneWidth = useLocalNumberPreference("rdm:model-editor:pane-width:v1", 300, 220, 560);
  const sourceWidth = useLocalNumberPreference("rdm:model-editor:source-width:v1", 320, 240, 560);
  const source = useDraftSource(draftId, outline?.version);
  const { dryRunQueued } = source;

  const [bottomOpen, setBottomOpen] = useState(() =>
    readLocalPreference(BOTTOM_KEY, false, (value): value is boolean => typeof value === "boolean"),
  );
  const toggleBottom = (open: boolean) => {
    setBottomOpen(open);
    writeLocalPreference(BOTTOM_KEY, open);
  };

  const load = useCallback(async () => {
    const next = await api.modelDraftOutline(draftId);
    version.current = next.version;
    setOutline(next);
    return next;
  }, [draftId]);

  // The editor is keyed by its draft, so a load starts from a clean state.
  useEffect(() => {
    let cancelled = false;
    Promise.all([api.modelDraftOutline(draftId), api.modelDraft(draftId)])
      .then(([next, draft]) => {
        if (cancelled) return;
        version.current = next.version;
        setOutline(next);
        setName(draft.name);
        setOwnBase(draft.baseReleaseId !== null);
      })
      .catch((cause) => {
        if (!cancelled) setLoadError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [draftId]);

  const history = useCursorFeed(
    async (cursor) => {
      const page = await api.modelDraftOperations(draftId, { cursor });
      // Read from the end: each page is oldest first, and its previous cursor reaches older steps.
      return { items: [...page.items].reverse(), nextCursor: page.prevCursor };
    },
    [draftId, outline?.version ?? 0],
    (previous, incoming) => {
      const seen = new Set(previous.map((item) => item.sequence));
      return [...previous, ...incoming.filter((item) => !seen.has(item.sequence))];
    },
  );
  const steps = historySteps(history.items);

  /** Sends a step at the draft's version; a stale version holds it and asks (D41). */
  const step = useCallback(
    async (send: Send): Promise<StepOutcome> => {
      setNotice(undefined);
      try {
        const answer = await send(version.current);
        if (answer.dryRun) dryRunQueued(answer.dryRun.jobId);
        const followed = followKeyChange(selected.current, answer.entries);
        if (followed) onSelect(followed);
      } catch (cause) {
        if (!isApiError(cause, "VERSION_CONFLICT")) throw cause;
        const details = (cause.details ?? {}) as { operations?: ModelDraftOperationEntry[]; more?: boolean };
        setStale({ since: details.operations ?? [], more: Boolean(details.more), send });
        await load();
        return "stale";
      }
      setStale(undefined);
      await load();
      return "applied";
    },
    [load, dryRunQueued, onSelect],
  );
  const run = useCallback(
    (operations: DraftOperation[]) => step((at) => api.applyModelDraftOperations(draftId, at, operations)),
    [draftId, step],
  );

  async function guarded(action: () => Promise<unknown>) {
    setBusy(true);
    try {
      await action();
    } catch (cause) {
      if (isApiError(cause, "OPERATION_HAS_DEPENDANTS")) {
        const details = (cause.details ?? {}) as { steps?: number[]; dependants?: number[] };
        setDialog({ kind: "dependants", steps: details.steps ?? [], dependants: details.dependants ?? [] });
      } else if (outline) setNotice({ tone: "error", text: refusalText(cause, outline) });
    } finally {
      setBusy(false);
    }
  }
  const undo = (steps?: number[]) =>
    guarded(async () => {
      await step((at) => api.undoModelDraftStep(draftId, at, steps));
      setBottomTab("history");
    });
  const redo = () =>
    guarded(async () => {
      await step((at) => api.redoModelDraftStep(draftId, at));
      setBottomTab("history");
    });

  function operate(operation: OperationSpec, target: OperationTarget, preset?: FieldValues) {
    setMenuOpen(false);
    if (!outline) return;
    if (operation.move === "attribute" && target.on === "attribute")
      setDialog({
        kind: "move",
        subject: { kind: "attribute", objectType: target.objectType, attributeType: target.attributeType },
      });
    else if (operation.move === "objectType" && target.on === "objectType")
      setDialog({ kind: "move", subject: { kind: "objectType", objectType: target.objectType } });
    else if (operation.direct) void guarded(() => run(operation.build({}, target as never, outline)));
    else setDialog({ kind: "operation", operation, target, preset });
  }

  function select(next: EditorSelection) {
    onSelect(next);
    if (next.show) setPaneTab(next.show === "consumerApi" ? "apis" : "model");
    if (phone) setPhoneTab("element");
  }

  function drop(item: PaneDrop) {
    if (item.kind === "column") {
      mapColumn(item.sheet, item.header, item.target);
      return;
    }
    setDialog(
      item.kind === "attribute"
        ? {
            kind: "move",
            subject: { kind: "attribute", objectType: item.objectType, attributeType: item.attributeType },
            target: item.target,
          }
        : { kind: "move", subject: { kind: "objectType", objectType: item.objectType }, target: item.target },
    );
  }

  /** Map to… a column, its target chosen when it was dropped on a type (D76). */
  function mapColumn(sheet: string, header: string, target?: string) {
    if (!outline) return;
    const profile = source.profile?.profile;
    const used = usesOf(profile, sheet, header).find((use) => !use.binding.ignore);
    setDialog({
      kind: "map",
      start: target
        ? { sheet, header, ...dropChoice(profile, outline, sheet, target) }
        : { sheet, header, rowType: used?.source.objectTypeKey },
    });
  }

  if (loadError)
    return (
      <div className="model-editor-state">
        <InlineError message={loadError} onRetry={() => window.location.reload()} />
      </div>
    );
  if (!outline)
    return (
      <div className="model-editor-state">
        <Skeleton lines={6} label="Loading the draft" />
      </div>
    );

  const names = nameOf(outline);
  const errors = outline.diagnostics.filter((item) => item.severity === "error").length;
  const warnings = outline.diagnostics.length - errors;
  const undoAvailable = steps.some(undoable);
  const redoAvailable = canRedo(steps);
  const base = outline.baseRelease;
  const workbench: RouteState = { kind: "settings", page: "model", draftId };
  const workbookLabel = source.profile?.sourceFile ? "Upload a newer workbook…" : "Add a workbook…";
  const addTarget: OperationTarget = paneTab === "apis" ? { on: "consumerApis" } : { on: "draft" };
  const selectedName =
    selection.show === "type"
      ? typeName(outline, selection.key)
      : selection.show === "application"
        ? (applicationOf(outline, selection.key)?.name ?? selection.key)
        : selection.show === "relationType"
          ? (relationTypeOf(outline, selection.key)?.name ?? selection.key)
          : selection.show === "attributeType"
            ? (attributeTypeOf(outline, selection.key)?.name ?? selection.key)
            : selection.show === "consumerApi"
              ? (consumerApiOf(outline, selection.key)?.name ?? selection.key)
              : selection.show === "column"
                ? selection.key
                : selection.show === "matrix"
                  ? "Matrix"
                  : "Selection";

  const hasSource = Boolean(source.profile?.sourceFile);
  const draftProfile = source.profile?.profile;
  // The types the selected column feeds, and the columns feeding the selected type.
  const linkedTypes = new Set(
    selection.show === "column"
      ? usesOf(draftProfile, selection.sheet, selection.key).flatMap((use) => typesFed(use))
      : [],
  );
  const linkedColumns = selection.show === "type" ? columnsOfType(draftProfile, selection.key) : new Set<string>();
  const sheetLoads = (sheet: string) => {
    const loads = (draftProfile?.sources ?? []).filter((item) => item.sheet === sheet);
    if (!loads.length) return "Not loaded yet: map a column to start";
    return `Loads ${loads
      .map((item) => {
        const key = item.key?.attributeTypeKey
          ? attributeTypeOf(outline, item.key.attributeTypeKey)?.name
          : item.key?.column;
        return `${typeName(outline, item.objectTypeKey)}${key ? ` (key ${key})` : ""}`;
      })
      .join(", ")}`;
  };
  const sourcePane = hasSource && (
    <SourcePane
      source={source}
      selection={selection}
      linked={linkedColumns}
      canDrag={!phone}
      sheetNames={sheetLoads}
      onSelect={select}
      onMap={(sheet, header) => mapColumn(sheet, header)}
      onIgnoreSheet={(sheet) => void guarded(() => run([{ kind: "ignoreSheet", sheet }]))}
    />
  );
  const onPaneMenu = (next: EditorSelection) => {
    select(next);
    setMenuOpen(true);
  };
  const pane = (
    <section
      className="model-editor-model"
      aria-label="Model and consumer APIs"
      onDragOver={(event) => {
        if (event.dataTransfer.types.includes(DRAG_COLUMN)) event.preventDefault();
      }}
      onDrop={(event) => {
        const column = droppedColumn(event);
        if (!column) return;
        event.preventDefault();
        mapColumn(column.sheet, column.header);
      }}
    >
      <Tabs
        label="Edit"
        selected={paneTab}
        onChange={setPaneTab}
        header={
          <div className="model-editor-pane-add">
            <OperationsMenu
              label={paneTab === "apis" ? "Add a consumer API" : "Add to the model"}
              icon="plus"
              tooltip="Add"
              target={addTarget}
              outline={outline}
              onOperation={operate}
            />
          </div>
        }
        tabs={[
          {
            id: "model",
            label: "Model",
            content: (
              <>
                {outline.applications.length === 0 && (
                  <p className="muted model-editor-empty">The draft is empty. Add an application to start.</p>
                )}
                <ModelPane
                  outline={outline}
                  selection={selection}
                  linked={linkedTypes}
                  canDrag={!phone}
                  onSelect={select}
                  onMenu={onPaneMenu}
                  onDrop={drop}
                />
              </>
            ),
          },
          {
            id: "apis",
            label: "Consumer APIs",
            content: <ConsumerApiPane outline={outline} selection={selection} onSelect={select} onMenu={onPaneMenu} />,
          },
        ]}
      />
    </section>
  );
  /** The selected type's preview or its layout editor (0.10 A4b), marked by a band of their own. */
  const typeKey = selection.show === "type" ? selection.key : undefined;
  const mode = selection.show === "type" ? selection.mode : undefined;
  const showType = (next?: EditorMode) =>
    typeKey && onSelect({ show: "type", key: typeKey, ...(next ? { mode: next } : {}) });
  const typePreview = (shown: EditorMode, actions: ReactNode) =>
    typeKey && (
      <TypePreview
        mode={shown}
        draftId={draftId}
        version={outline.version}
        objectTypeKey={typeKey}
        activeModel={activeModel}
        workspaceKey={workspaceKey}
        send={(operations) => guarded(() => run(operations))}
        onDialog={(operation, objectType) =>
          setDialog({ kind: "operation", operation, target: { on: "objectType", objectType } })
        }
        onShowIssues={() => {
          if (shown === "layout") showType();
          setBottomTab("issues");
          if (phone) setPhoneTab("issues");
          else toggleBottom(true);
        }}
        actions={actions}
      />
    );
  const centre = (
    <section
      className="model-editor-centre"
      aria-label={
        selection.show === "matrix"
          ? "Relationship matrix"
          : selection.show === "consumerApi"
            ? "Selected consumer API"
            : selection.show === "column"
              ? "Selected column"
              : "Selected element"
      }
    >
      {selection.show === "column" ? (
        <ColumnPanel
          key={`${selection.sheet}:${selection.key}`}
          sheet={selection.sheet}
          header={selection.key}
          source={source}
          outline={outline}
          busy={busy}
          run={(operations) => void guarded(() => run(operations))}
          onMap={() => mapColumn(selection.sheet, selection.key)}
          onValueMap={(use) => setDialog({ kind: "valueMap", use, header: selection.key })}
          onRows={(rows) => setDialog({ kind: "rows", rows })}
        />
      ) : mode === "preview" ? (
        typePreview(
          "preview",
          <>
            <button type="button" className="primary" onClick={() => showType("layout")}>
              <Icon name="pencil" /> Edit layout
            </button>
            <button type="button" className="secondary" onClick={() => showType()}>
              <Icon name="arrow-left" /> Back to definition
            </button>
          </>,
        )
      ) : selection.show === "consumerApi" ? (
        <ConsumerApiPanel
          key={selection.key}
          draftId={draftId}
          outline={outline}
          selection={selection}
          onSelect={select}
          menuOpen={menuOpen}
          onMenuOpenChange={setMenuOpen}
          onOperation={operate}
          run={run}
        />
      ) : selection.show === "matrix" ? (
        <>
          <header className="element-header">
            <div className="element-title">
              <h2 id="element-title">Relationship matrix</h2>
              <p className="muted">Which relation types may join which types · rows are the “from” end</p>
            </div>
          </header>
          <RelationshipMatrix outline={outline} onOperation={operate} />
        </>
      ) : (
        <ElementPanel
          outline={outline}
          selection={selection}
          tab={elementTab}
          onTab={setElementTab}
          menuOpen={menuOpen}
          onMenuOpenChange={setMenuOpen}
          canDrag={!phone}
          onOperation={operate}
          onSelect={select}
          run={run}
          onPreview={() => showType("preview")}
        />
      )}
    </section>
  );
  const issuesAndHistory = (
    <IssuesAndHistory
      outline={outline}
      tab={bottomTab}
      onTab={setBottomTab}
      history={history}
      onSelect={select}
      onUndoStep={(value) => void undo([value])}
      profile={source.profile}
      dryRun={
        hasSource
          ? {
              label: `Dry run · ${dryRunLabel(source.dryRun)}`,
              content: (
                <DryRunPanel
                  dryRun={source.dryRun}
                  error={source.dryRunError}
                  onRetry={source.retry}
                  outline={outline}
                  onRows={(rows) => setDialog({ kind: "rows", rows })}
                />
              ),
            }
          : undefined
      }
    />
  );
  const issueCount = outline.diagnostics.length + (draftProfile ? (source.profile?.diagnostics.length ?? 0) : 0);
  const drawerName = hasSource ? "Issues, history and dry run" : "Issues and history";
  // On a desktop the pane is a drawer at the bottom, closed until the reader opens it; nothing else
  // opens or closes it (the user, 2026-10-11). On a phone it is the Issues tab.
  const bottom = phone ? (
    <section className="model-editor-bottom" aria-label={drawerName}>
      {issuesAndHistory}
    </section>
  ) : (
    <section className={`model-editor-bottom${bottomOpen ? " open" : ""}`} aria-label={drawerName}>
      <button
        type="button"
        className="model-editor-bottom-toggle"
        aria-expanded={bottomOpen}
        aria-controls="model-editor-issues-history"
        onClick={() => toggleBottom(!bottomOpen)}
      >
        <Icon name={bottomOpen ? "chevron-down" : "chevron-right"} size={14} />
        <span>{drawerName}</span>
        <StatusPill tone={errors ? "error" : issueCount ? "warning" : "success"}>
          {issueCount ? `${issueCount} ${issueCount === 1 ? "issue" : "issues"}` : "No issues"}
        </StatusPill>
        <span className="muted">{steps.length ? `${steps.length} steps` : "No steps yet"}</span>
        {hasSource && <span className="muted">Dry run: {dryRunLabel(source.dryRun)}</span>}
      </button>
      <div id="model-editor-issues-history" className="model-editor-bottom-body" hidden={!bottomOpen}>
        {bottomOpen && issuesAndHistory}
      </div>
    </section>
  );

  return (
    <div className={`model-editor${mode === "layout" ? " model-editor-layout" : ""}`}>
      {mode !== "layout" && (
        <PageHeader
          className="model-editor-bar"
          variant="detail"
          icon={<Icon name="model" size={20} />}
          eyebrow={
            <RouteLink
              className="model-editor-crumb"
              href={routePath({ kind: "settings", page: "model" })}
              onNavigate={() => onNavigate({ kind: "settings", page: "model" })}
            >
              Settings › Model
            </RouteLink>
          }
          title={name || "Model draft"}
          description={
            <Facts
              label="About this draft"
              facts={[
                base && ownBase
                  ? {
                      icon: "model",
                      label: (
                        <>
                          Draft of <strong>{[base.key, base.version].filter(Boolean).join(" ")}</strong>
                        </>
                      ),
                    }
                  : { icon: "model", label: "A new model" },
                {
                  icon: "state-history",
                  label: (
                    <>
                      Version <strong>{outline.version}</strong>
                    </>
                  ),
                  title: "The draft's version: one more with every step",
                },
                { icon: "check", label: "Saved after every step" },
                ...(source.profile?.sourceFile
                  ? [
                      {
                        icon: "document" as const,
                        label: (
                          <>
                            Workbook <strong>{source.profile.sourceFile.name}</strong>
                          </>
                        ),
                      },
                    ]
                  : []),
                {
                  icon: errors ? "state-conflict" : "check",
                  label: errors
                    ? `${errors} ${errors === 1 ? "error" : "errors"}`
                    : warnings
                      ? `${warnings} warnings`
                      : "Valid",
                },
              ]}
            />
          }
          actions={
            <div className="model-editor-actions">
              {phone ? (
                <>
                  <IconButton
                    icon="undo"
                    label="Undo the last step"
                    disabled={busy || !undoAvailable}
                    onClick={() => void undo()}
                  />
                  <IconButton icon="redo" label="Redo" disabled={busy || !redoAvailable} onClick={() => void redo()} />
                  <ActionMenu
                    label="More: Open as JSON, Install and activate, Load, Add a workbook"
                    items={[
                      { id: "json", label: "Open as JSON", onAction: () => onNavigate(workbench) },
                      { id: "install", label: "Install and activate…", onAction: () => setDialog({ kind: "install" }) },
                      ...(hasSource
                        ? [
                            {
                              id: "load",
                              label: "Load into a change set…",
                              onAction: () => setDialog({ kind: "load" }),
                            },
                          ]
                        : []),
                      { id: "workbook", label: workbookLabel, onAction: () => setDialog({ kind: "workbook" }) },
                    ]}
                  />
                </>
              ) : (
                <>
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy || !undoAvailable}
                    onClick={() => void undo()}
                  >
                    <Icon name="undo" /> Undo
                  </button>
                  <button
                    type="button"
                    className="secondary"
                    disabled={busy || !redoAvailable}
                    onClick={() => void redo()}
                  >
                    <Icon name="redo" /> Redo
                  </button>
                  <RouteLink className="secondary" href={routePath(workbench)} onNavigate={() => onNavigate(workbench)}>
                    Open as JSON
                  </RouteLink>
                  <button
                    type="button"
                    className={hasSource ? "secondary" : "primary"}
                    onClick={() => setDialog({ kind: "install" })}
                  >
                    Install and activate…
                  </button>
                  {hasSource && (
                    <button type="button" className="primary" onClick={() => setDialog({ kind: "load" })}>
                      Load into a change set…
                    </button>
                  )}
                  <ActionMenu
                    label="More actions"
                    items={[{ id: "workbook", label: workbookLabel, onAction: () => setDialog({ kind: "workbook" }) }]}
                  />
                </>
              )}
            </div>
          }
        />
      )}
      {stale && (
        <Notice
          tone="warning"
          title="Another change came first"
          focusOnMount
          actions={
            <>
              <button
                type="button"
                className="primary"
                disabled={busy}
                onClick={() => void guarded(() => step(stale.send))}
              >
                Apply mine again
              </button>
              <button type="button" className="secondary" disabled={busy} onClick={() => setStale(undefined)}>
                Discard mine
              </button>
            </>
          }
        >
          Your change was not applied: the draft changed since you opened it.{" "}
          {stale.since.length > 0 && (
            <>
              Applied since:{" "}
              {stale.since.map((entry) => describeOperation(entry.kind, entry.parameters, names)).join("; ")}
              {stale.more ? " and more" : ""}.
            </>
          )}{" "}
          The model below shows the newer version.
        </Notice>
      )}
      {notice && (
        <Notice
          tone={notice.tone}
          actions={
            notice.applications?.map((key) => (
              <button key={key} type="button" className="secondary" onClick={() => onOpenApplication(key)}>
                Open {applicationOf(outline, key)?.name ?? key}
              </button>
            )) ?? (
              <button type="button" className="secondary" onClick={() => setNotice(undefined)}>
                Dismiss
              </button>
            )
          }
        >
          {notice.text}
        </Notice>
      )}
      {mode === "layout" ? (
        typePreview(
          "layout",
          <>
            <button type="button" className="secondary" disabled={busy || !undoAvailable} onClick={() => void undo()}>
              <Icon name="undo" /> Undo
            </button>
            <button type="button" className="secondary" disabled={busy || !redoAvailable} onClick={() => void redo()}>
              <Icon name="redo" /> Redo
            </button>
            <button type="button" className="secondary" onClick={() => showType("preview")}>
              Preview
            </button>
            <button type="button" className="primary" onClick={() => showType()}>
              <Icon name="arrow-left" /> Back to the model editor
            </button>
          </>,
        )
      ) : phone ? (
        <div className="model-editor-tabs">
          <Tabs
            label="Editor panes"
            selected={phoneTab}
            onChange={setPhoneTab}
            tabs={[
              ...(hasSource ? [{ id: "source", label: "Source", content: sourcePane }] : []),
              { id: "model", label: paneTab === "apis" ? "Consumer APIs" : "Model", content: pane },
              { id: "element", label: selectedName, content: centre },
              { id: "issues", label: `Issues ${issueCount}`, content: bottom },
            ]}
          />
        </div>
      ) : (
        <>
          <div
            className={`model-editor-panes${hasSource ? " with-source" : ""}`}
            style={
              { "--editor-pane": `${paneWidth.value}px`, "--source-pane": `${sourceWidth.value}px` } as CSSProperties
            }
          >
            {hasSource && (
              <>
                {sourcePane}
                <ResizeHandle
                  className="editor-resizer source-resizer"
                  label="Resize the source pane"
                  value={sourceWidth.value}
                  min={240}
                  max={560}
                  onChange={sourceWidth.change}
                  onReset={sourceWidth.reset}
                />
              </>
            )}
            {pane}
            <ResizeHandle
              className="editor-resizer"
              label="Resize the model pane"
              value={paneWidth.value}
              min={220}
              max={560}
              onChange={paneWidth.change}
              onReset={paneWidth.reset}
            />
            {centre}
          </div>
          {bottom}
        </>
      )}
      {dialog?.kind === "operation" && (
        <OperationDialog
          operation={dialog.operation}
          target={dialog.target}
          outline={outline}
          preset={dialog.preset}
          run={run}
          onClose={() => setDialog(undefined)}
        />
      )}
      {dialog?.kind === "move" && (
        <MoveToDialog
          subject={dialog.subject}
          outline={outline}
          initialTarget={dialog.target}
          run={run}
          onClose={() => setDialog(undefined)}
        />
      )}
      {dialog?.kind === "dependants" && (
        <ConfirmDialog
          title="Undo the steps that depend on it too?"
          confirmLabel={`Undo steps ${[...dialog.steps, ...dialog.dependants].sort((a, b) => a - b).join(", ")}`}
          pending={busy}
          onCancel={() => setDialog(undefined)}
          onConfirm={() => {
            const together = [...dialog.steps, ...dialog.dependants];
            setDialog(undefined);
            void undo(together);
          }}
        >
          <p>
            Step {dialog.dependants.join(", ")} uses what step {dialog.steps.join(", ")} created or re-keyed, so it
            cannot be undone alone.
          </p>
        </ConfirmDialog>
      )}
      {dialog?.kind === "map" && (
        <MapColumnDialog
          start={dialog.start}
          column={source.columns(dialog.start.sheet)?.find((item) => item.header === dialog.start.header)}
          profile={draftProfile}
          outline={outline}
          run={run}
          onClose={() => setDialog(undefined)}
        />
      )}
      {dialog?.kind === "valueMap" && (
        <ValueMapDialog
          source={dialog.use.source.id}
          header={dialog.header}
          mapName={dialog.use.binding.valueMap}
          column={source.columns(dialog.use.source.sheet)?.find((item) => item.header === dialog.header)}
          profile={draftProfile}
          outline={outline}
          run={run}
          onClose={() => setDialog(undefined)}
        />
      )}
      {dialog?.kind === "rows" && (
        <DryRunRowsDialog draftId={draftId} rows={dialog.rows} onClose={() => setDialog(undefined)} />
      )}
      {dialog?.kind === "workbook" && (
        <AddWorkbookDialog
          draftId={draftId}
          replaces={source.profile?.sourceFile?.name}
          defaultWorkspace={workspaceKey}
          onUploaded={(file) => {
            source.uploaded(file);
            toast(`${file.name} is uploaded and being profiled.`);
          }}
          onClose={() => setDialog(undefined)}
        />
      )}
      {dialog?.kind === "load" && source.profile && (
        <LoadDialog
          draftId={draftId}
          outline={outline}
          profile={source.profile}
          dryRun={source.dryRun}
          defaultWorkspace={workspaceKey}
          run={run}
          latestVersion={() => version.current}
          onActivated={async () => {
            await onActivated();
            await load();
          }}
          onOpenReview={(target) => {
            setDialog(undefined);
            onOpenChangeSet(target);
          }}
          onClose={() => setDialog(undefined)}
        />
      )}
      {dialog?.kind === "install" && (
        <InstallDialog
          draftId={draftId}
          outline={outline}
          run={run}
          latestVersion={() => version.current}
          onInstalledOnly={() => void load()}
          onActivated={async (release) => {
            await onActivated();
            await load();
            setDialog(undefined);
            toast(`${release.name} ${release.version} is the active model.`);
            setNotice({
              tone: "success",
              text: `${release.name} ${release.version} is installed and active. This draft continues from it.`,
              applications: outline.applications.map((item) => item.key).slice(0, 3),
            });
          }}
          onClose={() => setDialog(undefined)}
        />
      )}
    </div>
  );
}
