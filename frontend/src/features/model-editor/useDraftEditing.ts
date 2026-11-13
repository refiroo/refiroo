/**
 * What a page needs to edit a model draft the way the model editor does (0.17 CE1, PP-D3, PP-D79): the
 * draft's steps (`useDraftSteps`) with the editor's surroundings extracted from `ModelEditor` so that a
 * second page, the canvas, uses the same ones and no copy.
 *
 * - `guarded`: runs an action and says a refusal in its words, or asks about the dependants of an undo;
 * - `notice` and `stale`: what the last step could not keep, and a step held back because the draft moved
 *   on (D41), shown by `DraftEditingNotices`;
 * - `operate`: starts an operation from its menu for a target: straight away, as a flip, in Move to…, or
 *   in the operation dialog under the control that started it (`useOperationAnchor`, UX1); the dialogs
 *   are shown by `DraftEditingDialogs`;
 * - `setPaused`: editing waits while the engine proposes, so nothing a person changes is lost.
 *
 * A page that only reads the draft does not need it; `useDraftSteps` stays the plain layer under it.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { isApiError } from "@/api/errors";
import type { DraftOperation, EditorSelection, ModelDraftOutline, ModelDraftStep } from "@/types";
import { dependantsOf } from "@/features/model-editor/DependantsDialog";
import { followKeyChange, removedWords } from "@/features/model-editor/history";
import { refusalText, type StepOutcome } from "@/features/model-editor/OperationDialog";
import {
  flipField,
  initialValues,
  type FieldValues,
  type OperationSpec,
  type OperationTarget,
} from "@/features/model-editor/operations";
import { nameOf } from "@/features/model-editor/outline";
import type { MoveSubject } from "@/features/model-editor/MoveToDialog";
import { useDraftSteps, type DraftSteps, type StaleStep } from "@/features/model-editor/useDraftSteps";
import { useOperationAnchor } from "@/features/model-editor/useOperationAnchor";

/** The dialogs an operation can open: its form or question, Move to…, and the undo of dependants. */
export type EditingDialog =
  | {
      kind: "operation";
      operation: OperationSpec;
      target: OperationTarget;
      preset?: FieldValues;
      /** The control it was started from, under which a small operation opens. */
      anchor: HTMLElement | null;
    }
  | { kind: "move"; subject: MoveSubject; target?: string }
  | { kind: "dependants"; steps: number[]; dependants: number[] };

/** What the page says after a step: a refusal, what was removed, or the end of an install. */
export interface DraftNotice {
  tone: "error" | "success" | "warning";
  text: string;
  /** Applications the notice offers to open. */
  applications?: string[];
  /** The workspace the applications open in. */
  workspaceKey?: string;
}

export interface DraftEditingOptions {
  /** The selected element: a step that changes its key makes the selection follow it. */
  selection?: EditorSelection;
  onSelect?: (selection: EditorSelection) => void;
  /** Every answer of an applied step, after the hook's own reading of it (a queued dry run). */
  onAnswer?: (answer: ModelDraftStep) => void;
  /** An undo or redo went through: where the page shows the history. */
  onUndone?: () => void;
}

export interface DraftEditing {
  draftId: string;
  steps: DraftSteps;
  outline?: ModelDraftOutline;
  /** A step held back because the draft moved on, and how to send it again. */
  stale?: StaleStep;
  clearStale: () => void;
  notice?: DraftNotice;
  setNotice: (notice: DraftNotice | undefined) => void;
  /** An action of this hook is running. */
  working: boolean;
  /** Pauses editing while the engine proposes: a step then throws, apart from the proposals' own. */
  setPaused: (paused: boolean) => void;
  /** Sends one request at the draft's version; a stale version holds it and asks (D41). */
  step: (send: (version: number) => Promise<ModelDraftStep>, applyingProposals?: boolean) => Promise<StepOutcome>;
  /** Operations as one request and one undo step; a refusal is thrown, for a dialog that says it. */
  run: (operations: DraftOperation[]) => Promise<StepOutcome>;
  /** `run`, with the step the draft made of it: for a toast whose Undo takes back that step, not the last one. */
  runAnswered: (operations: DraftOperation[]) => Promise<{ outcome: StepOutcome; step?: number }>;
  /** Runs an action; a refusal is said in a notice, the dependants of an undo asked about. */
  guarded: (action: () => Promise<unknown>) => Promise<void>;
  /** `run` under `guarded`: for a control that has no surface of its own to say a refusal. */
  runGuarded: (operations: DraftOperation[]) => Promise<void>;
  undo: (steps?: number[]) => Promise<void>;
  redo: () => Promise<void>;
  /** Starts an operation for a target, as its menu does (the one entry for every surface). */
  operate: (operation: OperationSpec, target: OperationTarget, preset?: FieldValues) => void;
  dialog?: EditingDialog;
  openDialog: (dialog: EditingDialog) => void;
  closeDialog: () => void;
  /** The element's operations menu, opened by a shortcut. */
  menuOpen: boolean;
  setMenuOpen: (open: boolean) => void;
  /** The control an operation was started from, for a dialog the page opens itself. */
  anchor: () => HTMLElement | null;
}

export function useDraftEditing(draftId: string, options: DraftEditingOptions = {}): DraftEditing {
  const [stale, setStale] = useState<StaleStep>();
  const [notice, setNotice] = useState<DraftNotice>();
  const [working, setWorking] = useState(false);
  const [dialog, setDialog] = useState<EditingDialog>();
  const [menuOpen, setMenuOpen] = useState(false);
  const paused = useRef(false);
  const anchor = useOperationAnchor();
  // The selection and outline a step's answer is compared with: a changed key of the selected element
  // follows, and what the step removed is named in the outline it was read against.
  const handlers = useRef(options);
  const outlineNow = useRef<ModelDraftOutline>(undefined);
  const steps = useDraftSteps(draftId, {
    onAnswer: (answer) => {
      handlers.current.onAnswer?.(answer);
      // What the step could not keep anywhere is said, not dropped in silence.
      const removed = answer.entries.flatMap((entry) => entry.removed ?? []);
      if (removed.length && outlineNow.current)
        setNotice({ tone: "warning", text: removedWords(removed, nameOf(outlineNow.current)) });
      const selected = handlers.current.selection;
      const followed = selected && followKeyChange(selected, answer.entries);
      if (followed) handlers.current.onSelect?.(followed);
    },
    onStale: setStale,
  });
  const { outline, step: sendStep } = steps;
  useEffect(() => {
    handlers.current = options;
    outlineNow.current = outline;
  });

  const setPaused = useCallback((value: boolean) => {
    paused.current = value;
  }, []);

  const step = useCallback<DraftEditing["step"]>(
    async (send, applyingProposals = false) => {
      if (paused.current && !applyingProposals)
        throw new Error("Editing is paused until the proposals are applied, so nothing you change is lost.");
      setNotice(undefined);
      const outcome = await sendStep(send);
      if (outcome === "applied") setStale(undefined);
      return outcome;
    },
    [sendStep],
  );
  const run = useCallback<DraftEditing["run"]>(
    (operations) => step((at) => api.applyModelDraftOperations(draftId, at, operations)),
    [draftId, step],
  );

  const runAnswered = useCallback<DraftEditing["runAnswered"]>(
    async (operations) => {
      let answered: ModelDraftStep | undefined;
      const outcome = await step(async (at) => {
        answered = await api.applyModelDraftOperations(draftId, at, operations);
        return answered;
      });
      return { outcome, step: answered?.entries[0]?.step };
    },
    [draftId, step],
  );

  const guarded = useCallback<DraftEditing["guarded"]>(async (action) => {
    setWorking(true);
    try {
      await action();
    } catch (cause) {
      if (isApiError(cause, "OPERATION_HAS_DEPENDANTS"))
        setDialog({ kind: "dependants", ...dependantsOf(cause.details) });
      else setNotice({ tone: "error", text: refusalText(cause, outlineNow.current) });
    } finally {
      setWorking(false);
    }
  }, []);
  const runGuarded = useCallback((operations: DraftOperation[]) => guarded(() => run(operations)), [guarded, run]);
  const undo = useCallback(
    (which?: number[]) =>
      guarded(async () => {
        await step((at) => api.undoModelDraftStep(draftId, at, which));
        handlers.current.onUndone?.();
      }),
    [draftId, guarded, step],
  );
  const redo = useCallback(
    () =>
      guarded(async () => {
        await step((at) => api.redoModelDraftStep(draftId, at));
        handlers.current.onUndone?.();
      }),
    [draftId, guarded, step],
  );

  const operate = useCallback<DraftEditing["operate"]>(
    (operation, target, preset) => {
      setMenuOpen(false);
      const model = outlineNow.current;
      if (!model) return;
      if (operation.move === "attribute" && target.on === "attribute")
        setDialog({
          kind: "move",
          subject: { kind: "attribute", objectType: target.objectType, attributeType: target.attributeType },
        });
      else if (operation.move === "objectType" && target.on === "objectType")
        setDialog({ kind: "move", subject: { kind: "objectType", objectType: target.objectType } });
      else if (operation.direct) void guarded(() => run(operation.build({}, target as never, model)));
      else if (flipField(operation, target, model)) {
        // A yes or no with nothing else to ask flips from where it stands, as a direct operation does.
        const field = flipField(operation, target, model)!;
        const values = { ...initialValues(operation, target, model), ...preset };
        void guarded(() =>
          run(operation.build({ ...values, [field.name]: values[field.name] !== true }, target as never, model)),
        );
      } else setDialog({ kind: "operation", operation, target, preset, anchor: anchor() });
    },
    [anchor, guarded, run],
  );

  return {
    draftId,
    steps,
    outline,
    stale,
    clearStale: () => setStale(undefined),
    notice,
    setNotice,
    working,
    setPaused,
    step,
    run,
    runAnswered,
    guarded,
    runGuarded,
    undo,
    redo,
    operate,
    dialog,
    openDialog: setDialog,
    closeDialog: () => setDialog(undefined),
    menuOpen,
    setMenuOpen,
    anchor,
  };
}
