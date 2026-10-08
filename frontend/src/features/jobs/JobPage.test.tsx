import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { testModel } from "@/test/fixtures";
import type { Job, JobRow } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { JobNotificationsProvider } from "./JobNotifications";
import { JobPage } from "./JobPage";

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { job: vi.fn(), jobRows: vi.fn(), confirmJob: vi.fn(), cancelJob: vi.fn() },
}));

class SilentEventSource {
  static opened: string[] = [];
  constructor(url: string) {
    SilentEventSource.opened.push(url);
  }
  addEventListener() {}
  close() {}
}

/** A previewed import waiting for confirmation: SC-10's file, two rows refused (0.9 J3's shape). */
const waiting: Job = {
  id: "j7",
  kind: "import",
  workspaceKey: "west",
  changeSetId: "cs1",
  changeSetVersion: 4,
  state: "awaiting_confirmation",
  stage: null,
  progress: { total: 6, processed: 6 },
  counts: { applied: 4, rejected: 2, unprocessed: 0, created: 1, updated: 1, unchanged: 2, deleted: 0 },
  result: null,
  error: null,
  createdAt: "2026-10-08T09:00:00Z",
  startedAt: "2026-10-08T09:00:01Z",
  finishedAt: null,
  expiresAt: "2026-10-15T09:00:00Z",
  cancelRequestedAt: null,
  parameters: {
    policy: "independent",
    onExisting: "overwrite",
    file: { name: "codes.csv", format: "csv", bytes: 240 },
    profile: { key: "supplier", version: 1 },
  },
  output: null,
  confirmedAt: null,
  preview: {
    coverage: "complete",
    items: { total: 6, previewed: 6 },
    rows: { total: 6, previewed: 6, rejected: 2 },
    counts: { created: 1, updated: 1, unchanged: 2, deleted: 0, rejected: 2 },
    result: "partial",
    previewedAt: "2026-10-08T09:00:02Z",
  },
  bindingReport: [
    {
      sheet: "csv",
      objectTypeKey: "domain",
      rows: 6,
      rejectedRows: 2,
      columns: [
        {
          column: "Name",
          binding: "field",
          target: "name",
          cells: 6,
          empty: 0,
          converted: 6,
          valueMapped: 0,
          refused: 0,
        },
        {
          column: "Active",
          binding: "attributeTypeKey",
          target: "active",
          cells: 6,
          empty: 1,
          converted: 0,
          valueMapped: 0,
          refused: 5,
        },
        {
          column: "Parent",
          binding: "parent",
          target: "domain",
          cells: 6,
          empty: 0,
          refused: 0,
          resolved: 4,
          notFound: 1,
          ambiguous: 1,
        },
      ],
    },
  ],
};

const refusedRow: JobRow = {
  ref: "csv!4",
  sheet: "csv",
  row: 4,
  status: "rejected",
  actions: { created: 0, updated: 0, unchanged: 0, deleted: 0 },
  outcomes: [
    {
      index: 1,
      ref: "csv!4",
      status: "rejected",
      error: {
        code: "INVALID_ATTRIBUTE_VALUE",
        message: "…",
        details: {
          column: "Order",
          cells: [
            { column: "Order", code: "INVALID_ATTRIBUTE_VALUE", message: "'ten' is not a whole number" },
            { column: "From", code: "INVALID_ATTRIBUTE_VALUE", message: "'31.02.' is not a date" },
          ],
        },
      },
    },
  ],
};

function renderPage() {
  render(
    <ToastProvider>
      <JobNotificationsProvider model={testModel} onNavigate={vi.fn()}>
        <JobPage model={testModel} jobId="j7" canCancel jobsHref="/settings/jobs" onJobs={vi.fn()} />
      </JobNotificationsProvider>
    </ToastProvider>,
  );
}

describe("JobPage of an import (0.9 J4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SilentEventSource.opened = [];
    window.sessionStorage.clear();
    vi.stubGlobal("EventSource", SilentEventSource);
    vi.mocked(api.job).mockResolvedValue(waiting);
    vi.mocked(api.jobRows).mockResolvedValue({ items: [refusedRow], nextCursor: null });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows a waiting preview: its counts, result, coverage, the binding report and its refused rows", async () => {
    renderPage();
    await screen.findByRole("heading", { level: 1, name: "Import of codes.csv" });
    // A waiting preview is not followed: it may wait for days (D63).
    expect(SilentEventSource.opened).toEqual([]);
    const previewed = screen.getByRole("region", { name: "The preview" });
    expect(previewed).toHaveTextContent("Loading would apply the rows that can load and refuse 2 rows.");
    expect(previewed).toHaveTextContent("Created1");
    expect(previewed).not.toHaveTextContent("A sample");

    const columns = screen.getByRole("group", { name: "Columns of the CSV file" });
    const active = within(columns).getByRole("row", { name: /Active/ });
    expect(within(active).getByText("Check")).toBeInTheDocument();
    expect(within(columns).getByRole("row", { name: /^Name/ })).not.toHaveTextContent("Check");
    expect(within(columns).getByRole("row", { name: /Parent/ })).toHaveTextContent("Parent: Domain");

    await screen.findByText("'ten' is not a whole number", { exact: false });
    expect(screen.getByText("From: '31.02.' is not a date")).toBeInTheDocument();
    expect(api.jobRows).toHaveBeenCalledWith("j7", expect.objectContaining({ status: "rejected" }));
    expect(screen.getByRole("button", { name: "Load the file" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel import" })).toBeInTheDocument();
  });

  it("says why rows cannot load when the file's records belong to another workspace (0.9 J4a)", async () => {
    const message =
      "12 rows name their records by IDs of workspace 'default', so they cannot load here. Record IDs are unique across the instance: a file with record IDs, such as an export, loads only into the workspace it came from.";
    vi.mocked(api.job).mockResolvedValue({
      ...waiting,
      notices: [{ code: "RECORD_IDS_OF_ANOTHER_WORKSPACE", message, details: { workspaceKey: "default", rows: 12 } }],
    });
    renderPage();
    const notice = await screen.findByText("Why rows cannot load here");
    expect(notice.closest(".notice") ?? notice.parentElement).toHaveTextContent(message);
  });

  it("keeps the preview waiting when the confirm is refused, saying why", async () => {
    vi.mocked(api.confirmJob).mockRejectedValue(
      new ApiError(409, "CHANGE_SET_VERSION_CONFLICT", "The change set changed since the import was sent."),
    );
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Load the file" }));
    await screen.findByText("The file was not loaded");
    expect(screen.getByText(/The change set changed since the import was sent\./)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load the file" })).toBeEnabled();
    expect(screen.getByText("Awaiting confirmation")).toBeInTheDocument();
  });

  it("follows the job again once confirmed", async () => {
    vi.mocked(api.confirmJob).mockResolvedValue({ ...waiting, state: "queued", confirmedAt: "2026-10-08T09:05:00Z" });
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Load the file" }));
    await waitFor(() => expect(SilentEventSource.opened.length).toBeGreaterThan(0));
    expect(screen.queryByRole("button", { name: "Load the file" })).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "What the preview said" })).toBeInTheDocument();
  });
});
