import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ai } from "@/api/aiClient";
import { API_URL, api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { ApiReferencePage } from "@/features/settings/ApiReferencePage";
import { ConsumerApisPage } from "@/features/settings/ConsumerApisPage";
import { JobsPage } from "@/features/settings/JobsPage";
import { capabilitiesFixture } from "@/test/capabilities";
import { testModel } from "@/test/fixtures";
import { JobNotificationsProvider } from "@/features/jobs/JobNotifications";
import { ToastProvider } from "@/ui/Toast";
import type {
  ConsumerApiDocument,
  ConsumerApiIndexEntry,
  Job,
  JobGroup,
  JobGroupRow,
  RouteState,
  SettingsRoute,
  SystemResponse,
} from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

vi.mock("@/api/aiClient", async (load) => {
  const actual = await load<typeof import("@/api/aiClient")>();
  return { ...actual, ai: { ...actual.ai, task: vi.fn() } };
});

const system = {
  engine: {
    version: "0.9.0-alpha.1",
    managementApi: "v1",
    license: "AGPL-3.0-or-later",
    sourceCode: "https://github.com/refiroo/refiroo/tree/v0.9.0-alpha.1",
    build: { commit: null, tag: null },
  },
  schemaLanguages: ["0.8"],
  activeModelRelease: {
    id: "r1",
    key: "test",
    name: "Test",
    version: "0.3.0",
    schemaVersion: "0.8",
    activatedAt: "2026-10-07T08:00:00Z",
  },
  ai: { configured: false, provider: null, sendLevel: "structure" },
  mcp: { enabled: false },
} satisfies SystemResponse;

// Two consumer APIs, one on each page of the index.
const entries: ConsumerApiIndexEntry[] = [
  {
    consumerApi: "codes",
    name: "Codes",
    description: "Codes for consumers",
    contractVersion: 2,
    openapi: "/api/consumer/codes/v2/openapi.json",
  },
  { consumerApi: "plain", name: "Plain", contractVersion: 1, openapi: "/api/consumer/plain/v1/openapi.json" },
];

const job = (id: string, overrides: Partial<Job> = {}): Job => ({
  id,
  kind: "batch",
  workspaceKey: "default",
  changeSetId: null,
  state: "completed",
  stage: null,
  progress: { total: 3, processed: 3 },
  counts: { applied: 2, rejected: 1, unprocessed: 0, created: 2, updated: 0, unchanged: 0, deleted: 0 },
  result: "partial",
  error: null,
  createdAt: "2026-10-07T08:00:00Z",
  startedAt: "2026-10-07T08:00:01Z",
  finishedAt: "2026-10-07T08:00:02Z",
  expiresAt: "2026-10-14T08:00:00Z",
  cancelRequestedAt: null,
  requestedBy: null,
  parameters: {},
  output: null,
  ...overrides,
});

/** The jobs list in the providers the application gives every page (0.9 J1u). */
function renderJobs(
  route: Extract<SettingsRoute, { page: "jobs" }> = { kind: "settings", page: "jobs" },
  onNavigate: (route: RouteState) => void = vi.fn(),
) {
  render(
    <ToastProvider>
      <JobNotificationsProvider model={testModel} onNavigate={vi.fn()}>
        <JobsPage model={testModel} route={route} onNavigate={onNavigate} />
      </JobNotificationsProvider>
    </ToastProvider>,
  );
}

/** The browser's storage, which the test environment does not provide. */
function stubStorage() {
  const held = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => held.get(key) ?? null,
    setItem: (key: string, value: string) => held.set(key, value),
    removeItem: (key: string) => held.delete(key),
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  stubStorage();
  vi.mocked(api.system).mockResolvedValue(system);
  vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture());
  // The Jobs page names each workspace by its label.
  vi.mocked(api.workspaces).mockResolvedValue({ items: [], nextCursor: null });
  // Each definition's document names its routes, as the engine writes them (C6b).
  vi.mocked(api.consumerApiDocument).mockImplementation(async (url): Promise<ConsumerApiDocument> => {
    const base = new URL(url).pathname.replace(/\/openapi\.json$/, "");
    return {
      paths: {
        [`${base}/objects/{id}`]: { get: { summary: "Get by ID" } },
        [`${base}/xref`]: { get: { summary: "XREF lookup" } },
        [`${base}/resolve`]: { post: { summary: "Batch resolve" } },
      },
    };
  });
  vi.mocked(api.consumerApis)
    .mockResolvedValueOnce({ items: entries.slice(0, 1), nextCursor: "c2" })
    .mockResolvedValueOnce({ items: entries.slice(1), nextCursor: null });
});

const CONSUMER_APIS = { kind: "settings", page: "consumer-apis" } as const;
const API_REFERENCE = { kind: "settings", page: "api-reference" } as const;

describe("Consumer APIs", () => {
  it("shows each API of every index page with its base URL and its routes, each linked to its documentation", async () => {
    const onNavigate = vi.fn();
    render(<ConsumerApisPage route={CONSUMER_APIS} onNavigate={onNavigate} />);
    const codes = await screen.findByRole("region", { name: "Codes · v2" });
    expect(api.consumerApis).toHaveBeenLastCalledWith("c2", "");
    expect(api.consumerApiDocument).toHaveBeenCalledWith(`${API_URL}/api/consumer/codes/v2/openapi.json`);
    expect(codes).toHaveTextContent("Codes for consumers");
    expect(await screen.findByRole("region", { name: "Change feed" })).toHaveTextContent(/Change feed kept\s*30 days/);
    expect(within(codes).getByText(`${API_URL}/api/consumer/codes/v2`)).toBeInTheDocument();
    expect(within(codes).getByRole("button", { name: "Copy Base URL" })).toBeInTheDocument();
    expect(within(codes).getByRole("link", { name: `${API_URL}/api/consumer/codes/v2/openapi.json` })).toHaveAttribute(
      "href",
      `${API_URL}/api/consumer/codes/v2/openapi.json`,
    );
    expect(within(codes).getByRole("button", { name: "Copy OpenAPI document" })).toBeInTheDocument();
    const routes = within(codes).getByRole("group", { name: "Codes: routes" });
    expect(
      within(routes)
        .getAllByRole("rowheader")
        .map((cell) => cell.textContent),
    ).toEqual(["GET /objects/{id}", "GET /xref", "POST /resolve"]);
    expect(within(routes).getByRole("link", { name: "XREF lookup" })).toHaveAttribute(
      "href",
      `${API_URL}/docs/api#consumer-codes-v2/GET/api/consumer/codes/v2/xref`,
    );
    expect(within(routes).getByRole("link", { name: "Batch resolve" })).toHaveAttribute(
      "href",
      `${API_URL}/docs/api#consumer-codes-v2/POST/api/consumer/codes/v2/resolve`,
    );
    const plain = screen.getByRole("region", { name: "Plain · v1" });
    expect(within(plain).getByRole("link", { name: "Get by ID" })).toHaveAttribute(
      "href",
      `${API_URL}/docs/api#consumer-plain-v1/GET/api/consumer/plain/v1/objects/{id}`,
    );

    fireEvent.click(screen.getByRole("link", { name: "Open the release" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "model", releaseId: "r1" });
  });

  it("says when the active release declares none, and opens the model", async () => {
    vi.mocked(api.consumerApis).mockReset().mockResolvedValue({ items: [], nextCursor: null });
    const onNavigate = vi.fn();
    render(<ConsumerApisPage route={CONSUMER_APIS} onNavigate={onNavigate} />);
    expect(await screen.findByText("The active release declares no consumer API.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open model" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "model" });
  });
});

describe("Jobs", () => {
  beforeEach(() => localStorage.setItem("refiroo.jobs.view", JSON.stringify("all")));

  it("lists jobs with their state and counts, loads more, and shows the limits", async () => {
    vi.mocked(api.jobs)
      .mockResolvedValueOnce({ items: [job("j2")], nextCursor: "next" })
      .mockResolvedValueOnce({
        items: [job("j1", { state: "failed", result: null, error: { code: "JOB_FAILED", message: "It failed" } })],
        nextCursor: null,
      });
    renderJobs();
    const jobs = await screen.findByRole("group", { name: "Jobs" });
    expect(within(jobs).getByRole("row", { name: /j2/ })).toHaveTextContent(
      /default\s*Completed\s*Partly applied\s*3 of 3 processed: 2 applied, 1 rejected, 0 unprocessed/,
    );
    fireEvent.click(screen.getByRole("button", { name: "Load more jobs" }));
    expect(await within(jobs).findByRole("row", { name: /j1/ })).toHaveTextContent(/Failed\s*It failed/);
    expect(api.jobs).toHaveBeenLastCalledWith("next");
    expect(screen.queryByRole("button", { name: "Load more jobs" })).not.toBeInTheDocument();
    const limits = screen.getByRole("region", { name: "Limits" });
    expect(limits).toHaveTextContent(/Background batch\s*1,000,000 items, 50 MB/);
    // The change feed's retention is on Consumer APIs, whose consumers follow it (0.10 A5c).
    expect(limits).not.toHaveTextContent(/Change feed/);
  });

  it("cancels a running job after confirming, and shows the request", async () => {
    vi.mocked(api.jobs).mockResolvedValue({
      items: [job("j1", { state: "running", result: null, finishedAt: null })],
      nextCursor: null,
    });
    vi.mocked(api.cancelJob).mockResolvedValue(
      job("j1", { state: "running", result: null, finishedAt: null, cancelRequestedAt: "2026-10-07T08:00:03Z" }),
    );
    renderJobs();
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    fireEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Cancel job" }));
    const row = await screen.findByRole("row", { name: /j1/ });
    expect(await within(row).findByText("Cancel requested")).toBeInTheDocument();
    expect(api.cancelJob).toHaveBeenCalledWith("j1");
    expect(within(row).queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("says when the job finished first, and reloads the list", async () => {
    vi.mocked(api.jobs)
      .mockResolvedValueOnce({
        items: [job("j1", { state: "queued", result: null, finishedAt: null })],
        nextCursor: null,
      })
      .mockResolvedValueOnce({ items: [job("j1")], nextCursor: null });
    vi.mocked(api.cancelJob).mockRejectedValue(new ApiError(409, "JOB_FINISHED", "Job j1 has already finished"));
    renderJobs();
    fireEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    fireEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Cancel job" }));
    expect(await screen.findByText("Job j1 has already finished")).toBeInTheDocument();
    expect(await screen.findByText("Completed")).toBeInTheDocument();
    expect(api.jobs).toHaveBeenCalledTimes(2);
  });

  it("offers no cancel while jobs cannot be created", async () => {
    const capabilities = capabilitiesFixture();
    vi.mocked(api.capabilities).mockResolvedValue({
      ...capabilities,
      integrationJobs: { ...capabilities.integrationJobs, createJobs: false },
    });
    vi.mocked(api.jobs).mockResolvedValue({
      items: [job("j1", { state: "queued", result: null, finishedAt: null })],
      nextCursor: null,
    });
    renderJobs();
    await screen.findByRole("region", { name: "Limits" });
    await screen.findByText(/Background batch/);
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("says there are no jobs yet", async () => {
    vi.mocked(api.jobs).mockResolvedValue({ items: [], nextCursor: null });
    renderJobs();
    expect(await screen.findByText(/No jobs yet/)).toBeInTheDocument();
  });
});

describe("API reference", () => {
  it("lists the management API and each consumer API with its version and document", async () => {
    render(<ApiReferencePage route={API_REFERENCE} onNavigate={vi.fn()} />);
    const sources = await screen.findByRole("group", { name: "API reference sources" });
    const rows = within(sources).getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getByRole("rowheader").textContent)).toEqual([
      "Management API",
      "Codes",
      "Plain",
    ]);
    expect(rows[0]).toHaveTextContent(/v1 \(engine 0\.9\.0-alpha\.1\)/);
    expect(within(rows[0]).getByRole("link", { name: "Management API" })).toHaveAttribute(
      "href",
      `${API_URL}/docs/api?api=management`,
    );
    expect(within(rows[1]).getByRole("link", { name: "Codes" })).toHaveAttribute(
      "href",
      `${API_URL}/docs/api?api=consumer-codes-v2`,
    );
    expect(rows[1]).toHaveTextContent("v2");
    expect(within(rows[2]).getByRole("link", { name: "openapi.json" })).toHaveAttribute(
      "href",
      `${API_URL}/api/consumer/plain/v1/openapi.json`,
    );
  });
});

describe("A chosen workspace (the API reference and Consumer APIs)", () => {
  const twoWorkspaces = () =>
    vi.mocked(api.workspaces).mockResolvedValue({
      items: [
        { key: "stops", label: "STOPS" },
        { key: "rdm", label: "RDM" },
      ],
      nextCursor: null,
    } as never);

  it("offers no choice while there is one workspace, and no workspace parameter is sent", async () => {
    render(<ApiReferencePage route={API_REFERENCE} onNavigate={vi.fn()} />);
    await screen.findByRole("group", { name: "API reference sources" });
    expect(screen.queryByRole("combobox")).toBeNull();
    expect(api.consumerApis).toHaveBeenCalledWith(undefined, "");
  });

  it("reads and links the chosen workspace's APIs and asks the route to carry the choice", async () => {
    twoWorkspaces();
    vi.mocked(api.consumerApis).mockReset().mockResolvedValue({ items: entries, nextCursor: null });
    const onNavigate = vi.fn();
    const view = render(<ApiReferencePage route={API_REFERENCE} onNavigate={onNavigate} />);
    await screen.findByRole("group", { name: "API reference sources" });
    fireEvent.change(await screen.findByRole("combobox"), { target: { value: "stops" } });
    expect(onNavigate).toHaveBeenCalledWith({ ...API_REFERENCE, workspaceKey: "stops" }, true);
    // The route then names the workspace: the list, the links and the Consumer APIs page follow it.
    view.unmount();
    render(<ApiReferencePage route={{ ...API_REFERENCE, workspaceKey: "stops" }} onNavigate={onNavigate} />);
    await waitFor(() => expect(api.consumerApis).toHaveBeenLastCalledWith(undefined, "stops"));
    expect(await screen.findByRole("link", { name: "Codes" })).toHaveAttribute(
      "href",
      `${API_URL}/docs/api?api=consumer-codes-v2&workspace=stops`,
    );
    cleanup();
    render(<ConsumerApisPage route={{ ...CONSUMER_APIS, workspaceKey: "stops" }} onNavigate={vi.fn()} />);
    const codes = await screen.findByRole("region", { name: "Codes · v2" });
    expect(api.consumerApis).toHaveBeenLastCalledWith(undefined, "stops");
    expect(within(codes).getByRole("link", { name: "XREF lookup" })).toHaveAttribute(
      "href",
      `${API_URL}/docs/api?workspace=stops#consumer-codes-v2/GET/api/consumer/codes/v2/xref`,
    );
  });
});

const task = { kind: "aiTask", id: "t-1", name: "Leads workbook" } as const;
const groupRow = (states: Partial<JobGroup["states"]>, overrides: Partial<Job> = {}): JobGroupRow => {
  const all = { queued: 0, running: 0, awaiting_confirmation: 0, completed: 0, failed: 0, cancelled: 0, expired: 0 };
  const merged = { ...all, ...states };
  return {
    job: job("newest", { origin: task, kind: "dryRun", ...overrides }),
    group: {
      origin: task,
      jobs: Object.values(merged).reduce((a, b) => a + b, 0),
      states: merged,
      latestAt: "2026-10-07T08:00:02Z",
    },
  };
};

describe("Jobs grouped (0.13 JG)", () => {
  beforeEach(() => {
    localStorage.removeItem("refiroo.jobs.view");
    vi.mocked(api.jobGroups).mockResolvedValue({
      items: [groupRow({ running: 1, completed: 11 }), { job: job("solo", { kind: "export" }), group: null }],
      nextCursor: null,
    });
  });

  it("lists a group and a single job in one table, and opens the group", async () => {
    const onNavigate = vi.fn();
    renderJobs(undefined, onNavigate);
    const table = await screen.findByRole("group", { name: "Jobs" });
    const row = within(table).getByRole("row", { name: /Leads workbook/ });
    expect(row).toHaveTextContent("Assistant task");
    expect(row).toHaveTextContent("12 jobs");
    expect(row).toHaveTextContent("1 running");
    expect(row).toHaveTextContent("11 completed");
    expect(within(table).getByRole("row", { name: /solo/ })).toHaveTextContent("1 job");
    fireEvent.click(row);
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "jobs", group: { kind: "aiTask", id: "t-1" } });
    expect(within(row).getByRole("link", { name: /Leads workbook/ })).toHaveAttribute(
      "href",
      "/settings/jobs/groups/aiTask/t-1",
    );
  });

  it("says Cancel requested on a single job's row until it is cancelled", async () => {
    vi.mocked(api.jobGroups).mockResolvedValue({
      items: [{ job: job("solo", { state: "queued", cancelRequestedAt: "2026-10-07T08:00:03Z" }), group: null }],
      nextCursor: null,
    });
    renderJobs();
    expect(await screen.findByRole("row", { name: /solo/ })).toHaveTextContent("Cancel requested");
  });

  it("switches to every job and remembers the choice", async () => {
    vi.mocked(api.jobs).mockResolvedValue({ items: [job("j1")], nextCursor: null });
    renderJobs();
    await screen.findByRole("row", { name: /Leads workbook/ });
    fireEvent.click(screen.getByRole("button", { name: "All jobs" }));
    expect(await screen.findByRole("row", { name: /j1/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "All jobs" })).toHaveAttribute("aria-pressed", "true");
    expect(api.jobs).toHaveBeenCalledWith(undefined);
    cleanup();
    renderJobs();
    expect(await screen.findByRole("row", { name: /j1/ })).toBeInTheDocument();
  });
});

describe("A group of jobs opened (0.13 JG)", () => {
  const route = { kind: "settings", page: "jobs", group: { kind: "aiTask", id: "t-1" } } as const;
  beforeEach(() => {
    vi.mocked(api.jobGroups).mockResolvedValue({
      items: [groupRow({ running: 1, failed: 2, completed: 8 })],
      nextCursor: null,
    });
    vi.mocked(api.jobs).mockResolvedValue({ items: [job("j9", { origin: task })], nextCursor: null });
    vi.mocked(ai.task).mockResolvedValue({} as Awaited<ReturnType<typeof ai.task>>);
  });

  it("shows the trail, the summary with its state chips, and the group's jobs", async () => {
    const onNavigate = vi.fn();
    renderJobs({ ...route, state: "failed" }, onNavigate);
    const trail = await screen.findByRole("navigation", { name: "Where you are" });
    expect(trail).toHaveTextContent("JobsAssistant task: Leads workbook");
    expect(screen.getByRole("heading", { name: "Leads workbook" })).toBeInTheDocument();
    const chips = screen.getByRole("group", { name: "Show jobs in state" });
    expect(within(chips).getByRole("button", { name: /Failed/ })).toHaveAttribute("aria-pressed", "true");
    expect(within(chips).getByRole("button", { name: /All/ })).toHaveTextContent("11");
    expect(api.jobs).toHaveBeenLastCalledWith(undefined, { origin: "aiTask:t-1", state: "failed" });
    fireEvent.click(within(chips).getByRole("button", { name: /Running/ }));
    expect(onNavigate).toHaveBeenCalledWith({ ...route, state: "running" });
    fireEvent.click(within(chips).getByRole("button", { name: /All/ }));
    expect(onNavigate).toHaveBeenLastCalledWith(route);
    // A job opened from here keeps the group and the filter for its trail.
    expect(await screen.findByRole("link", { name: /j9/ })).toHaveAttribute(
      "href",
      "/settings/jobs/j9?group=aiTask%3At-1&state=failed",
    );
    fireEvent.click(screen.getByRole("button", { name: "‹ Jobs" }));
    expect(onNavigate).toHaveBeenLastCalledWith({ kind: "settings", page: "jobs" });
  });

  it("offers Open the task only when the person may open it, and never disabled", async () => {
    const onNavigate = vi.fn();
    renderJobs(route, onNavigate);
    fireEvent.click(await screen.findByRole("button", { name: "Open the task" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "ai-tasks", taskId: "t-1" });
  });

  it("leaves Open the task out when the task cannot be read", async () => {
    vi.mocked(ai.task).mockRejectedValue(new ApiError(403, "FORBIDDEN", "No"));
    renderJobs(route);
    await screen.findByRole("heading", { name: "Leads workbook" });
    await waitFor(() => expect(ai.task).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Open the task" })).not.toBeInTheDocument();
  });

  it("goes up one level on Escape: a group to the list, a job to its group", async () => {
    const onNavigate = vi.fn();
    renderJobs(route, onNavigate);
    await screen.findByRole("heading", { name: "Leads workbook" });
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "jobs" });
    cleanup();

    vi.mocked(api.job).mockResolvedValue(job("j9", { origin: task, kind: "dryRun" }));
    vi.mocked(api.model).mockResolvedValue(testModel);
    renderJobs({ ...route, jobId: "j9", state: "failed" }, onNavigate);
    const trail = await screen.findByRole("navigation", { name: "Where you are" });
    expect(trail).toHaveTextContent("JobsAssistant task: Leads workbookDry run");
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onNavigate).toHaveBeenLastCalledWith({ ...route, state: "failed" });
  });

  it("says when a group has no jobs the person can see", async () => {
    vi.mocked(api.jobGroups).mockResolvedValue({ items: [], nextCursor: null });
    renderJobs(route);
    expect(await screen.findByText(/This group has no jobs you can see/)).toBeInTheDocument();
  });
});
