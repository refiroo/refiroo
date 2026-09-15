import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import * as navigationGuard from "@/routing/navigationGuard";
import { api } from "@/api/client";
import { WorkspaceDataProvider, useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import { testModel, domainObject } from "@/test/fixtures";
import type { WorkspaceDraft } from "@/types";

const draft: WorkspaceDraft = {
  id: "draft",
  workspaceKey: "west",
  name: "Review",
  modelReleaseId: "old",
  modelReleaseKey: "test",
  modelReleaseVersion: "old",
  source: "currentLive",
  derivedFromRevisionId: null,
  version: 1,
  createdAt: "",
  updatedAt: "",
};
afterEach(() => vi.restoreAllMocks());
function Probe() {
  const data = useWorkspaceData();
  return (
    <>
      <p>
        {data.draft?.modelReleaseId}:{data.model?.release.version}
      </p>
      <p>{data.warning}</p>
      <button onClick={() => data.refresh!().catch(() => {})}>Refresh</button>
      <button
        onClick={() => data.api.updateObject("domain", "id", { name: "mine", expectedVersion: 1 }).catch(() => {})}
      >
        Save
      </button>
    </>
  );
}

it.each(["unavailable model", "dirty input"])("blocks writes and retries a pin refresh after %s", async (failure) => {
  vi.spyOn(api, "workspaceDraft")
    .mockResolvedValueOnce(draft)
    .mockResolvedValue({ ...draft, modelReleaseId: "new", version: 2 });
  vi.spyOn(api, "modelRuntimeState").mockResolvedValue({ activeReleaseId: "old" } as Awaited<
    ReturnType<typeof api.modelRuntimeState>
  >);
  const loadModel = vi.spyOn(api, "model").mockResolvedValueOnce(testModel);
  if (failure === "unavailable model") loadModel.mockRejectedValueOnce(new Error("Model unavailable"));
  loadModel.mockResolvedValue({ ...testModel, release: { ...testModel.release, version: "new" } });
  const save = vi.spyOn(api, "updateObject").mockResolvedValue(domainObject);
  render(
    <WorkspaceDataProvider draftId="draft" workspaceKey="west" model={testModel}>
      <Probe />
    </WorkspaceDataProvider>,
  );
  await screen.findByText(`old:${testModel.release.version}`);
  const guard = vi.spyOn(navigationGuard, "allowNavigation").mockReturnValue(failure !== "dirty input");
  fireEvent.click(screen.getByText("Refresh"));
  await screen.findByText(
    failure === "dirty input" ? /Your input is preserved; saving is blocked/ : "Model unavailable",
  );
  expect(screen.getByText(`old:${testModel.release.version}`)).toBeInTheDocument();
  fireEvent.click(screen.getByText("Save"));
  await waitFor(() => expect(save).not.toHaveBeenCalled());
  guard.mockReturnValue(true);
  fireEvent.click(screen.getByText("Refresh"));
  await screen.findByText("new:new");
  fireEvent.click(screen.getByText("Save"));
  await waitFor(() =>
    expect(save).toHaveBeenCalledWith("domain", "id", expect.objectContaining({ expectedWorkspaceDraftVersion: 2 })),
  );
  expect(loadModel).toHaveBeenCalledTimes(failure === "dirty input" ? 2 : 3);
});
