import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { openEventStream } from "@/api/eventStream";
import { api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { JobNotificationsProvider } from "@/features/jobs/JobNotifications";
import { ReadStopped } from "@/lib/readMatching";
import { emptySelection, selectMatching, toggle, type RecordSelection } from "@/lib/recordSelection";
import { capabilitiesFixture } from "@/test/capabilities";
import { PushedEventSource } from "@/test/jobStream";
import { testModel } from "@/test/fixtures";
import type { BatchUpdateItem, Job, JobItemOutcome } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { BulkChangeDialog } from "./BulkChangeDialog";

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

const waiting = job({
  state: "awaiting_confirmation",
  progress: { total: 2, processed: 2 },
  counts: { applied: 1, rejected: 1, unprocessed: 0, created: 0, updated: 1, unchanged: 0, deleted: 0 },
  preview: {
    coverage: "complete",
    items: { total: 2, previewed: 2 },
    counts: { created: 0, updated: 1, unchanged: 0, deleted: 0, rejected: 1 },
    result: "partial",
    previewedAt: "2026-10-09T09:00:00Z",
  },
});

const refusedBeta: JobItemOutcome = {
  index: 1,
  ref: "Beta",
  status: "rejected",
  error: { code: "VERSION_CONFLICT", message: "The record was changed by someone else." },
};

function open(selection: RecordSelection, selected: number, readMatching = vi.fn(), onOpenRecord = vi.fn()) {
  render(
    <ToastProvider>
      <JobNotificationsProvider model={testModel} onNavigate={vi.fn()}>
        <BulkChangeDialog
          model={testModel}
          objectType={domain}
          workspaceKey="west"
          selection={selection}
          selected={selected}
          readMatching={readMatching}
          onClose={vi.fn()}
          onApplied={vi.fn()}
          onOpenRecord={onOpenRecord}
        />
      </JobNotificationsProvider>
    </ToastProvider>,
  );
  return { readMatching, onOpenRecord };
}

/** A field added with ＋ Change a field (K6a, D167): its card. */
async function addField(name: string) {
  fireEvent.click(screen.getByRole("button", { name: "Change a field" }));
  const menu = await screen.findByRole("dialog", { name: "Change a field" });
  fireEvent.click(within(menu).getByRole("button", { name: new RegExp(`^${name}`) }));
  return screen.findByRole("group", { name });
}

/** Code added and set to a value, then Preview. */
async function setCodeAndPreview(value = "X-1") {
  const code = screen.queryByRole("group", { name: "Code" }) ?? (await addField("Code"));
  fireEvent.change(within(code).getByLabelText("Code"), { target: { value } });
  fireEvent.click(screen.getByRole("button", { name: "Preview" }));
}

describe("BulkChangeDialog (0.9 K2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    PushedEventSource.open = [];
    vi.mocked(openEventStream).mockImplementation((url) => new PushedEventSource(url));
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture());
    vi.mocked(api.startBatch).mockResolvedValue(job({}));
    vi.mocked(api.cancelJob).mockResolvedValue(job({ state: "cancelled" }));
    vi.mocked(api.jobItems).mockResolvedValue({ items: [refusedBeta], nextCursor: null });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("previews the hand-picked records with their versions, names the refused one and opens it", async () => {
    const { onOpenRecord } = open(picked, 2);
    expect(screen.getByText("2 domains")).toBeInTheDocument();
    // Code is required: it is set, never cleared (D117).
    expect(within(await addField("Code")).queryByRole("radio", { name: "Clear" })).toBeNull();
    await setCodeAndPreview();
    await waitFor(() => expect(api.startBatch).toHaveBeenCalled());
    const [body] = vi.mocked(api.startBatch).mock.calls[0];
    expect(body).toMatchObject({ workspaceKey: "west", policy: "independent", run: "background", stage: "preview" });
    expect((body.items as BatchUpdateItem[]).map((item) => [item.ref, item.target.id, item.expectedVersion])).toEqual([
      ["Alpha", "a", 3],
      ["Beta", "b", 5],
    ]);
    expect((body.items[0] as BatchUpdateItem).attributes).toEqual([{ attributeTypeKey: "code", value: "X-1" }]);

    await PushedEventSource.push(waiting);
    expect(await screen.findByText("Applying would change 1 domain and refuse 1.")).toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", { name: "Beta" }));
    expect(onOpenRecord).toHaveBeenCalledWith("b");
  });

  it("offers all or nothing only up to the deployment's limit, saying why", async () => {
    const capabilities = capabilitiesFixture();
    capabilities.integrationJobs.limits.atomicJobMaxItems = 1000;
    vi.mocked(api.capabilities).mockResolvedValue(capabilities);
    open(selectMatching(2345), 2345);
    expect(await screen.findByText(/All or nothing holds at most 1,000 records/)).toHaveTextContent(
      "ATOMIC_JOB_MAX_ITEMS",
    );
    expect(screen.queryByRole("radio", { name: "Change none" })).toBeNull();
    expect(screen.getByText("All 2,345 matching domains")).toBeInTheDocument();
  });

  it("reads all matching first, and Stop sends nothing", async () => {
    const readMatching = vi.fn(
      (signal: AbortSignal, onProgress: (read: number, total: number | undefined) => void) =>
        new Promise((_, reject) => {
          onProgress(500, 2345);
          signal.addEventListener("abort", () => reject(new ReadStopped()));
        }),
    );
    open(selectMatching(2345), 2345, readMatching);
    await setCodeAndPreview();
    expect(await screen.findByText("Reading 500 of 2,345 domains")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Stop" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Preview" })).toBeEnabled());
    expect(api.startBatch).not.toHaveBeenCalled();
  });

  it("explains a change set changed before Apply and previews again", async () => {
    vi.mocked(api.confirmJob).mockRejectedValue(
      new ApiError(409, "CHANGE_SET_VERSION_CONFLICT", "The change set changed since the batch was sent"),
    );
    open(picked, 2);
    await setCodeAndPreview();
    await waitFor(() => expect(api.startBatch).toHaveBeenCalledTimes(1));
    await PushedEventSource.push(waiting);
    fireEvent.click(await screen.findByRole("button", { name: "Apply" }));
    expect(await screen.findByText("The change set changed since the preview")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview again" }));
    await waitFor(() => expect(api.startBatch).toHaveBeenCalledTimes(2));
    expect(api.cancelJob).toHaveBeenCalledWith("j1");
    expect((vi.mocked(api.startBatch).mock.calls[1][0].items[0] as BatchUpdateItem).attributes).toEqual([
      { attributeTypeKey: "code", value: "X-1" },
    ]);
  });

  it("cancels the preview when the dialog is left, but keeps it waiting for View job", async () => {
    open(picked, 2);
    await setCodeAndPreview();
    await PushedEventSource.push(waiting);
    await screen.findByRole("button", { name: "Apply" });
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    await waitFor(() => expect(api.cancelJob).toHaveBeenCalledWith("j1"));

    vi.mocked(api.cancelJob).mockClear();
    open(picked, 2);
    await setCodeAndPreview();
    await PushedEventSource.push(waiting);
    fireEvent.click(await screen.findByRole("link", { name: "View job" }));
    expect(api.cancelJob).not.toHaveBeenCalled();
  });

  it("explains a change too large to send, naming the setting", async () => {
    vi.mocked(api.startBatch).mockRejectedValue(
      new ApiError(413, "BATCH_TOO_LARGE", "Too large", {
        setting: "BATCH_BACKGROUND_MAX_BYTES",
        maximum: 50 * 1024 * 1024,
      }),
    );
    open(picked, 2);
    await setCodeAndPreview();
    const notice = await screen.findByText(/more than one bulk change may hold/);
    expect(notice).toHaveTextContent("BATCH_BACKGROUND_MAX_BYTES");
    expect(notice).toHaveTextContent("Narrow the list");
  });

  it("adds only the fields being changed, each a card that sets or clears it (K6a, D167)", async () => {
    open(picked, 2);
    expect(screen.getByText("Fields you do not add keep their values.")).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Code" })).toBeNull();
    const active = await addField("Active");
    expect(
      within(active)
        .getAllByRole("radio")
        .map((radio) => radio.closest("label")?.textContent),
    ).toEqual(["Set to", "Clear"]);
    fireEvent.click(within(active).getByRole("radio", { name: "Clear" }));
    expect(within(active).getByText("Active is emptied on every selected domain.")).toBeInTheDocument();
    expect(screen.getByText("Changes 1 field on 2 domains")).toBeInTheDocument();
    // The menu offers only the fields not yet added, with their kinds.
    fireEvent.click(screen.getByRole("button", { name: "Change a field" }));
    const menu = await screen.findByRole("dialog", { name: "Change a field" });
    expect(within(menu).queryByRole("button", { name: /^Active/ })).toBeNull();
    expect(within(menu).getByRole("button", { name: /^Code/ })).toHaveTextContent("Text");
    fireEvent.keyDown(menu, { key: "Escape" });
    fireEvent.click(within(active).getByRole("button", { name: "Do not change Active" }));
    expect(screen.queryByRole("group", { name: "Active" })).toBeNull();
    expect(screen.getByText("Add a field to change")).toBeInTheDocument();
  });
});
