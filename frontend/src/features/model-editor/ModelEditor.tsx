/**
 * The model editor on a draft (0.10 A4a; MODEL_AUTHORING "The editor"): the model pane, the selected
 * element or the relationship matrix, and the issues and history, under a bar with undo, redo, the
 * JSON workbench and install and activate. Opened from Settings › Model (D7), full width in the
 * shared frame (D37). Below 760px the panes are tabs.
 *
 * Every change is an operation step on the server at the draft's version (A2). The editor reads the
 * draft back as its outline after each step (D36), so the browser never works out the model's rules.
 * A step refused because another editor moved the draft on is held, and the editor asks whether to
 * apply it again on the newer version (D41).
 */

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type {
  DraftOperation,
  EditorSelection,
  ModelDraftOperationEntry,
  ModelDraftOutline,
  ModelDraftStep,
  RouteState,
} from "@/types";
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
import { canRedo, describeOperation, historySteps, undoable } from "@/features/model-editor/history";
import { InstallDialog } from "@/features/model-editor/InstallDialog";
import { IssuesAndHistory } from "@/features/model-editor/IssuesAndHistory";
import { ModelPane, type PaneDrop } from "@/features/model-editor/ModelPane";
import { MoveToDialog, type MoveSubject } from "@/features/model-editor/MoveToDialog";
import { OperationDialog, refusalText, type StepOutcome } from "@/features/model-editor/OperationDialog";
import { type FieldValues, type OperationSpec, type OperationTarget } from "@/features/model-editor/operations";
import { applicationOf, attributeTypeOf, nameOf, relationTypeOf, typeName } from "@/features/model-editor/outline";
import { RelationshipMatrix } from "@/features/model-editor/RelationshipMatrix";
import { OperationsMenu } from "@/features/model-editor/OperationsMenu";

type Send = (version: number) => Promise<ModelDraftStep>;

/** Whether the reader left the issues and history pane open, remembered in this browser. */
const BOTTOM_KEY = "rdm:model-editor:issues-history-open:v1";

type Dialog =
  | { kind: "operation"; operation: OperationSpec; target: OperationTarget; preset?: FieldValues }
  | { kind: "move"; subject: MoveSubject; target?: string }
  | { kind: "install" }
  | { kind: "dependants"; steps: number[]; dependants: number[] };

/** A step refused because the draft moved on (D41): what came first, and how to send mine again. */
type Stale = { since: ModelDraftOperationEntry[]; more: boolean; send: Send };

export function ModelEditor({
  draftId,
  selection,
  onSelect,
  onNavigate,
  onActivated,
  onOpenApplication,
}: {
  draftId: string;
  selection: EditorSelection;
  onSelect: (selection: EditorSelection) => void;
  onNavigate: (route: RouteState) => void;
  /** Reloads the active model after an activation. */
  onActivated: () => Promise<unknown>;
  onOpenApplication: (applicationKey: string) => void;
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
  const [menuOpen, setMenuOpen] = useState(false);
  const version = useRef(0);
  const paneWidth = useLocalNumberPreference("rdm:model-editor:pane-width:v1", 300, 220, 560);
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
        await send(version.current);
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
    [load],
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
    if (phone) setPhoneTab("element");
  }

  function drop(item: PaneDrop) {
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
  const addTarget: OperationTarget = { on: "draft" };
  const selectedName =
    selection.show === "type"
      ? typeName(outline, selection.key)
      : selection.show === "application"
        ? (applicationOf(outline, selection.key)?.name ?? selection.key)
        : selection.show === "relationType"
          ? (relationTypeOf(outline, selection.key)?.name ?? selection.key)
          : selection.show === "attributeType"
            ? (attributeTypeOf(outline, selection.key)?.name ?? selection.key)
            : selection.show === "matrix"
              ? "Matrix"
              : "Selection";

  const pane = (
    <section className="model-editor-model" aria-labelledby="model-pane-title">
      <div className="model-editor-pane-head">
        <h2 id="model-pane-title" className="nav-label">
          Model
        </h2>
        <OperationsMenu
          label="Add to the model"
          icon="plus"
          tooltip="Add"
          target={addTarget}
          outline={outline}
          onOperation={operate}
        />
      </div>
      {outline.applications.length === 0 && (
        <p className="muted model-editor-empty">The draft is empty. Add an application to start.</p>
      )}
      <ModelPane
        outline={outline}
        selection={selection}
        canDrag={!phone}
        onSelect={select}
        onMenu={(next) => {
          select(next);
          setMenuOpen(true);
        }}
        onDrop={drop}
      />
    </section>
  );
  const centre = (
    <section
      className="model-editor-centre"
      aria-label={selection.show === "matrix" ? "Relationship matrix" : "Selected element"}
    >
      {selection.show === "matrix" ? (
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
    />
  );
  // On a desktop the pane is a drawer at the bottom, closed until the reader opens it; nothing else
  // opens or closes it (the user, 2026-10-11). On a phone it is the Issues tab.
  const bottom = phone ? (
    <section className="model-editor-bottom" aria-label="Issues and history">
      {issuesAndHistory}
    </section>
  ) : (
    <section className={`model-editor-bottom${bottomOpen ? " open" : ""}`} aria-label="Issues and history">
      <button
        type="button"
        className="model-editor-bottom-toggle"
        aria-expanded={bottomOpen}
        aria-controls="model-editor-issues-history"
        onClick={() => toggleBottom(!bottomOpen)}
      >
        <Icon name={bottomOpen ? "chevron-down" : "chevron-right"} size={14} />
        <span>Issues and history</span>
        <StatusPill tone={errors ? "error" : warnings ? "warning" : "success"}>
          {outline.diagnostics.length
            ? `${outline.diagnostics.length} ${outline.diagnostics.length === 1 ? "issue" : "issues"}`
            : "No issues"}
        </StatusPill>
        <span className="muted">{steps.length ? `${steps.length} steps` : "No steps yet"}</span>
      </button>
      <div id="model-editor-issues-history" className="model-editor-bottom-body" hidden={!bottomOpen}>
        {bottomOpen && issuesAndHistory}
      </div>
    </section>
  );

  return (
    <div className="model-editor">
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
                  label="More: Open as JSON, Install and activate"
                  items={[
                    { id: "json", label: "Open as JSON", onAction: () => onNavigate(workbench) },
                    { id: "install", label: "Install and activate…", onAction: () => setDialog({ kind: "install" }) },
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
                <button type="button" className="primary" onClick={() => setDialog({ kind: "install" })}>
                  Install and activate…
                </button>
              </>
            )}
          </div>
        }
      />
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
      {phone ? (
        <div className="model-editor-tabs">
          <Tabs
            label="Editor panes"
            selected={phoneTab}
            onChange={setPhoneTab}
            tabs={[
              { id: "model", label: "Model", content: pane },
              { id: "element", label: selectedName, content: centre },
              { id: "issues", label: `Issues ${outline.diagnostics.length}`, content: bottom },
            ]}
          />
        </div>
      ) : (
        <>
          <div className="model-editor-panes" style={{ "--editor-pane": `${paneWidth.value}px` } as CSSProperties}>
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
