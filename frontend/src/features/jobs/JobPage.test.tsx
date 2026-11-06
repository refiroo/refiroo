import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { openEventStream } from "@/api/eventStream";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { testModel } from "@/test/fixtures";
import type { Job, JobItemOutcome, JobRow } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { JobNotificationsProvider } from "./JobNotifications";
import { JobPage } from "./JobPage";

// Job streams are read with fetch (0.12 I2); the test drives them instead.
vi.mock("@/api/eventStream", () => ({ openEventStream: vi.fn() }));

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: { model: vi.fn(), job: vi.fn(), jobRows: vi.fn(), jobItems: vi.fn(), confirmJob: vi.fn(), cancelJob: vi.fn() },
}));

class SilentEventSource {
  static opened: string[] = [];
  constructor(readonly url: string) {
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
  requestedBy: null,
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

function renderPage(onNavigate = vi.fn()) {
  render(
    <ToastProvider>
      <JobNotificationsProvider model={testModel} onNavigate={vi.fn()}>
        <JobPage
          model={testModel}
          jobId="j7"
          canCancel
          jobsHref="/settings/jobs"
          onJobs={vi.fn()}
          onNavigate={onNavigate}
        />
      </JobNotificationsProvider>
    </ToastProvider>,
  );
}

describe("JobPage of an import (0.9 J4)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // The job's own workspace's model names its types (0.11 D49).
    vi.mocked(api.model).mockResolvedValue(testModel);
    SilentEventSource.opened = [];
    window.sessionStorage.clear();
    vi.mocked(openEventStream).mockImplementation((url) => new SilentEventSource(url));
    vi.mocked(api.job).mockResolvedValue(waiting);
    vi.mocked(api.jobRows).mockResolvedValue({ items: [refusedRow], nextCursor: null });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("leads an assistant task's job to the task's page (0.16 AP6a)", async () => {
    vi.mocked(api.job).mockResolvedValue({
      ...waiting,
      kind: "aiTask",
      state: "completed",
      preview: null,
      bindingReport: null,
      parameters: { taskId: "task-9" },
    });
    const onNavigate = vi.fn();
    renderPage(onNavigate);
    await screen.findByRole("heading", { level: 1, name: "Assistant: reading a workbook" });
    fireEvent.click(screen.getByRole("link", { name: "Open the load" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "ai-tasks", taskId: "task-9" });
  });

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

  it("cancels a waiting import in two steps: the button asks, the dialog's button cancels", async () => {
    vi.mocked(api.job).mockResolvedValue({ ...waiting });
    vi.mocked(api.cancelJob).mockResolvedValue({ ...waiting, state: "cancelled" });
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Cancel import" }));
    expect(api.cancelJob).not.toHaveBeenCalled();
    const dialog = await screen.findByRole("alertdialog", { name: "Cancel this import?" });
    fireEvent.click(within(dialog).getByRole("button", { name: "Cancel import" }));
    await waitFor(() => expect(api.cancelJob).toHaveBeenCalledWith("j7"));
    await waitFor(() => expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument());
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

  it("says another workspace's records load as this workspace's own, as information (0.9 J5)", async () => {
    const message =
      "3 rows name their records by IDs of workspace 'default'; they load as this workspace's own records, created on the first load and found again on the next.";
    vi.mocked(api.job).mockResolvedValue({
      ...waiting,
      notices: [{ code: "RECORD_IDS_AS_COUNTERPARTS", message, details: { workspaceKey: "default", rows: 3 } }],
    });
    renderPage();
    const title = await screen.findByText("Another workspace's records");
    expect(title.closest(".notice")).toHaveClass("info-notice");
    expect(title.closest(".notice")).toHaveTextContent(message);
    expect(screen.queryByText("Why rows cannot load here")).not.toBeInTheDocument();
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

/** A batch a bulk change sent (0.9 K2): applied, one record refused, one changed. */
const applied: Job = {
  ...waiting,
  id: "j8",
  kind: "batch",
  state: "completed",
  changeSetId: null,
  parameters: { policy: "independent", run: "background", stage: "preview", onExisting: "reject" },
  confirmedAt: "2026-10-09T09:01:00Z",
  finishedAt: "2026-10-09T09:01:02Z",
  result: "partial",
  progress: { total: 2, processed: 2 },
  counts: { applied: 1, rejected: 1, unprocessed: 0, created: 0, updated: 1, unchanged: 0, deleted: 0 },
  preview: {
    coverage: "complete",
    items: { total: 2, previewed: 2 },
    counts: { created: 0, updated: 2, unchanged: 0, deleted: 0, rejected: 0 },
    result: "applied",
    previewedAt: "2026-10-09T09:00:00Z",
  },
  bindingReport: null,
};

const outcomes: JobItemOutcome[] = [
  { index: 0, ref: "Alpha", status: "applied", action: "updated", id: "a", objectTypeKey: "domain", version: 4 },
  {
    index: 1,
    ref: "Beta",
    status: "rejected",
    error: { code: "VERSION_CONFLICT", message: "Changed by someone else" },
  },
];

function renderBatch(job: Job, onNavigate = vi.fn()) {
  vi.mocked(api.job).mockResolvedValue(job);
  render(
    <ToastProvider>
      <JobNotificationsProvider model={testModel} onNavigate={vi.fn()}>
        <JobPage
          model={testModel}
          jobId={job.id}
          canCancel
          jobsHref="/settings/jobs"
          onJobs={vi.fn()}
          onNavigate={onNavigate}
        />
      </JobNotificationsProvider>
    </ToastProvider>,
  );
  return onNavigate;
}

describe("JobPage of a batch (0.9 K2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SilentEventSource.opened = [];
    window.sessionStorage.clear();
    vi.mocked(openEventStream).mockImplementation((url) => new SilentEventSource(url));
    vi.mocked(api.jobItems).mockImplementation(async (_, query) => ({
      items: outcomes.filter((outcome) => !query?.status || outcome.status === query.status),
      nextCursor: null,
    }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("lists the items' outcomes, refused first, each linked to its record where it names one", async () => {
    const onNavigate = renderBatch(applied);
    const result = await screen.findByRole("region", { name: "The result" });
    expect(result).toHaveTextContent("1 item changed, 1 refused.");
    expect(screen.getByRole("region", { name: "What the preview said" })).toBeInTheDocument();
    await screen.findByText("Changed by someone else");
    expect(api.jobItems).toHaveBeenCalledWith("j8", expect.objectContaining({ status: "rejected" }));
    // A refused outcome names no record: its name is not a link.
    expect(screen.queryByRole("link", { name: "Beta" })).toBeNull();

    fireEvent.click(screen.getByRole("radio", { name: "All items" }));
    const alpha = await screen.findByRole("link", { name: "Alpha" });
    fireEvent.click(alpha);
    expect(onNavigate).toHaveBeenCalledWith(
      expect.objectContaining({ kind: "detail", objectTypeKey: "domain", objectId: "a", workspaceKey: "west" }),
    );
  });

  it("applies or cancels a waiting batch preview", async () => {
    const preview: Job = {
      ...applied,
      state: "awaiting_confirmation",
      confirmedAt: null,
      result: null,
      finishedAt: null,
    };
    vi.mocked(api.confirmJob).mockResolvedValue({ ...preview, state: "queued", confirmedAt: "2026-10-09T09:01:00Z" });
    renderBatch(preview);
    expect(await screen.findByRole("region", { name: "The preview" })).toHaveTextContent(
      "Applying would change 2 items.",
    );
    expect(screen.getByRole("button", { name: "Cancel preview" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));
    await waitFor(() => expect(api.confirmJob).toHaveBeenCalledWith("j8"));
    // Applying follows the job again.
    await waitFor(() => expect(SilentEventSource.opened.some((url) => url.includes("j8"))).toBe(true));
  });
});

describe("JobPage of a batch that deletes (0.9 K2b)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SilentEventSource.opened = [];
    window.sessionStorage.clear();
    vi.mocked(openEventStream).mockImplementation((url) => new SilentEventSource(url));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("shows what deleting removes and each delete item's impact, linking no record it removes", async () => {
    const deleting: Job = {
      ...applied,
      state: "awaiting_confirmation",
      confirmedAt: null,
      result: null,
      finishedAt: null,
      counts: { applied: 2, rejected: 0, unprocessed: 0, created: 0, updated: 0, unchanged: 1, deleted: 1 },
      preview: {
        coverage: "complete",
        items: { total: 2, previewed: 2 },
        counts: { created: 0, updated: 0, unchanged: 1, deleted: 1, rejected: 0 },
        deletion: {
          objectCount: 4,
          objectsByType: { domain: 1, codelist: 3 },
          relationshipCount: 5,
          retainedAssociationCount: 2,
        },
        result: "applied",
        previewedAt: "2026-10-09T09:00:00Z",
      },
    };
    vi.mocked(api.jobItems).mockResolvedValue({
      items: [
        {
          index: 0,
          ref: "Alpha",
          status: "applied",
          action: "deleted",
          id: "a",
          objectTypeKey: "domain",
          impact: {
            objectCount: 4,
            objectsByType: { domain: 1, codelist: 3 },
            relationshipCount: 5,
            retainedAssociationCount: 2,
            deletionPreviewToken: "t",
          },
        },
        {
          index: 1,
          ref: "Alpha's codelist",
          status: "applied",
          action: "unchanged",
          id: "c",
          objectTypeKey: "codelist",
          deletedWithItem: 0,
        },
      ],
      nextCursor: null,
    });
    renderBatch(deleting);
    const removes = await screen.findByRole("region", { name: "What deleting removes" });
    expect(removes).toHaveTextContent("4: 3 codelists, 1 domain");
    expect(removes).toHaveTextContent("Relationships removed5");
    expect(await screen.findByText("Would be deleted with 3 more records and 5 relationships")).toBeInTheDocument();
    expect(screen.getByText("Would go with item 1")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Alpha" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Alpha's codelist" })).toBeNull();
  });
});

describe("JobPage of a batch that changes relationships (0.9 K3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    SilentEventSource.opened = [];
    window.sessionStorage.clear();
    vi.mocked(openEventStream).mockImplementation((url) => new SilentEventSource(url));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("says relationship outcomes in a relationship's words, and a removal is not a delete of records", async () => {
    const removed: Job = {
      ...applied,
      result: "applied",
      counts: { applied: 3, rejected: 0, unprocessed: 0, created: 0, updated: 1, unchanged: 1, deleted: 1 },
      preview: {
        coverage: "complete",
        items: { total: 3, previewed: 3 },
        counts: { created: 0, updated: 1, unchanged: 1, deleted: 1, rejected: 0 },
        result: "applied",
        previewedAt: "2026-10-09T09:00:00Z",
      },
    };
    vi.mocked(api.jobItems).mockResolvedValue({
      items: [
        { index: 0, ref: "Alpha → Colours", status: "applied", action: "deleted", relationId: "r1" },
        { index: 1, ref: "Alpha → Sizes", status: "applied", action: "unchanged" },
        {
          index: 2,
          ref: "Beta",
          status: "applied",
          action: "updated",
          relationSetVersion: 4,
          previousRelationSetVersion: 3,
          relationIds: { created: ["r2", "r3"], kept: [], removed: ["r4"] },
        },
      ],
      nextCursor: null,
    });
    renderBatch(removed);
    const result = await screen.findByRole("region", { name: "The result" });
    expect(result).toHaveTextContent("2 items changed, 1 already as asked.");
    expect(await screen.findByText("Removed")).toBeInTheDocument();
    expect(screen.getByText("Not related")).toBeInTheDocument();
    expect(screen.getByText("Added 2, removed 1")).toBeInTheDocument();
    // A relationship's outcome names no record to open.
    expect(screen.queryByRole("link", { name: "Alpha → Colours" })).toBeNull();
  });
});
