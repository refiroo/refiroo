import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import * as navigationGuard from "@/routing/navigationGuard";
import { act } from "@testing-library/react";
import { api } from "@/api/client";
import { touchSubject } from "@/state/useInbox";
import { WorkspaceDataProvider, useWorkspaceData } from "@/state/WorkspaceDataContext";
import { testModel, domainObject } from "@/test/fixtures";
import type { ChangeSet } from "@/types";

const changeSet: ChangeSet = {
  id: "changeSet",
  workspaceKey: "west",
  name: "Review",
  modelReleaseId: "old",
  modelReleaseKey: "test",
  modelReleaseVersion: "old",
  source: "currentLive",
  derivedFromPublicationId: null,
  version: 1,
  createdAt: "",
  updatedAt: "",
  createdBy: null,
};
afterEach(() => vi.restoreAllMocks());
function Probe() {
  const data = useWorkspaceData();
  return (
    <>
      <p>
        {data.changeSet?.modelReleaseId}:{data.model?.release.version}
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
  vi.spyOn(api, "changeSet")
    .mockResolvedValueOnce(changeSet)
    .mockResolvedValue({ ...changeSet, modelReleaseId: "new", version: 2 });
  vi.spyOn(api, "modelRelease").mockRejectedValue(new Error("not needed"));
  vi.spyOn(api, "workspaceModel").mockResolvedValue({ releaseId: "old" } as Awaited<
    ReturnType<typeof api.workspaceModel>
  >);
  const loadModel = vi.spyOn(api, "model").mockResolvedValueOnce(testModel);
  if (failure === "unavailable model") loadModel.mockRejectedValueOnce(new Error("Model unavailable"));
  loadModel.mockResolvedValue({ ...testModel, release: { ...testModel.release, version: "new" } });
  const save = vi.spyOn(api, "updateObject").mockResolvedValue(domainObject);
  render(
    <WorkspaceDataProvider changeSetId="changeSet" workspaceKey="west" model={testModel}>
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
    expect(save).toHaveBeenCalledWith("domain", "id", expect.objectContaining({ expectedChangeSetVersion: 2 })),
  );
  expect(loadModel).toHaveBeenCalledTimes(failure === "dirty input" ? 2 : 3);
});

it("names a differing active release by key and version, not by its id", async () => {
  vi.spyOn(api, "changeSet").mockResolvedValue(changeSet);
  vi.spyOn(api, "workspaceModel").mockResolvedValue({ releaseId: "active-id" } as Awaited<
    ReturnType<typeof api.workspaceModel>
  >);
  vi.spyOn(api, "model").mockResolvedValue(testModel);
  const release = vi
    .spyOn(api, "modelRelease")
    .mockResolvedValue({ id: "active-id", key: "rdm-starter", version: "0.7.0" } as Awaited<
      ReturnType<typeof api.modelRelease>
    >);
  function Label() {
    const data = useWorkspaceData();
    return <p>active: {data.activeModelReleaseLabel ?? "none"}</p>;
  }
  render(
    <WorkspaceDataProvider changeSetId="changeSet" workspaceKey="west" model={testModel}>
      <Label />
    </WorkspaceDataProvider>,
  );
  await screen.findByText("active: rdm-starter 0.7.0");
  expect(release).toHaveBeenCalledWith("active-id");
});

it("reads the change set again when a notice about it arrives or is opened at its address", async () => {
  const read = vi
    .spyOn(api, "changeSet")
    .mockResolvedValueOnce({ ...changeSet, name: "Waiting" })
    .mockResolvedValue({ ...changeSet, name: "Sent back", version: 2 });
  vi.spyOn(api, "workspaceModel").mockResolvedValue({ releaseId: "old" } as Awaited<
    ReturnType<typeof api.workspaceModel>
  >);
  vi.spyOn(api, "modelRelease").mockRejectedValue(new Error("not needed"));
  vi.spyOn(api, "model").mockResolvedValue(testModel);
  function Name() {
    return <p>{useWorkspaceData().changeSet?.name}</p>;
  }
  render(
    <WorkspaceDataProvider changeSetId="changeSet" workspaceKey="west" model={testModel}>
      <Name />
    </WorkspaceDataProvider>,
  );
  await screen.findByText("Waiting");
  const reads = read.mock.calls.length;
  act(() => touchSubject("another-change-set"));
  expect(read).toHaveBeenCalledTimes(reads);
  act(() => touchSubject("changeSet"));
  await screen.findByText("Sent back");
  expect(read.mock.calls.length).toBeGreaterThan(reads);
});
