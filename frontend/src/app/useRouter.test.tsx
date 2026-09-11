import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { testModel } from "@/test/fixtures";
import { defaultRoute, routePath } from "@/routing/routes";
import { historyState } from "@/routing/navigationHistory";
import { useNavigationGuard } from "@/routing/navigationGuard";
import type { RouteState } from "@/types";
import { useRouter } from "@/app/useRouter";

vi.mock("@/api/client", () => ({ api: { model: vi.fn(), workspaceRuntimeState: vi.fn() } }));

const collection = {
  ...defaultRoute(testModel, "west"),
  search: "client",
  cursors: ["second", "third"],
  filters: [{ field: "code", operator: "eq", value: "A&B" }],
};
const detail: RouteState = {
  kind: "detail",
  applicationKey: "test-app",
  objectTypeKey: "domain",
  objectId: "one",
  workspaceKey: "west",
};

describe("record navigation", () => {
  beforeEach(() => {
    vi.mocked(api.model).mockResolvedValue(testModel);
    vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
      defaultWorkspaceKey: "default",
      version: 1,
      updatedAt: "",
    });
    window.history.replaceState({}, "", routePath(collection));
  });
  afterEach(() => vi.restoreAllMocks());

  it.each([undefined, "draft-1"])(
    "restores each entry's own collection across reload and history in %s context",
    async (workspaceDraftId) => {
      const origin = { ...collection, ...(workspaceDraftId ? { workspaceDraftId } : {}) };
      window.history.replaceState({}, "", routePath(origin));
      const first = renderHook(useRouter);
      await waitFor(() => expect(first.result.current.route?.kind).toBe("list"));
      act(() => {
        first.result.current.navigate({ ...detail, workspaceDraftId });
      });
      const related = { ...detail, objectId: "related", workspaceDraftId };
      act(() => {
        first.result.current.navigate(related);
      });
      expect(first.result.current.route).toMatchObject({ collectionOrigin: origin });
      const savedPath = window.location.href;
      first.unmount();
      const reloaded = renderHook(useRouter);
      await waitFor(() =>
        expect(reloaded.result.current.route).toMatchObject({ objectId: "related", collectionOrigin: origin }),
      );
      act(() => {
        reloaded.result.current.navigate({ ...origin, search: "another", cursors: undefined });
      });
      act(() => window.history.back());
      await waitFor(() => expect(window.location.href).toBe(savedPath));
      await waitFor(() =>
        expect(reloaded.result.current.route).toMatchObject({ objectId: "related", collectionOrigin: origin }),
      );
      act(() => window.history.back());
      await waitFor(() =>
        expect(reloaded.result.current.route).toMatchObject({ objectId: "one", collectionOrigin: origin }),
      );
      act(() => window.history.forward());
      await waitFor(() =>
        expect(reloaded.result.current.route).toMatchObject({ objectId: "related", collectionOrigin: origin }),
      );
    },
  );

  it("retains standalone hierarchy navigation through related records, reload and browser history", async () => {
    const first = renderHook(useRouter);
    await waitFor(() => expect(first.result.current.route?.kind).toBe("list"));
    act(() => first.result.current.navigate({ ...detail, collectionOrigin: null }));
    expect(first.result.current.route).toMatchObject({ collectionOrigin: null });
    act(() => first.result.current.navigate({ ...detail, objectId: "related" }));
    expect(first.result.current.route).toMatchObject({ collectionOrigin: null });
    first.unmount();
    const reloaded = renderHook(useRouter);
    await waitFor(() =>
      expect(reloaded.result.current.route).toMatchObject({ objectId: "related", collectionOrigin: null }),
    );
    act(() => window.history.back());
    await waitFor(() =>
      expect(reloaded.result.current.route).toMatchObject({ objectId: "one", collectionOrigin: null }),
    );
    act(() => window.history.forward());
    await waitFor(() =>
      expect(reloaded.result.current.route).toMatchObject({ objectId: "related", collectionOrigin: null }),
    );
  });

  it("drops origins on context change and gives a copied record URL no origin", async () => {
    const first = renderHook(useRouter);
    await waitFor(() => expect(first.result.current.route?.kind).toBe("list"));
    act(() => {
      first.result.current.navigate({ ...detail, workspaceDraftId: "draft-1" });
    });
    expect(first.result.current.route).not.toHaveProperty("collectionOrigin");
    act(() => {
      first.result.current.navigate({ ...detail, workspaceKey: "east" });
    });
    expect(first.result.current.route).not.toHaveProperty("collectionOrigin");
    first.unmount();
    window.history.replaceState({}, "", routePath(detail));
    const copied = renderHook(useRouter);
    await waitFor(() => expect(copied.result.current.route).toEqual(detail));
  });

  it.each([
    "/apps/test-app/views/missing?workspaceKey=west",
    "/apps/test-app/views/domains?workspaceKey=east",
    "/apps/test-app/views/domains?workspaceKey=west&workspaceDraftId=wrong",
    "/apps/test-app/views/domains?workspaceKey=west&workspaceRevisionId=wrong",
    "/apps/%ZZ/views/domains",
    "https://example.com/apps/test-app/views/domains",
  ])("ignores invalid saved origins: %s", async (collectionPath) => {
    const state = historyState(detail, 1);
    state.rdmNavigation.collectionPath = collectionPath;
    window.history.replaceState(state, "", routePath(detail));
    const hook = renderHook(useRouter);
    await waitFor(() => expect(hook.result.current.route).toEqual(detail));
  });

  it("cancels route changes, multi-entry Back and Forward without losing input or the history trail", async () => {
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.route?.kind).toBe("list"));
    act(() => {
      router.result.current.navigate(detail);
    });
    act(() => {
      router.result.current.navigate({ ...detail, objectId: "two" });
    });
    const dismiss = vi.fn();
    const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
    const guard = renderHook(() => useNavigationGuard(true, false, dismiss));
    const path = window.location.href;
    act(() => {
      expect(router.result.current.navigate({ ...collection, workspaceKey: "east" })).toBe(false);
    });
    expect(window.location.href).toBe(path);
    act(() => window.history.go(-2));
    await waitFor(() => expect(confirm).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(window.location.href).toBe(path));
    expect(router.result.current.route).toMatchObject({ objectId: "two" });
    expect(dismiss).not.toHaveBeenCalled();
    confirm.mockReturnValue(true);
    act(() => window.history.back());
    await waitFor(() => expect(router.result.current.route).toMatchObject({ objectId: "one" }));
    expect(dismiss).toHaveBeenCalledOnce();
    guard.unmount();
    renderHook(() => useNavigationGuard(true, false, dismiss));
    confirm.mockReturnValue(false);
    const middle = window.location.href;
    act(() => window.history.forward());
    await waitFor(() => expect(confirm).toHaveBeenCalledTimes(4));
    await waitFor(() => expect(window.location.href).toBe(middle));
    confirm.mockReturnValue(true);
    act(() => window.history.forward());
    await waitFor(() => expect(router.result.current.route).toMatchObject({ objectId: "two" }));
  });

  it("blocks in-flight navigation and native unload, then permits post-save navigation without a discard prompt", async () => {
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.route?.kind).toBe("list"));
    const alert = vi.spyOn(window, "alert").mockImplementation(() => undefined);
    const confirm = vi.spyOn(window, "confirm");
    const guard = renderHook(() => useNavigationGuard(true, true, vi.fn()));
    act(() => {
      expect(router.result.current.navigate(detail)).toBe(false);
    });
    expect(alert).toHaveBeenCalledWith(expect.stringContaining("still in progress"));
    const unload = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(unload);
    expect(unload.defaultPrevented).toBe(true);
    act(() => {
      guard.result.current();
      expect(router.result.current.navigate(detail)).toBe(true);
    });
    expect(confirm).not.toHaveBeenCalled();
    const savedUnload = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(savedUnload);
    expect(savedUnload.defaultPrevented).toBe(false);
  });
});
