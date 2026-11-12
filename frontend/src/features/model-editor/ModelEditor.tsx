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
 *
 * The inference fills the editor (0.10 A6b, D94): asked for by New from a workbook (once the workbook
 * is profiled) or by ⋯ › Propose again…, its proposals are applied as steps, one each. What is still
 * as proposed is marked Proposed in the panes, and its centre says why, with its alternatives.
 */

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { EditorMode, EditorSelection, EngineModel, JourneyRef, RouteState } from "@/types";
import { ColumnPanel } from "@/features/model-editor/ColumnPanel";
import { ListPanel } from "@/features/model-editor/ListPanel";
import { dropOperations, listHeader, listStatus, sourceOfList } from "@/features/model-editor/lists";
import { columnsOfType, typesFed, usesOf } from "@/features/model-editor/mapping";
import { DRAG_COLUMN, SourcePane } from "@/features/model-editor/SourcePane";
import { useDraftSource } from "@/features/model-editor/useDraftSource";
import { useEditorWorkspace } from "@/features/model-editor/useEditorWorkspace";
import { useDraftEditing } from "@/features/model-editor/useDraftEditing";
import { useSourceDialogs } from "@/features/model-editor/useSourceDialogs";
import { useDraftActions, draftJsonRoute } from "@/features/model-editor/useDraftActions";
import { DraftEditingDialogs, DraftEditingNotices } from "@/features/model-editor/DraftEditingDialogs";
import { DraftPreview } from "@/features/model-editor/DraftPreview";
import { DraftViewSwitch, draftViewRoute } from "@/features/model-editor/DraftViewSwitch";
import { useInference } from "@/features/model-editor/useInference";
import { ProposeDialog } from "@/features/model-editor/ProposeDialog";
import { ProposedBecause } from "@/features/model-editor/ProposedBecause";
import {
  columnElements,
  elementOfSelection,
  hasWaitingProposal,
  stillProposed,
  takeWaitingProposal,
} from "@/features/model-editor/proposing";
import { useDraftHistory } from "@/features/model-editor/useDraftHistory";
import { useLocalNumberPreference } from "@/lib/localPreference";
import { PageHeader } from "@/ui/PageHeader";
import { ResizeHandle } from "@/ui/ResizeHandle";
import { Facts } from "@/features/model-editor/Facts";
import { PHONE_WIDTH, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import { routePath } from "@/routing/routes";
import { ActionMenu } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { IconButton } from "@/ui/IconButton";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { RouteLink } from "@/ui/RouteLink";
import { Skeleton } from "@/ui/Skeleton";
import { Tabs } from "@/ui/Tabs";
import { useToast } from "@/ui/Toast";
import { ElementPanel } from "@/features/model-editor/ElementPanel";
import { canRedo, historySteps, undoable } from "@/features/model-editor/history";
import { ProposingProgress, type ProposingPhase } from "@/features/model-editor/ProposingProgress";
import { IssuesDrawer, issueCountOf, useIssuesDrawer } from "@/features/model-editor/IssuesDrawer";
import { droppedColumn, ModelPane, type PaneDrop } from "@/features/model-editor/ModelPane";
import { topOf, typeIn } from "@/features/model-editor/MoveToDialog";
import { refusalText } from "@/features/model-editor/OperationDialog";
import {
  applicationOf,
  attributeTypeOf,
  consumerApiOf,
  relationTypeOf,
  typeName,
} from "@/features/model-editor/outline";
import { ConsumerApiPane, ConsumerApiPanel } from "@/features/model-editor/ConsumerApis";
import { RelationshipMatrix } from "@/features/model-editor/RelationshipMatrix";
import { AddMenu } from "@/features/model-editor/AddMenu";

/**
 * Whether the reader left the issues and history pane open, remembered in this browser; closed until
 * they open it. Only the pane's own toggle stores it (the user, 2026-10-19: Show issues stored it
 * open, so it opened empty from then on; `v2` leaves those stored values behind).
 */

export function ModelEditor({
  draftId,
  journey,
  forWorkspace,
  onOpenWorkspace,
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
  /** The journey the editor was opened from: Close returns to it, not to the models. */
  journey?: JourneyRef;
  /** Opened from this workspace (0.16 WM1): the main action applies to it, Close returns to it. */
  forWorkspace?: string;
  onOpenWorkspace?: (workspaceKey: string) => void;
  selection: EditorSelection;
  onSelect: (selection: EditorSelection) => void;
  onNavigate: (route: RouteState) => void;
  /** Reloads a workspace's model after an activation into it. */
  onActivated: (workspaceKey: string) => Promise<unknown>;
  /** Opens an application of the draft's model, in `workspaceKey` (the editor's workspace without it). */
  onOpenApplication: (applicationKey: string, workspaceKey?: string) => void;
  /** After a load (0.10 A5b): the change set's review, in the application the profile loads. */
  onOpenChangeSet: (target: { applicationKey: string; workspaceKey: string; changeSetId: string }) => void;
  /** The running model: the preview reads its records through it (0.10 A4b, D44). */
  activeModel: EngineModel;
  /** The workspace the user came from; the preview reads records from it first when it runs the draft's model. */
  workspaceKey: string;
}) {
  const toast = useToast();
  const phone = useMediaQuery(PHONE_WIDTH);
  const dryRunFollow = useRef<(jobId: string) => void>(() => undefined);
  const [bottomTab, setBottomTab] = useState("issues");
  // Steps, refusals, the operation dialogs and the notices are the shared hook's: the canvas edits the
  // same draft through the same one (0.17 CE1, PP-D3).
  const editing = useDraftEditing(draftId, {
    selection,
    onSelect,
    onAnswer: (answer) => {
      if (answer.dryRun) dryRunFollow.current(answer.dryRun.jobId);
    },
    onUndone: () => setBottomTab("history"),
  });
  const {
    outline,
    steps: draftSteps,
    setNotice,
    guarded,
    run,
    step,
    undo,
    redo,
    operate,
    setMenuOpen,
    menuOpen,
  } = editing;
  const { loadError } = draftSteps;
  const name = draftSteps.draft?.name ?? "";
  // Whether the draft names a base release of its own; without one, the active release stands in (D17).
  const ownBase = draftSteps.draft?.ownBase ?? true;
  const editorWorkspace = useEditorWorkspace(outline?.release.key ?? undefined, workspaceKey);
  const [forWorkspaceLabel, setForWorkspaceLabel] = useState<string>();
  useEffect(() => {
    if (!forWorkspace) return;
    let active = true;
    api
      .workspace(forWorkspace)
      .then((found) => active && setForWorkspaceLabel(found.label))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [forWorkspace]);
  const appliesTo = forWorkspaceLabel ?? forWorkspace;
  const [proposeOpen, setProposeOpen] = useState(false);
  const [elementTab, setElementTab] = useState("attributes");
  const [phoneTab, setPhoneTab] = useState(selection.show ? "element" : "model");
  // The left pane's tab (0.10 A4c, D59): it follows a selected consumer API, and stays where the reader put it.
  const [paneTab, setPaneTab] = useState(selection.show === "consumerApi" ? "apis" : "model");
  const paneWidth = useLocalNumberPreference("rdm:model-editor:pane-width:v1", 300, 220, 560);
  const sourceWidth = useLocalNumberPreference("rdm:model-editor:source-width:v1", 320, 240, 560);
  const source = useDraftSource(draftId, outline?.version);
  const { dryRunQueued, loadColumns } = source;
  const sourceDialogs = useSourceDialogs(editing, source);
  useEffect(() => {
    dryRunFollow.current = dryRunQueued;
  });
  // A list opened from the address or the phone's tab: its sheet's columns name it (0.10 A8b).
  const listSheetName = selection.show === "list" ? selection.sheet : undefined;
  const sheetsRead = source.sheets.length > 0;
  useEffect(() => {
    if (listSheetName && sheetsRead) loadColumns(listSheetName);
  }, [listSheetName, sheetsRead, loadColumns]);

  const drawer = useIssuesDrawer();

  /** Opens the Issues tab, leaving the layout editor (which has no pane) first. */
  const showIssues = () => {
    if (selection.show === "type" && selection.mode === "layout")
      onSelect({
        show: "type",
        key: selection.key,
        ...(selection.application ? { application: selection.application } : {}),
      });
    setBottomTab("issues");
    // Opened for now; only the pane's own toggle is the reader's choice.
    if (phone) setPhoneTab("issues");
    else drawer.show();
  };
  const showIssuesNow = useRef(showIssues);
  useEffect(() => {
    showIssuesNow.current = showIssues;
  });
  // A step that leaves the draft with more errors than before says so, with a way to the Issues tab.
  // Opening a draft, and errors that fall or stay, say nothing.
  const errorsSeen = useRef<{ draftId: string; count: number }>(undefined);
  useEffect(() => {
    if (!outline) return;
    const count = outline.diagnostics.filter((item) => item.severity === "error").length;
    const before = errorsSeen.current;
    errorsSeen.current = { draftId, count };
    if (!before || before.draftId !== draftId || count <= before.count) return;
    const more = count - before.count;
    toast(`The draft now has ${count} ${count === 1 ? "issue" : "issues"}, ${more} more than before.`, {
      tone: "info",
      actions: [{ label: "Show issues", onPress: () => showIssuesNow.current() }],
    });
  }, [outline, draftId, toast]);

  const history = useDraftHistory(draftId, outline?.version);
  const steps = historySteps(history.items);

  // The inference completed: its open proposals become steps, one each (D89).
  const inference = useInference(draftId, outline?.version, (done) => {
    if (!done.counts.open) {
      inference.settled();
      const nothing = done.disagreements.length
        ? `Nothing new to propose. The workbook reads ${done.disagreements.length} ${done.disagreements.length === 1 ? "column" : "columns"} otherwise than you decided: see Issues.`
        : "Nothing new to propose: the draft holds what the workbook shows.";
      setNotice({ tone: "success", text: nothing });
      return;
    }
    void guarded(async () => {
      try {
        let first: string | undefined;
        const outcome = await step(async (at) => {
          const answer = await api.applyProposals(draftId, at);
          // The sheet's type the first proposal added: shown, so the proposals are in view.
          // A model description's type, when the workbook describes one (0.10 A7).
          first = answer.entries.find(
            (entry) =>
              entry.kind === "addObjectType" &&
              (entry.origin.pattern === "keyColumn" || entry.origin.pattern === "modelDescription"),
          )?.parameters.key as string | undefined;
          return answer;
        }, true);
        if (outcome === "applied" && first) select({ show: "type", key: first });
        if (outcome === "applied") {
          toast(`${done.counts.open} ${done.counts.open === 1 ? "proposal" : "proposals"} applied, one step each.`);
          setBottomTab("history");
        }
      } catch (cause) {
        setNotice({
          tone: "error",
          text: isApiError(cause, "INFERENCE_STALE")
            ? "The draft changed while the workbook was read. Propose again from the ⋯ menu."
            : outline
              ? refusalText(cause, outline)
              : errorMessage(cause),
        });
      } finally {
        inference.settled();
      }
    });
  });
  // Stop before the workbook is profiled drops the request that waits for it.
  const [dropped, setDropped] = useState(false);
  const { propose: proposeFrom, running: proposingNow } = inference;
  const profileState = source.profile?.sourceFile?.profile;
  const profiled = profileState === "completed";
  // A proposal waiting for the profile is as good as running: editing waits for it too.
  const waiting =
    hasWaitingProposal(draftId) &&
    !dropped &&
    (profileState === "queued" || profileState === "running" || profileState === "completed");
  const proposing = proposingNow || waiting;
  const { setPaused } = editing;
  useEffect(() => {
    setPaused(proposing);
  }, [proposing, setPaused]);
  const busy = editing.working || proposing;
  const proposingPhase: ProposingPhase = !proposingNow
    ? "profiling"
    : inference.inference?.state === "completed"
      ? "applying"
      : "reading";
  const draftActions = useDraftActions({
    editing,
    source,
    forWorkspace,
    workspaceKey: editorWorkspace,
    proposing,
    onActivated,
    onOpenWorkspace,
    onNavigate,
    onOpenChangeSet,
    onShowIssues: showIssues,
  });
  // New from a workbook asked to propose: once the workbook is profiled, the editor does.
  useEffect(() => {
    if (!profiled || proposingNow || !hasWaitingProposal(draftId)) return;
    const request = takeWaitingProposal(draftId);
    if (request) void proposeFrom(request);
  }, [profiled, proposingNow, draftId, proposeFrom]);

  function select(next: EditorSelection) {
    onSelect(next);
    if (next.show) setPaneTab(next.show === "consumerApi" ? "apis" : "model");
    if (phone) setPhoneTab("element");
  }

  function drop(item: PaneDrop) {
    if (item.kind === "column") {
      sourceDialogs.openMap(item.sheet, item.header, item.target);
      return;
    }
    editing.openDialog(
      item.kind === "attribute"
        ? {
            kind: "move",
            subject: { kind: "attribute", objectType: item.objectType, attributeType: item.attributeType },
            target: item.target,
          }
        : {
            kind: "move",
            subject: { kind: "objectType", objectType: item.objectType, application: item.from || undefined },
            target: item.application
              ? item.target
                ? typeIn(item.application, item.target)
                : topOf(item.application)
              : undefined,
          },
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

  const errors = outline.diagnostics.filter((item) => item.severity === "error").length;
  const warnings = outline.diagnostics.length - errors;
  const undoAvailable = steps.some(undoable);
  const redoAvailable = canRedo(steps);
  const base = outline.baseRelease;
  // The selected list of a sheet laid out for reading (0.10 A8b): its block, header and source.
  const listSheet = selection.show === "list" ? source.sheets.find((item) => item.name === selection.sheet) : undefined;
  const listBlock =
    selection.show === "list" ? listSheet?.blocks.find((item) => item.index === selection.block) : undefined;
  const listName = listBlock && listSheet ? listHeader(listBlock, source.columns(listSheet.name)) : undefined;
  const listLoads =
    listBlock && listSheet ? sourceOfList(source.profile?.profile, listSheet.name, listBlock) : undefined;
  const selectedName =
    selection.show === "list"
      ? (listName ?? "List")
      : selection.show === "type"
        ? typeName(outline, selection.key)
        : selection.show === "group"
          ? (applicationOf(outline, selection.application)?.navigation.groups.find((g) => g.key === selection.key)
              ?.label ?? selection.key)
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
  // What is still as the inference proposed it (D92), and the section saying why for the selection.
  // An installed element is part of a release: it reads Released, and its alternatives would be
  // migrations, so it is no longer marked Proposed.
  const proposedElements = stillProposed(inference.proposed, outline);
  // The sheets the inference read as a model description (0.10 A7).
  const describingSheets = new Set(
    inference.proposals
      .filter((item) => item.pattern === "modelDescription" && item.sheet)
      .map((item) => item.sheet as string),
  );
  const proposedElement =
    selection.show === "column"
      ? columnElements(draftProfile, selection.sheet, selection.key).find((element) => proposedElements.has(element))
      : selection.show === "list"
        ? [`source:${listLoads?.id}`, `objectType:${listLoads?.objectTypeKey}`].find((element) =>
            proposedElements.has(element),
          )
        : elementOfSelection(selection);
  const proposedNote =
    proposedElement && proposedElements.has(proposedElement) ? (
      <ProposedBecause
        proposal={inference.proposed.get(proposedElement)}
        busy={busy}
        run={(operations) => void guarded(() => run(operations))}
      />
    ) : undefined;
  const toModels: RouteState = { kind: "settings", page: "model" };
  // Close returns to where the editor was opened from: the journey's page, else the models.
  const toClose: RouteState =
    journey?.kind === "aiTask" ? { kind: "settings", page: "ai-tasks", taskId: journey.taskId } : toModels;
  const close = () => (forWorkspace ? onOpenWorkspace?.(forWorkspace) : onNavigate(toClose));
  const proposeAgain = profiled
    ? [{ id: "propose", label: "Propose again…", disabled: proposing, onAction: () => setProposeOpen(true) }]
    : [];
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
          : item.key?.field === "name"
            ? "Name"
            : item.key?.column;
        return `${typeName(outline, item.objectTypeKey)}${key ? ` (key ${key})` : ""}`;
      })
      .join(", ")}`;
  };
  // The profile key's field is in the source pane, a tab of its own on a phone.
  const goToProfileKey = () => {
    if (phone) setPhoneTab("source");
    requestAnimationFrame(() => document.querySelector<HTMLElement>("#profile-key-field button")?.focus());
  };
  const sourcePane = hasSource && (
    <SourcePane
      source={source}
      selection={selection}
      linked={linkedColumns}
      canDrag={!phone}
      sheetNames={sheetLoads}
      proposed={proposedElements}
      describing={describingSheets}
      onSelect={select}
      onMap={(sheet, header) => sourceDialogs.openMap(sheet, header)}
      onIgnoreSheet={(sheet) => void guarded(() => run([{ kind: "ignoreSheet", sheet }]))}
      outline={outline}
      onSetProfile={proposing ? undefined : (patch) => run([{ kind: "setProfile", ...patch }])}
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
        sourceDialogs.openMap(column.sheet, column.header);
      }}
    >
      <Tabs
        label="Edit"
        selected={paneTab}
        onChange={setPaneTab}
        header={
          <div className="model-editor-pane-add">
            <AddMenu outline={outline} consumerApis={paneTab === "apis"} onOperation={operate} />
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
                  proposed={proposedElements}
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
  const typeApplication = selection.show === "type" ? selection.application : undefined;
  const showType = (next?: EditorMode) =>
    typeKey &&
    onSelect({
      show: "type",
      key: typeKey,
      ...(typeApplication ? { application: typeApplication } : {}),
      ...(next ? { mode: next } : {}),
    });
  const typePreview = (shown: EditorMode, actions: ReactNode) =>
    typeKey && (
      <DraftPreview
        editing={editing}
        mode={shown}
        objectTypeKey={typeKey}
        applicationKey={typeApplication}
        onApplication={(next) =>
          typeKey && onSelect({ show: "type", key: typeKey, application: next, ...(shown ? { mode: shown } : {}) })
        }
        activeModel={activeModel}
        workspaceKey={editorWorkspace}
        onShowIssues={showIssues}
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
              : selection.show === "list"
                ? "Selected list"
                : "Selected element"
      }
    >
      {selection.show === "list" ? (
        listBlock && listSheet ? (
          <ListPanel
            key={`${listSheet.name}:${listBlock.index}`}
            sheet={listSheet.name}
            block={listBlock}
            header={listName ?? ""}
            fileId={source.profile?.sourceFile?.id}
            listSource={listLoads}
            status={listStatus(listLoads, proposedElements)}
            outline={outline}
            busy={busy}
            proposed={proposedNote}
            onAdjust={() => sourceDialogs.openList("adjust", listSheet.name, listBlock.index)}
            onLoad={() => sourceDialogs.openList("load", listSheet.name, listBlock.index)}
            onSetMissing={(operations) => void editing.runGuarded(operations)}
            readings={{
              profile: draftProfile,
              columns: source.columns(listSheet.name),
              run: (operations) => void editing.runGuarded(operations),
            }}
            onDrop={() => {
              if (listLoads) void guarded(() => run(dropOperations(outline, draftProfile, listLoads)));
            }}
            onShowType={(key) => select({ show: "type", key })}
          />
        ) : (
          <Skeleton lines={6} label="Reading the list" />
        )
      ) : selection.show === "column" ? (
        <ColumnPanel
          key={`${selection.sheet}:${selection.key}`}
          sheet={selection.sheet}
          header={selection.key}
          source={source}
          outline={outline}
          busy={busy}
          run={(operations) => void guarded(() => run(operations))}
          onMap={() => sourceDialogs.openMap(selection.sheet, selection.key)}
          onValueMap={(use) => sourceDialogs.openValueMap(use, selection.key)}
          onRows={sourceDialogs.openRows}
          proposed={proposedNote}
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
          proposed={proposedNote}
        />
      )}
    </section>
  );
  const issueCount = issueCountOf(outline, source.profile);
  const bottom = (
    <IssuesDrawer
      editing={editing}
      outline={outline}
      history={history}
      source={source}
      sourceDialogs={sourceDialogs}
      proposing={proposing}
      tab={bottomTab}
      onTab={setBottomTab}
      open={drawer.open}
      onToggle={drawer.toggle}
      onSelect={select}
      onGoToProfileKey={goToProfileKey}
      inTab={phone}
    />
  );

  return (
    <div className={`model-editor${mode === "layout" ? " model-editor-layout" : ""}`}>
      {mode !== "layout" && (
        <PageHeader
          className="model-editor-bar"
          variant="detail"
          icon={<Icon name="model" size={20} />}
          eyebrow={
            forWorkspace ? (
              <button type="button" className="model-editor-crumb" onClick={() => onOpenWorkspace?.(forWorkspace)}>
                {appliesTo}
              </button>
            ) : (
              <RouteLink
                className="model-editor-crumb"
                href={routePath({ kind: "settings", page: "model" })}
                onNavigate={() => onNavigate({ kind: "settings", page: "model" })}
              >
                Settings › Model
              </RouteLink>
            )
          }
          title={name || "Model draft"}
          description={
            <Facts
              label="About this draft"
              facts={[
                ...(forWorkspace
                  ? [
                      {
                        icon: "model" as const,
                        label: (
                          <>
                            Applies to <strong>{appliesTo}</strong>
                          </>
                        ),
                      },
                    ]
                  : []),
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
                {
                  icon: "check",
                  label: "Saved as you go: closing keeps the draft and its proposals.",
                },
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
              <DraftViewSwitch
                draftId={draftId}
                view="editor"
                onChange={(view) => onNavigate(draftViewRoute(draftId, view, { forWorkspace, journey }))}
              />
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
                    label="More: Open as JSON, Install and activate, Load, Add a workbook, Propose again, Close, Delete"
                    items={[
                      ...draftActions.items(["apply"]),
                      { id: "close", label: "Close", onAction: close },
                      ...draftActions.items(["json", "install", "load", "workbook"]),
                      ...proposeAgain,
                      ...draftActions.items(["delete"]),
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
                  <RouteLink
                    className="secondary"
                    href={routePath(draftJsonRoute(draftId))}
                    onNavigate={() => draftActions.open("json")}
                  >
                    Open as JSON
                  </RouteLink>
                  {forWorkspace ? (
                    <button
                      type="button"
                      className="primary"
                      disabled={proposing}
                      onClick={() => draftActions.open("apply")}
                    >
                      Apply to this workspace…
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        className={hasSource ? "secondary" : "primary"}
                        disabled={proposing}
                        onClick={() => draftActions.open("install")}
                      >
                        Install and activate…
                      </button>
                      {hasSource && (
                        <button
                          type="button"
                          className="primary"
                          disabled={proposing}
                          onClick={() => draftActions.open("load")}
                        >
                          Load into a change set…
                        </button>
                      )}
                    </>
                  )}
                  {forWorkspace ? (
                    <button type="button" className="secondary" onClick={close}>
                      Close
                    </button>
                  ) : (
                    <RouteLink className="secondary" href={routePath(toClose)} onNavigate={close}>
                      Close
                    </RouteLink>
                  )}
                  <ActionMenu
                    label="More actions"
                    items={[
                      ...(forWorkspace ? draftActions.items(["install", "load"]) : []),
                      ...draftActions.items(["workbook"]),
                      ...proposeAgain,
                      ...draftActions.items(["delete"]),
                    ]}
                  />
                </>
              )}
            </div>
          }
        />
      )}
      {proposing && (
        <ProposingProgress
          phase={proposingPhase}
          onStop={() => {
            if (proposingNow) void inference.stop();
            else {
              takeWaitingProposal(draftId);
              setDropped(true);
            }
          }}
        />
      )}
      {inference.error && !proposing && (
        <Notice tone="error" title="Nothing was proposed">
          {inference.error}
        </Notice>
      )}
      <DraftEditingNotices editing={editing} busy={busy} onOpenApplication={onOpenApplication} />
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
      <DraftEditingDialogs editing={editing} busy={busy} />
      {sourceDialogs.dialogs}
      {draftActions.dialogs}
      {proposeOpen && source.profile?.sourceFile && (
        <ProposeDialog
          fileName={source.profile.sourceFile.name}
          initialMode={inference.inference?.mode}
          onPropose={(request) => {
            setProposeOpen(false);
            void proposeFrom(request);
          }}
          onClose={() => setProposeOpen(false)}
        />
      )}
    </div>
  );
}
