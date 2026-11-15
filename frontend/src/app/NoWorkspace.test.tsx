import { describe, expect, it, vi } from "vitest";
import { noWorkspaceText } from "./NoWorkspace";
import { openingWorkspace } from "./useRouter";
import { api } from "@/api/client";
import { resetPermissionsForTests } from "@/state/permissions";
import { permissionsFixture } from "@/test/permissions";

vi.mock("@/api/client", () => ({ api: { myPermissions: vi.fn(), workspaces: vi.fn() } }));

const page = (keys: string[]) => ({ items: keys.map((key) => ({ key })), nextCursor: null }) as never;

describe("the workspace the application opens in (0.12 Z5, D326)", () => {
  it("opens the default workspace when the person may browse it", async () => {
    vi.mocked(api.myPermissions).mockResolvedValue(permissionsFixture("default", ["browse"]));
    expect(await openingWorkspace("default")).toBe("default");
    expect(api.workspaces).not.toHaveBeenCalled();
  });

  it("opens the first workspace the person may browse otherwise", async () => {
    vi.mocked(api.myPermissions).mockResolvedValue(permissionsFixture("default", ["security-admin"]));
    vi.mocked(api.workspaces).mockResolvedValue(page(["east"]));
    expect(await openingWorkspace("default")).toBe("east");
    expect(api.workspaces).toHaveBeenCalledWith({ holding: "browse", status: "all", pageSize: 1 });
  });

  it("opens none when there is none, and keeps the default when the permissions cannot be read", async () => {
    vi.mocked(api.myPermissions).mockResolvedValue(permissionsFixture("default", []));
    vi.mocked(api.workspaces).mockResolvedValue(page([]));
    expect(await openingWorkspace("default")).toBeUndefined();
    // The permissions are kept for the page load: a new read needs them forgotten.
    resetPermissionsForTests();
    vi.mocked(api.myPermissions).mockRejectedValue(new Error("offline"));
    expect(await openingWorkspace("default")).toBe("default");
  });
});

describe("what the no-workspace page says", () => {
  it("names the roles, and leads a Security administrator to People", () => {
    expect(noWorkspaceText([], false)).toBe(
      "You hold no roles yet. Ask a security administrator for a role in a workspace.",
    );
    expect(noWorkspaceText(["Security administrator"], true)).toBe(
      "You hold Security administrator, which reads no workspace's data. A role in a workspace is granted on People.",
    );
    expect(noWorkspaceText(["Integration administrator", "Operator"], false)).toMatch(
      /^You hold Integration administrator and Operator, which reads no workspace's data\. Ask/,
    );
  });
});
