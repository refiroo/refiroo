import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import type { ModelReleaseSummary } from "@/types";
import { ModelStructure, clearModelStructureCache } from "@/features/model-admin/ModelStructure";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const release = (id: string, version: string, installedAt: string): ModelReleaseSummary => ({
  id,
  key: "m",
  name: "M",
  version,
  schemaVersion: "0.10",
  modelHash: `h-${id}`,
  installedAt,
  assigned: false,
  status: "active" as const,
  statusVersion: 1,
  deletable: false,
  workspaces: [],
});
const older = release("r1", "1.0.0", "2026-01-01T00:00:00Z");
const newer = release("r2", "1.1.0", "2026-02-01T00:00:00Z");

const attributeTypes = Array.from({ length: 8 }, (_, i) => ({ key: `a${i}`, name: `Attr ${i}`, valueType: "text" }));
const model = {
  attributeTypes,
  objectTypes: [
    { key: "t1", name: "Alpha", attributes: attributeTypes.map((a) => ({ attributeTypeKey: a.key, order: 0 })) },
    { key: "t2", name: "Beta" },
  ],
  relationTypes: [{ key: "r", name: "links", reverseName: "linked by" }],
  objectTypeRelations: [{ relationTypeKey: "r", fromObjectTypeKey: "t1", toObjectTypeKey: "t2" }],
  applications: [
    { key: "a", name: "First app", objectTypeKeys: ["t1"], views: [{}] },
    { key: "b", name: "Second app", objectTypeKeys: ["t2"], views: [] },
  ],
};

beforeEach(() => {
  clearModelStructureCache();
  vi.mocked(api.modelRelease).mockReset();
});

describe("ModelStructure", () => {
  it("shows the latest release, the first application open and a type's attributes and relations", async () => {
    vi.mocked(api.modelRelease).mockResolvedValue({ ...newer, model });
    render(<ModelStructure releases={[older, newer]} />);
    expect(await screen.findByRole("button", { name: /First app/ })).toHaveAttribute("aria-expanded", "true");
    expect(api.modelRelease).toHaveBeenCalledWith("r2", true);
    expect(screen.getByRole("button", { name: /Second app/ })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("Attr 0")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: /Alpha/ }));
    expect(screen.getByText("Attr 5")).toBeInTheDocument();
    expect(screen.queryByText("Attr 6")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "+ 2 more" }));
    expect(screen.getByText("Attr 7")).toBeInTheDocument();
    const relations = screen.getByRole("region", { name: "Relations" });
    expect(within(relations).getByText("links")).toBeInTheDocument();
    expect(within(relations).getByText("Beta")).toBeInTheDocument();
    expect(within(relations).getByText("linked by")).toBeInTheDocument();
  });

  it("reads a chosen release once and serves it from the cache afterwards", async () => {
    vi.mocked(api.modelRelease).mockImplementation(async (id) => ({ ...(id === "r1" ? older : newer), model }));
    render(<ModelStructure releases={[older, newer]} />);
    await screen.findByRole("button", { name: /First app/ });
    const choose = async (name: RegExp) => {
      fireEvent.click(screen.getByRole("button", { name: "Release" }));
      fireEvent.click(await screen.findByRole("option", { name }));
      await screen.findByRole("button", { name: /First app/ });
    };
    await choose(/1\.0\.0/);
    await waitFor(() => expect(api.modelRelease).toHaveBeenCalledWith("r1", true));
    await choose(/1\.1\.0/);
    await choose(/1\.0\.0/);
    expect(api.modelRelease).toHaveBeenCalledTimes(2);
  });

  it("shows latest once, lists releases with active workspaces, and keeps the read-only sentence", async () => {
    vi.mocked(api.modelRelease).mockResolvedValue({ ...newer, model });
    render(<ModelStructure releases={[older, { ...newer, workspaces: ["a", "b"] }]} />);
    await screen.findByRole("button", { name: /First app/ });
    expect(screen.getAllByText("latest")).toHaveLength(1);
    expect(screen.getByText(/Read only\. Open a release to compare it or export it\./)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Release" }));
    const options = await screen.findAllByRole("option");
    expect(options[0]).toHaveTextContent("1.1.0");
    expect(options[0]).toHaveAttribute("aria-selected", "true");
    expect(within(options[0]).getByText("Active in 2")).toBeInTheDocument();
    expect(within(options[1]).queryByText(/Active in/)).toBeNull();
  });

  it("shows a single release as plain text without a picker", async () => {
    vi.mocked(api.modelRelease).mockResolvedValue({ ...newer, model });
    render(<ModelStructure releases={[newer]} />);
    await screen.findByRole("button", { name: /First app/ });
    expect(screen.getByText("1.1.0")).toBeInTheDocument();
    expect(screen.getByText("latest")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Release" })).toBeNull();
  });

  it("offers a retry when the read fails", async () => {
    vi.mocked(api.modelRelease)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValue({ ...newer, model });
    render(<ModelStructure releases={[newer]} />);
    fireEvent.click(await screen.findByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("button", { name: /First app/ })).toBeInTheDocument();
  });

  it("explains a release whose structure cannot be read", async () => {
    vi.mocked(api.modelRelease).mockResolvedValue({ ...newer, model: { weird: true } });
    render(<ModelStructure releases={[newer]} />);
    expect(await screen.findByText(/uses schema 0\.10; its structure can be read as raw JSON/)).toBeInTheDocument();
  });
});
