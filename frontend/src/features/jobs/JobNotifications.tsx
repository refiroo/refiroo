/**
 * Notifications about the jobs this tab started (0.9 J1u, D59, D63). A job is followed from the
 * moment it is started until it ends, over its own event stream; the jobs are remembered for the
 * tab (`sessionStorage`), so a reload follows them again. When a job ends, a notification says so:
 * a completed export links to its file and its job page, a failed or cancelled job to its page,
 * which shows why. A closed browser is told nothing.
 */

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { jobOutputUrl } from "@/api/client";
import { routePath } from "@/routing/routes";
import type { EngineModel, Job, RouteState } from "@/types";
import { useToast, type ToastAction } from "@/ui/Toast";
import { isFinal, useJobStream } from "./useJobStream";

const STORAGE_KEY = "rdm.followedJobs";

interface JobNotifications {
  /** Follow a job this tab started, saying it started. */
  follow: (job: Job) => void;
}

const JobNotificationsContext = createContext<JobNotifications | undefined>(undefined);

function remembered(): string[] {
  try {
    const value = JSON.parse(window.sessionStorage.getItem(STORAGE_KEY) ?? "[]");
    return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
  } catch {
    return [];
  }
}

function remember(ids: string[]) {
  try {
    window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Without storage the tab still follows its jobs until it is reloaded.
  }
}

export function JobNotificationsProvider({
  model,
  onNavigate,
  children,
}: {
  model: EngineModel;
  onNavigate: (route: RouteState) => void;
  children: ReactNode;
}) {
  const toast = useToast();
  const [followed, setFollowed] = useState<string[]>(remembered);

  const update = useCallback((change: (ids: string[]) => string[]) => {
    setFollowed((ids) => {
      const next = change(ids);
      remember(next);
      return next;
    });
  }, []);

  const jobPage = useCallback(
    (job: Job): ToastAction => {
      const route: RouteState = { kind: "settings", page: "jobs", jobId: job.id };
      return { label: "View job", href: routePath(route), onNavigate: () => onNavigate(route) };
    },
    [onNavigate],
  );

  const follow = useCallback(
    (job: Job) => {
      toast(`${jobTitle(model, job)} started.`, { actions: [jobPage(job)] });
      if (!isFinal(job)) update((ids) => (ids.includes(job.id) ? ids : [...ids, job.id]));
    },
    [jobPage, model, toast, update],
  );

  const ended = useCallback(
    (job: Job) => {
      update((ids) => ids.filter((id) => id !== job.id));
      const title = jobTitle(model, job);
      if (job.state === "completed") {
        const download: ToastAction[] = job.output
          ? [{ label: "Download", href: jobOutputUrl(job.id), download: true }]
          : [];
        toast(`${title} completed.`, { actions: [...download, jobPage(job)] });
      } else {
        toast(`${title} ${job.state === "cancelled" ? "was cancelled" : "failed"}.`, {
          actions: [jobPage(job)],
          tone: "info",
        });
      }
    },
    [jobPage, model, toast, update],
  );

  return (
    <JobNotificationsContext.Provider value={{ follow }}>
      {children}
      {followed.map((id) => (
        <FollowedJob key={id} jobId={id} onEnded={ended} />
      ))}
    </JobNotificationsContext.Provider>
  );
}

function FollowedJob({ jobId, onEnded }: { jobId: string; onEnded: (job: Job) => void }) {
  useJobStream(jobId, (job) => {
    if (isFinal(job)) onEnded(job);
  });
  return null;
}

export function useJobNotifications(): JobNotifications {
  const value = useContext(JobNotificationsContext);
  if (!value) throw new Error("useJobNotifications needs a JobNotificationsProvider");
  return value;
}

/** "Export of Codelists, Codes", or the job's kind for other jobs. */
export function jobTitle(model: EngineModel, job: Job): string {
  if (job.kind !== "export") return job.kind === "batch" ? "Batch" : "Import";
  const scope = job.parameters.scope as { types?: { objectTypeKey: string }[] } | undefined;
  const names = (scope?.types ?? []).map(
    (item) => model.objectTypes.find((type) => type.key === item.objectTypeKey)?.pluralName ?? item.objectTypeKey,
  );
  return names.length ? `Export of ${names.join(", ")}` : "Export";
}
