import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/api/client";
import { forgetWorkspaceModel } from "@/model/workspaceModels";
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
  anchor: "second",
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
    // Each workspace's model is held for the tab (0.11 D49); every case starts without one.
    forgetWorkspaceModel();
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
    async (changeSetId) => {
      const origin = { ...collection, ...(changeSetId ? { changeSetId } : {}) };
      window.history.replaceState({}, "", routePath(origin));
      const first = renderHook(useRouter);
      await waitFor(() => expect(first.result.current.route?.kind).toBe("list"));
      act(() => {
        first.result.current.navigate({ ...detail, changeSetId });
      });
      const related = { ...detail, objectId: "related", changeSetId };
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
        reloaded.result.current.navigate({ ...origin, search: "another", anchor: undefined });
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

  it("keeps a record opened beside its collection beside it across reload and history", async () => {
    const first = renderHook(useRouter);
    await waitFor(() => expect(first.result.current.route?.kind).toBe("list"));
    act(() => first.result.current.navigate({ ...detail, fullPage: false }));
    act(() => first.result.current.navigate({ ...detail, objectId: "full", fullPage: true }));
    first.unmount();
    const reloaded = renderHook(useRouter);
    await waitFor(() =>
      expect(reloaded.result.current.route).toMatchObject({
        objectId: "full",
        fullPage: true,
        collectionOrigin: collection,
      }),
    );
    act(() => window.history.back());
    await waitFor(() =>
      expect(reloaded.result.current.route).toMatchObject({
        objectId: "one",
        fullPage: false,
        collectionOrigin: collection,
      }),
    );
  });

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
      first.result.current.navigate({ ...detail, changeSetId: "draft-1" });
    });
    // The change set's model loads before its page shows.
    await waitFor(() => expect(first.result.current.route).toMatchObject({ changeSetId: "draft-1" }));
    expect(first.result.current.route).not.toHaveProperty("collectionOrigin");
    act(() => {
      first.result.current.navigate({ ...detail, workspaceKey: "east" });
    });
    // Another workspace's model loads before its page shows (0.11 M5).
    await waitFor(() => expect(first.result.current.route).toMatchObject({ workspaceKey: "east" }));
    expect(first.result.current.route).not.toHaveProperty("collectionOrigin");
    first.unmount();
    window.history.replaceState({}, "", routePath(detail));
    const copied = renderHook(useRouter);
    await waitFor(() => expect(copied.result.current.route).toEqual(detail));
  });

  it.each([
    "/apps/test-app/views/missing?workspaceKey=west",
    "/apps/test-app/views/domains?workspaceKey=east",
    "/apps/test-app/views/domains?workspaceKey=west&changeSetId=wrong",
    "/apps/test-app/views/domains?workspaceKey=west&publicationId=wrong",
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

describe("a workspace's own model (0.11 M5, D48, D49)", () => {
  /** A model of another line: its one application has another key. */
  const otherModel = {
    ...testModel,
    release: { key: "other", name: "Other model", version: "1.0.0" },
    applications: testModel.applications.map((application) => ({ ...application, key: "other-app" })),
  };

  beforeEach(() => {
    forgetWorkspaceModel();
    vi.mocked(api.model).mockImplementation(async ({ workspaceKey } = {}) =>
      workspaceKey === "east" ? otherModel : testModel,
    );
    vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
      defaultWorkspaceKey: "default",
      version: 1,
      updatedAt: "",
    });
    window.history.replaceState({}, "", routePath(collection));
  });
  afterEach(() => vi.restoreAllMocks());

  it("loads the model of the workspace the address names, and swaps it with the workspace", async () => {
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.model).toBe(testModel));
    expect(api.model).toHaveBeenCalledWith({ workspaceKey: "west" });
    act(() => {
      router.result.current.openWorkspace("east");
    });
    await waitFor(() => expect(router.result.current.model).toBe(otherModel));
    expect(router.result.current.route).toMatchObject({ applicationKey: "other-app", workspaceKey: "east" });
    expect(router.result.current.problem).toBeUndefined();
  });

  it("drops a model read for a workspace the person has left while it was read", async () => {
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.model).toBe(testModel));
    let release: (model: typeof testModel) => void = () => undefined;
    vi.mocked(api.model).mockImplementationOnce(() => new Promise((resolve) => (release = resolve)));
    let reading: Promise<void> = Promise.resolve();
    act(() => {
      reading = router.result.current.reloadModel("west");
    });
    act(() => {
      router.result.current.openWorkspace("east");
    });
    await waitFor(() => expect(router.result.current.model).toBe(otherModel));
    await act(async () => {
      release({ ...testModel });
      await reading;
    });
    expect(router.result.current.model).toBe(otherModel);
  });

  it("opens navigation again when a step back it undoes is never answered", async () => {
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.route?.kind).toBe("list"));
    vi.spyOn(window, "alert").mockImplementation(() => undefined);
    vi.spyOn(window, "confirm").mockReturnValue(false);
    act(() => {
      router.result.current.navigate(detail);
    });
    const guard = renderHook(() => useNavigationGuard(true, true, vi.fn()));
    const go = vi.spyOn(window.history, "go").mockImplementation(() => undefined);
    vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
    try {
      // Back is refused while the guard holds; the undoing step is never answered by the browser.
      act(() => window.history.back());
      await vi.waitFor(() => expect(go).toHaveBeenCalled());
      expect(router.result.current.navigate(detail)).toBe(false);
      act(() => {
        vi.advanceTimersByTime(1500);
      });
    } finally {
      vi.useRealTimers();
    }
    guard.unmount();
    act(() => {
      expect(router.result.current.navigate(detail)).toBe(true);
    });
  });

  it("opens the start of another workspace's model when a switch carried a page it lacks", async () => {
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.route?.kind).toBe("list"));
    act(() => {
      router.result.current.navigate({ ...collection, workspaceKey: "east" }, false, true);
    });
    await waitFor(() => expect(router.result.current.modelWorkspaceKey).toBe("east"));
    expect(router.result.current.problem).toBeUndefined();
    // The address names the start that is shown, not the carried page, so a reload opens the same.
    const start = routePath(router.result.current.route!);
    expect(`${window.location.pathname}${window.location.search}`).toBe(start);
    expect(window.location.pathname).not.toBe("/apps/test-app/views/domains");
    router.unmount();
    const reloaded = renderHook(useRouter);
    await waitFor(() => expect(reloaded.result.current.model).toBe(otherModel));
    expect(reloaded.result.current.problem).toBeUndefined();
    expect(routePath(reloaded.result.current.route!)).toBe(start);
  });

  it("says what another workspace's model lacks instead of opening its start silently", async () => {
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.route?.kind).toBe("list"));
    act(() => {
      router.result.current.navigate({ ...collection, viewKey: "only-here", workspaceKey: "east" });
    });
    await waitFor(() =>
      expect(router.result.current.problem).toEqual({
        kind: "application",
        applicationKey: "test-app",
        workspaceKey: "east",
      }),
    );
    // The page shown is the workspace's own start under its own model; the address stays as asked.
    expect(router.result.current.model).toBe(otherModel);
    expect(router.result.current.route).toMatchObject({ applicationKey: "other-app", workspaceKey: "east" });
    expect(window.location.pathname).toBe("/apps/test-app/views/only-here");
    expect(window.location.search).toContain("workspaceKey=east");
    act(() => {
      router.result.current.navigate(collection);
    });
    await waitFor(() => expect(router.result.current.problem).toBeUndefined());
    expect(router.result.current.model).toBe(testModel);
  });
});

describe("a change set's own model", () => {
  /** The change set's release adds an application the workspace's active release lacks. */
  const changeSetModel = {
    ...testModel,
    applications: [
      ...testModel.applications,
      {
        ...testModel.applications[0],
        key: "person-lists",
        views: [{ ...testModel.applications[0].views[0], key: "people" }],
      },
    ],
  };
  const inChangeSet: RouteState = {
    ...defaultRoute(changeSetModel, "stops"),
    applicationKey: "person-lists",
    viewKey: "people",
    changeSetId: "cs1",
  };

  beforeEach(() => {
    forgetWorkspaceModel();
    vi.mocked(api.model).mockImplementation(async ({ changeSetId } = {}) => (changeSetId ? changeSetModel : testModel));
    vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
      defaultWorkspaceKey: "default",
      version: 1,
      updatedAt: "",
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("parses an address inside a change set under the change set's model", async () => {
    window.history.replaceState({}, "", routePath(inChangeSet));
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.model).toBe(changeSetModel));
    expect(api.model).toHaveBeenCalledWith({ workspaceKey: "stops", changeSetId: "cs1" });
    expect(router.result.current.problem).toBeUndefined();
    expect(router.result.current.route).toMatchObject({ applicationKey: "person-lists", changeSetId: "cs1" });
  });

  it("enters a change set from the workspace page and leaves it for the workspace's model again", async () => {
    window.history.replaceState({}, "", routePath(defaultRoute(testModel, "stops")));
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.model).toBe(testModel));
    act(() => {
      router.result.current.navigate(inChangeSet);
    });
    await waitFor(() => expect(router.result.current.model).toBe(changeSetModel));
    expect(router.result.current.problem).toBeUndefined();
    expect(router.result.current.route).toMatchObject({ applicationKey: "person-lists", changeSetId: "cs1" });
    // Inside the change set, another page of the new application stays under its model.
    act(() => {
      router.result.current.navigate({ ...inChangeSet, search: "x" });
    });
    expect(router.result.current.model).toBe(changeSetModel);
    expect(router.result.current.problem).toBeUndefined();
    // Out of the change set, the workspace's model lacks the application again.
    act(() => {
      router.result.current.navigate({ ...inChangeSet, changeSetId: undefined });
    });
    await waitFor(() => expect(router.result.current.model).toBe(testModel));
    expect(router.result.current.problem).toEqual({
      kind: "application",
      applicationKey: "person-lists",
      workspaceKey: "stops",
    });
  });

  it("falls back to the workspace's model when the change set's cannot be read", async () => {
    vi.mocked(api.model).mockImplementation(async ({ changeSetId } = {}) => {
      if (changeSetId) throw new Error("gone");
      return testModel;
    });
    window.history.replaceState({}, "", routePath({ ...inChangeSet, applicationKey: "test-app", viewKey: "domains" }));
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.model).toBe(testModel));
    expect(router.result.current.route).toMatchObject({ applicationKey: "test-app", changeSetId: "cs1" });
  });
});

describe("a collection moved to another application", () => {
  it("opens the old address in its new application, in place of the entry, with no problem", async () => {
    forgetWorkspaceModel();
    const moved = {
      ...testModel,
      applications: [
        { ...testModel.applications[0], key: "old-app", objectTypeKeys: [], views: [] },
        { ...testModel.applications[0], key: "test-app" },
      ],
    };
    vi.mocked(api.model).mockResolvedValue(moved);
    vi.mocked(api.workspaceRuntimeState).mockResolvedValue({
      defaultWorkspaceKey: "default",
      version: 1,
      updatedAt: "",
    });
    window.history.replaceState({}, "", "/apps/old-app/views/domains?workspaceKey=west&search=client");
    const length = window.history.length;
    const router = renderHook(useRouter);
    await waitFor(() => expect(router.result.current.route?.kind).toBe("list"));
    expect(router.result.current.problem).toBeUndefined();
    expect(router.result.current.route).toMatchObject({ applicationKey: "test-app", search: "client" });
    expect(window.location.pathname).toBe("/apps/test-app/views/domains");
    expect(window.location.search).toContain("search=client");
    expect(window.history.length).toBe(length);
  });
});
