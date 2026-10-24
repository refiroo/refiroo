import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { createChangeSetClient } from "@/api/changeSetClient";
import { ApiError } from "@/api/errors";
import type { ChangeSet } from "@/types";
import { domainObject } from "@/test/fixtures";
const changeSet: ChangeSet = {
  id: "changeSet",
  workspaceKey: "west",
  name: "Review",
  modelReleaseId: "model",
  modelReleaseKey: "rdm-starter",
  modelReleaseVersion: "0.7.0",
  source: "currentLive",
  derivedFromPublicationId: null,
  version: 4,
  createdAt: "",
  updatedAt: "",
  createdBy: null,
};
afterEach(() => vi.restoreAllMocks());

describe("change set record context", () => {
  it("reads aggregate versions from the resource even when record reads omit them, and carries deletion confirmation", async () => {
    const changed = vi.fn();
    const controller = createChangeSetClient(changeSet, changed, vi.fn());
    vi.spyOn(api, "changeSet").mockResolvedValue({ ...changeSet, version: 5 });
    const object = vi.spyOn(api, "object").mockResolvedValue(domainObject);
    const update = vi.spyOn(api, "updateObject").mockResolvedValue(domainObject);
    const remove = vi.spyOn(api, "deleteObject").mockResolvedValue();
    await controller.client.object("domain", "id", "west");
    await controller.client.updateObject("domain", "id", { expectedVersion: 2, name: "mine" });
    await controller.client.deleteObject("domain", "id", 3, { cascade: true, deletionPreviewToken: "signed" });
    expect(object).toHaveBeenCalledWith("domain", "id", "west", "changeSet");
    expect(update).toHaveBeenCalledWith("domain", "id", {
      expectedVersion: 2,
      name: "mine",
      changeSetId: "changeSet",
      expectedChangeSetVersion: 4,
    });
    expect(remove).toHaveBeenCalledWith("domain", "id", 3, {
      cascade: true,
      deletionPreviewToken: "signed",
      changeSetId: "changeSet",
      expectedChangeSetVersion: 5,
    });
    expect(changed).toHaveBeenCalledWith(expect.objectContaining({ version: 5 }));
  });
  it("reads a relation matrix in the change set and stages a claimed unlink in it", async () => {
    const controller = createChangeSetClient(changeSet, vi.fn(), vi.fn());
    vi.spyOn(api, "changeSet").mockResolvedValue({ ...changeSet, version: 5 });
    const matrix = vi.spyOn(api, "relationMatrix").mockResolvedValue({ items: [], nextCursor: null, columns: [] });
    const remove = vi.spyOn(api, "deleteRelation").mockResolvedValue();
    await controller.client.relationMatrix({ workspaceKey: "west", applicationKey: "app", viewKey: "matrix" });
    await controller.client.deleteRelation(
      "relation",
      2,
      {},
      { expectedRelationSetVersion: 3, relationSetDirection: "incoming" },
    );
    expect(matrix).toHaveBeenCalledWith(expect.objectContaining({ changeSetId: "changeSet" }));
    expect(remove).toHaveBeenCalledWith(
      "relation",
      2,
      { changeSetId: "changeSet", expectedChangeSetVersion: 4 },
      { expectedRelationSetVersion: 3, relationSetDirection: "incoming" },
    );
  });
  it("refreshes after an aggregate conflict without replaying the user's mutation", async () => {
    const controller = createChangeSetClient(changeSet, vi.fn(), vi.fn());
    const conflict = new ApiError(409, "CHANGE_SET_VERSION_CONFLICT", "Change set changed");
    const update = vi.spyOn(api, "updateObject").mockRejectedValueOnce(conflict).mockResolvedValue(domainObject);
    vi.spyOn(api, "changeSet").mockResolvedValue({ ...changeSet, version: 9 });
    await expect(controller.client.updateObject("domain", "id", { expectedVersion: 2, name: "mine" })).rejects.toBe(
      conflict,
    );
    expect(update).toHaveBeenCalledTimes(1);
    await controller.client.updateObject("domain", "id", { expectedVersion: 2, name: "mine" });
    expect(update).toHaveBeenLastCalledWith(
      "domain",
      "id",
      expect.objectContaining({ name: "mine", expectedVersion: 2, expectedChangeSetVersion: 9 }),
    );
  });
  it("reports a successful save truthfully if version refresh fails, blocking another write until explicit refresh", async () => {
    const warning = vi.fn();
    const controller = createChangeSetClient(changeSet, vi.fn(), warning);
    const update = vi.spyOn(api, "updateObject").mockResolvedValue(domainObject);
    vi.spyOn(api, "changeSet")
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockResolvedValue({ ...changeSet, version: 5 });
    await expect(controller.client.updateObject("domain", "id", { expectedVersion: 2 })).resolves.toBe(domainObject);
    expect(warning).toHaveBeenCalledWith(expect.stringContaining("Saved, but"));
    await expect(controller.client.updateObject("domain", "id", { expectedVersion: 3 })).rejects.toThrow(
      "Refresh the change set version",
    );
    expect(update).toHaveBeenCalledTimes(1);
    await controller.refresh();
    await controller.client.updateObject("domain", "id", { expectedVersion: 3 });
    expect(update).toHaveBeenLastCalledWith("domain", "id", expect.objectContaining({ expectedChangeSetVersion: 5 }));
  });
});
