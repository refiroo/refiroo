/**
 * The canvas (0.17 PL3b, CE1): a model draft drawn as lists on a board, with the workbook's sheets on the left, the
 * inspector on the right and the issues and history at the foot. It is a view of the model draft (PP-D3): the same
 * draft, steps, undo and dry run as the model editor, through the same editing hook, so what the editor does to an
 * element the canvas does through the element's menu, with the editor's own forms and panels. A gesture a drop makes
 * applies at once as one request and one undo step, with no dialog (PP-D4); a drop the engine refuses changes nothing
 * and says why above the board. The count of rows that load or are refused follows every step and never holds the next
 * drop back (PP-D9). A question a gesture cannot answer by itself (which of two tied columns, what to call two new
 * columns) is a small popover at the drop, never a guess. Every gesture has a menu or keyboard path, and on a phone the
 * menus do what the drags do. Card positions, folds and the chosen scope belong to the draft's canvas, never to its
 * version: opening a model, moving cards, Tidy and folding change nothing in it.
 */

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent, type ReactNode } from "react";
import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { count, counted } from "@/lib/count";
import { objectTypeOf, typeName } from "@/model/outline";
import { openWorkspace } from "@/state/openWorkspace";
import { DraftEditingDialogs, DraftEditingNotices } from "@/features/model-editor/DraftEditingDialogs";
import { DraftPreview } from "@/features/model-editor/DraftPreview";
import { DraftViewSwitch, draftViewRoute } from "@/features/model-editor/DraftViewSwitch";
import { DryRunRowsDialog, type DryRunRows } from "@/features/model-editor/DryRunPanel";
import { usesOf } from "@/features/model-editor/mapping";
import { refusalText } from "@/features/model-editor/OperationDialog";
import { ProposeDialog } from "@/features/model-editor/ProposeDialog";
import { stillProposed } from "@/model/proposing";
import { useDraftActions } from "@/features/model-editor/useDraftActions";
import { useDraftEditing } from "@/features/model-editor/useDraftEditing";
import { useDraftHistory } from "@/features/model-editor/useDraftHistory";
import { useDraftSource } from "@/features/model-editor/useDraftSource";
import { useEditorWorkspace } from "@/features/model-editor/useEditorWorkspace";
import { useProposing } from "@/features/model-editor/useProposing";
import { useSourceDialogs } from "@/features/model-editor/useSourceDialogs";
import { ValueMapDialog } from "@/features/model-editor/ValueMapDialog";
import { AddMenu } from "@/features/model-editor/AddMenu";
import { useHeldAnywhere } from "@/state/permissions";
import { useCapabilities } from "@/state/useSystem";
import { startsFromWorkbook } from "@/features/workspaces/fromWorkbook";
import { readLocalPreference, writeLocalPreference } from "@/lib/localPreference";
import { PHONE_WIDTH, useMediaQuery } from "@/lib/hooks/useMediaQuery";
import type { CanvasSelection, EditorSelection, EngineModel, JourneyRef, OutlineElement, RouteState } from "@/types";
import { IssuesDrawer, useIssuesDrawer } from "@/features/model-editor/IssuesDrawer";
import type { DraftOperation, ModelDraftStep } from "@/types/modelAdmin";
import type { JoinCandidate, SourceColumn } from "@/types/sources";
import { ActionMenu, type ActionMenuItem } from "@/ui/ActionMenu";
import { Icon } from "@/ui/Icon";
import { Notice } from "@/ui/Notice";
import { useOptionalToast } from "@/ui/Toast";
import { ChooserPopover, TiePopover, type Choice } from "./CanvasAsks";
import { HeadingPopover, UnpivotPopover } from "@/features/model-editor/ReadingAsks";
import { CanvasBoard, DRAG_FIELD, type BoardApi, type ConnectTarget, type DroppedColumns } from "./CanvasBoard";
import { CanvasFind } from "./CanvasFind";
import { CanvasInspector, type InspectorTab } from "./CanvasInspector";
import { CreateWorkspaceDialog } from "./CreateWorkspaceDialog";
import { LinePopover } from "./LinePopover";
import { RefusedDialog, type Reason } from "./RefusedDialog";
import { useCanvasDocument } from "./useCanvasDocument";
import { useDraftModel } from "./useDraftModel";
import { WorkbookPane } from "./WorkbookPane";
import {
  SCOPES,
  cardsOf,
  containOperations,
  defaultScope,
  filterOperations,
  groupOperations,
  joinOperations,
  joinRequest,
  leaveOutOperations,
  linesOf,
  loadFigures,
  nameColumnOf,
  pickJoin,
  placed,
  closeUp,
  relatePlan,
  releaseOperations,
  sameSheetJoin,
  sheetAsListOperations,
  columnAsListOperations,
  dropPlace,
  freshCardOf,
  tidy,
  unrelateOperations,
  withApplication,
  type CanvasCard,
  type CanvasField,
  type CanvasLine,
  type Position,
  type WrongValues,
} from "./canvasModel";
import { columnDropOperations, type ColumnDrop } from "@/features/model-editor/columnDrop";
import {
  addedColumns,
  fillDownOperations,
  headingOperations,
  sourceOfColumn,
  unpivotDefaults,
  unpivotOperations,
} from "@/features/model-editor/readings";
import {
  ZOOM_KEY,
  clampZoom,
  moveAttributeDropOperations,
  pickOf,
  renameFieldOperations,
  renameListOperations,
  reorderAttributeOperations,
  selectionOfPick,
  stepAttributeOperations,
  targetOfLine,
  type AddedKind,
  type CanvasPick,
  addedKeys,
  addedName,
  isAddedKind,
  type FindHit,
} from "./canvasView";
import { everyPage } from "@/lib/everyPage";

/** Up to this many lists a card's menu names one by one; more go behind one chooser with a search. */
const INLINE_LISTS = 4;

type Dialog =
  | { kind: "create" }
  | { kind: "refused"; typeKey: string; reasons: Reason[] }
  | {
      kind: "valueMap";
      sourceId: string;
      sheet: string;
      header: string;
      mapName: string | null | undefined;
      suggested: WrongValues["values"];
    };

const isZoom = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value);

export function WorkbookCanvas({
  draftId,
  forWorkspace,
  workspaceKey = "",
  journey,
  selection,
  onSelect,
  activeModel,
  onNavigate,
  onActivated,
  onOpenWorkspace,
  onOpenChangeSet,
}: {
  draftId: string;
  /** Opened from this workspace's Edit model: the main finish applies the model to it (0.16 WM1). */
  forWorkspace?: string;
  /** The workspace the person came from: a load into an existing workspace starts there. */
  workspaceKey?: string;
  /** The journey the canvas was opened from: the switch to the editor keeps it. */
  journey?: JourneyRef;
  /** What is selected, kept in the address (CE1); without it the canvas keeps its own. */
  selection?: CanvasSelection;
  onSelect?: (selection: CanvasSelection) => void;
  /** The running model: a list's preview reads its records through it; without it no preview is offered. */
  activeModel?: EngineModel;
  onNavigate: (route: RouteState) => void;
  /** Reloads a workspace's model after an activation into it. */
  onActivated?: (workspaceKey: string) => Promise<unknown>;
  onOpenWorkspace?: (workspaceKey: string) => void;
  /** After a load into a workspace: the change set's review. */
  onOpenChangeSet?: (target: { applicationKey: string; workspaceKey: string; changeSetId: string }) => void;
}) {
  const toast = useOptionalToast();
  const phone = useMediaQuery(PHONE_WIDTH);
  const held = useHeldAnywhere();
  const { capabilities } = useCapabilities();
  const followDryRun = useRef<(jobId: string) => void>(() => undefined);
  const [localPick, setLocalPick] = useState<CanvasPick>();
  const pick = selection ? pickOf(selection) : localPick;
  const setPick = useCallback(
    (next: CanvasPick | undefined) => {
      if (onSelect) onSelect(selectionOfPick(next));
      else setLocalPick(next);
    },
    [onSelect],
  );
  // What a step makes is selected once its answer says what it made (a new list, a new field).
  const afterStep = useRef<(answer: ModelDraftStep) => void>(() => undefined);
  /** The step the draft's latest answer made: a toast's Undo takes back that step, not whatever came last. */
  const lastStep = useRef<number>(undefined);
  const live = useRef<{ pick?: CanvasPick; setPick: (pick: CanvasPick | undefined) => void }>({ setPick });
  useEffect(() => {
    live.current = { pick, setPick };
  });
  const drawer = useIssuesDrawer();
  const [bandSlot, setBandSlot] = useState<HTMLDivElement | null>(null);
  const [drawerTab, setDrawerTab] = useState("issues");
  const editing = useDraftEditing(draftId, {
    // A step that changes the key of what is selected makes the selection follow it.
    get selection(): EditorSelection {
      const current = live.current.pick;
      if (current?.element === "type" && current.key) return { show: "type", key: current.key };
      if (current?.element === "field" && current.field?.startsWith("attribute:"))
        return { show: "attributeType", key: current.field.slice("attribute:".length) };
      return {};
    },
    onSelect: (followed) => {
      const current = live.current.pick;
      if (followed.show === "type" && current?.element === "type")
        live.current.setPick({ ...current, key: followed.key });
      else if (followed.show === "attributeType" && current?.element === "field")
        live.current.setPick({ ...current, field: `attribute:${followed.key}` });
    },
    onAnswer: (answer: ModelDraftStep) => {
      if (answer.dryRun) followDryRun.current(answer.dryRun.jobId);
      lastStep.current = answer.entries[0]?.step;
      afterStep.current(answer);
    },
    onUndone: () => setDrawerTab("history"),
  });
  const { outline, run, step } = editing;
  const steps = editing.steps;
  const source = useDraftSource(draftId, outline?.version);
  useEffect(() => {
    followDryRun.current = source.dryRunQueued;
  });
  const profile = source.profile?.profile;
  const model = useDraftModel(draftId, outline?.version);
  const editorWorkspace = useEditorWorkspace(outline?.release.key ?? undefined, workspaceKey);
  const history = useDraftHistory(draftId, outline?.version);
  const sourceDialogs = useSourceDialogs(editing, source);

  const [notice, setNotice] = useState<{ tone: "error" | "warning" | "info"; text: string }>();
  const [busy, setBusy] = useState(false);
  const [sheetName, setSheetName] = useState<string>();
  const [picked, setPicked] = useState<{ sheet: string; headers: string[] }>();
  const [rows, setRows] = useState<DryRunRows>();
  const [dialog, setDialog] = useState<Dialog>();
  const [proposeOpen, setProposeOpen] = useState(false);
  const [tab, setTab] = useState<InspectorTab>("inspector");
  // A panel the board has no card for (an attribute type, a relation type) shown in the inspector.
  const [panel, setPanel] = useState<EditorSelection>();
  const [consumer, setConsumer] = useState<EditorSelection>({});
  const [preview, setPreview] = useState<{ typeKey: string; mode: "preview" | "layout" }>();
  const [menu, setMenu] = useState<string>();
  const [openLine, setOpenLine] = useState<string>();
  const [zoom, setZoomState] = useState(() => clampZoom(readLocalPreference(ZOOM_KEY, 1, isZoom)));
  const setZoom = useCallback((next: number) => {
    const clamped = clampZoom(next);
    setZoomState(clamped);
    writeLocalPreference(ZOOM_KEY, clamped);
  }, []);
  const boardApi = useRef<BoardApi | null>(null);
  const centreAfter = useRef<{ typeKey: string; fieldId?: string }>(undefined);
  const inspectorBox = useRef<HTMLDivElement>(null);
  /** A small question open under an element: it draws itself and says when it is done. */
  const [ask, setAsk] = useState<{ render: (close: () => void) => ReactNode }>();
  const boardBox = useRef<HTMLDivElement>(null);

  const closeAsk = useCallback(() => setAsk(undefined), []);
  const openAsk = useCallback((render: (close: () => void) => ReactNode) => setAsk({ render }), []);
  /** The element a question opens under: a card, a field, a column, else the board. */
  const anchorOf = useCallback(
    (selector: string): HTMLElement =>
      document.querySelector<HTMLElement>(selector) ?? boardBox.current ?? document.body,
    [],
  );
  const cardAnchor = (typeKey: string) => anchorOf(`[data-canvas-card="${CSS.escape(typeKey)}"]`);
  const columnAnchor = (header: string) => anchorOf(`[data-column-pick="${CSS.escape(header)}"]`);

  /** One gesture: its operations as one request; a refusal is said above the board, nothing changed. */
  const draftName = steps.draft?.name ?? "";
  /** An Undo that takes back the one step it names (PP-D76: the toolbar's takes the last). */
  const undoOf = useCallback(
    (made: number | undefined) => () => void editing.undo(made === undefined ? undefined : [made]),
    [editing],
  );
  const act = useCallback(
    async (said: string, operations: DraftOperation[] | (() => Promise<DraftOperation[] | null>)) => {
      setNotice(undefined);
      setBusy(true);
      try {
        const sent = typeof operations === "function" ? await operations() : operations;
        // A question answered with a close sends nothing and says nothing.
        if (sent === null) return false;
        if (!sent.length) {
          setNotice({ tone: "info", text: "Nothing changed: that is already how the draft reads it." });
          return false;
        }
        const { outcome, step: made } = await editing.runAnswered(
          outline ? withApplication(sent, outline, draftName) : sent,
        );
        // A step held back because the draft moved on is the editing hook's to say, with its two buttons.
        if (outcome === "stale") return false;
        toast(said, { actions: [{ label: "Undo", onPress: undoOf(made) }] });
        return true;
      } catch (cause) {
        setNotice({ tone: "error", text: refusalText(cause, outline) });
        return false;
      } finally {
        setBusy(false);
      }
    },
    [toast, outline, draftName, undoOf, editing],
  );

  // An inference that completed: its proposals become steps, as in the editor, and stay marked Proposed.
  const inference = useProposing(draftId, outline?.version, {
    step,
    say: setNotice,
    nothingNew: () =>
      setNotice({ tone: "info", text: "Nothing new to propose: the draft holds what the workbook shows." }),
    staleText: "The draft changed while the workbook was read. Choose Propose again.",
    refusal: (cause) => refusalText(cause, outline),
    around: async (work) => {
      setBusy(true);
      try {
        await work();
      } finally {
        setBusy(false);
      }
    },
  });
  const proposing = inference.running;
  const { setPaused } = editing;
  useEffect(() => {
    setPaused(proposing);
  }, [proposing, setPaused]);
  const proposedElements = useMemo(
    () => (outline ? stillProposed(inference.proposed, outline) : new Set<string>()),
    [inference.proposed, outline],
  );

  const doc = useCanvasDocument(draftId);
  const hasFile = Boolean(source.file ?? source.profile?.sourceFile);
  // "From the workbook" means nothing without a workbook: it is hidden then, and a scope kept on the draft falls back.
  const scope = doc.scope === "workbook" && !hasFile ? "model" : (doc.scope ?? defaultScope(hasFile));
  const scopes = hasFile ? SCOPES : SCOPES.filter((item) => item.id !== "workbook");
  // A workbook added here, to a draft that had none, keeps the board on what it showed: the default for a draft with a
  // workbook (its lists) would leave the board empty until the workbook is mapped.
  const hadNoFile = useRef(false);
  const { chooseScope } = doc;
  useEffect(() => {
    if (source.profile === undefined || !doc.ready) return;
    if (!hasFile) hadNoFile.current = true;
    else if (hadNoFile.current) {
      hadNoFile.current = false;
      if (!doc.scope) chooseScope("model");
    }
  }, [source.profile, hasFile, doc.ready, doc.scope, chooseScope]);
  const cards = useMemo(
    () => (outline ? cardsOf(outline, profile, proposedElements, model, { scope, folded: doc.folded }) : []),
    [outline, profile, proposedElements, model, scope, doc.folded],
  );
  const lines = useMemo(() => (outline ? linesOf(outline, cards) : []), [outline, cards]);
  const figures = useMemo(() => loadFigures(source.dryRun), [source.dryRun]);

  const ready = outline !== undefined;
  const [boardWidth, setBoardWidth] = useState(1100);
  useEffect(() => {
    const element = boardBox.current;
    if (!element) return;
    const read = () => setBoardWidth(Math.max(360, element.clientWidth));
    read();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(read);
    observer.observe(element);
    return () => observer.disconnect();
  }, [ready]);
  // On a phone the board is one column of cards: the places chosen on a desktop do not fit its width.
  const positions = useMemo(
    () => (phone ? tidy(cards, lines, boardWidth) : placed(cards, lines, doc.positions, boardWidth)),
    [phone, cards, lines, doc.positions, boardWidth],
  );
  const { savePositions } = doc;
  /** A fold closes up its column: on a board of kept places the cards under it move (a laid-out board lays itself out). */
  function foldCard(typeKey: string, folded: boolean) {
    if (!phone && Object.keys(doc.positions).length) {
      const moved = closeUp(cards, positions, typeKey, folded);
      if (Object.keys(moved).length) savePositions(moved);
    }
    doc.fold(typeKey, folded);
  }
  // A stored place that was moved to stand clear of another card (or inside the board) is written back once,
  // after a pause, through the canvas save: a place, never a model step.
  useEffect(() => {
    if (phone || !doc.ready) return;
    const moved: Record<string, Position> = {};
    for (const [key, place] of Object.entries(doc.positions)) {
      const now = positions[key];
      if (now && (now.x !== place.x || now.y !== place.y)) moved[key] = now;
    }
    if (!Object.keys(moved).length) return;
    const timer = setTimeout(() => savePositions(moved), 600);
    return () => clearTimeout(timer);
  }, [phone, doc.ready, doc.positions, positions, savePositions]);
  /**
   * The place a drop on the empty board asks for is kept for the card the step is about to add: the card that was
   * not on the board when the drop was made, never one that stood there without a kept place.
   */
  const placeNext = useRef<{ at: Position; before: ReadonlySet<string> }>(undefined);
  useEffect(() => {
    const wanted = placeNext.current;
    if (!wanted || !doc.ready) return;
    const fresh = freshCardOf(cards, wanted.before);
    if (!fresh) return;
    placeNext.current = undefined;
    savePositions({ [fresh.typeKey]: dropPlace(wanted.at) });
  }, [cards, doc.positions, doc.ready, savePositions]);

  // What the board was asked to show: centred once the card is there (a scope may have to widen first).
  useEffect(() => {
    const wanted = centreAfter.current;
    if (!wanted || !cards.some((card) => card.typeKey === wanted.typeKey)) return;
    const frame = requestAnimationFrame(() => {
      if (boardApi.current?.centreOn(wanted.typeKey, wanted.fieldId)) centreAfter.current = undefined;
    });
    return () => cancelAnimationFrame(frame);
  }, [cards, positions, pick, zoom]);

  const sheets = source.sheets;
  const sheet = sheets.find((item) => item.name === sheetName) ?? sheets[0];
  const { loadColumns } = source;
  useEffect(() => {
    if (sheet) loadColumns(sheet.name);
  }, [sheet, loadColumns]);
  const columns = (sheet ? source.columns(sheet.name) : undefined) ?? [];
  const columnOf = (sheetOf: string, header: string): SourceColumn | undefined =>
    source.columns(sheetOf)?.find((item) => item.header === header);
  const chosen = picked && picked.sheet === sheet?.name ? picked.headers : [];

  const forThisWorkspace = forWorkspace ?? steps.draft?.workspaceKey ?? undefined;
  const draftActions = useDraftActions({
    editing,
    source,
    forWorkspace: forThisWorkspace,
    workspaceKey: editorWorkspace,
    proposing,
    onActivated: async (workspaceOf) => {
      await onActivated?.(workspaceOf);
    },
    onOpenWorkspace,
    onNavigate,
    onOpenChangeSet: (target) => onOpenChangeSet?.(target),
    onShowIssues: () => {
      setDrawerTab("issues");
      drawer.show();
    },
  });

  // A selection brought into view on a phone, where the inspector stands under the board.
  useEffect(() => {
    if (phone && pick) inspectorBox.current?.scrollIntoView?.({ block: "nearest" });
  }, [phone, pick]);

  // An object type made from the Add menu is shown: selected, and the board centred on it.
  const addWatch = useRef(false);
  const knownTypes = useRef<Set<string>>(undefined);
  useEffect(() => {
    const keys = new Set((outline?.objectTypes ?? []).map((item) => item.key));
    const before = knownTypes.current;
    if (outline) knownTypes.current = keys;
    if (!addWatch.current || !before) return;
    const made = [...keys].find((key) => !before.has(key));
    if (!made) return;
    addWatch.current = false;
    if (!cards.some((card) => card.typeKey === made)) doc.chooseScope("model");
    centreAfter.current = { typeKey: made };
    live.current.setPick({ element: "type", key: made });
    setTab("inspector");
  }, [outline, cards, doc]);

  // An attribute type, a relation type or a navigation group made from the Add menu has no card: it is selected in
  // the inspector (its own panel, or the Navigation tab with the group) and said in the usual toast.
  const addedElement = useRef<{ id: AddedKind; known: ReadonlySet<string> }>(undefined);
  useEffect(() => {
    const added = addedElement.current;
    if (!added || !outline) return;
    const made = [...addedKeys(added.id, outline)].find((entry) => !added.known.has(entry));
    if (!made) return;
    addedElement.current = undefined;
    const name = addedName(added.id, made, outline);
    if (added.id === "add-group") {
      const [application, key] = made.split("\u0000");
      setPanel(undefined);
      live.current.setPick({ element: "group", application, key });
      setTab("navigation");
    } else {
      live.current.setPick(undefined);
      setPanel({ show: added.id === "add-attribute-type" ? "attributeType" : "relationType", key: made });
      setTab("inspector");
    }
    toast(`${name} added`, { actions: [{ label: "Undo", onPress: undoOf(lastStep.current) }] });
  }, [outline, toast, undoOf]);

  if (steps.loadError) return <Notice tone="error">{steps.loadError}</Notice>;
  if (!outline) return <p className="canvas-loading">Reading the draft…</p>;

  const cardOf = (typeKey: string) => cards.find((card) => card.typeKey === typeKey);
  const editable = true;
  const fileName = source.profile?.sourceFile?.name ?? source.file?.name;
  // Hidden, never disabled, for a person who lacks a step the one route makes (D323).
  // A finish that has nothing to load is hidden as well: an empty board has no list a sheet loads (D323).
  const loadsAList = (profile?.sources ?? []).some((item) => cards.some((card) => card.typeKey === item.objectTypeKey));
  const canCreate = !forThisWorkspace && hasFile && loadsAList && startsFromWorkbook(held, capabilities);
  const toSelection = (next: CanvasPick | undefined) => {
    addedElement.current = undefined;
    setPanel(undefined);
    setOpenLine(undefined);
    setMenu(undefined);
    setPick(next);
  };

  // --- by hand ---

  /** An attribute row dropped on another object type's card: the editor's Move to…; a refusal is said above the board. */
  function moveAttribute(fromKey: string, fieldId: string, toKey: string) {
    const from = cardOf(fromKey);
    const to = cardOf(toKey);
    const field = from?.fields.find((item) => item.id === fieldId);
    if (!from || !to || !field) return;
    const sent = moveAttributeDropOperations(from, field, toKey);
    if (sent.length) void act(`${field.label} moved to ${to.name}`, sent);
  }

  /** An attribute row dropped beside another of its card: its position, as the editor's Move up / Move down. */
  function reorderAttribute(typeKey: string, fieldId: string, besideId: string, after: boolean) {
    const card = cardOf(typeKey);
    const field = card?.fields.find((item) => item.id === fieldId);
    const other = card?.fields.find((item) => item.id === besideId);
    if (!card || !field?.attributeTypeKey || !other?.attributeTypeKey) return;
    const sent = reorderAttributeOperations(outline!, typeKey, field.attributeTypeKey, other.attributeTypeKey, after);
    if (sent.length) void act(`${field.label} moved in ${card.name}`, sent);
  }

  function stepAttribute(card: CanvasCard, field: CanvasField, direction: -1 | 1) {
    const sent = stepAttributeOperations(card, field, direction, outline!);
    if (sent.length) void act(`${field.label} moved ${direction < 0 ? "up" : "down"}`, sent);
  }

  /** A name changed where it stands: sent as the editor's Rename…; a refusal is thrown to stay under the field. */
  async function renameWith(operations: DraftOperation[]) {
    const { outcome, step: made } = await editing.runAnswered(operations);
    // A rename held back because the draft moved on is the editing hook's to say: no "Renamed." for it.
    if (outcome === "stale") return false as const;
    return () => editing.undo(made === undefined ? undefined : [made]);
  }
  async function renameList(card: CanvasCard, name: string) {
    return renameWith(renameListOperations(card, name));
  }
  async function renameField(card: CanvasCard, field: CanvasField, name: string) {
    return renameWith(renameFieldOperations(card, field, name, outline!));
  }

  /** Find: the list or field, centred on the board and selected; a scope that leaves it off widens to the whole model. */
  function goTo(hit: FindHit) {
    if (!cards.some((card) => card.typeKey === hit.typeKey)) doc.chooseScope("model");
    centreAfter.current = { typeKey: hit.typeKey, fieldId: hit.fieldId };
    toSelection(
      hit.fieldId ? { element: "field", key: hit.typeKey, field: hit.fieldId } : { element: "type", key: hit.typeKey },
    );
    setTab("inspector");
    setPreview(undefined);
  }

  /** An issue's link: its element selected on the board and centred, or its tab opened. */
  function followIssue(target: EditorSelection, element?: OutlineElement) {
    setPreview(undefined);
    if (target.show === "type") goTo({ typeKey: target.key, label: target.key, hint: "" });
    else if (target.show === "attributeType") {
      const holder = cards.find((card) => card.fields.some((field) => field.attributeTypeKey === target.key));
      const field = holder?.fields.find((item) => item.attributeTypeKey === target.key);
      if (holder && field) goTo({ typeKey: holder.typeKey, fieldId: field.id, label: field.label, hint: holder.name });
      else {
        const type = outline!.objectTypes.find((item) => item.attributes.some((a) => a.attributeType === target.key));
        if (type) goTo({ typeKey: type.key, label: type.name, hint: "" });
      }
    } else if (target.show === "relationType") {
      const line = lines.find((item) => item.relationType === target.key);
      const relation = outline!.relations.find((item) => item.relationType === target.key);
      if (line) {
        centreAfter.current = { typeKey: line.from };
        toSelection({ element: "line", key: line.id });
      } else if (relation) goTo({ typeKey: relation.from, label: relation.relationType, hint: "" });
    } else if (target.show === "matrix") {
      // An issue about a relationship between two lists: its line on the board (a parent's line for a containment),
      // or the list it starts from when the board draws no line for it.
      const about = element?.relationType && element.from ? element : undefined;
      const relation =
        about &&
        outline!.relations.find(
          (item) =>
            item.relationType === about.relationType && item.from === about.from && (!about.to || item.to === about.to),
        );
      const line =
        relation &&
        lines.find((item) =>
          relation.containment
            ? item.kind === "contains" && item.from === relation.from && item.to === relation.to
            : item.relationType === relation.relationType && item.from === relation.from && item.to === relation.to,
        );
      if (line) {
        centreAfter.current = { typeKey: line.from };
        toSelection({ element: "line", key: line.id });
      } else if (about?.from) goTo({ typeKey: about.from, label: about.from, hint: "" });
    } else if (target.show === "application") toSelection({ element: "application", key: target.key });
    else if (target.show === "group") {
      toSelection({ element: "group", application: target.application, key: target.key });
      setTab("navigation");
    } else if (target.show === "consumerApi") {
      setConsumer(target);
      setTab("consumer");
    } else if (target.show === "column") toSelection({ element: "column", sheet: target.sheet, key: target.key });
    else if (target.show === "list") toSelection({ element: "list", sheet: target.sheet, block: target.block });
  }

  /** The list of a sheet that loads a card: its panel, with what a load does with the records no row names. */
  function openSheet(card: CanvasCard, sheetOf: string) {
    const table = sheets.find((item) => item.name === sheetOf);
    const reading = (profile?.sources ?? []).find(
      (item) => item.sheet === sheetOf && item.objectTypeKey === card.typeKey,
    );
    const block = table?.blocks.find((item) => item.firstColumn === reading?.block?.firstColumn) ?? table?.blocks[0];
    if (table && block) toSelection({ element: "list", sheet: table.name, block: block.index });
  }

  // --- drops ---

  function dropColumn(column: DroppedColumns, typeKey: string, field?: CanvasField) {
    const card = cardOf(typeKey);
    if (!card || !outline) return;
    if (column.headers.length > 1) {
      unpivotAsk(column.sheet, column.headers, field ? { on: "field", typeKey, field } : { on: "card", typeKey }, () =>
        field
          ? anchorOf(`[data-canvas-card="${CSS.escape(typeKey)}"] [data-canvas-field="${CSS.escape(field.id)}"]`)
          : cardAnchor(typeKey),
      );
      return;
    }
    const operations = columnDropOperations(
      column.sheet,
      column.header,
      field ? { on: "field", typeKey, field } : { on: "card", typeKey },
      profile,
      outline,
      columnOf(column.sheet, column.header),
    );
    void act(
      field ? `${column.header} fills ${field.label} of ${card.name}` : `${column.header} added to ${card.name}`,
      operations,
    );
  }

  /** Several columns onto a list or a field: the two new columns are named in a small popover first. */
  function unpivotAsk(sheetOf: string, headers: string[], drop: ColumnDrop, anchor: () => HTMLElement) {
    const taken = new Set([
      ...(source.columns(sheetOf) ?? []).flatMap((item) => (item.header ? [item.header] : [])),
      ...addedColumns(profile, sheetOf).map((item) => item.header),
    ]);
    const element = anchor();
    openAsk((close) => (
      <UnpivotPopover
        anchor={element}
        count={headers.length}
        initial={unpivotDefaults(headers, taken)}
        onClose={close}
        onSubmit={(names) => {
          close();
          const plan = { sheet: sheetOf, columns: headers, ...names, drop };
          void act(
            `${headers.length} columns read as rows`,
            unpivotOperations(plan, profile, outline!, (header) => columnOf(sheetOf, header)),
          );
        }}
      />
    ));
  }

  /** The chosen columns' menu path: pick the list or field they fill, then name the new columns. */
  function unpivotChoose(anchor: HTMLElement) {
    if (!sheet || chosen.length < 2) return;
    const drops = new Map<string, ColumnDrop>();
    const choices: Choice[] = cards.flatMap((card) => {
      drops.set(`card:${card.typeKey}`, { on: "card", typeKey: card.typeKey });
      return [
        { id: `card:${card.typeKey}`, label: card.name, hint: "new attributes" },
        ...card.fields.map((field): Choice => {
          drops.set(`field:${card.typeKey}:${field.id}`, { on: "field", typeKey: card.typeKey, field });
          return { id: `field:${card.typeKey}:${field.id}`, label: `${card.name} › ${field.label}` };
        }),
      ];
    });
    openAsk((close) => (
      <ChooserPopover
        anchor={anchor}
        title={`Read ${chosen.length} columns as rows into`}
        searchLabel="Search object types and attributes"
        choices={choices}
        onClose={close}
        onChoose={(id) => {
          close();
          const drop = drops.get(id);
          if (drop) unpivotAsk(sheet.name, chosen, drop, () => anchor);
        }}
      />
    ));
  }

  /** A column dropped on a list's Filters, or one chosen for it. */
  function filterColumn(typeKey: string, column?: DroppedColumns) {
    if (!column) {
      if (!sheet) return;
      const choices = columns.flatMap((item) =>
        item.header ? [{ id: item.header, label: item.header, hint: item.values?.[0]?.value }] : [],
      );
      const anchor = anchorOf(`[data-canvas-filters="${CSS.escape(typeKey)}"] button`);
      openAsk((close) => (
        <ChooserPopover
          anchor={anchor}
          title={`Filter ${typeName(outline!, typeKey)} by`}
          searchLabel="Search columns"
          choices={choices}
          onClose={close}
          onChoose={(header) => {
            close();
            filterColumn(typeKey, { sheet: sheet.name, header, headers: [header] });
          }}
        />
      ));
      return;
    }
    void act(`${typeName(outline!, typeKey)} filters by ${column.header}`, async () => {
      const result = filterOperations(
        { sheet: column.sheet, header: column.header, typeKey },
        profile,
        outline!,
        model,
        columnOf(column.sheet, column.header),
      );
      if (result.problem === "noView") {
        setNotice({
          tone: "warning",
          text: "This object type has no table view to hold a filter, or the model has an issue that stops it being read. Open the model editor to see which.",
        });
        return null;
      }
      if (result.problem === "already") {
        setNotice({
          tone: "info",
          text: `${typeName(outline!, typeKey)} already filters by ${column.header}.`,
        });
        return null;
      }
      return result.operations;
    });
  }

  /** A column on the empty board: its distinct values as a list of their own, linked back (one request, no inference). */
  function columnToSpace(column: DroppedColumns, at: Position) {
    placeNext.current = { at: dropPlace(at), before: new Set(cards.map((card) => card.typeKey)) };
    void act(`An object type made of the values of ${column.header}`, async () => {
      const table = sheets.find((item) => item.name === column.sheet);
      if (!table || !outline) return [];
      const operations = columnAsListOperations(table, column.header, profile, outline);
      if (!operations.length)
        setNotice({
          tone: "info",
          text: `${column.header} is read as the object type's name, its parent or a relationship already. Drag it back to the workbook first to make an object type of its values.`,
        });
      return operations.length ? operations : null;
    }).then((applied) => {
      if (!applied) placeNext.current = undefined;
    });
  }

  function sheetToSpace(name: string, at: Position) {
    placeNext.current = { at: dropPlace(at), before: new Set(cards.map((card) => card.typeKey)) };
    void act(`An object type made of the sheet ${name}`, async () => {
      const table = sheets.find((item) => item.name === name);
      const fileId = source.profile?.sourceFile?.id ?? source.file?.id;
      if (!table || !fileId || !outline) return [];
      // A sheet a list already reads is not made a list twice: the card of the list that reads it is said.
      const reading = (profile?.sources ?? []).find((item) => item.sheet === name);
      if (reading && (profile?.sources ?? []).filter((item) => item.sheet === name).length >= table.blocks.length) {
        setNotice({
          tone: "info",
          text: `${typeName(outline, reading.objectTypeKey)} already reads ${name}: its card is on the board.`,
        });
        return null;
      }
      // Every column of the sheet, read to the end: the list takes them all as fields.
      const all: SourceColumn[] = await everyPage((cursor) => api.sourceColumns(fileId, name, cursor));
      return sheetAsListOperations(table, all, profile, outline);
    }).then((applied) => {
      if (!applied) placeNext.current = undefined;
    });
  }

  // --- connecting: the link, and the column that fills it over every row (PP-D8) ---

  /**
   * A parent and child or a relationship between two lists. When sheets load both, the join route is
   * asked over every row which column of the starting list's sheet names the other list's records,
   * and the binding goes in the same request as the link. Tied columns are asked about, never guessed.
   */
  function link(kind: "parent" | "relation", from: string, to: string) {
    if (!outline) return;
    const fromName = typeName(outline, from);
    const toName = typeName(outline, to);
    const plan = kind === "parent" ? undefined : relatePlan(from, to, outline);
    const base = kind === "parent" ? containOperations(from, to, outline) : plan!.operations;
    let noColumn = false;
    void act(
      kind === "parent" ? `${toName} now contains ${fromName}` : `${fromName} related to ${toName}`,
      async () => {
        const found = (profile?.sources ?? []).find((item) => item.objectTypeKey === from);
        // A column that already links the list to the other one as a relationship may become its parent link instead.
        const start =
          found && kind === "parent"
            ? { ...found, columns: found.columns.filter((binding) => binding.relation?.objectTypeKey !== to) }
            : found;
        const other = nameColumnOf(profile, to);
        const filled =
          kind === "parent" &&
          Boolean(start?.columns.some((binding) => !binding.ignore && binding.parent?.objectTypeKey === to));
        if (!start || !other || filled) {
          noColumn = !filled;
          return base;
        }
        let header: string | undefined;
        try {
          const answer = await api.joinCandidates(draftId, joinRequest(other, start));
          const { best, tied } = pickJoin(answer, start);
          if (best) header = best.header ?? undefined;
          else if (tied.length) {
            const letter = await new Promise<string | null | undefined>((resolve) =>
              openAsk((close) => (
                <TiePopover
                  anchor={cardAnchor(from)}
                  other={toName}
                  candidates={tied as JoinCandidate[]}
                  onClose={() => {
                    close();
                    resolve(undefined);
                  }}
                  onChoose={(chosenLetter) => {
                    close();
                    resolve(chosenLetter);
                  }}
                />
              )),
            );
            // A closed question changes nothing: not even the link.
            if (letter === undefined) return null;
            header = tied.find((item) => item.letter === letter)?.header ?? undefined;
          }
        } catch {
          // A join that cannot be read leaves the link made and nothing filling it; the notice says so.
        }
        header ??= sameSheetJoin(start, other);
        if (!header) {
          noColumn = true;
          return base;
        }
        return [
          ...base,
          ...joinOperations(kind, start, header, { typeKey: to, matchBy: other.matchBy }, plan?.relationType),
        ];
      },
    ).then((applied) => {
      if (applied && noColumn)
        setNotice({
          tone: "info",
          text: `The link is made, but no column of the workbook was found that names the ${toName} records, so nothing fills it yet. Drop a column on its attribute to fill it.`,
        });
    });
  }

  function connect(from: string, target: ConnectTarget, relate: boolean) {
    if (!outline) return;
    const fromName = typeName(outline, from);
    if (target.group) {
      const { applicationKey, key, fresh } = target.group;
      void act(
        fresh ? `${fromName} placed in a new group` : `${fromName} placed in the navigation`,
        groupOperations(from, applicationKey, fresh ? { label: `${fromName} group` } : key ? { key } : null, outline),
      );
      return;
    }
    if (!target.typeKey) return;
    // Onto a field, or with Alt held: a relationship. Onto the card: the dragged list goes under it.
    link(target.fieldId || relate ? "relation" : "parent", from, target.typeKey);
  }

  /** The Connect handle from the keyboard, or on a phone: the lists, relationships and groups to choose from. */
  function connectMenu(card: CanvasCard) {
    const others = cards.filter((item) => item.typeKey !== card.typeKey);
    const application = outline!.applications.find((item) => item.key === card.applicationKey);
    const choices: Choice[] = [
      ...others.map((other) => ({ id: `under:${other.typeKey}`, label: `Put under ${other.name}`, hint: "Hierarchy" })),
      ...others.map((other) => ({
        id: `relate:${other.typeKey}`,
        label: `Relate to ${other.name}`,
        hint: "Relationship",
      })),
      ...(application?.navigation.groups ?? []).map((group) => ({
        id: `group:${group.key}`,
        label: `Place in the group ${group.label}`,
        hint: "Navigation",
      })),
    ];
    const anchor = cardAnchor(card.typeKey);
    openAsk((close) => (
      <ChooserPopover
        anchor={anchor}
        title={`Connect ${card.name}`}
        searchLabel="Search object types and groups"
        choices={choices}
        onClose={close}
        onChoose={(id) => {
          close();
          const how = id.slice(0, id.indexOf(":"));
          const key = id.slice(id.indexOf(":") + 1);
          if (how === "under") connect(card.typeKey, { typeKey: key }, false);
          else if (how === "relate") connect(card.typeKey, { typeKey: key }, true);
          else if (application) connect(card.typeKey, { group: { applicationKey: application.key, key } }, false);
        }}
      />
    ));
  }

  function removeLine(line: CanvasLine) {
    if (line.kind === "contains")
      void act(`${typeName(outline!, line.to)} moved to the top level`, releaseOperations(line.to));
    else if (line.relationType)
      void act(
        "Relationship removed",
        unrelateOperations({ relationType: line.relationType, from: line.from, to: line.to }),
      );
  }

  // --- menus: every gesture by name ---

  /** The lists a menu would name one by one: inline when few, one chooser with a search when many. */
  function listEntries(
    id: string,
    label: (name: string) => string,
    section: string,
    lists: readonly CanvasCard[],
    anchor: () => HTMLElement,
    choose: (typeKey: string) => void,
    chooserLabel: string,
  ): ActionMenuItem[] {
    if (lists.length <= INLINE_LISTS)
      return lists.map((other) => ({
        id: `${id}:${other.typeKey}`,
        label: label(other.name),
        section,
        onAction: () => choose(other.typeKey),
      }));
    return [
      {
        id,
        label: `${chooserLabel}…`,
        section,
        onAction: () => {
          const element = anchor();
          openAsk((close) => (
            <ChooserPopover
              anchor={element}
              title={chooserLabel}
              searchLabel="Search object types"
              choices={lists.map((other) => ({ id: other.typeKey, label: other.name }))}
              onClose={close}
              onChoose={(typeKey) => {
                close();
                choose(typeKey);
              }}
            />
          ));
        },
      },
    ];
  }

  function menuFor(card: CanvasCard): ActionMenuItem[] {
    const others = cards.filter((item) => item.typeKey !== card.typeKey);
    const type = objectTypeOf(outline!, card.typeKey);
    const application = outline!.applications.find((item) => item.key === card.applicationKey);
    const anchor = () => cardAnchor(card.typeKey);
    return [
      ...listEntries(
        "under",
        (name) => `Put under ${name}`,
        "Canvas",
        others,
        anchor,
        (typeKey) => connect(card.typeKey, { typeKey }, false),
        "Put under",
      ),
      ...(type?.parents.length
        ? [
            {
              id: "top",
              label: "Move to the top level",
              section: "Canvas",
              onAction: () => void act(`${card.name} moved to the top level`, releaseOperations(card.typeKey)),
            } satisfies ActionMenuItem,
          ]
        : []),
      ...listEntries(
        "relate",
        (name) => `Relate to ${name}`,
        "Canvas",
        others,
        anchor,
        (typeKey) => connect(card.typeKey, { typeKey }, true),
        "Relate to",
      ),
      ...(sheet
        ? [
            {
              id: "filter",
              label: "Add a filter…",
              section: "Canvas",
              onAction: () => filterColumn(card.typeKey),
            } satisfies ActionMenuItem,
          ]
        : []),
      ...(application?.navigation.groups ?? []).map((group): ActionMenuItem => ({
        id: `group:${group.key}`,
        label: `Move to group ${group.label}`,
        section: "Canvas",
        onAction: () => connect(card.typeKey, { group: { applicationKey: application!.key, key: group.key } }, false),
      })),
    ];
  }

  /** A sheet tab's menu: the object type its drag onto the board makes, by menu and keyboard (PP-D75). */
  function sheetMenu(name: string): ActionMenuItem[] {
    return [
      {
        id: "new-list",
        label: "Make an object type of this sheet",
        section: "New",
        onAction: () => sheetToSpace(name, { x: 24, y: 24 }),
      },
    ];
  }

  function columnMenu(column: SourceColumn): ActionMenuItem[] {
    const header = column.header ?? "";
    const where = { sheet: column.sheet, header, headers: [header] };
    const anchor = () => columnAnchor(header);
    const owner = sourceOfColumn(profile, column.sheet, header);
    const reading = {
      fill: owner?.fillDown?.includes(header) ?? false,
      headings: owner?.headings?.column === header,
      wide: owner?.unpivot?.columns.includes(header) ?? false,
    };
    return [
      ...listEntries(
        "add",
        (name) => `Add to ${name}`,
        "Fill an object type",
        cards,
        anchor,
        (typeKey) => dropColumn(where, typeKey),
        "Add to",
      ),
      ...(cards.length
        ? listEntries(
            "filterby",
            (name) => `Use as a filter of ${name}`,
            "Filter an object type",
            cards,
            anchor,
            (typeKey) => filterColumn(typeKey, where),
            "Use as a filter of",
          )
        : []),
      ...(chosen.length > 1 && chosen.includes(header)
        ? [
            {
              id: "unpivot",
              label: "Read these columns as rows…",
              section: "Readings",
              onAction: () => unpivotChoose(anchor()),
            } satisfies ActionMenuItem,
          ]
        : []),
      ...(reading.wide && owner
        ? [
            {
              id: "unpivot-clear",
              label: "Stop reading these columns as rows",
              section: "Readings",
              onAction: () =>
                void act("The columns are read as columns again", [{ kind: "clearUnpivot", source: owner.id }]),
            } satisfies ActionMenuItem,
          ]
        : []),
      ...(owner
        ? [
            {
              id: "fill",
              label: reading.fill ? "Stop filling blanks from the cell above" : "Fill blanks from the cell above",
              section: "Readings",
              onAction: () =>
                void act(
                  reading.fill ? `${header} no longer fills blanks` : `Blanks of ${header} filled from the cell above`,
                  fillDownOperations(owner, header, !reading.fill),
                ),
            } satisfies ActionMenuItem,
            reading.headings
              ? ({
                  id: "headings-clear",
                  label: "Stop reading rows holding only this column as headings",
                  section: "Readings",
                  onAction: () =>
                    void act("Headings are read as rows again", [{ kind: "clearHeadingRows", source: owner.id }]),
                } satisfies ActionMenuItem)
              : ({
                  id: "headings",
                  label: "Rows holding only this column are headings…",
                  section: "Readings",
                  onAction: () => headingAsk(header, owner.sheet, owner.objectTypeKey, anchor()),
                } satisfies ActionMenuItem),
          ]
        : []),
      {
        id: "list",
        label: "Make an object type of its values",
        section: "New",
        onAction: () => columnToSpace(where, { x: 24, y: 24 }),
      },
      {
        id: "ignore",
        label: "Leave out",
        section: "New",
        onAction: () => {
          const uses = usesOf(profile, column.sheet, header);
          void act(
            `${header} left out`,
            uses.length
              ? uses.map((use) => ({ kind: "ignoreColumn", source: use.source.id, column: header }))
              : (profile?.sources ?? [])
                  .filter((item) => item.sheet === column.sheet)
                  .slice(0, 1)
                  .map((item) => ({ kind: "ignoreColumn", source: item.id, column: header })),
          );
        },
      },
    ];
  }

  /** Rows holding only one column are headings: what to call the new column, and which list is the parent. */
  function headingAsk(header: string, sheetOf: string, rowType: string, anchor: HTMLElement) {
    const type = objectTypeOf(outline!, rowType);
    const parents = cards
      .filter((card) => card.typeKey !== rowType)
      .map((card) => ({ key: card.typeKey, name: card.name }));
    const taken = new Set([
      ...(source.columns(sheetOf) ?? []).flatMap((item) => (item.header ? [item.header] : [])),
      ...addedColumns(profile, sheetOf).map((item) => item.header),
    ]);
    let initialInto = `${header} heading`;
    for (let n = 2; taken.has(initialInto); n += 1) initialInto = `${header} heading ${n}`;
    openAsk((close) => (
      <HeadingPopover
        anchor={anchor}
        column={header}
        initialInto={initialInto}
        parents={parents}
        initialParent={type?.parents.find((key) => parents.some((item) => item.key === key))}
        onClose={close}
        onSubmit={(answer) => {
          close();
          void act(
            `Rows holding only ${header} read as headings`,
            headingOperations({ sheet: sheetOf, column: header, rowType, ...answer }, profile, outline!),
          );
        }}
      />
    ));
  }

  /** A press on a row number of the preview: that row is the header, for the sources that read the sheet. */
  function headerRowOf(row: number) {
    if (!sheet) return;
    // The source whose block the preview shows (the pane reads the first one of the sheet), as Adjust list… does.
    const owner = (profile?.sources ?? []).find((item) => item.sheet === sheet.name);
    if (!owner) return;
    void act(`Row ${row} of ${sheet.name} read as the header`, [
      { kind: "setSource", source: owner.id, headerRow: row },
    ]);
  }

  /** A field dragged back onto the workbook leaves its columns out. */
  function fieldBack(event: DragEvent) {
    const [typeKey, fieldId] = event.dataTransfer.getData(DRAG_FIELD).split("\u0000");
    const field = cardOf(typeKey)?.fields.find((item) => item.id === fieldId);
    if (!field?.columns.length) return;
    event.preventDefault();
    void act(`${field.label} no longer loads`, leaveOutOperations(field));
  }

  const refusedOf = (typeKey: string) => {
    const reasons = figures.byType[typeKey]?.reasons ?? [];
    if (reasons.length) setDialog({ kind: "refused", typeKey, reasons: reasons.map((item) => ({ ...item })) });
  };

  /** The profile source a dry run's source number stands for, to correct a column's values. */
  function correctValues(reason: Reason, found: WrongValues) {
    const ran = source.dryRun?.summary?.sources.find((item) => item.source === reason.source);
    const owner = (profile?.sources ?? []).find(
      (item) => item.sheet === ran?.sheet && item.objectTypeKey === ran?.objectTypeKey,
    );
    if (!owner) return;
    const use = usesOf(profile, owner.sheet, found.column).find((item) => item.source.id === owner.id);
    setDialog({
      kind: "valueMap",
      sourceId: owner.id,
      sheet: owner.sheet,
      header: found.column,
      mapName: use?.binding.valueMap,
      suggested: found.values,
    });
  }

  const changed = outline.objectTypes.filter((type) => type.mark !== "released").length;
  const previewCard = preview ? cardOf(preview.typeKey) : undefined;
  const moreItems: ActionMenuItem[] = [
    ...(forThisWorkspace ? draftActions.items(["install", "load"]) : draftActions.items(["load"])),
    ...draftActions.items(["workbook", "json"]),
    ...(source.file
      ? [{ id: "propose", label: "Propose again…", disabled: proposing, onAction: () => setProposeOpen(true) }]
      : []),
    ...draftActions.items(["delete"]),
  ];
  const lineOpen = lines.find((item) => item.id === openLine);
  // The preview's band stands in the strip's place while a type's preview or layout editor is shown.
  const shownPreview =
    preview && previewCard && activeModel ? (
      <DraftPreview
        editing={editing}
        mode={preview.mode}
        objectTypeKey={preview.typeKey}
        applicationKey={previewCard.applicationKey}
        activeModel={activeModel}
        workspaceKey={editorWorkspace}
        compact
        bandIn={bandSlot}
        onShowIssues={() => {
          setDrawerTab("issues");
          drawer.show();
        }}
        actions={
          <>
            {preview.mode === "preview" ? (
              <button type="button" className="primary" onClick={() => setPreview({ ...preview, mode: "layout" })}>
                <Icon name="pencil" /> Edit layout
              </button>
            ) : (
              <>
                <button type="button" className="secondary" disabled={busy} onClick={() => void editing.undo()}>
                  <Icon name="undo" /> Undo
                </button>
                <button type="button" className="secondary" disabled={busy} onClick={() => void editing.redo()}>
                  <Icon name="redo" /> Redo
                </button>
                <button type="button" className="secondary" onClick={() => setPreview({ ...preview, mode: "preview" })}>
                  Preview
                </button>
              </>
            )}
            <button type="button" className="secondary" onClick={() => setPreview(undefined)}>
              <Icon name="arrow-left" /> Back to the board
            </button>
          </>
        }
      />
    ) : undefined;

  return (
    <div className={`workbook-canvas${phone ? " phone" : ""}`}>
      <header className="canvas-top">
        <div className="canvas-title">
          <span className="canvas-eyebrow">Model draft · canvas</span>
          <h1>{steps.draft?.name ?? "Model draft"}</h1>
          {fileName && <span className="canvas-file">{fileName}</span>}
        </div>
        <DraftViewSwitch
          draftId={draftId}
          view="canvas"
          onChange={(view) => onNavigate(draftViewRoute(draftId, view, { forWorkspace: forThisWorkspace, journey }))}
        />
        <div className="canvas-actions">
          {forThisWorkspace ? (
            <button type="button" className="primary" disabled={proposing} onClick={() => draftActions.open("apply")}>
              Apply to this workspace…
            </button>
          ) : (
            <>
              {canCreate && (
                <button type="button" className="primary" onClick={() => setDialog({ kind: "create" })}>
                  Create workspace…
                </button>
              )}
              <button
                type="button"
                className={canCreate ? "secondary" : "primary"}
                disabled={proposing}
                onClick={() => draftActions.open("install")}
              >
                Install and activate…
              </button>
            </>
          )}
          <ActionMenu label="More actions" items={moreItems} />
        </div>
      </header>
      {shownPreview ? (
        <div className="canvas-preview-band" ref={setBandSlot} />
      ) : (
        <div className="canvas-count-strip">
          <div className="canvas-strip-group canvas-strip-scope">
            <span>Showing</span>
            <div className="segmented" role="group" aria-label="What the board shows">
              {scopes.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  aria-pressed={scope === item.id}
                  onClick={() => doc.chooseScope(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
            {/* Without a workbook there is no workbook pane: a workbook is added here, where its scope would stand. */}
            {!hasFile && draftActions.has("workbook") && (
              <button
                type="button"
                className="secondary"
                disabled={proposing}
                onClick={() => draftActions.open("workbook")}
              >
                {draftActions.label("workbook")}
              </button>
            )}
          </div>
          <div className="canvas-strip-group canvas-strip-tools">
            <CanvasFind outline={outline} onGo={goTo} />
            <div className="canvas-actions">
              <button type="button" onClick={() => void editing.undo()} disabled={busy}>
                <Icon name="undo" size={14} /> Undo
              </button>
              <button type="button" onClick={() => void editing.redo()} disabled={busy}>
                <Icon name="redo" size={14} /> Redo
              </button>
              {cards.length > 1 && !phone && (
                <button type="button" onClick={() => savePositions(tidy(cards, lines, boardWidth))}>
                  Tidy
                </button>
              )}
              <AddMenu
                outline={outline}
                onOperation={(operation, target, preset) => {
                  if (operation.id === "add-type") addWatch.current = true;
                  if (isAddedKind(operation.id))
                    addedElement.current = { id: operation.id, known: addedKeys(operation.id, outline) };
                  editing.operate(operation, target, preset);
                }}
              />
            </div>
          </div>
          <div className="canvas-strip-group canvas-strip-summary">
            <span className="canvas-pill">{counted(outline.applications.length, "application")}</span>
            <span className="canvas-pill">{counted(outline.objectTypes.length, "object type")}</span>
            {changed > 0 && <span className="canvas-pill canvas-pill-loads">{changed} changed</span>}
          </div>
          {hasFile && (
            <span className="canvas-check" role="status">
              {figures.state === "none" && <span>No check has run yet: it runs after the first step.</span>}
              {figures.state === "checking" && <span className="canvas-pill">Checking…</span>}
              {figures.state === "failed" && <span>The check could not finish. The next step runs it again.</span>}
              {figures.state === "checked" && (
                <>
                  <span>Workbook check: {count(figures.total)} rows, every one</span>
                  <span className="canvas-pill canvas-pill-loads">{count(figures.loads)} load</span>
                  <span className={`canvas-pill${figures.refused ? " canvas-pill-refused" : ""}`}>
                    {count(figures.refused)} refused
                  </span>
                </>
              )}
            </span>
          )}
        </div>
      )}
      <div className="canvas-notices">
        <DraftEditingNotices editing={editing} busy={busy} />
        {notice && (
          <div className="canvas-notice">
            <Notice tone={notice.tone}>{notice.text}</Notice>
          </div>
        )}
      </div>
      <div className={`canvas-grid${hasFile ? "" : " no-workbook"}`}>
        {hasFile && (
          <WorkbookPane
            sheets={sheets}
            sheet={sheet}
            onSheet={setSheetName}
            menuForSheet={sheetMenu}
            columns={columns}
            profile={profile}
            proposed={proposedElements}
            fileId={source.profile?.sourceFile?.id}
            hasFile={hasFile}
            error={source.error}
            canDrag={!phone}
            editable={editable}
            chosen={chosen}
            onChosen={(headers) => sheet && setPicked({ sheet: sheet.name, headers })}
            onOpenColumn={(header) => sheet && toSelection({ element: "column", sheet: sheet.name, key: header })}
            menuFor={columnMenu}
            onUnpivot={unpivotChoose}
            onHeaderRow={headerRowOf}
            onFieldBack={fieldBack}
          />
        )}
        <div className="canvas-main" ref={boardBox}>
          {shownPreview ?? (
            <CanvasBoard
              cards={cards}
              lines={lines}
              positions={positions}
              figures={figures}
              outline={outline}
              selection={pick}
              editable={editable}
              canDrag={!phone}
              busy={busy}
              hasWorkbook={hasFile}
              zoom={zoom}
              flow={phone}
              apiRef={boardApi}
              onZoom={setZoom}
              onSelect={toSelection}
              onMove={(typeKey, position) => savePositions({ [typeKey]: position })}
              onColumnDrop={dropColumn}
              onColumnToSpace={columnToSpace}
              onSheetToSpace={sheetToSpace}
              onConnect={connect}
              onConnectMenu={connectMenu}
              onFilter={filterColumn}
              onRemoveLine={removeLine}
              onRefused={refusedOf}
              onFold={foldCard}
              onRenameList={renameList}
              onRenameField={renameField}
              onMoveAttribute={moveAttribute}
              onReorderAttribute={reorderAttribute}
              onStepAttribute={stepAttribute}
              onOpenSheet={openSheet}
              openMenu={menu}
              onOpenMenu={setMenu}
              onOperation={editing.operate}
              menuFor={menuFor}
              openLine={lineOpen?.id}
              onOpenLine={(line) => {
                setOpenLine(line?.id);
                setMenu(undefined);
              }}
              linePopover={(line) => {
                const target = targetOfLine(line, outline);
                if (!target || target.on !== "relation") return null;
                return (
                  <LinePopover
                    title={line.label}
                    target={target}
                    outline={outline}
                    contains={line.kind === "contains"}
                    onOperation={editing.operate}
                    run={(operations) => void editing.runGuarded(operations)}
                    onClose={() => setOpenLine(undefined)}
                    menuOpen={menu === `line:${line.id}`}
                    onMenuOpenChange={(open) => setMenu(open ? `line:${line.id}` : undefined)}
                  />
                );
              }}
            />
          )}
        </div>
        <div className="canvas-inspector-box" ref={inspectorBox}>
          <CanvasInspector
            editing={editing}
            outline={outline}
            selection={selection ?? selectionOfPick(pick)}
            cards={cards}
            lines={lines}
            source={source}
            sourceDialogs={sourceDialogs}
            busy={busy}
            proposedElements={proposedElements}
            phone={phone}
            tab={tab}
            onTab={setTab}
            onPick={toSelection}
            onPreview={activeModel ? (typeKey, mode) => setPreview({ typeKey, mode }) : undefined}
            consumer={consumer}
            onConsumer={setConsumer}
            panel={panel}
            onPanel={setPanel}
          />
        </div>
      </div>
      <IssuesDrawer
        editing={editing}
        outline={outline}
        history={history}
        source={source}
        sourceDialogs={sourceDialogs}
        proposing={proposing}
        tab={drawerTab}
        onTab={setDrawerTab}
        open={drawer.open}
        onToggle={drawer.toggle}
        onSelect={followIssue}
      />
      {ask?.render(closeAsk)}
      {rows && <DryRunRowsDialog draftId={draftId} rows={rows} onClose={() => setRows(undefined)} />}
      {proposeOpen && source.file && (
        <ProposeDialog
          fileName={source.file.name}
          initialMode={inference.inference?.mode}
          onPropose={(requested) => {
            setProposeOpen(false);
            void inference.propose(requested).catch((cause) => setNotice({ tone: "error", text: errorMessage(cause) }));
          }}
          onClose={() => setProposeOpen(false)}
        />
      )}
      {dialog?.kind === "refused" && (
        <RefusedDialog
          draftId={draftId}
          list={typeName(outline, dialog.typeKey)}
          reasons={dialog.reasons}
          onClose={() => setDialog(undefined)}
          onSeeRows={(reason) => {
            setDialog(undefined);
            setRows({
              source: reason.source,
              status: "rejected",
              code: reason.code,
              title: `${typeName(outline, dialog.typeKey)}: ${reason.rows} rows refused`,
            });
          }}
          onCorrect={(reason, found) => correctValues(reason, found)}
        />
      )}
      {dialog?.kind === "valueMap" && (
        <ValueMapDialog
          source={dialog.sourceId}
          header={dialog.header}
          mapName={dialog.mapName}
          column={columnOf(dialog.sheet, dialog.header)}
          suggested={dialog.suggested}
          profile={profile}
          outline={outline}
          run={run}
          onClose={() => setDialog(undefined)}
        />
      )}
      {dialog?.kind === "create" && fileName && (
        <CreateWorkspaceDialog
          draftId={draftId}
          latestVersion={steps.latestVersion}
          fileName={fileName}
          initialName={steps.draft?.name ?? ""}
          figures={figures.state === "checked" ? { loads: figures.loads, refused: figures.refused } : undefined}
          onClose={() => setDialog(undefined)}
          onCreated={(createdKey) => {
            setDialog(undefined);
            // The workspace's own page, where the load's progress and result are shown (as New workspace from a workbook lands).
            openWorkspace(createdKey, onNavigate);
          }}
        />
      )}
      <DraftEditingDialogs editing={editing} busy={busy} />
      {sourceDialogs.dialogs}
      {draftActions.dialogs}
    </div>
  );
}
