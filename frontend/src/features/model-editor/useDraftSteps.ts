/**
 * A model draft read as its outline, and steps sent at its version (0.17 PL3b, PP-D3): what the
 * workbook canvas and the model editor both need to change one draft. A step answers "applied", or
 * "stale" when the draft moved on elsewhere since it was read: the outline is then read again and
 * nothing was written. Every other refusal is thrown to the caller, to be said in its words.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { DraftOperation, ModelDraftOperationEntry, ModelDraftOutline, ModelDraftStep } from "@/types/modelAdmin";

export type StepOutcome = "applied" | "stale";

type Send = (expectedVersion: number) => Promise<ModelDraftStep>;

/** A step refused because the draft moved on (D41): what came first, and how to send it again. */
export interface StaleStep {
  since: ModelDraftOperationEntry[];
  more: boolean;
  send: Send;
}

export interface DraftStepsOptions {
  /** Every answer of a step the draft applied: a queued dry run, what it removed, a key it changed. */
  onAnswer?: (answer: ModelDraftStep) => void;
  /** A step refused because the draft moved on: the outline is read again, nothing was written. */
  onStale?: (stale: StaleStep) => void;
}

export interface DraftSteps {
  outline?: ModelDraftOutline;
  /** The draft's name and whether it builds on a release, once read. */
  draft?: { name: string; ownBase: boolean; workspaceKey?: string | null };
  loadError: string;
  /** Reads the outline again. */
  reload: () => Promise<ModelDraftOutline>;
  /** The draft's version as last read, for a dialog that sends its own steps. */
  latestVersion: () => number;
  /** Sends one request at the draft's present version. */
  step: (send: Send) => Promise<StepOutcome>;
  /** Operations as one request and one undo step. */
  run: (operations: DraftOperation[]) => Promise<StepOutcome>;
  /** Undoes the last step, or the listed ones together. */
  undo: (steps?: number[]) => Promise<StepOutcome>;
  redo: () => Promise<StepOutcome>;
}

export function useDraftSteps(draftId: string, options: DraftStepsOptions = {}): DraftSteps {
  const [outline, setOutline] = useState<ModelDraftOutline>();
  const [draft, setDraft] = useState<DraftSteps["draft"]>();
  const [loadError, setLoadError] = useState("");
  const version = useRef(0);
  const handlers = useRef(options);
  useEffect(() => {
    handlers.current = options;
  });

  const reload = useCallback(async () => {
    const next = await api.modelDraftOutline(draftId);
    version.current = next.version;
    setOutline(next);
    return next;
  }, [draftId]);

  useEffect(() => {
    let cancelled = false;
    Promise.all([api.modelDraftOutline(draftId), api.modelDraft(draftId)])
      .then(([next, read]) => {
        if (cancelled) return;
        version.current = next.version;
        setOutline(next);
        setDraft({ name: read.name, ownBase: read.baseReleaseId !== null, workspaceKey: read.workspaceKey });
      })
      .catch((cause) => {
        if (!cancelled) setLoadError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [draftId]);

  // Steps go out one after another (PP-D9: the page still takes the next gesture at once): each is sent at the
  // version the previous answer returned, so two quick gestures of one person never conflict with each other.
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const exchange = useCallback(
    async (send: Send): Promise<StepOutcome> => {
      try {
        const answer = await send(version.current);
        version.current = answer.version;
        handlers.current.onAnswer?.(answer);
      } catch (cause) {
        if (!isApiError(cause, "VERSION_CONFLICT")) throw cause;
        const details = (cause.details ?? {}) as { operations?: ModelDraftOperationEntry[]; more?: boolean };
        handlers.current.onStale?.({ since: details.operations ?? [], more: Boolean(details.more), send });
        await reload();
        return "stale";
      }
      await reload();
      return "applied";
    },
    [reload],
  );
  const step = useCallback<DraftSteps["step"]>(
    (send) => {
      const sent = queue.current.then(() => exchange(send));
      queue.current = sent.catch(() => undefined);
      return sent;
    },
    [exchange],
  );
  const run = useCallback<DraftSteps["run"]>(
    (operations) => step((at) => api.applyModelDraftOperations(draftId, at, operations)),
    [draftId, step],
  );
  const undo = useCallback(
    (steps?: number[]) => step((at) => api.undoModelDraftStep(draftId, at, steps)),
    [draftId, step],
  );
  const redo = useCallback(() => step((at) => api.redoModelDraftStep(draftId, at)), [draftId, step]);

  const latestVersion = useCallback(() => version.current, []);
  return { outline, draft, loadError, reload, latestVersion, step, run, undo, redo };
}
