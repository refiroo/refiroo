import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("API client", () => {
  it("preserves structured errors", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: "version_conflict", message: "Stale version", details: { current: 3 } } }), { status: 409 })));
    await expect(api.deleteObject("thing", "id", 2)).rejects.toEqual(expect.objectContaining({ status: 409, code: "version_conflict", message: "Stale version", details: { current: 3 } }));
  });

  it("omits application filtering for cross-application lookup and encodes the query", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], nextCursor: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.objects("external value", { workspaceKey: "west", search: "A&B", pageSize: 12 });
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("/objects/external%20value?");
    expect(url).toContain("workspaceKey=west");
    expect(url).toContain("search=A%26B");
    expect(url).not.toContain("applicationKey");
  });

  it("encodes repeatable state filters and built-in sorting", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], nextCursor: null }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.objects("domain", { workspaceKey: "west", state: ["active", "draft"], sort: "-updatedAt", pageSize: 50 });
    const url = new URL(String(fetchMock.mock.calls[0][0]));
    expect(url.searchParams.getAll("state")).toEqual(["active", "draft"]);
    expect(url.searchParams.get("sort")).toBe("-updatedAt");
  });

  it("requests a bounded object history page", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], nextCursor: null }), { status: 200 }));
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
    await api.deleteObject("kind", "object", 7, true);
    expect(fetchMock.mock.calls[0][0]).not.toContain("cascade=true");
    expect(fetchMock.mock.calls[1][0]).toContain("cascade=true");
  });

  it("creates direction-ready relationship payloads without changing them", async () => {
    const payload = { relationTypeKey: "links", fromObjectId: "from", toObjectId: "to", attributes: { score: 0 } };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ id: "r1", ...payload, version: 1 }), { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.createRelation(payload);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual(payload);
  });

  it("uses model lifecycle concurrency tokens", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ valid: true, diagnostics: [], compatibility: { classification: "compatible", activeReleaseId: "active", diagnostics: [] }, changes: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ activeReleaseId: "active", activeModelHash: "hash", version: 4, updatedAt: "2026-09-05T00:00:00Z" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await api.compileModelDraft("draft/id", 7);
    await api.activateModelRelease("release/id", { activeReleaseId: "active", activeModelHash: "hash", version: 3, updatedAt: "2026-09-05T00:00:00Z" });
    expect(fetchMock.mock.calls[0][0]).toContain("/model-drafts/draft%2Fid/compile");
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ expectedVersion: 7 });
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({ expectedRuntimeVersion: 3, expectedActiveReleaseId: "active" });
  });
});
