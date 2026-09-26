import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { createPublicationClient } from "@/api/publicationClient";
import { domainObject } from "@/test/fixtures";

afterEach(() => vi.restoreAllMocks());

describe("historical record context", () => {
  it("carries the immutable publication through shared object, field and relationship reads", async () => {
    const client = createPublicationClient("publication/id");
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

    await client.objects("domain", { workspaceKey: "west", changeSetId: "ignored" });
    await client.object("domain", domainObject.id, "west", "ignored");
    await client.attribute("domain", domainObject.id, "code", "ignored");
    await client.relations(domainObject.id, { workspaceKey: "west", changeSetId: "ignored" });
    await client.relation("relation", "west", "ignored");
    await client.mappingCoverage({
      workspaceKey: "west",
      applicationKey: "app",
      viewKey: "coverage",
      relationTypeKey: "maps",
      fromObjectTypeKey: "source",
      toObjectTypeKey: "target",
      direction: "outgoing",
      changeSetId: "ignored",
    });
    await client.mappingTargets({
      workspaceKey: "west",
      relationTypeKey: "maps",
      fromObjectTypeKey: "source",
      toObjectTypeKey: "target",
      direction: "outgoing",
      sourceObjectId: "source-1",
      mappingVersion: 0,
      changeSetId: "ignored",
    });

    expect(objects).toHaveBeenCalledWith("domain", {
      workspaceKey: "west",
      changeSetId: undefined,
      publicationId: "publication/id",
    });
    expect(object).toHaveBeenCalledWith("domain", domainObject.id, "west", undefined, "publication/id");
    expect(attribute).toHaveBeenCalledWith("domain", domainObject.id, "code", undefined, "publication/id");
    expect(relations).toHaveBeenCalledWith(domainObject.id, {
      workspaceKey: "west",
      changeSetId: undefined,
      publicationId: "publication/id",
    });
    expect(relation).toHaveBeenCalledWith("relation", "west", undefined, "publication/id");
    expect(coverage).toHaveBeenCalledWith(
      expect.objectContaining({ changeSetId: undefined, publicationId: "publication/id" }),
    );
    expect(targets).toHaveBeenCalledWith(
      expect.objectContaining({ changeSetId: undefined, publicationId: "publication/id" }),
    );
  });
});
