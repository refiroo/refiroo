/**
 * Notifications about the jobs this tab started (0.9 J1u, D59, D63). A job is followed from the
 * moment it is started until it ends, over its own event stream; the jobs are remembered for the
 * tab (`sessionStorage`), so a reload follows them again. When a job ends, a notification says so:
 * a completed export links to its file and its job page, a failed or cancelled job to its page,
 * which shows why. A closed browser is told nothing.
 *
 * An import preview that waits for confirmation (0.9 J4) is told as Preview ready, with Review
 * opening its page, and is no longer followed: it may wait for days, and each stream holds a
 * connection. Confirming it follows it again. Pages that show data hear when a job ends
 * (`useJobEnded`), so a collection reloads after an import into it.
 */

import { loadedWorkspaceModel } from "@/model/workspaceModels";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { jobOutputUrl } from "@/api/client";
import { routePath } from "@/routing/routes";
import type { EngineModel, Job, RouteState } from "@/types";
import { useToast, type ToastAction } from "@/ui/Toast";
import { importTitle } from "./ImportOutcome";
import { forPeople, KIND } from "./jobText";
import { isFinal, useJobStream } from "./useJobStream";

const STORAGE_KEY = "rdm.followedJobs";

type EndedListener = (job: Job) => void;

interface JobNotifications {
  /** Follow a job this tab started, saying it started unless `announce` is false. */
  follow: (job: Job, options?: { announce?: boolean }) => void;
  /** Hear of each followed job that ends; returns the way to stop listening. */
  onEnded: (listener: EndedListener) => () => void;
  /** Open a job's page in Settings › Jobs, with its address for a link. */
  view: { href: (job: Pick<Job, "id">) => string; open: (job: Pick<Job, "id">) => void };
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
  const listeners = useRef(new Set<EndedListener>());

  const update = useCallback((change: (ids: string[]) => string[]) => {
    setFollowed((ids) => {
      const next = change(ids);
      remember(next);
      return next;
    });
  }, []);

  // A job's own page shows what a notification would say: none is shown while it is open.
  const onItsPage = (job: Job) =>
    window.location.pathname === routePath({ kind: "settings", page: "jobs", jobId: job.id });

  const jobPage = useCallback(
    (job: Job): ToastAction => {
      const route: RouteState = { kind: "settings", page: "jobs", jobId: job.id };
      return { label: "View job", href: routePath(route), onNavigate: () => onNavigate(route) };
    },
    [onNavigate],
  );

  const follow = useCallback(
    (job: Job, options: { announce?: boolean } = {}) => {
      if (options.announce !== false)
        toast(`${jobTitle(modelOf(job, model), job)} started.`, { actions: [jobPage(job)] });
      if (!isFinal(job)) update((ids) => (ids.includes(job.id) ? ids : [...ids, job.id]));
    },
    [jobPage, model, toast, update],
  );

  const view = {
    href: (job: Pick<Job, "id">) => routePath({ kind: "settings", page: "jobs", jobId: job.id }),
    open: (job: Pick<Job, "id">) => onNavigate({ kind: "settings", page: "jobs", jobId: job.id }),
  };

  const onEnded = useCallback((listener: EndedListener) => {
    listeners.current.add(listener);
    return () => {
      listeners.current.delete(listener);
    };
  }, []);

  const waiting = useCallback(
    (job: Job) => {
      update((ids) => ids.filter((id) => id !== job.id));
      if (onItsPage(job)) return;
      toast(`${jobTitle(modelOf(job, model), job)}: the preview is ready.`, {
        actions: [{ ...jobPage(job), label: "Review" }],
      });
    },
    [jobPage, model, toast, update],
  );

  const ended = useCallback(
    (job: Job) => {
      update((ids) => ids.filter((id) => id !== job.id));
      listeners.current.forEach((listener) => listener(job));
      if (onItsPage(job)) return;
      const title = jobTitle(modelOf(job, model), job);
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
    <JobNotificationsContext.Provider value={{ follow, onEnded, view }}>
      {children}
      {followed.map((id) => (
        <FollowedJob key={id} jobId={id} onEnded={ended} onWaiting={waiting} />
      ))}
    </JobNotificationsContext.Provider>
  );
}

function FollowedJob({
  jobId,
  onEnded,
  onWaiting,
}: {
  jobId: string;
  onEnded: (job: Job) => void;
  onWaiting: (job: Job) => void;
}) {
  useJobStream(jobId, (job) => {
    if (isFinal(job)) onEnded(job);
    else if (job.state === "awaiting_confirmation") onWaiting(job);
  });
  return null;
}

export function useJobNotifications(): JobNotifications {
  const value = useContext(JobNotificationsContext);
  if (!value) throw new Error("useJobNotifications needs a JobNotificationsProvider");
  return value;
}

/** Calls `listener` with each job this tab followed when it ends. */
export function useJobEnded(listener: EndedListener) {
  const { onEnded } = useJobNotifications();
  const latest = useRef(listener);
  useEffect(() => {
    latest.current = listener;
  });
  useEffect(() => onEnded((job) => latest.current(job)), [onEnded]);
}

/** "Export of Codelists, Codes", "Import of codes.csv", "Profile of codes.csv", "Dry run of
 * codes.csv", or "Batch". */
/** The model of the job's own workspace when it has loaded, else `model` (0.11 D49). */
function modelOf(job: Job, model: EngineModel): EngineModel {
  return (job.workspaceKey ? loadedWorkspaceModel(job.workspaceKey) : undefined) ?? model;
}

export function jobTitle(model: EngineModel, job: Job): string {
  if (job.kind === "import") return importTitle(job);
  if (job.kind === "profile" || job.kind === "dryRun") return sourceTitle(job);
  if (job.kind !== "export") return "Batch";
  const scope = job.parameters.scope as { types?: { objectTypeKey: string }[] } | undefined;
  const names = (scope?.types ?? []).map(
    (item) => model.objectTypes.find((type) => type.key === item.objectTypeKey)?.pluralName ?? item.objectTypeKey,
  );
  if (forPeople(job)) return names.length ? `Workbook for people of ${names.join(", ")}` : "Workbook for people";
  return names.length ? `Export of ${names.join(", ")}` : "Export";
}

/** A source file's profile or a model draft's dry run (0.10 A3), named after the file. */
function sourceTitle(job: Job): string {
  const label = KIND[job.kind];
  const name = (job.parameters.file as { name?: string } | undefined)?.name;
  return name ? `${label} of ${name}` : label;
}
