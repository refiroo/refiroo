/**
 * The draft's inference as the editor needs it (0.10 A6b): the latest inference read after every
 * step (which elements are still as proposed changes with every edit, D92), its proposals read once
 * per inference, and proposing: the inference queued, its job followed over the event stream, and
 * on completion the editor told, so it applies the open proposals as its own step.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { Inference, InferenceRequest, Proposal } from "@/types";
import { isFinal, useJobStream } from "@/features/jobs/useJobStream";

export interface DraftInference {
  inference?: Inference;
  proposals: Proposal[];
  /** Element (`objectType:item`, `column:items/Code`) to the proposal it is still as. */
  proposed: Map<string, Proposal | undefined>;
  /** Element to the AI assistant's applied proposal that named it (0.16 AP1), beside the rules' own. */
  assistantFor: Map<string, Proposal>;
  /** Proposing: the inference queued or running, or its proposals being applied. */
  running: boolean;
  error: string;
  propose: (request: InferenceRequest) => Promise<void>;
  /** The editor applied the proposals (or gave up): proposing has ended. */
  settled: () => void;
}

export function useInference(
  draftId: string,
  version: number | undefined,
  onCompleted: (inference: Inference) => void,
): DraftInference {
  const [inference, setInference] = useState<Inference>();
  const [proposals, setProposals] = useState<{ jobId: string; items: Proposal[] }>();
  const [follow, setFollow] = useState<string>();
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const completed = useRef(onCompleted);
  useEffect(() => {
    completed.current = onCompleted;
  });

  const read = useCallback(
    () =>
      api
        .modelDraftInference(draftId)
        .then((next) => {
          setInference(next);
          return next;
        })
        .catch((cause) => {
          if (!isApiError(cause, "INFERENCE_NOT_FOUND")) setError(errorMessage(cause));
          return undefined;
        }),
    [draftId],
  );

  // Which elements are still the engine's changes with every step.
  useEffect(() => {
    if (version !== undefined) void read();
  }, [read, version]);

  // The proposals, once per completed inference: their evidence and alternatives do not change.
  const jobId = inference?.state === "completed" ? inference.jobId : undefined;
  useEffect(() => {
    if (!jobId || proposals?.jobId === jobId) return;
    let cancelled = false;
    api
      .modelDraftProposals(draftId)
      .then((items) => {
        if (!cancelled) setProposals({ jobId, items });
      })
      .catch((cause) => {
        if (!cancelled) setError(errorMessage(cause));
      });
    return () => {
      cancelled = true;
    };
  }, [draftId, jobId, proposals?.jobId]);

  useJobStream(follow, (job) => {
    if (!isFinal(job)) return;
    setFollow(undefined);
    void read().then((next) => {
      if (next?.state === "completed") completed.current(next);
      else {
        setRunning(false);
        setError(next?.error?.message ?? "The inference did not complete; propose again from the ⋯ menu.");
      }
    });
  });

  const propose = useCallback(
    async (request: InferenceRequest) => {
      setError("");
      setRunning(true);
      try {
        const started = await api.proposeFromWorkbook(draftId, request);
        setInference(started);
        setFollow(started.jobId);
      } catch (cause) {
        setRunning(false);
        setError(errorMessage(cause));
      }
    },
    [draftId],
  );

  const items = useMemo(() => (proposals && proposals.jobId === jobId ? proposals.items : []), [proposals, jobId]);
  const proposed = useMemo(() => {
    const byId = new Map(items.map((item) => [item.id, item]));
    return new Map(
      (inference?.proposed ?? []).map((item) => [
        item.element,
        item.proposalId ? byId.get(item.proposalId) : undefined,
      ]),
    );
  }, [inference, items]);

  const assistantFor = useMemo(() => {
    const named = new Map<string, Proposal>();
    for (const proposal of items)
      if (proposal.pattern === "assistant" && proposal.status === "applied")
        for (const operation of proposal.operations) {
          const type = (operation.element as { objectType?: string } | undefined)?.objectType;
          if (operation.kind === "setLabel" && type) named.set(`objectType:${type}`, proposal);
        }
    return named;
  }, [items]);

  return {
    inference,
    proposals: items,
    proposed,
    assistantFor,
    running,
    error,
    propose,
    settled: useCallback(() => setRunning(false), []),
  };
}
