import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { openEventStream } from "@/api/eventStream";
import { api } from "@/api/client";
import { JobNotificationsProvider } from "@/ui/JobNotifications";
import { emptySelection, toggle } from "@/lib/recordSelection";
import { capabilitiesFixture } from "@/test/capabilities";
import { domainObject, testModel } from "@/test/fixtures";
import { PushedEventSource } from "@/test/jobStream";
import type { BatchRelationItem, EngineModel, Job, JobItemOutcome } from "@/types";
import { ToastProvider } from "@/ui/Toast";
import { BulkRelationDialog } from "./BulkRelationDialog";

// Job streams are read with fetch (0.12 I2); the test drives them instead.
vi.mock("@/api/eventStream", () => ({ openEventStream: vi.fn() }));

vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: {
    capabilities: vi.fn(),
    objects: vi.fn(),
    heldRecords: vi.fn(),
    startBatch: vi.fn(),
    confirmJob: vi.fn(),
    cancelJob: vi.fn(),
    jobItems: vi.fn(),
  },
}));

/** The test model where a domain cites codelists (many-to-many) and is filed under one (one-to-many). */
const model: EngineModel = {
  ...testModel,
  relationTypes: [
    ...testModel.relationTypes,
    { key: "cites", name: "Cites", reverseName: "Cited by", features: {} },
    { key: "files", name: "Files", reverseName: "Filed under", features: {} },
  ] as EngineModel["relationTypes"],
  objectTypeRelations: [
    ...testModel.objectTypeRelations,
    { relationTypeKey: "cites", fromObjectTypeKey: "domain", toObjectTypeKey: "codelist", cardinality: "many-to-many" },
    { relationTypeKey: "files", fromObjectTypeKey: "codelist", toObjectTypeKey: "domain", cardinality: "one-to-many" },
  ],
};
const domain = model.objectTypes.find((type) => type.key === "domain")!;
const picked = toggle(toggle(emptySelection, { id: "a", version: 3, name: "Alpha" }), {
  id: "b",
  version: 5,
  name: "Beta",
});
const codelists = [
  { ...domainObject, id: "c1", objectTypeKey: "codelist", name: "Colours" },
  { ...domainObject, id: "c2", objectTypeKey: "codelist", name: "Sizes" },
];

const job = (extra: Partial<Job>): Job =>
  ({
    id: "j1",
    kind: "batch",
    workspaceKey: "west",
    changeSetId: null,
    state: "queued",
    stage: null,
    progress: { total: 4, processed: 0 },
    counts: { applied: 0, rejected: 0, unprocessed: 0, created: 0, updated: 0, unchanged: 0, deleted: 0 },
    result: null,
    error: null,
    parameters: { policy: "independent", run: "background", stage: "preview" },
    confirmedAt: null,
    ...extra,
  }) as Job;

function open(selected = 2) {
  const onOpenRecord = vi.fn();
  render(
    <ToastProvider>
      <JobNotificationsProvider model={model} onNavigate={vi.fn()}>
        <BulkRelationDialog
          model={model}
          objectType={domain}
          workspaceKey="west"
          selection={picked}
          selected={selected}
          readMatching={vi.fn()}
          onClose={vi.fn()}
          onApplied={vi.fn()}
          onOpenRecord={onOpenRecord}
        />
      </JobNotificationsProvider>
    </ToastProvider>,
  );
  return { onOpenRecord };
}

/** A record ticked in the dialog's record checklist (K6a). */
async function tick(name: string) {
  const list = await screen.findByRole("group", { name: "Codelists" });
  const row = (await within(list).findByText(name)).closest("label")!;
  fireEvent.click(within(row).getByRole("checkbox"));
  return row;
}

const modes = () =>
  within(screen.getByRole("group", { name: "What to do" }))
    .getAllByRole("radio")
    .map((radio) => radio.closest("label")?.textContent);

describe("BulkRelationDialog (0.9 K3)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    PushedEventSource.open = [];
    vi.mocked(openEventStream).mockImplementation((url) => new PushedEventSource(url));
    vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture());
    vi.mocked(api.objects).mockResolvedValue({ items: codelists, nextCursor: null });
    // Alpha holds Sizes (D165).
    vi.mocked(api.heldRecords).mockResolvedValue({
      items: [{ object: { id: "c2", name: "Sizes", objectTypeKey: "codelist" }, count: 1 }],
      nextCursor: null,
    });
    vi.mocked(api.startBatch).mockResolvedValue(job({}));
    vi.mocked(api.cancelJob).mockResolvedValue(job({ state: "cancelled" }));
  });
  afterEach(() => vi.unstubAllGlobals());

  it("offers each relationship's actions from its cardinality", () => {
    open();
    const relationship = screen.getByRole("radiogroup", { name: "Which relationship" });
    expect(
      within(relationship)
        .getAllByRole("radio")
        .map((radio) => radio.textContent),
    ).toEqual(["Cites · Codelists", "Filed under · Codelists"]);
    expect(modes()).toEqual(["Add", "Remove", "Replace with", "Clear"]);
    fireEvent.click(within(relationship).getByRole("radio", { name: /^Filed under/ }));
    // A domain is filed under one codelist: it is set, not added to (D128).
    expect(modes()).toEqual(["Set to", "Clear"]);
  });

  it("removes only what the selection holds, each with how many hold it; Add marks those held (K6a, D165)", async () => {
    open();
    fireEvent.click(screen.getByRole("radio", { name: "Remove" }));
    const row = await tick("Sizes");
    expect(row).toHaveTextContent("on 1 of 2");
    expect(within(screen.getByRole("group", { name: "Codelists" })).queryByText("Colours")).toBeNull();
    expect(api.heldRecords).toHaveBeenCalledWith(
      expect.objectContaining({
        objectTypeKey: "domain",
        relationTypeKey: "cites",
        direction: "outgoing",
        objectIds: ["a", "b"],
      }),
    );
    expect(screen.getByText("Removes 1 relationship")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview" }));
    await waitFor(() => expect(api.startBatch).toHaveBeenCalled());
    const items = vi.mocked(api.startBatch).mock.calls[0][0].items as BatchRelationItem[];
    expect(items.map((item) => [item.op, item.ref])).toEqual([
      ["ensureNoRelation", "Alpha → Sizes"],
      ["ensureNoRelation", "Beta → Sizes"],
    ]);
    // The preview follows its job's stream; the test ends once it is open.
    await waitFor(() => expect(PushedEventSource.open.length).toBeGreaterThan(0));
  });

  it("adds by the two records, states the changes it makes and says the preview in relationships", async () => {
    vi.mocked(api.jobItems).mockResolvedValue({
      items: [
        { index: 0, ref: "Alpha → Colours", status: "applied", action: "created", relationId: "r1" },
        { index: 1, ref: "Alpha → Sizes", status: "applied", action: "unchanged" },
        {
          index: 2,
          ref: "Beta → Colours",
          status: "rejected",
          error: {
            code: "DUPLICATE_RELATION_SCOPE",
            message: "A related object already exists for this ancestor scope",
          },
        },
      ] as JobItemOutcome[],
      nextCursor: null,
    });
    const { onOpenRecord } = open();
    expect(await tick("Sizes")).toHaveTextContent("already on 1");
    await tick("Colours");
    expect(screen.getByText("2 domains × 2 codelists: up to 4 changes")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview" }));
    await waitFor(() => expect(api.startBatch).toHaveBeenCalled());
    const items = vi.mocked(api.startBatch).mock.calls[0][0].items as BatchRelationItem[];
    expect(items.map((item) => [item.op, item.ref])).toEqual([
      ["ensureRelation", "Alpha → Sizes"],
      ["ensureRelation", "Alpha → Colours"],
      ["ensureRelation", "Beta → Sizes"],
      ["ensureRelation", "Beta → Colours"],
    ]);

    await PushedEventSource.push(
      job({
        state: "awaiting_confirmation",
        preview: {
          coverage: "complete",
          items: { total: 4, previewed: 4 },
          counts: { created: 1, updated: 0, unchanged: 1, deleted: 1, rejected: 1 },
          result: "partial",
          previewedAt: "2026-10-09T09:00:00Z",
        },
      }),
    );
    expect(await screen.findByText("Applying would change 2 relationships and refuse 1.")).toBeInTheDocument();
    // Counted and listed in a relationship's words.
    expect(screen.getAllByText("Would be added")).toHaveLength(2);
    expect(screen.getByText("Would be removed")).toBeInTheDocument();
    expect(screen.getByText("Not related")).toBeInTheDocument();
    // A refused pair opens its selected record.
    fireEvent.click(await screen.findByRole("button", { name: "Beta → Colours" }));
    expect(onOpenRecord).toHaveBeenCalledWith("b");
  });

  it("explains a replacement larger than one preview and sends nothing (D131)", async () => {
    vi.mocked(api.capabilities).mockResolvedValue({
      ...capabilitiesFixture(),
      integrationJobs: {
        ...capabilitiesFixture().integrationJobs,
        limits: { ...capabilitiesFixture().integrationJobs.limits, previewMaxItems: 1 },
      },
    });
    open();
    await waitFor(() => expect(api.capabilities).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("radio", { name: "Clear" }));
    fireEvent.click(screen.getByRole("button", { name: "Preview" }));
    expect(await screen.findByText(/a preview on this deployment tries at most 1/)).toBeInTheDocument();
    expect(screen.getByText(/JOB_PREVIEW_MAX_ITEMS/)).toBeInTheDocument();
    expect(api.startBatch).not.toHaveBeenCalled();
  });

  it("names a record whose set changed since the preview and offers Preview again", async () => {
    vi.mocked(api.jobItems).mockResolvedValue({
      items: [
        {
          index: 1,
          ref: "Beta",
          status: "rejected",
          error: { code: "RELATION_SET_VERSION_CONFLICT", message: "The relation set has changed since it was read" },
        },
      ] as JobItemOutcome[],
      nextCursor: null,
    });
    const waiting = job({
      state: "awaiting_confirmation",
      progress: { total: 2, processed: 2 },
      preview: {
        coverage: "complete",
        items: { total: 2, previewed: 2 },
        counts: { created: 0, updated: 2, unchanged: 0, deleted: 0, rejected: 0 },
        result: "applied",
        previewedAt: "2026-10-09T09:00:00Z",
      },
    });
    vi.mocked(api.confirmJob).mockResolvedValue({ ...waiting, state: "queued", confirmedAt: "2026-10-09T09:01:00Z" });
    open();
    fireEvent.click(screen.getByRole("radio", { name: "Replace with" }));
    await tick("Colours");
    expect(screen.getByText("One change for each selected domain: 2 changes")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview" }));
    await PushedEventSource.push(waiting);
    fireEvent.click(await screen.findByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.confirmJob).toHaveBeenCalledWith("j1"));
    await PushedEventSource.push({
      ...waiting,
      state: "completed",
      result: "partial",
      confirmedAt: "2026-10-09T09:01:00Z",
      counts: { applied: 1, rejected: 1, unprocessed: 0, created: 0, updated: 1, unchanged: 0, deleted: 0 },
    });
    expect(await screen.findByText("The relation set has changed since it was read")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Preview again" }));
    await waitFor(() => expect(api.startBatch).toHaveBeenCalledTimes(2));
    expect(await screen.findByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });
});
