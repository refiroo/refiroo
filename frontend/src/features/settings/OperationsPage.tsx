/**
 * Settings › Operations (Track U U7, Product 0.11 O2): the running instance, read only. The four
 * figures of `GET /system/summary`; each active workspace and the live processes that do not serve
 * it (`GET /system/readiness`); every engine process as it last reported itself (`GET
 * /system/processes`); the last backup rehearsal with each workspace of the restored copy and the
 * earlier ones (`GET /system/backup-rehearsals`); how to rehearse; the probe addresses. Read on
 * opening, on Refresh, and every 15 seconds while the page is visible (D202).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL, api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { formatServerTime } from "@/lib/dates";
import type { BackupRehearsal, EngineProcess, SystemSummary, WorkspaceReadiness } from "@/types";
import { CopyValue } from "@/ui/CopyValue";
import { InlineError } from "@/ui/InlineError";
import { Notice } from "@/ui/Notice";
import { Section } from "@/ui/Section";
import { SettingsLayout } from "@/ui/SettingsLayout";
import { SettingsTable } from "@/ui/SettingsTable";
import { Skeleton } from "@/ui/Skeleton";
import { StatusPill } from "@/ui/StatusPill";
import {
  THREAD_LABELS,
  databaseReason,
  shortProcess,
  sinceBackup,
  summaryFigures,
  unavailableReason,
} from "./operationsText";

export const REFRESH_SECONDS = 15;

interface Operations {
  summary: SystemSummary;
  readiness: WorkspaceReadiness[];
  processes: EngineProcess[];
  rehearsals: BackupRehearsal[];
  moreRehearsals: string | null;
  asOf: Date;
}

async function readOperations(): Promise<Operations> {
  const [summary, readiness, processes, rehearsals] = await Promise.all([
    api.systemSummary(),
    api.readiness(),
    api.processes(),
    api.backupRehearsals(),
  ]);
  return {
    summary,
    readiness,
    processes,
    rehearsals: rehearsals.items,
    moreRehearsals: rehearsals.nextCursor,
    asOf: new Date(),
  };
}

/** The page's reads, again on `refresh` and every 15 seconds while the document is visible. */
function useOperations() {
  const [data, setData] = useState<Operations>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const current = useRef(0);
  const refresh = useCallback(() => {
    const attempt = ++current.current;
    setLoading(true);
    readOperations()
      .then((loaded) => {
        if (attempt !== current.current) return;
        setData((previous) =>
          // Earlier rehearsals loaded beyond the first page stay while the first page is unchanged.
          previous && previous.rehearsals[0]?.id === loaded.rehearsals[0]?.id
            ? { ...loaded, rehearsals: previous.rehearsals, moreRehearsals: previous.moreRehearsals }
            : loaded,
        );
        setError("");
      })
      .catch((cause) => attempt === current.current && setError(errorMessage(cause)))
      .finally(() => attempt === current.current && setLoading(false));
  }, []);
  useEffect(() => {
    refresh();
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, REFRESH_SECONDS * 1000);
    const onVisible = () => document.visibilityState === "visible" && refresh();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
      current.current += 1;
    };
  }, [refresh]);
  const more = data?.moreRehearsals;
  const loadMore = useCallback(async () => {
    if (!more) return;
    try {
      const page = await api.backupRehearsals(more);
      setData(
        (previous) =>
          previous && {
            ...previous,
            rehearsals: [...previous.rehearsals, ...page.items],
            moreRehearsals: page.nextCursor,
          },
      );
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }, [more]);
  return { data, error, loading, refresh, loadMore };
}

export function OperationsPage() {
  const { data, error, loading, refresh, loadMore } = useOperations();
  return (
    <SettingsLayout
      eyebrow="Administration"
      title="Operations"
      description="How this instance's engine processes are running, which workspaces they serve, and when a backup was last restored and checked. Read only."
      actions={
        <div className="operations-refresh">
          {data && (
            <span className="settings-note" aria-live="polite">
              As of {data.asOf.toLocaleTimeString("en-GB")} · refreshed every {REFRESH_SECONDS} seconds
            </span>
          )}
          <button type="button" className="secondary" onClick={refresh} disabled={loading}>
            Refresh
          </button>
        </div>
      }
    >
      {error && data && (
        <Notice tone="warning" title="Could not refresh">
          {error} The figures below are from {data.asOf.toLocaleTimeString("en-GB")}.
        </Notice>
      )}
      {error && !data ? (
        <InlineError message={error} onRetry={refresh} />
      ) : !data ? (
        <Skeleton label="Loading the instance's state" lines={10} />
      ) : (
        <>
          <Summary data={data} />
          <Workspaces readiness={data.readiness} />
          <Processes processes={data.processes} />
          <Rehearsals rehearsals={data.rehearsals} more={Boolean(data.moreRehearsals)} onMore={loadMore} />
          <Monitoring />
        </>
      )}
    </SettingsLayout>
  );
}

function Summary({ data }: { data: Operations }) {
  return (
    <section aria-label="Summary">
      <ul className="operations-figures">
        {summaryFigures(data.summary, data.readiness, data.processes).map((figure) => (
          <li key={figure.label}>
            <span className="operations-figure-label">{figure.label}</span>
            <StatusPill tone={figure.tone} className="operations-figure-value">
              {figure.value}
            </StatusPill>
            <span className="settings-note">{figure.note}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Workspaces({ readiness }: { readiness: WorkspaceReadiness[] }) {
  return (
    <Section
      title="Workspaces"
      description="A workspace is served when every live process can serve the release it runs."
    >
      <SettingsTable label="Workspaces" columns={["Workspace", "Release", "Schema", "State", "Not served by"]}>
        {readiness.map((item) => (
          <tr key={item.workspaceKey}>
            <th scope="row">
              <code>{item.workspaceKey}</code>
            </th>
            <td data-label="Release">
              {item.release ? (
                <>
                  <code>{item.release.key}</code> {item.release.version}
                </>
              ) : (
                "None"
              )}
            </td>
            <td data-label="Schema">{item.release?.schemaVersion ?? "None"}</td>
            <td data-label="State">
              <StatusPill tone={item.state === "served" ? "success" : "error"}>
                {item.state === "served" ? "Served" : "Unavailable"}
              </StatusPill>
            </td>
            <td data-label="Not served by">
              {item.release === null
                ? unavailableReason("noRelease")
                : item.unavailableIn.length
                  ? item.unavailableIn
                      .map(
                        (process) =>
                          `${shortProcess(process.processId)}: ${unavailableReason(process.reason, process.schemaVersion)}`,
                      )
                      .join("; ")
                  : "None"}
            </td>
          </tr>
        ))}
      </SettingsTable>
    </Section>
  );
}

const wide = () =>
  typeof window === "undefined" || !window.matchMedia || window.matchMedia("(min-width: 761px)").matches;

function Processes({ processes }: { processes: EngineProcess[] }) {
  const [open] = useState(wide);
  return (
    <Section
      title="Engine processes"
      description="Every process on this database, as it last reported itself. The process that answered is current; the others are up to one report old."
    >
      <ul className="operations-processes">
        {processes.map((process) => (
          <li key={process.id}>
            <details open={open}>
              <summary>
                <code>{process.id}</code>
                <StatusPill tone={process.state === "live" ? "success" : "warning"}>
                  {process.state === "live" ? "Live" : "Silent"}
                </StatusPill>
                <StatusPill tone={process.ready ? "success" : "error"}>
                  {process.ready ? (process.state === "live" ? "Ready" : "Ready at last report") : "Not ready"}
                </StatusPill>
                <span className="settings-note operations-process-times">
                  Engine {process.engineVersion} · started {formatServerTime(process.startedAt)} · last report{" "}
                  {formatServerTime(process.heartbeatAt)}
                </span>
              </summary>
              <ProcessFacts process={process} />
            </details>
          </li>
        ))}
      </ul>
    </Section>
  );
}

function ProcessFacts({ process }: { process: EngineProcess }) {
  const missing = Object.entries(process.counters.databaseUnavailable).filter(([, times]) => times > 0);
  const total = missing.reduce((sum, [, times]) => sum + times, 0);
  return (
    <dl className="operations-process-facts">
      <div>
        <dt>Background threads</dt>
        <dd>
          <ul className="operations-threads">
            {process.threads.map((thread) => (
              <li key={thread.name}>
                <span>{THREAD_LABELS[thread.name]}</span>
                <StatusPill
                  tone={thread.state === "running" ? "success" : thread.state === "failing" ? "warning" : "neutral"}
                >
                  {thread.state === "running" ? "Running" : thread.state === "failing" ? "Failing" : "Off"}
                </StatusPill>
                {thread.state === "failing" && (
                  <span className="settings-note">
                    {thread.since ? `Since ${formatServerTime(thread.since)}: ` : ""}
                    {databaseReason(thread.reason)}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </dd>
      </div>
      <div>
        <dt>Database connections</dt>
        <dd>
          {process.pool.inUse} in use of {process.pool.size} + {process.pool.maxOverflow} overflow
          <span className="settings-note">
            {total
              ? `Without a connection ${total} ${total === 1 ? "time" : "times"}: ${missing.map(([reason, times]) => `${reason} ${times}`).join(", ")}`
              : "Never without a connection"}
          </span>
        </dd>
      </div>
      <div>
        <dt>Requests since start</dt>
        <dd>
          {process.counters.requests.toLocaleString("en-GB")} answered,{" "}
          {process.counters.serverErrors.toLocaleString("en-GB")} with a server error
        </dd>
      </div>
      <div>
        <dt>Releases it cannot serve</dt>
        <dd>
          {process.unavailableReleases.length
            ? process.unavailableReleases
                .map((release) => `${release.releaseId}: ${unavailableReason(release.reason, release.schemaVersion)}`)
                .join("; ")
            : "None"}
        </dd>
      </div>
    </dl>
  );
}

function Rehearsals({
  rehearsals,
  more,
  onMore,
}: {
  rehearsals: BackupRehearsal[];
  more: boolean;
  onMore: () => void;
}) {
  const [showEarlier, setShowEarlier] = useState(false);
  const [latest, ...earlier] = rehearsals;
  return (
    <Section
      title="Last backup rehearsal"
      description="A backup restored into a separate database and checked there by the engine, recorded here. Nothing on this page restores data."
    >
      {!latest ? (
        <Notice tone="warning" title="No backup has been rehearsed">
          No restore of this instance's backups has been checked yet. Rehearse one as described below.
        </Notice>
      ) : (
        <div className="operations-rehearsal">
          <p className="operations-rehearsal-head">
            <StatusPill tone={latest.result === "passed" ? "success" : "error"}>
              {latest.result === "passed" ? "Passed" : "Failed"}
            </StatusPill>
            <strong>Checked {formatServerTime(latest.checkedAt)}</strong>
            {latest.backup && (
              <span>
                Backup <code>{latest.backup}</code>
              </span>
            )}
            {latest.dataAsOf && <span>Data as of {formatServerTime(latest.dataAsOf)}</span>}
          </p>
          {latest.failure && (
            <Notice tone="error" title={failureTitle(latest.failure.code)}>
              {latest.failure.message}
            </Notice>
          )}
          <dl className="operations-process-facts">
            <div>
              <dt>Database revision</dt>
              <dd>
                {latest.revisionAfter ? (
                  <>
                    <span>
                      <code>{latest.revisionBefore ?? "unversioned"}</code>
                      {latest.revisionAfter !== latest.revisionBefore && (
                        <>
                          {" "}
                          → <code>{latest.revisionAfter}</code>
                        </>
                      )}
                    </span>
                    <span className="settings-note">Prepared as startup would prepare it</span>
                  </>
                ) : (
                  <span>The copy could not be prepared</span>
                )}
              </dd>
            </div>
            <div>
              <dt>Checked by</dt>
              <dd>
                Engine {latest.engineVersion} on <code>{latest.host}</code>
              </dd>
            </div>
          </dl>
          {latest.workspaces.length > 0 && (
            <SettingsTable
              label="Each workspace in the restored copy"
              columns={[
                "Workspace",
                "Release in the copy",
                "Served",
                "Records",
                "Relationships",
                "Open change sets",
                "Publications",
                "Live now",
              ]}
            >
              {latest.workspaces.map((item) => (
                <tr key={item.workspaceKey}>
                  <th scope="row">
                    <code>{item.workspaceKey}</code>
                  </th>
                  <td data-label="Release in the copy">
                    {item.release ? (
                      <>
                        <code>{item.release.key}</code> {item.release.version}
                      </>
                    ) : (
                      "None"
                    )}
                  </td>
                  <td data-label="Served">
                    <StatusPill tone={item.state === "served" ? "success" : "error"}>
                      {item.state === "served"
                        ? "Served"
                        : `Not served: ${unavailableReason(item.reason ?? "invalid", item.release?.schemaVersion)}`}
                    </StatusPill>
                  </td>
                  <td data-label="Records" className="numeric">
                    {item.records.toLocaleString("en-GB")}
                  </td>
                  <td data-label="Relationships" className="numeric">
                    {item.relations.toLocaleString("en-GB")}
                  </td>
                  <td data-label="Open change sets" className="numeric">
                    {item.openChangeSets.toLocaleString("en-GB")}
                  </td>
                  <td data-label="Publications" className="numeric">
                    {item.publications.toLocaleString("en-GB")}
                  </td>
                  <td data-label="Live now">{sinceBackup(item)}</td>
                </tr>
              ))}
            </SettingsTable>
          )}
          {(earlier.length > 0 || more) && (
            <button
              type="button"
              className="link-button"
              aria-expanded={showEarlier}
              onClick={() => setShowEarlier((value) => !value)}
            >
              {showEarlier
                ? "Hide earlier rehearsals"
                : `Show earlier rehearsals (${earlier.length}${more ? "+" : ""})`}
            </button>
          )}
          {showEarlier && (
            <>
              <ul className="operations-earlier">
                {earlier.map((item) => (
                  <li key={item.id}>
                    <StatusPill tone={item.result === "passed" ? "success" : "error"}>
                      {item.result === "passed" ? "Passed" : "Failed"}
                    </StatusPill>
                    <span>{formatServerTime(item.checkedAt)}</span>
                    {item.backup && <code>{item.backup}</code>}
                    <span className="settings-note">
                      {item.failure
                        ? failureTitle(item.failure.code)
                        : `${item.workspaces.length} ${item.workspaces.length === 1 ? "workspace" : "workspaces"} served`}
                    </span>
                  </li>
                ))}
              </ul>
              {more && (
                <button type="button" className="load-more" onClick={onMore}>
                  Load more rehearsals
                </button>
              )}
            </>
          )}
        </div>
      )}
      <details className="operations-howto">
        <summary>How to rehearse a restore</summary>
        <p>
          Restore the backup into a new, empty database with the ICU root collation, then check it from the backend
          directory with this instance's <code>DATABASE_URL</code>. The check upgrades the copy as startup would, loads
          every workspace's release and counts its data, and records the result here. Delete the copy afterwards.
        </p>
        <pre>
          {`createdb -T template0 --locale-provider=icu --icu-locale=und --locale=C rdm_restore_check
pg_restore --no-owner -d rdm_restore_check <backup>.dump
python -m app.cli.restore_check \\
    --restored postgresql+psycopg://<user>@<host>/rdm_restore_check \\
    --backup <backup>.dump
dropdb rdm_restore_check`}
        </pre>
        <p className="settings-note">
          The operations guide (OPERATIONS.md, Backup and restore) describes recovery in place.
        </p>
      </details>
    </Section>
  );
}

const FAILURES: Record<string, string> = {
  DATABASE_COLLATION: "The copy has the wrong collation",
  DATABASE_EXTENSIONS: "The copy lacks an extension the engine needs",
  DATABASE_REVISION_UNKNOWN: "The copy's schema is newer than this engine",
  DATABASE_MIGRATION_FAILED: "The copy could not be upgraded",
  DATABASE_UNREACHABLE: "The copy could not be reached",
  DATABASE_URL_INVALID: "The copy's address is not usable",
  WORKSPACES_NOT_SERVED: "Not every workspace could be served from the copy",
};

function failureTitle(code: string) {
  return FAILURES[code] ?? code;
}

function Monitoring() {
  const probes = [
    {
      name: "Liveness",
      path: "/health/live",
      what: "Answers 200 while the process answers; never asks the database",
    },
    {
      name: "Readiness",
      path: "/health",
      what: "503 while the database is unreachable or no workspace can be served",
    },
    {
      name: "Metrics",
      path: "/metrics",
      what: "Prometheus text: every live process and the instance in one scrape",
    },
  ];
  return (
    <Section
      title="For monitoring"
      description="What an orchestrator and a metrics collector read. Keep them off a public network."
    >
      <SettingsTable label="Monitoring addresses" columns={["Probe", "Address", "What it answers"]}>
        {probes.map((probe) => (
          <tr key={probe.name}>
            <th scope="row">{probe.name}</th>
            <td data-label="Address">
              <CopyValue label={`${probe.name} address`} value={`${API_URL}${probe.path}`} labelled={false} />
            </td>
            <td data-label="What it answers">{probe.what}</td>
          </tr>
        ))}
      </SettingsTable>
    </Section>
  );
}
