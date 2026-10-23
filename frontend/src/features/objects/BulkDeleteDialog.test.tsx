import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { openEventStream } from "@/api/eventStream";
import { api } from "@/api/client";
import { JobNotificationsProvider } from "@/features/jobs/JobNotifications";
import { emptySelection, toggle } from "@/lib/recordSelection";
import { capabilitiesFixture } from "@/test/capabilities";
import { testModel } from "@/test/fixtures";
import { PushedEventSource } from "@/test/jobStream";
import type { BatchDeleteItem, Job, JobItemOutcome } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { BulkDeleteDialog } from "./BulkDeleteDialog";

// Job streams are read with fetch (0.12 I2); the test drives them instead.
vi.mock("@/api/eventStream", () => ({ openEventStream: vi.fn() }));

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: {
    capabilities: vi.fn(),
    startBatch: vi.fn(),
    confirmJob: vi.fn(),
    cancelJob: vi.fn(),
    jobItems: vi.fn(),
  },
}));

const domain = testModel.objectTypes.find((type) => type.key === "domain")!;
const picked = toggle(toggle(emptySelection, { id: "a", version: 3, name: "Alpha" }), {
  id: "b",
  version: 5,
  name: "Beta",
});

const job = (extra: Partial<Job>): Job =>
  ({
    id: "j1",
    kind: "batch",
    workspaceKey: "west",
    changeSetId: null,
    state: "queued",
    stage: null,
    progress: { total: 2, processed: 0 },
    counts: { applied: 0, rejected: 0, unprocessed: 0, created: 0, updated: 0, unchanged: 0, deleted: 0 },
    result: null,
    error: null,
    parameters: { policy: "independent", run: "background", stage: "preview" },
    confirmedAt: null,
    ...extra,
  }) as Job;

const preview = {
  coverage: "complete" as const,
  items: { total: 2, previewed: 2 },
  counts: { created: 0, updated: 0, unchanged: 0, deleted: 2, rejected: 0 },
  deletion: {
    objectCount: 5,
    objectsByType: { domain: 2, codelist: 3 },
    relationshipCount: 4,
    retainedAssociationCount: 1,
  },
  result: "applied" as const,
  previewedAt: "2026-10-09T09:00:00Z",
};
const waiting = job({
  state: "awaiting_confirmation",
  progress: { total: 2, processed: 2 },
  counts: { applied: 2, rejected: 0, unprocessed: 0, created: 0, updated: 0, unchanged: 0, deleted: 2 },
  preview,
});
const changedBeta: JobItemOutcome = {
  index: 1,
  ref: "Beta",
  status: "rejected",
  error: { code: "DELETION_PREVIEW_CHANGED", message: "The object was modified by another session. Please retry." },
};

function open() {
  const onDeleted = vi.fn();
  render(
    <ToastProvider>
      <JobNotificationsProvider model={testModel} onNavigate={vi.fn()}>
        <BulkDeleteDialog
          model={testModel}
          objectType={domain}
          workspaceKey="west"
          selection={picked}
          selected={2}
          readMatching={vi.fn()}
          onClose={vi.fn()}
          onDeleted={onDeleted}
          onOpenRecord={vi.fn()}
        />
      </JobNotificationsProvider>
    </ToastProvider>,
  );
  return { onDeleted };
}

describe("BulkDeleteDialog (0.9 K2b)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    PushedEventSource.open = [];
    vi.mocked(openEventStream).mockImplementation((url) => new PushedEventSource(url));
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture());
    vi.mocked(api.startBatch).mockResolvedValue(job({}));
    vi.mocked(api.cancelJob).mockResolvedValue(job({ state: "cancelled" }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("previews cascading deletes and says, by type, what goes with them before a destructive Delete", async () => {
    vi.mocked(api.jobItems).mockResolvedValue({ items: [], nextCursor: null });
    open();
    fireEvent.click(screen.getByRole("button", { name: "Preview" }));
    await waitFor(() => expect(api.startBatch).toHaveBeenCalled());
    const items = vi.mocked(api.startBatch).mock.calls[0][0].items as BatchDeleteItem[];
    expect(items.map((item) => [item.op, item.target.id, item.expectedVersion, item.cascade])).toEqual([
      ["delete", "a", 3, true],
      ["delete", "b", 5, true],
    ]);

    await PushedEventSource.push(waiting);
    expect(
      await screen.findByText(
        "Deletes 2 domains and 3 records inside or owned by them: 3 codelists. Removes 4 relationships; 1 of them links to records that stay, which are kept.",
      ),
    ).toBeInTheDocument();
    const destroy = screen.getByRole("button", { name: "Delete 5 records" });
    expect(destroy).toHaveClass("danger");
  });

  it("names a record whose impact changed since the preview and previews it again", async () => {
    vi.mocked(api.jobItems).mockResolvedValue({ items: [changedBeta], nextCursor: null });
    vi.mocked(api.confirmJob).mockResolvedValue({ ...waiting, state: "queued", confirmedAt: "2026-10-09T09:01:00Z" });
    const { onDeleted } = open();
    fireEvent.click(screen.getByRole("button", { name: "Preview" }));
    await PushedEventSource.push(waiting);
    fireEvent.click(await screen.findByRole("button", { name: "Delete 5 records" }));
    await waitFor(() => expect(api.confirmJob).toHaveBeenCalledWith("j1"));
    await PushedEventSource.push({
      ...waiting,
      state: "completed",
      result: "partial",
      confirmedAt: "2026-10-09T09:01:00Z",
      counts: { applied: 1, rejected: 1, unprocessed: 0, created: 0, updated: 0, unchanged: 0, deleted: 1 },
    });
    expect(await screen.findByText("The object was modified by another session. Please retry.")).toBeInTheDocument();
    await waitFor(() => expect(onDeleted).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Preview again" }));
    await waitFor(() => expect(api.startBatch).toHaveBeenCalledTimes(2));
    // The new preview runs, its stream open, before the test leaves it.
    expect(await screen.findByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });
});
