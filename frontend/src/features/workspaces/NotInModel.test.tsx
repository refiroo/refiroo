import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { resetPermissionsForTests } from "@/features/security/permissions";
import { NotInModel } from "@/features/workspaces/NotInModel";
import { defaultRoute } from "@/routing/routes";
import { testModel, testWorkspaceModel } from "@/test/fixtures";
import { heldAnywhereFixture } from "@/test/permissions";
import type { Workspace } from "@/types";

vi.mock("@/api/client", async (load) => {
  const actual = await load<typeof import("@/api/client")>();
  return { ...actual, api: Object.fromEntries(Object.keys(actual.api).map((key) => [key, vi.fn()])) };
});

const time = "2026-10-27T08:00:00Z";
const stuck: Workspace = {
  key: "harbour",
  label: "harbour",
  status: "active",
  version: 1,
  createdAt: time,
  updatedAt: time,
  model: testWorkspaceModel,
  availability: {
    state: "unavailable",
    reason: "schemaLeftWindow",
    releaseId: "release-old",
    schemaVersion: "0.8",
    supportedSchemaVersions: ["0.10"],
    raisable: true,
  },
};

function show(unavailable?: string) {
  render(
    <NotInModel
      problem={{ kind: "workspace", workspaceKey: "harbour", ...(unavailable ? { unavailable } : {}) }}
      model={testModel}
      startRoute={defaultRoute(testModel, "default")}
      onNavigate={vi.fn()}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  resetPermissionsForTests();
  vi.mocked(api.myActionGroups).mockResolvedValue(heldAnywhereFixture(["browse"]));
  vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
    defaultWorkspaceKey: "default",
    version: 1,
    updatedAt: time,
  });
  vi.mocked(api.workspaces).mockResolvedValue({ items: [stuck], nextCursor: null });
});

describe("NotInModel for a workspace", () => {
  it("shows the shared screen for a workspace that cannot be served", async () => {
    vi.mocked(api.workspace).mockResolvedValue({ ...stuck, deletable: false });
    show("The model cannot be loaded.");
    expect(await screen.findByRole("heading", { level: 1, name: "harbour cannot be opened" })).toBeInTheDocument();
    expect(await screen.findByRole("region", { name: "Bring it up to date" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Or continue elsewhere" })).toBeInTheDocument();
  });

  it("keeps the plain sentence when the workspace's availability cannot be read", async () => {
    vi.mocked(api.workspace).mockRejectedValue(new Error("down"));
    show("The model cannot be loaded.");
    expect(
      await screen.findByText(/The model cannot be loaded\. The other workspaces are not affected/),
    ).toBeInTheDocument();
  });

  it("says a workspace that does not exist does not exist", () => {
    show();
    expect(screen.getByRole("heading", { level: 1, name: "No workspace harbour" })).toBeInTheDocument();
  });
});
