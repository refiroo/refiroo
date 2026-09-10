import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";

afterEach(() => vi.unstubAllGlobals());

describe("API client", () => {
  it("preserves structured errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ error: { code: "version_conflict", message: "Stale version", details: { current: 3 } } }),
            { status: 409 },
          ),
        ),
    );
    await expect(api.deleteObject("thing", "id", 2)).rejects.toEqual(
      expect.objectContaining({
        status: 409,
        code: "version_conflict",
        message: "Stale version",
        details: { current: 3 },
      }),
    );
  });

  it("omits application filtering for cross-application lookup and encodes the query", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ items: [], nextCursor: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.objects("external value", { workspaceKey: "west", search: "A&B", pageSize: 12 });
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("/objects/external%20value?");
    expect(url).toContain("workspaceKey=west");
    expect(url).toContain("search=A%26B");
    expect(url).not.toContain("applicationKey");
  });

  it("encodes workspace context on record and relationship reads", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({}), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.object("external value", "object/id", "West & East");
    await api.relations("object/id", { workspaceKey: "West & East", cursor: "next token" });
    await api.relation("relation/id", "West & East");
    for (const [url] of fetchMock.mock.calls) {
      expect(new URL(String(url)).searchParams.get("workspaceKey")).toBe("West & East");
    }
    expect(new URL(String(fetchMock.mock.calls[0][0])).pathname).toBe("/api/v1/objects/external%20value/object%2Fid");
    expect(new URL(String(fetchMock.mock.calls[1][0])).searchParams.get("cursor")).toBe("next token");
  });

  it("encodes built-in sorting", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ items: [], nextCursor: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.objects("domain", { workspaceKey: "west", sort: "-updatedAt", pageSize: 50 });
    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.searchParams.get("sort")).toBe("-updatedAt");
  });

  it("encodes repeatable typed table filters", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ items: [], nextCursor: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.objects("domain", {
      filters: [
        { field: "code", operator: "eq", value: "A" },
        { field: "code", operator: "eq", value: "B" },
        { field: "active", operator: "eq", value: "true" },
      ],
    });
    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.searchParams.getAll("filter.code.eq")).toEqual(["A", "B"]);
    expect(url.searchParams.get("filter.active.eq")).toBe("true");
  });

  it("searches the bounded workspace catalogue", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ items: [], nextCursor: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.workspaces({ search: "Central & East", status: "all", pageSize: 25 });
    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.pathname).toBe("/api/v1/workspaces");
    expect(url.searchParams.get("search")).toBe("Central & East");
    expect(url.searchParams.get("status")).toBe("all");
    expect(url.searchParams.get("pageSize")).toBe("25");
  });

  it("requests a bounded object history page", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ items: [], nextCursor: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.objectHistory("external value", "object/id", { cursor: "next token", pageSize: 10 });
    expect(fetchMock.mock.calls[0][0]).toContain("/objects/external%20value/object%2Fid/history?");
    expect(fetchMock.mock.calls[0][0]).toContain("cursor=next+token");
  });

  it("sends versions and handles empty delete responses", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(api.deleteAttribute("kind", "object", "enabled", 7)).resolves.toBeUndefined();
    expect(fetchMock.mock.calls[0][0]).toContain("expectedVersion=7");
    expect(fetchMock.mock.calls[0][1]).toEqual(expect.objectContaining({ method: "DELETE" }));
  });

  it("adds cascade only after explicit confirmation", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.deleteObject("kind", "object", 7);
    await api.deleteObject("kind", "object", 7, {
      cascade: true,
      deletionPreviewToken: "signed-preview",
      workspaceDraftId: "draft/id",
      expectedWorkspaceDraftVersion: 11,
    });
    expect(fetchMock.mock.calls[0][0]).not.toContain("cascade=true");
    expect(fetchMock.mock.calls[1][0]).toContain("cascade=true");
    expect(fetchMock.mock.calls[1][0]).toContain("deletionPreviewToken=signed-preview");
    expect(fetchMock.mock.calls[1][0]).toContain("workspaceDraftId=draft%2Fid");
    expect(fetchMock.mock.calls[1][0]).toContain("expectedWorkspaceDraftVersion=11");
  });

  it("creates direction-ready relationship payloads without changing them", async () => {
    const payload = { relationTypeKey: "links", fromObjectId: "from", toObjectId: "to", attributes: { score: 0 } };
    const fetchMock = vi
      .fn()
      .mockResolvedValue(new Response(JSON.stringify({ id: "r1", ...payload, version: 1 }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.createRelation(payload);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(payload);
  });

  it("uses model lifecycle concurrency tokens", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            valid: true,
            diagnostics: [],
            compatibility: { classification: "compatible", activeReleaseId: "active", diagnostics: [] },
            changes: [],
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            activeReleaseId: "active",
            activeModelHash: "hash",
            version: 4,
            updatedAt: "2026-09-05T00:00:00Z",
          }),
          { status: 200 },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    await api.compileModelDraft("draft/id", 7);
    await api.activateModelRelease("release/id", {
      activeReleaseId: "active",
      activeModelHash: "hash",
      version: 3,
      updatedAt: "2026-09-05T00:00:00Z",
    });
    expect(fetchMock.mock.calls[0][0]).toContain("/model-drafts/draft%2Fid/compile");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ expectedVersion: 7 });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      expectedRuntimeVersion: 3,
      expectedActiveReleaseId: "active",
    });
  });
});

it("encodes canonical draft reads, mutations and explicit current-live lifecycle requests", async () => {
  const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({}), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  const context = { workspaceDraftId: "draft/id", expectedWorkspaceDraftVersion: 7 };
  await api.object("type", "id", "west", context.workspaceDraftId);
  await api.objects("type", { workspaceKey: "west", workspaceDraftId: context.workspaceDraftId });
  await api.relations("id", { workspaceKey: "west", workspaceDraftId: context.workspaceDraftId });
  await api.relation("id", "west", context.workspaceDraftId);
  await api.updateAttribute("type", "id", "flag", false, 3, context);
  await api.deleteAttribute("type", "id", "flag", 3, context);
  await api.deleteRelation("id", 2, context);
  await api.createWorkspaceDraft("west", "Coordinated changes");
  await api.activateWorkspaceDraft("draft/id", 7, null);
  for (const [url] of fetchMock.mock.calls.slice(0, 4))
    expect(new URL(url).searchParams.get("workspaceDraftId")).toBe("draft/id");
  expect(JSON.parse(fetchMock.mock.calls[4][1].body)).toEqual({ value: false, expectedVersion: 3, ...context });
  for (const [url] of fetchMock.mock.calls.slice(5, 7))
    expect(new URL(url).searchParams.get("expectedWorkspaceDraftVersion")).toBe("7");
  expect(JSON.parse(fetchMock.mock.calls[7][1].body)).toEqual({ name: "Coordinated changes", source: "currentLive" });
  expect(JSON.parse(fetchMock.mock.calls[8][1].body)).toEqual({
    expectedDraftVersion: 7,
    expectedActiveRevisionId: null,
  });
});

it("encodes immutable history reads, historical derivation and publication retirement", async () => {
  const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({}), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  await api.workspaceRevisions("west", "older token");
  await api.workspaceRevision("revision/id");
  await api.object("type", "object", "west", undefined, "revision/id");
  await api.objects("type", { workspaceKey: "west", workspaceRevisionId: "revision/id" });
  await api.relations("object", { workspaceKey: "west", workspaceRevisionId: "revision/id" });
  await api.createHistoricalWorkspaceDraft("west", "Review old values", "revision/id");
  await api.retireWorkspacePublication("west", "revision/id");

  expect(new URL(fetchMock.mock.calls[0][0]).searchParams.get("cursor")).toBe("older token");
  expect(fetchMock.mock.calls[1][0]).toContain("/workspace-revisions/revision%2Fid");
  for (const [url] of fetchMock.mock.calls.slice(2, 5))
    expect(new URL(url).searchParams.get("workspaceRevisionId")).toBe("revision/id");
  expect(JSON.parse(fetchMock.mock.calls[5][1].body)).toEqual({
    name: "Review old values",
    source: "revision",
    derivedFromRevisionId: "revision/id",
  });
  expect(JSON.parse(fetchMock.mock.calls[6][1].body)).toEqual({ expectedActiveRevisionId: "revision/id" });
});
