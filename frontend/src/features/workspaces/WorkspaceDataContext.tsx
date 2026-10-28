import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { createChangeSetClient } from "@/api/changeSetClient";
import { createPublicationClient } from "@/api/publicationClient";
import { setExpectedRelease } from "@/api/expectedRelease";
import { errorMessage, isApiError } from "@/api/errors";
import type { EngineModel, ChangeSet, MyPermissions, Publication } from "@/types";
import { useInbox } from "@/features/inbox/useInbox";
import { allowNavigation } from "@/routing/navigationGuard";
import {
  ALL_WRITES,
  NO_WRITES,
  recordWrites,
  useWorkspacePermissions,
  type RecordWrites,
} from "@/features/security/permissions";

class WorkspaceContextError extends Error {
  constructor(
    message: string,
    readonly retryable: boolean,
  ) {
    super(message);
  }
}

interface DataContext {
  api: typeof api;
  changeSet?: ChangeSet;
  publication?: Publication;
  model?: EngineModel;
  activeModelReleaseId?: string;
  /** "key version" of the active release, resolved only when it differs from the pinned one. */
  activeModelReleaseLabel?: string;
  warning: string;
  /** Set when the workspace context could not be loaded at all. */
  loadingError?: string;
  /** Retry loading after a transient failure. */
  retryLoading?: () => void;
  refresh?: () => Promise<ChangeSet>;
  reloadChangeSetModel?: () => Promise<void>;
  /** The change set no longer exists (published, discarded elsewhere): the page moves to live data. */
  changeSetGone?: boolean;
  /**
   * Which records the person may write here (0.12 Z5, D329): Edit live's in live data, Work in
   * change sets' in a change set, none in a publication. Absent without a workspace (the model
   * editor's preview, whose client refuses writes): every record. Read it with `useRecordWrites`.
   */
  writes?: RecordWrites;
  /** The person's permissions in this workspace, once read. */
  permissions?: MyPermissions;
}
const Context = createContext<DataContext>({ api, warning: "", writes: ALL_WRITES });
export const useWorkspaceData = () => useContext(Context);
export const useDataApi = () => useContext(Context).api;
/** Which records the person may write in the data shown (0.12 Z5, D329). */
export const useRecordWrites = () => useContext(Context).writes ?? ALL_WRITES;

/**
 * The data of the model editor's preview (0.10 A4b, D44): live records read through a client that
 * refuses every write (`api/previewClient`), under a model the server is not running.
 */
export function PreviewDataProvider({ client, children }: { client: typeof api; children: ReactNode }) {
  return <Context.Provider value={{ api: client, warning: "", writes: ALL_WRITES }}>{children}</Context.Provider>;
}

export function WorkspaceDataProvider({
  changeSetId,
  publicationId,
  workspaceKey,
  model,
  children,
}: {
  changeSetId?: string;
  publicationId?: string;
  workspaceKey: string;
  model: EngineModel;
  children: ReactNode;
}) {
  const [loaded, setLoaded] = useState<{
    changeSet?: ChangeSet;
    publication?: Publication;
    model: EngineModel;
    activeModelReleaseId?: string;
    activeModelReleaseLabel?: string;
  }>();
  const [error, setError] = useState<{ message: string; retryable: boolean; gone?: boolean }>();
  const permissions = useWorkspacePermissions(workspaceKey);
  const writes = useMemo(
    () => (publicationId ? NO_WRITES : recordWrites(permissions, changeSetId ? "change-sets" : "edit-live")),
    [permissions, changeSetId, publicationId],
  );
  const live = useMemo(() => ({ api, warning: "", writes, permissions }), [writes, permissions]);
  const [retry, setRetry] = useState(0);
  // The release this page's data writes name (M6a, D65): live data its model's; a change set its
  // own (LoadedChangeSet); a publication none, as it takes no writes.
  const liveRelease = changeSetId || publicationId ? undefined : model.releaseId;
  useEffect(() => {
    if (changeSetId) return;
    setExpectedRelease(liveRelease);
    return () => setExpectedRelease(undefined);
  }, [changeSetId, liveRelease]);
  useEffect(() => {
    if (!changeSetId && !publicationId) return;
    let active = true;
    async function load() {
      const [context, runtime] = await Promise.all([
        changeSetId ? api.changeSet(changeSetId) : api.publication(publicationId!),
        api.workspaceModel(workspaceKey).catch(() => undefined),
      ]);
      const label = changeSetId ? "change set" : "publication";
      if (context.workspaceKey !== workspaceKey)
        throw new WorkspaceContextError(
          `This ${label} belongs to another workspace. Return to Live and select its workspace.`,
          false,
        );
      const pinnedModel = await api.model({
        workspaceKey,
        ...(changeSetId ? { changeSetId } : { publicationId }),
      });
      const activeLabel = await differingReleaseLabel(runtime?.releaseId, context.modelReleaseId);
      if (active) {
        setLoaded({
          ...(changeSetId ? { changeSet: context as ChangeSet } : { publication: context as Publication }),
          model: pinnedModel,
          activeModelReleaseId: runtime?.releaseId,
          activeModelReleaseLabel: activeLabel,
        });
        setError(undefined);
      }
    }
    load().catch(
      (cause) =>
        active &&
        setError({
          ...contextLoadError(cause, changeSetId ? "change set" : "publication"),
          gone: Boolean(changeSetId) && isApiError(cause, "CHANGE_SET_NOT_FOUND"),
        }),
    );
    return () => {
      active = false;
    };
  }, [changeSetId, publicationId, workspaceKey, model.schemaVersion, retry]);
  if (!changeSetId && !publicationId) return <Context.Provider value={live}>{children}</Context.Provider>;
  if (!loaded)
    return (
      <Context.Provider
        value={{
          api,
          warning: "",
          writes: NO_WRITES,
          permissions,
          loadingError: error?.gone ? undefined : error?.message,
          changeSetGone: error?.gone,
          retryLoading: error?.retryable ? () => setRetry((value) => value + 1) : undefined,
        }}
      >
        {children}
      </Context.Provider>
    );
  return loaded.changeSet ? (
    <LoadedChangeSet
      writes={writes}
      permissions={permissions}
      initial={loaded.changeSet}
      model={loaded.model}
      activeModelReleaseId={loaded.activeModelReleaseId}
      activeModelReleaseLabel={loaded.activeModelReleaseLabel}
    >
      {children}
    </LoadedChangeSet>
  ) : (
    <Context.Provider
      value={{
        api: createPublicationClient(loaded.publication!.id),
        publication: loaded.publication,
        model: loaded.model,
        activeModelReleaseId: loaded.activeModelReleaseId,
        activeModelReleaseLabel: loaded.activeModelReleaseLabel,
        warning: "",
        writes,
        permissions,
      }}
    >
      {children}
    </Context.Provider>
  );
}

function LoadedChangeSet({
  writes,
  permissions,
  initial,
  model: initialModel,
  activeModelReleaseId: initialActiveId,
  activeModelReleaseLabel: initialActiveLabel,
  children,
}: {
  writes: RecordWrites;
  permissions?: MyPermissions;
  initial: ChangeSet;
  model: EngineModel;
  activeModelReleaseId?: string;
  activeModelReleaseLabel?: string;
  children: ReactNode;
}) {
  const [changeSet, setChangeSet] = useState(initial);
  const [model, setModel] = useState(initialModel);
  const [activeModelReleaseId, setActiveModelReleaseId] = useState(initialActiveId);
  const [activeModelReleaseLabel, setActiveModelReleaseLabel] = useState(initialActiveLabel);
  const [warning, setWarning] = useState("");
  const [gone, setGone] = useState(false);
  const pinned = changeSet.modelReleaseId;
  // A change set left open while it was published (approved by someone else) is found again when
  // the person returns to the tab; its controls would only answer errors.
  const changeSetId = changeSet.id;
  useEffect(() => {
    function check() {
      if (document.visibilityState === "hidden") return;
      api.changeSet(changeSetId).catch((cause) => isApiError(cause, "CHANGE_SET_NOT_FOUND") && setGone(true));
    }
    document.addEventListener("visibilitychange", check);
    window.addEventListener("focus", check);
    return () => {
      document.removeEventListener("visibilitychange", check);
      window.removeEventListener("focus", check);
    };
  }, [changeSetId]);
  // The change set follows its request: a notice about it (arrived, or opened at this address) means the
  // submission may have moved, a decision sent back or given, so it is read again.
  const { touched } = useInbox(false);
  const lastTouch = useRef(touched?.count ?? 0);
  useEffect(() => {
    if (!touched || touched.count === lastTouch.current) return;
    lastTouch.current = touched.count;
    if (touched.subjectId === changeSetId) void refresh().catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [touched, changeSetId]);
  useEffect(() => {
    setExpectedRelease(pinned);
    return () => setExpectedRelease(undefined);
  }, [pinned]);
  const [controller] = useState(() => {
    let loadedReleaseId = initial.modelReleaseId;
    return createChangeSetClient(
      initial,
      async (refreshed) => {
        let nextModel: EngineModel | undefined;
        if (refreshed.modelReleaseId !== loadedReleaseId) {
          if (!allowNavigation())
            throw new Error(
              "The change set's model changed. Your input is preserved; saving is blocked until you accept a model refresh.",
            );
          nextModel = await api.model({
            workspaceKey: refreshed.workspaceKey,
            changeSetId: refreshed.id,
          });
        }
        const runtime = await api.workspaceModel(refreshed.workspaceKey);
        const activeLabel = await differingReleaseLabel(runtime.releaseId, refreshed.modelReleaseId);
        if (nextModel) {
          setModel(nextModel);
          loadedReleaseId = refreshed.modelReleaseId;
        }
        setActiveModelReleaseId(runtime.releaseId);
        setActiveModelReleaseLabel(activeLabel);
        setChangeSet(refreshed);
      },
      setWarning,
    );
  });
  async function refresh() {
    try {
      return await controller.refresh();
    } catch (cause) {
      if (isApiError(cause, "CHANGE_SET_NOT_FOUND")) setGone(true);
      setWarning(errorMessage(cause));
      throw cause;
    }
  }
  async function reloadChangeSetModel() {
    await refresh();
  }
  return (
    <Context.Provider
      value={{
        api: controller.client,
        changeSet,
        model,
        activeModelReleaseId,
        activeModelReleaseLabel,
        warning,
        refresh,
        reloadChangeSetModel,
        changeSetGone: gone,
        writes,
        permissions,
      }}
    >
      {children}
    </Context.Provider>
  );
}

/** Name the active release by key and version where it differs from the pinned one; ids are not for people. */
async function differingReleaseLabel(activeId: string | undefined, pinnedId: string) {
  if (!activeId || activeId === pinnedId) return undefined;
  const release = await api.modelRelease(activeId).catch(() => undefined);
  return release ? `${release.key} ${release.version}` : undefined;
}

function contextLoadError(cause: unknown, label: "change set" | "publication") {
  if (cause instanceof WorkspaceContextError) {
    return { message: cause.message, retryable: cause.retryable };
  }
  if (isApiError(cause, "UNSUPPORTED_PINNED_MODEL_SCHEMA")) {
    const details = cause.details as { schemaVersion?: string } | undefined;
    return {
      message: `This ${label}'s pinned model uses schema ${details?.schemaVersion ?? "an unsupported version"}. The ${label} is preserved and was not interpreted; return to Live.`,
      retryable: false,
    };
  }
  if (
    isApiError(cause, "PINNED_MODEL_INVALID") ||
    isApiError(cause, "PINNED_MODEL_UNAVAILABLE") ||
    isApiError(cause, "WORKSPACE_CONTEXT_MISMATCH")
  ) {
    return {
      message: `${errorMessage(cause)} The ${label} was not interpreted; return to Live.`,
      retryable: false,
    };
  }
  return { message: errorMessage(cause), retryable: true };
}
