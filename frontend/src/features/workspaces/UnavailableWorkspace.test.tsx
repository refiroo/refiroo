import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/api/client";
import { resetPermissionsForTests } from "@/state/permissions";
import { UnavailableWorkspace } from "@/features/workspaces/UnavailableWorkspace";
import { testAvailability, testModel, testWorkspaceModel } from "@/test/fixtures";
import { heldAnywhereFixture } from "@/test/permissions";
import type { ModelReleaseRaising, Workspace, WorkspaceAvailability } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const time = "2026-10-27T08:00:00Z";
function unavailable(
  reason: "schemaLeftWindow" | "schemaAfterWindow" | "invalidRelease",
  raisable = true,
): WorkspaceAvailability {
  return {
    state: "unavailable",
    reason,
    releaseId: "release-old",
    schemaVersion: reason === "schemaAfterWindow" ? "0.12" : "0.8",
    supportedSchemaVersions: ["0.9", "0.10"],
    raisable,
  };
}
function workspace(availability: WorkspaceAvailability): Workspace {
  return {
    key: "harbour",
    label: "harbour",
    status: "active",
    version: 1,
    createdAt: time,
    updatedAt: time,
    model: { ...testWorkspaceModel, releaseName: "RDM Starter Model", releaseVersion: "0.9.0" },
    availability,
  };
}
const preview = (hash = "hash-1"): ModelReleaseRaising => ({
  applied: false,
  releaseId: "release-old",
  releaseKey: "starter",
  releaseVersion: "0.9.0",
  schemaFrom: "0.8",
  schemaTo: "0.10",
  consumerApisRewritten: 1,
  modelHash: hash,
  workspaces: [{ key: "harbour", label: "harbour" }],
});

function show(item: Workspace, form: "page" | "banner" = "page") {
  const onNavigate = vi.fn();
  const onRaised = vi.fn();
  render(<UnavailableWorkspace workspace={item} form={form} onNavigate={onNavigate} onRaised={onRaised} />);
  return { onNavigate, onRaised };
}

beforeEach(() => {
  vi.clearAllMocks();
  resetPermissionsForTests();
  vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture(["model-release"]));
  vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
    defaultWorkspaceKey: "default",
    version: 1,
    updatedAt: time,
  });
  vi.mocked(api.workspaces).mockResolvedValue({
    items: [
      { ...workspace(testAvailability), key: "another", label: "another" },
      { ...workspace(testAvailability), key: "default", label: "default" },
      { ...workspace(unavailable("invalidRelease")), key: "broken", label: "broken" },
      workspace(unavailable("schemaLeftWindow")),
    ],
    nextCursor: null,
  });
  vi.mocked(api.model).mockResolvedValue(testModel);
});

describe("UnavailableWorkspace", () => {
  it("says why a schema that left the window cannot be read, and what the engine reads", async () => {
    show(workspace(unavailable("schemaLeftWindow")));
    expect(await screen.findByRole("heading", { level: 1, name: "harbour cannot be opened" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Its model, RDM Starter Model 0.9.0, was written in schema language 0.8, which this version of refiroo no longer reads (it reads 0.9, 0.10). Nothing was lost and nothing was changed. The other workspaces work.",
      ),
    ).toBeInTheDocument();
  });

  it("offers no repair for a later engine's schema or an invalid release", async () => {
    const { unmount } = render(
      <UnavailableWorkspace workspace={workspace(unavailable("schemaAfterWindow"))} form="page" onNavigate={vi.fn()} />,
    );
    expect(
      await screen.findByText(/written by a newer version of refiroo \(schema language 0.12\)/),
    ).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Bring it up to date" })).not.toBeInTheDocument();
    unmount();
    show(workspace(unavailable("invalidRelease")));
    expect(await screen.findByText(/Its model release is not valid/)).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Bring it up to date" })).not.toBeInTheDocument();
  });

  it("offers the review to someone who may install models", async () => {
    show(workspace(unavailable("schemaLeftWindow")));
    const card = await screen.findByRole("region", { name: "Bring it up to date" });
    expect(
      await within(card).findByText(
        "Raise the model to schema 0.10. Its records, history and change sets stay as they are.",
      ),
    ).toBeInTheDocument();
    expect(within(card).getByRole("button", { name: "Review the change…" })).toBeInTheDocument();
  });

  it("shows nothing in the card while the permissions load, then only a sentence without the right", async () => {
    let answer: (value: ReturnType<typeof heldAnywhereFixture>) => void = () => undefined;
    vi.mocked(api.myActionGroups).mockReturnValue(new Promise((resolve) => (answer = resolve)));
    show(workspace(unavailable("schemaLeftWindow")));
    const card = await screen.findByRole("region", { name: "Bring it up to date" });
    expect(within(card).queryByRole("button")).not.toBeInTheDocument();
    expect(within(card).queryByText(/Ask someone/)).not.toBeInTheDocument();
    answer(heldAnywhereFixture(["browse"]));
    expect(
      await within(card).findByText(
        "Ask someone with the Model administrator role to bring this workspace up to date.",
      ),
    ).toBeInTheDocument();
    expect(within(card).queryByRole("button")).not.toBeInTheDocument();
  });

  it("holding the right only in a workspace is not holding it at the instance", async () => {
    vi.mocked(api.myActionGroups).mockResolvedValue({
      items: [{ key: "model-release", name: "x", instance: false, workspaces: [{ key: "default", label: "default" }] }],
    });
    show(workspace(unavailable("schemaLeftWindow")));
    expect(await screen.findByText(/Ask someone with the Model administrator role/)).toBeInTheDocument();
  });

  it("says a model that cannot be raised cannot be brought up to date automatically", async () => {
    show(workspace(unavailable("schemaLeftWindow", false)));
    expect(await screen.findByText("This model cannot be brought up to date automatically.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Review the change…" })).not.toBeInTheDocument();
  });

  it("lists the workspaces that open, the default first, and All workspaces", async () => {
    const { onNavigate } = show(workspace(unavailable("schemaLeftWindow")));
    const card = await screen.findByRole("region", { name: "Or continue elsewhere" });
    const rows = await within(card).findAllByRole("button", { name: /RDM|Starter|default|another/ });
    expect(rows.map((row) => row.querySelector("strong")?.textContent)).toEqual(["default", "another"]);
    fireEvent.click(within(card).getByRole("button", { name: "All workspaces" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "workspaces" });
    fireEvent.click(rows[1]);
    await waitFor(() =>
      expect(onNavigate).toHaveBeenCalledWith(expect.objectContaining({ kind: "list", workspaceKey: "another" })),
    );
  });

  it("previews, then raises with the preview's hash, and says the workspace is back", async () => {
    vi.mocked(api.previewModelReleaseRaising).mockResolvedValue(preview());
    vi.mocked(api.raiseModelRelease).mockResolvedValue({ ...preview(), applied: true });
    const { onNavigate, onRaised } = show(workspace(unavailable("schemaLeftWindow")));
    fireEvent.click(await screen.findByRole("button", { name: "Review the change…" }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("0.8 → 0.10")).toBeInTheDocument();
    expect(within(dialog).getByText("Consumer APIs rewritten")).toBeInTheDocument();
    expect(within(dialog).getByText("Workspaces that return")).toBeInTheDocument();
    expect(within(dialog).getByText("unchanged")).toBeInTheDocument();
    expect(within(dialog).getByText("This edits the stored release in place (before 1.0 only).")).toBeInTheDocument();
    expect(api.previewModelReleaseRaising).toHaveBeenCalledWith("release-old");
    fireEvent.click(within(dialog).getByRole("button", { name: "Raise and reopen" }));
    await waitFor(() => expect(api.raiseModelRelease).toHaveBeenCalledWith("release-old", "hash-1"));
    const notice = await screen.findByRole("status");
    expect(notice).toHaveTextContent("harbour is back.");
    expect(onRaised).toHaveBeenCalled();
    fireEvent.click(within(notice).getByRole("button", { name: "Choose another model…" }));
    expect(onNavigate).toHaveBeenCalledWith({ kind: "settings", page: "model" });
    fireEvent.click(within(notice).getByRole("button", { name: "Open harbour" }));
    await waitFor(() =>
      expect(onNavigate).toHaveBeenCalledWith(expect.objectContaining({ kind: "list", workspaceKey: "harbour" })),
    );
  });

  it("reads the release again when it changed after the preview", async () => {
    vi.mocked(api.previewModelReleaseRaising)
      .mockResolvedValueOnce(preview("hash-1"))
      .mockResolvedValueOnce(preview("hash-2"));
    vi.mocked(api.raiseModelRelease)
      .mockRejectedValueOnce(new ApiError(409, "MODEL_HASH_CHANGED", "changed"))
      .mockResolvedValueOnce({ ...preview("hash-2"), applied: true });
    show(workspace(unavailable("schemaLeftWindow")), "banner");
    fireEvent.click(await screen.findByRole("button", { name: "Review the change…" }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("0.8 → 0.10");
    fireEvent.click(within(dialog).getByRole("button", { name: "Raise and reopen" }));
    expect(
      await within(dialog).findByText("The release changed after you looked. Review it again."),
    ).toBeInTheDocument();
    await waitFor(() => expect(api.previewModelReleaseRaising).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(within(dialog).getByRole("button", { name: "Raise and reopen" })).toBeEnabled());
    fireEvent.click(within(dialog).getByRole("button", { name: "Raise and reopen" }));
    await waitFor(() => expect(api.raiseModelRelease).toHaveBeenLastCalledWith("release-old", "hash-2"));
    expect(await screen.findByText("harbour is back.")).toBeInTheDocument();
  });

  it("shows a refusal's reason and diagnostics in the dialog", async () => {
    vi.mocked(api.previewModelReleaseRaising).mockResolvedValue(preview());
    vi.mocked(api.raiseModelRelease).mockRejectedValue(
      new ApiError(422, "RELEASE_RAISE_REFUSED", "Release cannot be raised: the raised model is invalid", {
        diagnostics: ["View x names no object type"],
      }),
    );
    show(workspace(unavailable("schemaLeftWindow")), "banner");
    fireEvent.click(await screen.findByRole("button", { name: "Review the change…" }));
    const dialog = await screen.findByRole("dialog");
    await within(dialog).findByText("0.8 → 0.10");
    fireEvent.click(within(dialog).getByRole("button", { name: "Raise and reopen" }));
    expect(
      await within(dialog).findByText(/the raised model is invalid.*View x names no object type/),
    ).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Raise and reopen" })).toBeEnabled();
  });

  it("is a warning at the top of the workspace's page in its banner form, without the other workspaces", async () => {
    show(workspace(unavailable("schemaLeftWindow")), "banner");
    expect(await screen.findByText("harbour cannot be opened")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Or continue elsewhere" })).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Review the change…" })).toBeInTheDocument();
  });
});
