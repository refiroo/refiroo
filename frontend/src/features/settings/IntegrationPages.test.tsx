import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { API_URL, api } from "@/api/client";
import { ApiError } from "@/api/errors";
import { ApiReferencePage } from "@/features/settings/ApiReferencePage";
import { ConsumerApisPage } from "@/features/settings/ConsumerApisPage";
import { JobsPage } from "@/features/settings/JobsPage";
import { capabilitiesFixture } from "@/test/capabilities";
import type { ConsumerApiDocument, ConsumerApiIndexEntry, Job, SystemResponse } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const system = {
  engine: { version: "0.9.0-alpha.1", managementApi: "v1" },
  schemaLanguages: ["0.8"],
  activeModelRelease: {
    id: "r1",
    key: "test",
    name: "Test",
    version: "0.3.0",
    schemaVersion: "0.8",
    activatedAt: "2026-10-07T08:00:00Z",
  },
  database: { revision: "x" },
  settings: [],
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
  ...overrides,
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.system).mockResolvedValue(system);
  vi.mocked(api.capabilities).mockResolvedValue(capabilitiesFixture());
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

describe("Consumer APIs", () => {
  it("shows each API of every index page with its base URL and its routes, each linked to its documentation", async () => {
    const onNavigate = vi.fn();
    render(<ConsumerApisPage onNavigate={onNavigate} />);
    const codes = await screen.findByRole("region", { name: "Codes · v2" });
    expect(api.consumerApis).toHaveBeenLastCalledWith("c2");
    expect(api.consumerApiDocument).toHaveBeenCalledWith(`${API_URL}/api/consumer/codes/v2/openapi.json`);
    expect(codes).toHaveTextContent("Codes for consumers");
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
      `${API_URL}/docs#consumer-codes-v2/GET/api/consumer/codes/v2/xref`,
    );
    expect(within(routes).getByRole("link", { name: "Batch resolve" })).toHaveAttribute(
      "href",
      `${API_URL}/docs#consumer-codes-v2/POST/api/consumer/codes/v2/resolve`,
    );
    const plain = screen.getByRole("region", { name: "Plain · v1" });
    expect(within(plain).getByRole("link", { name: "Get by ID" })).toHaveAttribute(
      "href",
      `${API_URL}/docs#consumer-plain-v1/GET/api/consumer/plain/v1/objects/{id}`,
    );

    fireEvent.click(screen.getByRole("link", { name: "Open the release" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "model", releaseId: "r1" });
  });

  it("says when the active release declares none, and opens the model", async () => {
    vi.mocked(api.consumerApis).mockReset().mockResolvedValue({ items: [], nextCursor: null });
    const onNavigate = vi.fn();
    render(<ConsumerApisPage onNavigate={onNavigate} />);
    expect(await screen.findByText("The active release declares no consumer API.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open model" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "model" });
  });
});

describe("Jobs and feed", () => {
  it("lists jobs with their state and counts, loads more, and shows the limits", async () => {
    vi.mocked(api.jobs)
      .mockResolvedValueOnce({ items: [job("j2")], nextCursor: "next" })
      .mockResolvedValueOnce({
        items: [job("j1", { state: "failed", result: null, error: { code: "JOB_FAILED", message: "It failed" } })],
        nextCursor: null,
      });
    render(<JobsPage />);
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
    expect(limits).toHaveTextContent(/Change feed kept\s*30 days/);
  });

  it("cancels a running job after confirming, and shows the request", async () => {
    vi.mocked(api.jobs).mockResolvedValue({
      items: [job("j1", { state: "running", result: null, finishedAt: null })],
      nextCursor: null,
    });
    vi.mocked(api.cancelJob).mockResolvedValue(
      job("j1", { state: "running", result: null, finishedAt: null, cancelRequestedAt: "2026-10-07T08:00:03Z" }),
    );
    render(<JobsPage />);
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
    render(<JobsPage />);
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
    render(<JobsPage />);
    await screen.findByRole("region", { name: "Limits" });
    await screen.findByText(/Background batch/);
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });

  it("says there are no jobs yet", async () => {
    vi.mocked(api.jobs).mockResolvedValue({ items: [], nextCursor: null });
    render(<JobsPage />);
    expect(await screen.findByText(/No jobs yet/)).toBeInTheDocument();
  });
});

describe("API reference", () => {
  it("lists the management API and each consumer API with its version and document", async () => {
    render(<ApiReferencePage />);
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
      `${API_URL}/docs?api=management`,
    );
    expect(within(rows[1]).getByRole("link", { name: "Codes" })).toHaveAttribute(
      "href",
      `${API_URL}/docs?api=consumer-codes-v2`,
    );
    expect(rows[1]).toHaveTextContent("v2");
    expect(within(rows[2]).getByRole("link", { name: "openapi.json" })).toHaveAttribute(
      "href",
      `${API_URL}/api/consumer/plain/v1/openapi.json`,
    );
  });
});
