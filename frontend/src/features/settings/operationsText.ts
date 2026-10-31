/**
 * The words Settings › Operations uses for what the engine reports (0.11 O1, O2): thread names,
 * why a thread fails, why a process cannot serve a release, and the four summary figures.
 */

import type {
  DatabaseReason,
  EngineProcess,
  ProcessThread,
  RehearsalWorkspace,
  SystemSummary,
  UnavailableReason,
  WorkspaceReadiness,
} from "@/types";
import type { StatusTone } from "@/ui/StatusPill";

export const THREAD_LABELS: Record<ProcessThread["name"], string> = {
  jobWorker: "Job worker",
  exportWorker: "Export worker",
  assistantWorker: "Assistant worker",
  jobListener: "Job listener",
  eventDeriver: "Event deriver",
  webhookDispatcher: "Webhook dispatcher",
  mailSender: "Mail sender",
  heartbeat: "Heartbeat",
};

const DATABASE_REASONS: Record<DatabaseReason, string> = {
  poolExhausted: "no free connection in its pool",
  tooManyConnections: "the database server takes no more connections",
  transactionEnded: "the database ended an idle transaction",
  unreachable: "the database is unreachable",
  error: "an unexpected error",
};

export function databaseReason(reason: DatabaseReason | null | undefined) {
  return reason ? DATABASE_REASONS[reason] : "an unexpected error";
}

/** Why a process cannot serve a release, in words an operator acts on. */
export function unavailableReason(reason: UnavailableReason | "noRelease", schemaVersion = "") {
  switch (reason) {
    case "unsupportedSchema":
      return `schema language ${schemaVersion} is outside what this engine reads`;
    case "invalid":
      return "the model does not validate in this engine";
    case "notLoaded":
      return "activated after the process loaded it; served again after a restart";
    case "noRelease":
      return "the workspace runs no release";
  }
}

const count = (value: number) => value.toLocaleString("en-GB");

export interface SummaryFigure {
  label: string;
  value: string;
  note: string;
  tone: StatusTone;
}

/** The four figures at the top of the page, each with a tone that says whether it needs a look. */
export function summaryFigures(
  summary: SystemSummary,
  readiness: WorkspaceReadiness[],
  processes: EngineProcess[],
): SummaryFigure[] {
  const { served, unavailable } = summary.workspaces;
  const notServed = readiness.filter((item) => item.state === "unavailable").map((item) => item.workspaceKey);
  const silent = processes.filter((item) => item.state === "silent");
  const jobs = (state: SystemSummary["jobs"][number]["state"]) =>
    summary.jobs.filter((job) => job.state === state).reduce((total, job) => total + job.count, 0);
  const waiting = jobs("awaiting_confirmation");
  const hooks = summary.webhookSubscriptions;
  return [
    {
      label: "Workspaces",
      value: `${count(served)} of ${count(served + unavailable)} served`,
      note: unavailable ? `Not served: ${notServed.join(", ")}` : "By every live process",
      tone: unavailable ? "error" : "success",
    },
    {
      label: "Engine processes",
      value: summary.processes.silent
        ? `${count(summary.processes.live)} live · ${count(summary.processes.silent)} silent`
        : `${count(summary.processes.live)} live`,
      note: silent.length
        ? `Silent: ${silent.map((item) => shortProcess(item.id)).join(", ")}`
        : processes.every((item) => item.ready)
          ? "All ready"
          : "Not all ready",
      tone: silent.length || !processes.every((item) => item.ready) ? "warning" : "success",
    },
    {
      label: "Jobs",
      value: `${count(jobs("running"))} running · ${count(jobs("queued"))} queued`,
      note: waiting ? `${count(waiting)} awaiting confirmation` : "None awaiting confirmation",
      tone: "success",
    },
    {
      label: "Webhook subscriptions",
      value: hooks.failing
        ? `${count(hooks.active)} active · ${count(hooks.failing)} failing`
        : `${count(hooks.active)} active`,
      note: `${count(hooks.failing)} failing · ${count(hooks.suspended)} suspended`,
      tone: hooks.failing || hooks.suspended ? "warning" : "success",
    },
  ];
}

/** `host:pid`, without the random part that makes a process ID unique. */
export function shortProcess(id: string) {
  return id.split(":").slice(0, 2).join(":");
}

/** What the instance has gained or lost since the backup, for one workspace of the copy. */
export function sinceBackup(item: RehearsalWorkspace) {
  const difference = item.liveRecords - item.records;
  if (difference === 0) return "Same record count";
  return difference > 0
    ? `${count(difference)} more ${difference === 1 ? "record" : "records"} since`
    : `${count(-difference)} fewer ${difference === -1 ? "record" : "records"} since`;
}
