import type { JobState, SettingsRoute } from "@/types";

type JobsRoute = Extract<SettingsRoute, { page: "jobs" }>;

export const JOBS: JobsRoute = { kind: "settings", page: "jobs" };

/** A group of related jobs, narrowed to a state when one is given (0.13 JG). */
export const groupRoute = (group: NonNullable<JobsRoute["group"]>, state?: JobState): JobsRoute => ({
  ...JOBS,
  group,
  ...(state ? { state } : {}),
});

/** One job's page; opened from a group, it keeps the group and its state for the trail. */
export const jobRoute = (
  jobId: string,
  from?: { group: NonNullable<JobsRoute["group"]>; state?: JobState },
): JobsRoute => ({
  ...JOBS,
  jobId,
  ...(from ? { group: from.group, ...(from.state ? { state: from.state } : {}) } : {}),
});
