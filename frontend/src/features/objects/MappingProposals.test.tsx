import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { api } from "@/api/client";
import { openEventStream } from "@/api/eventStream";
import { JobNotificationsProvider } from "@/ui/JobNotifications";
import { CollectionView } from "@/features/objects/views/CollectionViewHost";
import { permissionsFixture } from "@/test/permissions";
import { PushedEventSource } from "@/test/jobStream";
import { testModel } from "@/test/fixtures";
import type {
  AiSystemInfo,
  ChangeSet,
  Job,
  MappingCoveragePage,
  MappingGridViewDefinition,
  SystemResponse,
} from "@/types";
import { ToastProvider } from "@/ui/Toast";

vi.mock("@/api/eventStream", () => ({ openEventStream: vi.fn() }));
vi.mock("@/api/aiClient", () => ({ ai: { status: vi.fn() } }));
vi.mock("@/api/client", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/api/client")>()),
  api: {
    system: vi.fn(),
    mappingCoverage: vi.fn(),
    proposeMappingTargets: vi.fn(),
    cancelJob: vi.fn(),
  },
}));

// The page's data: live, or a change set, held by what each test sets.
const data = vi.hoisted(() => ({ value: {} as Record<string, unknown> }));
vi.mock("@/state/WorkspaceDataContext", () => ({
  useWorkspaceData: () => data.value,
  useDataApi: () => data.value.api,
  useRecordWrites: () => ({
    any: true,
    permits: () => true,
    permitsType: () => true,
    permitsRelation: () => true,
  }),
}));

const model = structuredClone(testModel);
model.schemaVersion = "0.6";
model.relationTypes.push({
  key: "maps-to",
  reverseKey: "mapped-from",
  name: "Maps to",
  reverseName: "Mapped from",
  isOriented: true,
  features: {},
});
model.objectTypeRelations.push({
  relationTypeKey: "maps-to",
  fromObjectTypeKey: "domain",
  toObjectTypeKey: "codelist",
  cardinality: "many-to-many",
});
const view: MappingGridViewDefinition = {
  key: "domain-to-codelist-mapping",
  name: "Domain to Codelist Mapping",
  type: "mappingGrid",
  config: {
    relationTypeKey: "maps-to",
    fromObjectTypeKey: "domain",
    toObjectTypeKey: "codelist",
    direction: "outgoing",
    sourceColumns: ["code"],
    targetDisplayColumns: [],
    candidateSearchFields: ["code"],
    pageSize: 20,
  },
};
model.applications[0].views.push(view);

const origin = {
  kind: "ai" as const,
  provider: "fake",
  model: "fake-1",
  promptVersion: "1",
  confidence: 0.86,
  reason: "The name says it is the same thing.",
  proposedBy: "p1",
};
const coverage: MappingCoveragePage = {
  items: [
    {
      source: { id: "s1", objectTypeKey: "domain", name: "Connections", fields: { code: "CLI" } },
      state: "mapped",
      mappingVersion: 3,
      targetCount: 1,
      targets: [
        {
          relationId: "r1",
          attributes: {},
          object: { id: "t1", objectTypeKey: "codelist", name: "Means of transport", fields: {} },
          origin,
        },
      ],
      targetsNextCursor: null,
    },
    {
      source: { id: "s2", objectTypeKey: "domain", name: "Financial", fields: { code: "FIN" } },
      state: "mapped",
      mappingVersion: 1,
      targetCount: 1,
      targets: [
        {
          relationId: "r2",
          attributes: {},
          object: { id: "t2", objectTypeKey: "codelist", name: "Invoice types", fields: {} },
        },
      ],
      targetsNextCursor: null,
    },
  ],
  nextCursor: null,
  totalCount: 2,
};

const changeSet = { id: "cs1", name: "October cleanup", version: 7, workspaceKey: "west" } as ChangeSet;
const query = { search: "", sort: "", pageSize: 20, filters: [] };

const job = (extra: Partial<Job>): Job =>
  ({
    id: "j1",
    kind: "aiProposal",
    workspaceKey: "west",
    changeSetId: "cs1",
    state: "queued",
    progress: { total: 300, processed: 0 },
    counts: {},
    error: null,
    parameters: {},
    aiProposal: null,
    ...extra,
  }) as Job;

function setUp(options: {
  ai?: AiSystemInfo;
  groups?: string[];
  changeSet?: ChangeSet;
  props?: Partial<Parameters<typeof CollectionView>[0]>;
}) {
  const aiInfo = options.ai ?? { configured: true, provider: "fake", model: "fake-1", sendLevel: "values" };
  vi.mocked(api.system).mockResolvedValue({ ai: aiInfo } as SystemResponse);
  data.value = {
    api,
    warning: "",
    changeSet: options.changeSet,
    permissions: permissionsFixture("west", options.groups ?? ["ai-proposals", "change-sets"]),
    refresh: options.changeSet ? vi.fn().mockResolvedValue(options.changeSet) : undefined,
  };
  const onQueryChange = vi.fn();
  const onShowProposed = vi.fn();
  render(
    <ToastProvider>
      <JobNotificationsProvider model={model} onNavigate={vi.fn()}>
        <CollectionView
          model={model}
          application={model.applications[0]}
          view={view}
          workspaceKey="west"
          query={query}
          onQueryChange={onQueryChange}
          onShowProposed={onShowProposed}
          onOpen={vi.fn()}
          {...options.props}
        />
      </JobNotificationsProvider>
    </ToastProvider>,
  );
  return { onQueryChange, onShowProposed };
}

const button = "Propose targets";

describe("Propose targets (0.16 AP2)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    PushedEventSource.open = [];
    vi.mocked(openEventStream).mockImplementation((url) => new PushedEventSource(url));
    vi.mocked(api.mappingCoverage).mockImplementation(async (query) =>
      query.state === "unmapped" ? { items: [], nextCursor: null, totalCount: 300 } : coverage,
    );
    vi.mocked(ai.status).mockResolvedValue({ minConfidence: 0.5, model: "fake-1" } as never);
    vi.mocked(api.proposeMappingTargets).mockResolvedValue(job({}));
  });

  it("marks a target the AI proposed with its confidence and reason, and no other", async () => {
    setUp({});
    await screen.findByText("Means of transport");
    expect(screen.getByText("Proposed by the AI · 86%")).toBeInTheDocument();
    expect(screen.getByText("The name says it is the same thing.")).toBeInTheDocument();
    expect(screen.getAllByText(/Proposed by the AI/)).toHaveLength(1);
  });

  it("offers the Proposed filter only in a change set, and asks the server for it", async () => {
    const { onQueryChange } = setUp({ changeSet });
    const status = screen.getByRole("group", { name: "Mapping status" });
    fireEvent.click(within(status).getByRole("button", { name: "Proposed" }));
    expect(onQueryChange).toHaveBeenCalledWith(
      expect.objectContaining({ mappingProposed: true, mappingState: undefined }),
    );
  });

  it("reads only the proposed sources when the filter is on", async () => {
    setUp({ changeSet, props: { query: { ...query, mappingProposed: true } } });
    await waitFor(() =>
      expect(api.mappingCoverage).toHaveBeenCalledWith(expect.objectContaining({ proposed: true, state: undefined })),
    );
    const status = screen.getByRole("group", { name: "Mapping status" });
    expect(within(status).getByRole("button", { name: "Proposed" })).toHaveAttribute("aria-pressed", "true");
    expect(within(status).getByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "false");
  });

  it("has no Proposed segment in live data", async () => {
    setUp({});
    await screen.findByText("Means of transport");
    expect(screen.queryByRole("button", { name: "Proposed" })).toBeNull();
  });

  it.each([
    ["no provider is set", { configured: false, provider: null, sendLevel: "values" as const }, undefined],
    [
      "the send level is below values",
      { configured: true, provider: "fake", sendLevel: "samples" as const },
      undefined,
    ],
    ["the person lacks ai-proposals", undefined, ["browse", "change-sets"]],
    ["the grid is read only", undefined, undefined],
  ])("does not draw the button when %s", async (name, aiInfo, groups) => {
    setUp({ ai: aiInfo, groups, props: name === "the grid is read only" ? { readOnly: true } : {} });
    await screen.findByText("Means of transport");
    await waitFor(() => expect(api.system).toHaveBeenCalled());
    await new Promise((done) => setTimeout(done, 20));
    expect(screen.queryByRole("button", { name: button })).toBeNull();
  });

  it("offers the button, says what it will do and what is sent, and proposes into the current change set", async () => {
    setUp({ changeSet, props: { query: { ...query, search: "cli" } } });
    fireEvent.click(await screen.findByRole("button", { name: button }));
    const dialog = await screen.findByRole("dialog", { name: button });
    await within(dialog).findByText("300 unmapped domains");
    expect(within(dialog).getByText(/The search “cli” applies/)).toBeInTheDocument();
    expect(within(dialog).getByRole("radio", { name: "Current: “October cleanup”" })).toBeChecked();
    expect(
      within(dialog).getByText(
        "Sent to fake (fake-1): the names of the domains and codelists and the fields this view shows. Proposals below 50% confidence are not offered.",
      ),
    ).toBeInTheDocument();
    expect(api.mappingCoverage).toHaveBeenCalledWith(
      expect.objectContaining({ state: "unmapped", search: "cli", includeTotal: true, changeSetId: "cs1" }),
    );
    fireEvent.click(within(dialog).getByRole("button", { name: "Propose" }));
    await waitFor(() => expect(api.proposeMappingTargets).toHaveBeenCalled());
    expect(api.proposeMappingTargets).toHaveBeenCalledWith("west", {
      applicationKey: "test-app",
      viewKey: "domain-to-codelist-mapping",
      search: "cli",
      changeSetId: "cs1",
      expectedChangeSetVersion: 7,
    });
  });

  it("proposes into a new change set named in the dialog, the only choice when none is open", async () => {
    setUp({});
    fireEvent.click(await screen.findByRole("button", { name: button }));
    const dialog = await screen.findByRole("dialog", { name: button });
    await within(dialog).findByText("300 unmapped domains");
    expect(within(dialog).queryByRole("radio")).toBeNull();
    const name = within(dialog).getByLabelText("Name of the new change set");
    expect(name).toHaveValue("AI proposals: Domain to Codelist Mapping");
    fireEvent.change(name, { target: { value: "Mine" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Propose" }));
    await waitFor(() => expect(api.proposeMappingTargets).toHaveBeenCalled());
    const body = vi.mocked(api.proposeMappingTargets).mock.calls[0][1];
    expect(body).toMatchObject({ changeSetName: "Mine" });
    expect(body).not.toHaveProperty("changeSetId");
  });

  it("follows the job, then shows the counts and warnings and moves to the change set", async () => {
    const { onShowProposed } = setUp({});
    fireEvent.click(await screen.findByRole("button", { name: button }));
    const dialog = await screen.findByRole("dialog", { name: button });
    await within(dialog).findByText("300 unmapped domains");
    fireEvent.click(within(dialog).getByRole("button", { name: "Propose" }));
    await PushedEventSource.push(job({ state: "running", progress: { total: 300, processed: 125 } }));
    expect(await screen.findByText("125 of 300 domains")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stop" })).toBeInTheDocument();
    await PushedEventSource.push(
      job({
        state: "completed",
        progress: { total: 300, processed: 300 },
        aiProposal: {
          proposed: 212,
          unmatched: 80,
          changed: 8,
          refused: 0,
          notAnswered: 0,
          changeSetId: "cs-new",
          warnings: ["1 batch of 25 was not answered (the provider timed out)."],
        },
      }),
    );
    const result = await screen.findByRole("dialog", { name: "Targets proposed" });
    const counts = result;
    expect(within(counts).getByText("212")).toBeInTheDocument();
    expect(within(counts).getByText("80")).toBeInTheDocument();
    expect(within(counts).getByText("8")).toBeInTheDocument();
    expect(within(counts).queryByText("Refused by the model’s rules")).toBeNull();
    expect(within(counts).getByText(/1 batch of 25 was not answered/)).toBeInTheDocument();
    fireEvent.click(within(counts).getByRole("button", { name: "Show proposed" }));
    expect(onShowProposed).toHaveBeenCalledWith("cs-new");
  });

  it("names what stops a request: no provider any more", async () => {
    vi.mocked(api.proposeMappingTargets).mockRejectedValue(
      new (await import("@/api/errors")).ApiError(409, "AI_SEND_LEVEL_TOO_LOW", "too low"),
    );
    setUp({});
    fireEvent.click(await screen.findByRole("button", { name: button }));
    const dialog = await screen.findByRole("dialog", { name: button });
    await within(dialog).findByText("300 unmapped domains");
    fireEvent.click(within(dialog).getByRole("button", { name: "Propose" }));
    expect(await within(dialog).findByText(/does not let record names leave the server/)).toBeInTheDocument();
  });
});
