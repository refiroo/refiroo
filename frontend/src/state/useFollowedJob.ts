/**
 * Follow a job as it changes (0.9 J1u, J24.7): the engine pushes the job over a server-sent event
 * stream at once and after each committed change; nothing is polled unless a caller asks for a
 * poll as well. The stream is read with `fetch` so it carries the access token (0.12 I2, D247).
 * It is closed once the job reaches a final state, so the browser does not reconnect to a stream
 * the engine has ended, or once a preview waits for confirmation (`isResting`).
 *
 * One hook serves every caller (SR4). Two forms:
 * - A caller that shows the job keeps it here (the default): the job is read once from `jobId`, or
 *   seeded by the caller (`seed`, or `setJob` with the answer of the request that started it), and
 *   then followed until `done` says it needs no stream. Setting a job that is not done again (the
 *   answer of a confirm) opens the stream again.
 * - A caller that keeps no job passes `keep: false` and only the id: the stream opens for the id
 *   and `onChange`/`onFinal` carry what changed.
 */

import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { api, jobEventsUrl } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { openEventStream } from "@/api/eventStream";
import type { Job, JobState } from "@/types";

export const FINAL_STATES: readonly JobState[] = ["completed", "failed", "cancelled", "expired"];

export const isFinal = (job: Pick<Job, "state">) => FINAL_STATES.includes(job.state);

/**
 * A job that will not change until someone acts: finished, or a preview awaiting confirmation (0.9
 * J4). A preview may wait days, and each stream holds a connection (D63), so it is not followed
 * meanwhile; confirming it starts a new stream.
 */
export const isResting = (job: Pick<Job, "state">) => isFinal(job) || job.state === "awaiting_confirmation";

export interface FollowOptions {
  /** Keep the job in the hook (default), or only follow the id and report through the callbacks. */
  keep?: boolean;
  /** The job as the caller already holds it, so the first read is not made. */
  seed?: Job;
  /** Whether to read the job first when `jobId` is given (default true; only with `keep`). */
  read?: boolean;
  /**
   * When the job needs no stream (only with `keep`): `isResting` by default; `isFinal` for a
   * caller that follows a preview while it waits to be confirmed; or any rule of the caller's.
   */
  done?: (job: Job) => boolean;
  /** A streamed job this returns false for is ignored (a caller that shows one run among several). */
  filter?: (job: Job) => boolean;
  /** Each streamed change; never the first read, so opening a finished job does not run it again. */
  onChange?: (job: Job) => void;
  /** A streamed change that is final. */
  onFinal?: (job: Job) => void;
  /**
   * Also run `run` every `every` ms while `enabled` (by default, while the stream is open): a
   * stream lags a change that has not committed yet, so a caller that reads something else of the
   * job's work reads it again now and then.
   */
  poll?: { every: number; run: () => void; enabled?: boolean };
}

export interface FollowedJob {
  job: Job | undefined;
  /** Replaces the job (the answer of a start, confirm or cancel); a job not done is followed again. */
  setJob: Dispatch<SetStateAction<Job | undefined>>;
  /** Why the first read failed, in words; empty while it has not. */
  error: string;
  /** Reads the job again, clearing the error (the Retry of a failed read). */
  reload: () => void;
  /** Whether the held job needs no stream (`done`). */
  done: boolean;
}

export function useFollowedJob(jobId: string | undefined, options: FollowOptions = {}): FollowedJob {
  const keep = options.keep !== false;
  const [job, setJob] = useState<Job | undefined>(options.seed);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const latest = useRef(options);
  useEffect(() => {
    latest.current = options;
  });
  const seeded = useRef(options.seed?.id);
  const reads = keep && options.read !== false && jobId !== undefined;

  useEffect(() => {
    if (!reads || !jobId) return;
    if (seeded.current === jobId) {
      seeded.current = undefined;
      return;
    }
    let active = true;
    api.job(jobId).then(
      (loaded) => active && setJob(loaded),
      (cause) => active && setError(errorMessage(cause)),
    );
    return () => {
      active = false;
    };
  }, [reads, jobId, attempt]);

  const held = keep && job && (jobId === undefined || job.id === jobId) ? job : undefined;
  const isDone = options.done ?? isResting;
  const done = held ? isDone(held) : false;
  const streamId = keep ? (held && !done ? held.id : undefined) : jobId;

  useEffect(() => {
    if (!streamId) return;
    const source = openEventStream(jobEventsUrl(streamId));
    source.addEventListener("job", (event) => {
      const next = JSON.parse(event.data) as Job;
      const now = latest.current;
      if (now.filter && !now.filter(next)) return;
      if (keep) setJob(next);
      now.onChange?.(next);
      if (isFinal(next)) now.onFinal?.(next);
      if (isResting(next)) source.close();
    });
    return () => source.close();
  }, [streamId, keep]);

  const poll = options.poll;
  const polling = Boolean(poll && (poll.enabled ?? streamId !== undefined));
  const every = poll?.every;
  useEffect(() => {
    if (!polling || every === undefined) return;
    const timer = setInterval(() => latest.current.poll?.run(), every);
    return () => clearInterval(timer);
  }, [polling, every]);

  return {
    job,
    setJob,
    error,
    reload: () => {
      setError("");
      setAttempt((value) => value + 1);
    },
    done,
  };
}
