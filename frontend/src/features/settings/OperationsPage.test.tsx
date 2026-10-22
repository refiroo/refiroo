import { act, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { OperationsPage, REFRESH_SECONDS } from "@/features/settings/OperationsPage";
import type { BackupRehearsal, EngineProcess, SystemSummary, WorkspaceReadiness } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const threads = (failing = false): EngineProcess["threads"] =>
  (["jobWorker", "exportWorker", "jobListener", "eventDeriver", "webhookDispatcher", "heartbeat"] as const).map(
    (name) =>
      failing && name === "jobWorker"
        ? { name, state: "failing", reason: "poolExhausted", since: "2026-10-22T12:28:00Z" }
        : { name, state: "running" },
  );

const process = (id: string, changes: Partial<EngineProcess> = {}): EngineProcess => ({
  id,
  host: id.split(":")[0],
  pid: Number(id.split(":")[1]),
  engineVersion: "0.11.0",
  startedAt: "2026-10-22T08:00:00Z",
  heartbeatAt: "2026-10-22T12:32:00Z",
  state: "live",
  ready: true,
  threads: threads(),
  pool: { size: 5, maxOverflow: 10, inUse: 2 },
  unavailableReleases: [],
  counters: { requests: 1200, serverErrors: 0, databaseUnavailable: {} },
  ...changes,
});

const release = (key: string, version: string) => ({ id: `${key}-${version}`, key, version, schemaVersion: "0.10" });

const rehearsal = (changes: Partial<BackupRehearsal> = {}): BackupRehearsal => ({
  id: "b1",
  checkedAt: "2026-10-22T03:10:00Z",
  backup: "rdm-20261022-0200.dump",
  dataAsOf: "2026-10-22T01:59:00Z",
  revisionBefore: "20261025_01",
  revisionAfter: "20261025_01",
  engineVersion: "0.11.0",
  host: "ops-host",
  result: "passed",
  failure: null,
  workspaces: [
    {
      workspaceKey: "north",
      release: release("library", "2.1.0"),
      state: "served",
      reason: null,
      records: 31204,
      relations: 52880,
      openChangeSets: 2,
      publications: 14,
      liveRecords: 31250,
    },
  ],
  ...changes,
});

function respond({
  summary,
  readiness,
  processes,
  rehearsals,
}: {
  summary?: Partial<SystemSummary>;
  readiness?: WorkspaceReadiness[];
  processes?: EngineProcess[];
  rehearsals?: BackupRehearsal[];
} = {}) {
  vi.mocked(api.systemSummary).mockResolvedValue({
    processes: { live: 2, silent: 0 },
    workspaces: { served: 2, unavailable: 0 },
    jobs: [{ kind: "batch", state: "running", count: 1 }],
    webhookSubscriptions: { active: 3, failing: 0, suspended: 0 },
    ...summary,
  });
  vi.mocked(api.readiness).mockResolvedValue(
    readiness ?? [
      { workspaceKey: "archive", release: release("archive", "1.1.0"), state: "served", unavailableIn: [] },
      { workspaceKey: "north", release: release("library", "2.1.0"), state: "served", unavailableIn: [] },
    ],
  );
  vi.mocked(api.processes).mockResolvedValue(processes ?? [process("node-1:101:aa"), process("node-2:202:bb")]);
  vi.mocked(api.backupRehearsals).mockResolvedValue({ items: rehearsals ?? [rehearsal()], nextCursor: null });
}

beforeEach(() => {
  vi.clearAllMocks();
});
afterEach(() => {
  vi.useRealTimers();
});

describe("Operations", () => {
  it("shows every workspace served, the processes and the last rehearsal passed", async () => {
    respond();
    render(<OperationsPage />);
    expect(await screen.findByText("2 of 2 served")).toBeInTheDocument();
    expect(screen.getByText("2 live")).toBeInTheDocument();
    const workspaces = screen.getByRole("group", { name: "Workspaces" });
    expect(within(workspaces).getAllByText("Served")).toHaveLength(2);
    expect(screen.getByText("node-1:101:aa")).toBeInTheDocument();
    expect(screen.getByText("Passed")).toBeInTheDocument();
    const copy = screen.getByRole("group", { name: "Each workspace in the restored copy" });
    expect(within(copy).getByText("31,204")).toBeInTheDocument();
    expect(within(copy).getByText("46 more records since")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy Liveness address" })).toBeInTheDocument();
  });

  it("names what is wrong: a workspace not served, a silent process, a failing thread, a failed rehearsal", async () => {
    respond({
      summary: { processes: { live: 1, silent: 1 }, workspaces: { served: 1, unavailable: 1 } },
      readiness: [
        {
          workspaceKey: "archive",
          release: release("archive", "1.1.0"),
          state: "unavailable",
          unavailableIn: [{ processId: "node-1:101:aa", reason: "notLoaded", schemaVersion: "0.10" }],
        },
        { workspaceKey: "north", release: release("library", "2.1.0"), state: "served", unavailableIn: [] },
      ],
      processes: [
        process("node-1:101:aa", {
          threads: threads(true),
          counters: { requests: 900, serverErrors: 37, databaseUnavailable: { poolExhausted: 37 } },
        }),
        process("node-3:303:cc", { state: "silent" }),
      ],
      rehearsals: [
        rehearsal({
          result: "failed",
          failure: { code: "WORKSPACES_NOT_SERVED", message: "A recovery from this backup would leave workspace 'training' …" },
        }),
        rehearsal({ id: "b0", checkedAt: "2026-10-15T03:10:00Z", backup: "older.dump" }),
      ],
    });
    render(<OperationsPage />);
    expect(await screen.findByText("1 of 2 served")).toBeInTheDocument();
    expect(screen.getByText("Not served: archive")).toBeInTheDocument();
    expect(screen.getByText("1 live · 1 silent")).toBeInTheDocument();
    expect(screen.getByText("Silent: node-3:303")).toBeInTheDocument();
    expect(
      screen.getByText("node-1:101: activated after the process loaded it; served again after a restart"),
    ).toBeInTheDocument();
    expect(screen.getByText("Failing")).toBeInTheDocument();
    expect(screen.getByText(/^Since .*: no free connection in its pool$/)).toBeInTheDocument();
    expect(screen.getByText("Without a connection 37 times: poolExhausted 37")).toBeInTheDocument();
    expect(screen.getByText("Not every workspace could be served from the copy")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show earlier rehearsals (1)" }));
    expect(screen.getByText("older.dump")).toBeInTheDocument();
  });

  it("says when no backup has been rehearsed", async () => {
    respond({ rehearsals: [] });
    render(<OperationsPage />);
    expect(await screen.findByText("No backup has been rehearsed")).toBeInTheDocument();
  });

  it("reads again on Refresh and every 15 seconds while visible, keeping the last figures on a failure", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    respond();
    render(<OperationsPage />);
    expect(await screen.findByText("2 of 2 served")).toBeInTheDocument();
    expect(api.systemSummary).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REFRESH_SECONDS * 1000);
    });
    expect(api.systemSummary).toHaveBeenCalledTimes(2);
    vi.mocked(api.systemSummary).mockRejectedValue(new Error("The engine did not answer"));
    fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
    expect(await screen.findByText("Could not refresh")).toBeInTheDocument();
    expect(screen.getByText("2 of 2 served")).toBeInTheDocument();
  });
});
