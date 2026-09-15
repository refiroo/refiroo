import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { createHistoryClient } from "@/api/historyClient";
import { domainObject } from "@/test/fixtures";

afterEach(() => vi.restoreAllMocks());

describe("historical record context", () => {
  it("carries the immutable revision through shared object, field and relationship reads", async () => {
    const client = createHistoryClient("revision/id");
    const objects = vi.spyOn(api, "objects").mockResolvedValue({ items: [], nextCursor: null });
    const object = vi.spyOn(api, "object").mockResolvedValue(domainObject);
    const attribute = vi.spyOn(api, "attribute").mockResolvedValue({
      id: "attribute",
      attributeTypeKey: "code",
      name: "Code",
      valueType: "text",
      value: "OLD",
      objectVersion: 1,
    });
    const relations = vi.spyOn(api, "relations").mockResolvedValue({ items: [], nextCursor: null });
    const relation = vi.spyOn(api, "relation").mockResolvedValue({
      id: "relation",
      relationTypeKey: "contains",
      fromObjectId: domainObject.id,
      toObjectId: domainObject.id,
      attributes: {},
      version: 1,
      createdAt: "",
      updatedAt: "",
    });
    const coverage = vi.spyOn(api, "mappingCoverage").mockResolvedValue({ items: [], nextCursor: null });
    const targets = vi
      .spyOn(api, "mappingTargets")
      .mockResolvedValue({ mappingVersion: 0, targetCount: 0, items: [], nextCursor: null });

    await client.objects("domain", { workspaceKey: "west", workspaceDraftId: "ignored" });
    await client.object("domain", domainObject.id, "west", "ignored");
    await client.attribute("domain", domainObject.id, "code", "ignored");
    await client.relations(domainObject.id, { workspaceKey: "west", workspaceDraftId: "ignored" });
    await client.relation("relation", "west", "ignored");
    await client.mappingCoverage({
      workspaceKey: "west",
      applicationKey: "app",
      viewKey: "coverage",
      relationTypeKey: "maps",
      fromObjectTypeKey: "source",
      toObjectTypeKey: "target",
      direction: "outgoing",
      workspaceDraftId: "ignored",
    });
    await client.mappingTargets({
      workspaceKey: "west",
      relationTypeKey: "maps",
      fromObjectTypeKey: "source",
      toObjectTypeKey: "target",
      direction: "outgoing",
      sourceObjectId: "source-1",
      mappingVersion: 0,
      workspaceDraftId: "ignored",
    });

    expect(objects).toHaveBeenCalledWith("domain", {
      workspaceKey: "west",
      workspaceDraftId: undefined,
      workspaceRevisionId: "revision/id",
    });
    expect(object).toHaveBeenCalledWith("domain", domainObject.id, "west", undefined, "revision/id");
    expect(attribute).toHaveBeenCalledWith("domain", domainObject.id, "code", undefined, "revision/id");
    expect(relations).toHaveBeenCalledWith(domainObject.id, {
      workspaceKey: "west",
      workspaceDraftId: undefined,
      workspaceRevisionId: "revision/id",
    });
    expect(relation).toHaveBeenCalledWith("relation", "west", undefined, "revision/id");
    expect(coverage).toHaveBeenCalledWith(
      expect.objectContaining({ workspaceDraftId: undefined, workspaceRevisionId: "revision/id" }),
    );
    expect(targets).toHaveBeenCalledWith(
      expect.objectContaining({ workspaceDraftId: undefined, workspaceRevisionId: "revision/id" }),
    );
  });
});
