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
import { isFinal, useFollowedJob } from "@/state/useFollowedJob";

export interface DraftInference {
  inference?: Inference;
  proposals: Proposal[];
  /** Element (`objectType:item`, `column:items/Code`) to the proposal it is still as. */
  proposed: Map<string, Proposal | undefined>;
  /** Proposing: the inference queued or running, or its proposals being applied. */
  running: boolean;
  error: string;
  propose: (request: InferenceRequest) => Promise<void>;
  /** Cancels the running inference: nothing is applied and proposing has ended. */
  stop: () => Promise<void>;
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
  // The job whose end was handled: a late read that still says checking must not resume it.
  const ended = useRef<string | undefined>(undefined);
  // Stop pressed while the start request is still out: the job id is not known yet, so the start
  // cancels the job itself once it is (R17-F49).
  const starting = useRef(false);
  const stopAsked = useRef(false);
  const completed = useRef(onCompleted);
  useEffect(() => {
    completed.current = onCompleted;
  });

  const read = useCallback(
    (fresh = false) =>
      api
        .modelDraftInference(draftId, fresh)
        .then((next) => {
          setInference(next);
          // The editor opened (or reloaded) while the inference runs: pick its job up.
          if (next.state === "checking" && ended.current !== next.jobId) {
            setFollow((now) => now ?? next.jobId);
            setRunning(true);
          }
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

  useFollowedJob(follow, {
    keep: false,
    onChange: (job) => {
      if (!isFinal(job)) {
        // The job moved on: read the inference again.
        void read();
        return;
      }
      setFollow(undefined);
      ended.current = job.id;
      // A read of its own: one already in flight (the poll below) may answer from before the end.
      void read(true).then((next) => {
        if (next?.state === "completed") completed.current(next);
        else {
          setRunning(false);
          setError(next?.error?.message ?? "The inference did not complete; propose again from the ⋯ menu.");
        }
      });
    },
    // A job's change is pushed when it commits; reading now and then keeps the read from lagging.
    poll: { every: 3000, run: () => void read() },
  });

  const stop = useCallback(async () => {
    if (!follow) {
      if (starting.current) stopAsked.current = true;
      return;
    }
    try {
      await api.cancelJob(follow);
    } catch (cause) {
      setError(errorMessage(cause));
    }
    ended.current = follow;
    setFollow(undefined);
    setRunning(false);
    await read();
  }, [follow, read]);

  const propose = useCallback(
    async (request: InferenceRequest) => {
      setError("");
      setRunning(true);
      starting.current = true;
      stopAsked.current = false;
      try {
        const started = await api.proposeFromWorkbook(draftId, request);
        setInference(started);
        if (stopAsked.current) {
          ended.current = started.jobId;
          try {
            await api.cancelJob(started.jobId);
          } catch (cause) {
            setError(errorMessage(cause));
          }
          setRunning(false);
          await read();
        } else {
          setFollow(started.jobId);
        }
      } catch (cause) {
        setRunning(false);
        setError(errorMessage(cause));
      } finally {
        starting.current = false;
        stopAsked.current = false;
      }
    },
    [draftId, read],
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

  return {
    inference,
    proposals: items,
    proposed,
    running,
    error,
    stop,
    propose,
    settled: useCallback(() => setRunning(false), []),
  };
}
