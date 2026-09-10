import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { createDraftClient } from "@/api/draftClient";
import { ApiError } from "@/api/errors";
import type { WorkspaceDraft } from "@/types";
import { domainObject } from "@/test/fixtures";
const draft: WorkspaceDraft = {
  id: "draft",
  workspaceKey: "west",
  name: "Review",
  modelReleaseId: "model",
  source: "currentLive",
  derivedFromRevisionId: null,
  version: 4,
  createdAt: "",
  updatedAt: "",
};
afterEach(() => vi.restoreAllMocks());

describe("draft record context", () => {
  it("reads aggregate versions from the resource even when record reads omit them, and carries deletion confirmation", async () => {
    const changed = vi.fn();
    const controller = createDraftClient(draft, changed, vi.fn());
    vi.spyOn(api, "workspaceDraft").mockResolvedValue({ ...draft, version: 5 });
    const object = vi.spyOn(api, "object").mockResolvedValue(domainObject);
    const update = vi.spyOn(api, "updateObject").mockResolvedValue(domainObject);
    const remove = vi.spyOn(api, "deleteObject").mockResolvedValue();
    await controller.client.object("domain", "id", "west");
    await controller.client.updateObject("domain", "id", { expectedVersion: 2, name: "mine" });
    await controller.client.deleteObject("domain", "id", 3, { cascade: true, deletionPreviewToken: "signed" });
    expect(object).toHaveBeenCalledWith("domain", "id", "west", "draft");
    expect(update).toHaveBeenCalledWith("domain", "id", {
      expectedVersion: 2,
      name: "mine",
      workspaceDraftId: "draft",
      expectedWorkspaceDraftVersion: 4,
    });
    expect(remove).toHaveBeenCalledWith("domain", "id", 3, {
      cascade: true,
      deletionPreviewToken: "signed",
      workspaceDraftId: "draft",
      expectedWorkspaceDraftVersion: 5,
    });
    expect(changed).toHaveBeenCalledWith(expect.objectContaining({ version: 5 }));
  });
  it("refreshes after an aggregate conflict without replaying the user's mutation", async () => {
    const controller = createDraftClient(draft, vi.fn(), vi.fn());
    const conflict = new ApiError(409, "workspace_draft_version_conflict", "Draft changed");
    const update = vi.spyOn(api, "updateObject").mockRejectedValueOnce(conflict).mockResolvedValue(domainObject);
    vi.spyOn(api, "workspaceDraft").mockResolvedValue({ ...draft, version: 9 });
    await expect(controller.client.updateObject("domain", "id", { expectedVersion: 2, name: "mine" })).rejects.toBe(
      conflict,
    );
    expect(update).toHaveBeenCalledTimes(1);
    await controller.client.updateObject("domain", "id", { expectedVersion: 2, name: "mine" });
    expect(update).toHaveBeenLastCalledWith(
      "domain",
      "id",
      expect.objectContaining({ name: "mine", expectedVersion: 2, expectedWorkspaceDraftVersion: 9 }),
    );
  });
  it("reports a successful save truthfully if version refresh fails, blocking another write until explicit refresh", async () => {
    const warning = vi.fn();
    const controller = createDraftClient(draft, vi.fn(), warning);
    const update = vi.spyOn(api, "updateObject").mockResolvedValue(domainObject);
    vi.spyOn(api, "workspaceDraft")
      .mockRejectedValueOnce(new Error("Unavailable"))
      .mockResolvedValue({ ...draft, version: 5 });
    await expect(controller.client.updateObject("domain", "id", { expectedVersion: 2 })).resolves.toBe(domainObject);
    expect(warning).toHaveBeenCalledWith(expect.stringContaining("Saved, but"));
    await expect(controller.client.updateObject("domain", "id", { expectedVersion: 3 })).rejects.toThrow(
      "Refresh the draft version",
    );
    expect(update).toHaveBeenCalledTimes(1);
    await controller.refresh();
    await controller.client.updateObject("domain", "id", { expectedVersion: 3 });
    expect(update).toHaveBeenLastCalledWith(
      "domain",
      "id",
      expect.objectContaining({ expectedWorkspaceDraftVersion: 5 }),
    );
  });
});
