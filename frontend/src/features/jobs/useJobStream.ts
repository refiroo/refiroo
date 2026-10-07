/**
 * Follow a job as it changes (0.9 J1u, J24.7): the engine pushes the job over a server-sent event
 * stream at once and after each committed change; nothing is polled. The stream is closed once the
 * job reaches a final state, so the browser does not reconnect to a stream the engine has ended.
 */

import { useEffect, useRef } from "react";
import { jobEventsUrl } from "@/api/client";
import type { Job, JobState } from "@/types";

export const FINAL_STATES: readonly JobState[] = ["completed", "failed", "cancelled", "expired"];

export const isFinal = (job: Pick<Job, "state">) => FINAL_STATES.includes(job.state);

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
      if (isFinal(job)) source.close();
    });
    return () => source.close();
  }, [jobId]);
}
