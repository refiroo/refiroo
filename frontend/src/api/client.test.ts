import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";

afterEach(() => vi.unstubAllGlobals());

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

describe("API client", () => {
  it("requests the exact model for a workspace context", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await api.model({ workspaceKey: "West & East", publicationId: "publication/id" });

    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.pathname).toBe("/api/v1/model");
    expect(url.searchParams.get("workspaceKey")).toBe("West & East");
    expect(url.searchParams.get("publicationId")).toBe("publication/id");
  });

  it("reads move targets live or in a change set, with search, a type and paging", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({ items: [], nextCursor: null }));
    vi.stubGlobal("fetch", fetchMock);

    await api.parentCandidates("system group", "id/1", {
      workspaceKey: "west",
      parentObjectTypeKey: "system",
      search: "lab",
      pageSize: 20,
      cursor: "next",
    });
    await api.parentCandidates("group", "id", { workspaceKey: "west", changeSetId: "cs/1", position: 40 });

    const live = new URL(String(fetchMock.mock.calls[0][0]));
    expect(live.pathname).toBe("/api/v1/objects/system%20group/id%2F1/parent-candidates");
    expect(Object.fromEntries(live.searchParams)).toEqual({
      workspaceKey: "west",
      parentObjectTypeKey: "system",
      search: "lab",
      pageSize: "20",
      cursor: "next",
    });
    // A change set names the context on its own, as the route takes one or the other.
    const staged = new URL(String(fetchMock.mock.calls[1][0]));
    expect(Object.fromEntries(staged.searchParams)).toEqual({ changeSetId: "cs/1", position: "40" });
  });

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
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], nextCursor: null }));
    vi.stubGlobal("fetch", fetchMock);
    await api.objects("external value", { workspaceKey: "west", search: "A&B", pageSize: 12 });
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("/objects/external%20value?");
    expect(url).toContain("workspaceKey=west");
    expect(url).toContain("search=A%26B");
    expect(url).not.toContain("applicationKey");
  });

  it("encodes workspace context on record and relationship reads", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({}));
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
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], nextCursor: null }));
    vi.stubGlobal("fetch", fetchMock);
    await api.objects("domain", { workspaceKey: "west", sort: "-updatedAt", pageSize: 50 });
    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.searchParams.get("sort")).toBe("-updatedAt");
  });

  it("asks for top-level records only when requested", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({ items: [], nextCursor: null }));
    vi.stubGlobal("fetch", fetchMock);
    await api.objects("domain", { workspaceKey: "west", topLevel: true });
    await api.objects("domain", { workspaceKey: "west" });
    expect(new URL(String(fetchMock.mock.calls[0][0])).searchParams.get("topLevel")).toBe("true");
    expect(new URL(String(fetchMock.mock.calls[1][0])).searchParams.has("topLevel")).toBe(false);
  });

  it("encodes repeatable typed table filters", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], nextCursor: null }));
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
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], nextCursor: null }));
    vi.stubGlobal("fetch", fetchMock);
    await api.workspaces({ search: "Central & East", status: "all", pageSize: 25 });
    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.pathname).toBe("/api/v1/workspaces");
    expect(url.searchParams.get("search")).toBe("Central & East");
    expect(url.searchParams.get("status")).toBe("all");
    expect(url.searchParams.get("pageSize")).toBe("25");
  });

  it("requests a bounded object history page", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], nextCursor: null }));
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
      changeSetId: "change-set/id",
      expectedChangeSetVersion: 11,
    });
    expect(fetchMock.mock.calls[0][0]).not.toContain("cascade=true");
    expect(fetchMock.mock.calls[1][0]).toContain("cascade=true");
    expect(fetchMock.mock.calls[1][0]).toContain("deletionPreviewToken=signed-preview");
    expect(fetchMock.mock.calls[1][0]).toContain("changeSetId=change-set%2Fid");
    expect(fetchMock.mock.calls[1][0]).toContain("expectedChangeSetVersion=11");
  });

  it("creates direction-ready relationship payloads without changing them", async () => {
    const payload = { relationTypeKey: "links", fromObjectId: "from", toObjectId: "to", attributes: { score: 0 } };
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ id: "r1", ...payload, version: 1 }, 201));
    vi.stubGlobal("fetch", fetchMock);
    await api.createRelation(payload);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(payload);
  });

  it("uses model lifecycle concurrency tokens", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        jsonResponse({
          valid: true,
          diagnostics: [],
          compatibility: { classification: "compatible", activeReleaseId: "active", diagnostics: [] },
          changes: [],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          activeReleaseId: "active",
          activeModelHash: "hash",
          version: 4,
          updatedAt: "2026-09-05T00:00:00Z",
        }),
      );
    vi.stubGlobal("fetch", fetchMock);
    await api.compileModelDraft("change-set/id", 7);
    await api.activateModelRelease("release/id", {
      activeReleaseId: "active",
      activeModelHash: "hash",
      version: 3,
      updatedAt: "2026-09-05T00:00:00Z",
    });
    expect(fetchMock.mock.calls[0][0]).toContain("/model-drafts/change-set%2Fid/compile");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ expectedVersion: 7 });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      expectedRuntimeVersion: 3,
      expectedActiveReleaseId: "active",
    });
  });
});

it("encodes canonical change-set reads, mutations and explicit current-live lifecycle requests", async () => {
  const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({}));
  vi.stubGlobal("fetch", fetchMock);
  const context = { changeSetId: "change-set/id", expectedChangeSetVersion: 7 };
  await api.object("type", "id", "west", context.changeSetId);
  await api.objects("type", { workspaceKey: "west", changeSetId: context.changeSetId });
  await api.relations("id", { workspaceKey: "west", changeSetId: context.changeSetId });
  await api.relation("id", "west", context.changeSetId);
  await api.updateAttribute("type", "id", "flag", false, 3, context);
  await api.deleteAttribute("type", "id", "flag", 3, context);
  await api.deleteRelation("id", 2, context);
  await api.createChangeSet("west", "Coordinated changes");
  await api.publishChangeSet("change-set/id", 7, null);
  for (const [url] of fetchMock.mock.calls.slice(0, 4))
    expect(new URL(url).searchParams.get("changeSetId")).toBe("change-set/id");
  expect(JSON.parse(fetchMock.mock.calls[4][1].body)).toEqual({ value: false, expectedVersion: 3, ...context });
  for (const [url] of fetchMock.mock.calls.slice(5, 7))
    expect(new URL(url).searchParams.get("expectedChangeSetVersion")).toBe("7");
  expect(JSON.parse(fetchMock.mock.calls[7][1].body)).toEqual({ name: "Coordinated changes", source: "currentLive" });
  expect(JSON.parse(fetchMock.mock.calls[8][1].body)).toEqual({
    expectedChangeSetVersion: 7,
    expectedActivePublicationId: null,
  });
});

it("encodes relation matrix reads and a claimed unlink as the A2/A3 contract names them", async () => {
  const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({}));
  vi.stubGlobal("fetch", fetchMock);
  const view = { workspaceKey: "west/1", applicationKey: "app", viewKey: "matrix" };
  await api.relationMatrix({ ...view, columnIds: ["c1", "c2"], state: "historyOnly", search: "a&b", position: 40 });
  await api.relationMatrix({ ...view, columnCursor: "next", publicationId: "pub" });
  await api.relationMatrixContainers({ ...view, columnId: "c1", changeSetId: "cs" });
  await api.relationMatrixLinkCandidates({ ...view, columnId: "c1", rowId: "r1", search: "x" });
  await api.deleteRelation("rel", 2, {}, { expectedRelationSetVersion: 5, relationSetDirection: "outgoing" });
  const urls = fetchMock.mock.calls.map(([url]) => new URL(url));
  expect(urls[0].pathname).toBe("/api/v1/workspaces/west%2F1/relation-matrix");
  expect(urls[0].searchParams.getAll("columnIds")).toEqual(["c1", "c2"]);
  expect(Object.fromEntries(urls[0].searchParams)).toMatchObject({
    applicationKey: "app",
    viewKey: "matrix",
    state: "historyOnly",
    search: "a&b",
    position: "40",
  });
  expect(Object.fromEntries(urls[1].searchParams)).toMatchObject({ columnCursor: "next", publicationId: "pub" });
  expect(urls[2].pathname).toBe("/api/v1/workspaces/west%2F1/relation-matrix/containers");
  expect(Object.fromEntries(urls[2].searchParams)).toMatchObject({ columnId: "c1", changeSetId: "cs" });
  expect(urls[3].pathname).toBe("/api/v1/workspaces/west%2F1/relation-matrix/link-candidates");
  expect(Object.fromEntries(urls[3].searchParams)).toMatchObject({ columnId: "c1", rowId: "r1", search: "x" });
  expect(Object.fromEntries(urls[4].searchParams)).toEqual({
    expectedVersion: "2",
    expectedRelationSetVersion: "5",
    relationSetDirection: "outgoing",
  });
});

describe("HTML and non-JSON response hardening", () => {
  it("does not expose HTML error bodies as messages", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<!DOCTYPE html><html><body>Vite dev page</body></html>", {
          status: 502,
          headers: { "content-type": "text/html" },
        }),
      ),
    );
    const request = api.model();
    await expect(request).rejects.toEqual(
      expect.objectContaining({
        status: 502,
        code: "http_error",
        message: expect.not.stringContaining("<!DOCTYPE"),
      }),
    );
  });

  it("rejects unexpected HTML 200 responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<html><body>OK</body></html>", {
          status: 200,
          headers: { "content-type": "text/html" },
        }),
      ),
    );
    await expect(api.model()).rejects.toEqual(
      expect.objectContaining({
        status: 200,
        code: "unexpected_response",
      }),
    );
  });

  it("does not expose plain-text non-JSON error bodies", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response("Service unavailable", { status: 503, headers: { "content-type": "text/plain" } }),
        ),
    );
    const request = api.model();
    await expect(request).rejects.toEqual(
      expect.objectContaining({
        status: 503,
        message: expect.stringMatching(/\/api\/v1\/model.*503.*Retry/),
      }),
    );
    await expect(request).rejects.toEqual(
      expect.objectContaining({ message: expect.not.stringContaining("Service unavailable") }),
    );
  });

  it("does not expose an HTML fragment that omits document tags", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<body>upstream failure</body>", {
          status: 500,
          headers: { "content-type": "text/plain" },
        }),
      ),
    );
    await expect(api.model()).rejects.toEqual(
      expect.objectContaining({
        status: 500,
        message: expect.not.stringContaining("<body>"),
      }),
    );
  });
});

it("encodes publication reads, derivation from a publication and withdrawal", async () => {
  const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({}));
  vi.stubGlobal("fetch", fetchMock);
  await api.publications("west", "older token");
  await api.publication("publication/id");
  await api.object("type", "object", "west", undefined, "publication/id");
  await api.objects("type", { workspaceKey: "west", publicationId: "publication/id" });
  await api.relations("object", { workspaceKey: "west", publicationId: "publication/id" });
  await api.createChangeSetFromPublication("west", "Review old values", "publication/id");
  await api.withdrawPublication("publication/id");

  expect(new URL(fetchMock.mock.calls[0][0]).searchParams.get("cursor")).toBe("older token");
  expect(fetchMock.mock.calls[1][0]).toContain("/publications/publication%2Fid");
  for (const [url] of fetchMock.mock.calls.slice(2, 5))
    expect(new URL(url).searchParams.get("publicationId")).toBe("publication/id");
  expect(JSON.parse(fetchMock.mock.calls[5][1].body)).toEqual({
    name: "Review old values",
    source: "publication",
    derivedFromPublicationId: "publication/id",
  });
  expect(fetchMock.mock.calls[5][0]).toContain("/workspaces/west/change-sets");
  expect(fetchMock.mock.calls[6][0]).toContain("/publications/publication%2Fid/withdrawal");
  expect(fetchMock.mock.calls[6][1]).toMatchObject({ method: "POST" });
  expect(fetchMock.mock.calls[6][1].body).toBeUndefined();
});

it("encodes contextual mapping coverage filters", async () => {
  const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ items: [], nextCursor: null }));
  vi.stubGlobal("fetch", fetchMock);
  await api.mappingCoverage({
    workspaceKey: "west",
    applicationKey: "app",
    viewKey: "coverage",
    relationTypeKey: "maps-to",
    fromObjectTypeKey: "source",
    toObjectTypeKey: "target",
    direction: "outgoing",
    publicationId: "publication/id",
    parentObjectId: "parent/id",
    state: "unmapped",
  });
  const url = new URL(fetchMock.mock.calls[0][0]);
  expect(url.searchParams.get("parentObjectId")).toBe("parent/id");
  expect(url.searchParams.get("state")).toBe("unmapped");
  expect(url.searchParams.get("publicationId")).toBe("publication/id");
});
