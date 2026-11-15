/**
 * The move editor's dry run (0.11 X4, D140): one dry run of every item per state of the mapping,
 * the selection and copy or move. A new state cancels the run before it and starts the next; the
 * figures are the last finished run's, with the run before it kept for the differences. A run named
 * by the address (after a reload) is followed again while it was asked for the same state.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/api/client";
import { errorMessage, isApiError } from "@/api/errors";
import type { Job, MappingProblem, MoveRequest } from "@/types";
import { isFinal, isResting, useFollowedJob } from "@/state/useFollowedJob";
import { figuresOf, jobRunKey, runKey, type Figures } from "@/model/moveRun";
import { useSubjectSeen } from "@/state/useInbox";

export interface MoveDryRun {
  /** The run asked for the current state; it may still be checking. */
  job?: Job;
  /** The last finished run's figures, and those of the finished run before it. */
  figures?: Figures;
  previous?: Figures;
  checking: boolean;
  error: string;
  /** The mapping's problems, when the engine refused the run for them (D145). */
  problems: MappingProblem[];
  /** Start the run again for the current state, such as after the mapping changed elsewhere. */
  rerun: () => void;
  /** The job after its confirmation, as the stream follows it. */
  setJob: (job: Job) => void;
}

export function useMoveDryRun(
  request: MoveRequest | undefined,
  /** The run the address names, followed again when it was asked for this state. */
  addressedJobId: string | undefined,
  /** A run started: the address names it, so a reload follows it. */
  onStarted: (jobId: string) => void,
  /** A confirmed run finished loading (or failed to). */
  onLoaded?: (job: Job) => void,
): MoveDryRun {
  // One run is shown, as it changes: a streamed change of another run is ignored. The answer of a
  // start, or a run read once after a reload, is set through `finish`.
  const { job, setJob } = useFollowedJob(undefined, {
    filter: (next) => !current.current || next.id === current.current.id,
    onChange: (next) => finish(next),
  });
  const [finished, setFinished] = useState<{ now?: Figures; before?: Figures }>({});
  const [error, setError] = useState("");
  const [problems, setProblems] = useState<MappingProblem[]>([]);
  const [attempt, setAttempt] = useState(0);
  const current = useRef<Job>(undefined);
  const started = useRef(onStarted);
  const loaded = useRef(onLoaded);
  useEffect(() => {
    started.current = onStarted;
    loaded.current = onLoaded;
  });
  const key = request ? runKey(request.mapping.expectedVersion, request.selection, request.mode) : undefined;
  const asked = useRef(request);
  useEffect(() => {
    asked.current = request;
  });
  const addressed = useRef(addressedJobId);
  const handled = useRef(0);

  const finish = useCallback(
    (next: Job) => {
      const before = current.current;
      current.current = next;
      setJob(next);
      if (next.confirmedAt && isFinal(next) && !(before?.id === next.id && isFinal(before))) loaded.current?.(next);
      if (next.move && (next.state === "awaiting_confirmation" || next.state === "completed")) {
        const figures = figuresOf(next.move);
        setFinished((shown) =>
          shown.now && JSON.stringify(shown.now) === JSON.stringify(figures)
            ? shown
            : { now: figures, before: shown.now },
        );
      }
    },
    [setJob],
  );

  useEffect(() => {
    const body = asked.current;
    if (!body || !key) return;
    let active = true;
    const run = async () => {
      const shown = current.current;
      // The run the address names, read once after a reload.
      const named = addressed.current;
      if (!shown && named) {
        const found = await api.job(named).catch(() => undefined);
        if (!active) return;
        addressed.current = undefined;
        if (found && jobRunKey(found) === key && !["cancelled", "expired", "failed"].includes(found.state)) {
          setError("");
          finish(found);
          return;
        }
      }
      const forced = attempt !== handled.current;
      handled.current = attempt;
      if (shown && jobRunKey(shown) === key && !forced) return;
      if (shown && !shown.confirmedAt && (shown.state === "awaiting_confirmation" || !isResting(shown)))
        await api.cancelJob(shown.id).catch(() => undefined);
      try {
        const next = await api.startMove(body);
        if (!active) {
          await api.cancelJob(next.id).catch(() => undefined);
          return;
        }
        current.current = next;
        setError("");
        setProblems([]);
        setJob(next);
        started.current(next.id);
      } catch (cause) {
        if (!active) return;
        current.current = undefined;
        setJob(undefined);
        if (isApiError(cause, "MOVE_MAPPING_HAS_PROBLEMS")) {
          const details = cause.details as { problems?: MappingProblem[] } | undefined;
          setError("");
          setProblems(details?.problems ?? []);
        } else setError(errorMessage(cause));
      }
    };
    void run();
    return () => {
      active = false;
    };
  }, [key, attempt, finish, setJob]);

  // The move shown here: its notices are read, and one made while it is shown (0.12 NT1).
  useSubjectSeen(job?.id);

  const checking = Boolean(job && !isResting(job) && !job.confirmedAt);
  return {
    job,
    figures: finished.now,
    previous: finished.before,
    checking,
    error: error || (job?.state === "failed" && !job.confirmedAt ? (job.error?.message ?? "The dry run failed") : ""),
    problems,
    rerun: () => setAttempt((value) => value + 1),
    setJob: finish,
  };
}
