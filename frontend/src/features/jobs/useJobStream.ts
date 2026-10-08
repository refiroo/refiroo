/**
 * Follow a job as it changes (0.9 J1u, J24.7): the engine pushes the job over a server-sent event
 * stream at once and after each committed change; nothing is polled. The stream is closed once the
 * job reaches a final state, so the browser does not reconnect to a stream the engine has ended, or
 * once a preview waits for confirmation (`isResting`).
 */

import { useEffect, useRef } from "react";
import { jobEventsUrl } from "@/api/client";
import type { Job, JobState } from "@/types";

export const FINAL_STATES: readonly JobState[] = ["completed", "failed", "cancelled", "expired"];

export const isFinal = (job: Pick<Job, "state">) => FINAL_STATES.includes(job.state);

/**
 * A job that will not change until someone acts: finished, or a preview awaiting confirmation (0.9
 * J4). A preview may wait days, and each stream holds a connection (D63), so it is not followed
 * meanwhile; confirming it starts a new stream.
 */
export const isResting = (job: Pick<Job, "state">) => isFinal(job) || job.state === "awaiting_confirmation";

export function useJobStream(jobId: string | undefined, onJob: (job: Job) => void) {
  const latest = useRef(onJob);
  useEffect(() => {
    latest.current = onJob;
  });
  useEffect(() => {
    if (!jobId) return;
    const source = new EventSource(jobEventsUrl(jobId));
    source.addEventListener("job", (event) => {
      const job = JSON.parse((event as MessageEvent<string>).data) as Job;
      latest.current(job);
      if (isResting(job)) source.close();
    });
    return () => source.close();
  }, [jobId]);
}
