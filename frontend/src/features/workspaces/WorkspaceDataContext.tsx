import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { createChangeSetClient } from "@/api/changeSetClient";
import { createPublicationClient } from "@/api/publicationClient";
import { errorMessage, isApiError } from "@/api/errors";
import type { EngineModel, ChangeSet, Publication } from "@/types";
import { allowNavigation } from "@/routing/navigationGuard";

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
}
const Context = createContext<DataContext>({ api, warning: "" });
export const useWorkspaceData = () => useContext(Context);
export const useDataApi = () => useContext(Context).api;

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
  const [error, setError] = useState<{ message: string; retryable: boolean }>();
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!changeSetId && !publicationId) return;
    let active = true;
    async function load() {
      const [context, runtime] = await Promise.all([
        changeSetId ? api.changeSet(changeSetId) : api.publication(publicationId!),
        api.modelRuntimeState().catch(() => undefined),
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
      const activeLabel = await differingReleaseLabel(runtime?.activeReleaseId, context.modelReleaseId);
      if (active) {
        setLoaded({
          ...(changeSetId ? { changeSet: context as ChangeSet } : { publication: context as Publication }),
          model: pinnedModel,
          activeModelReleaseId: runtime?.activeReleaseId,
          activeModelReleaseLabel: activeLabel,
        });
        setError(undefined);
      }
    }
    load().catch((cause) => active && setError(contextLoadError(cause, changeSetId ? "change set" : "publication")));
    return () => {
      active = false;
    };
  }, [changeSetId, publicationId, workspaceKey, model.schemaVersion, retry]);
  if (!changeSetId && !publicationId) return children;
  if (!loaded)
    return (
      <Context.Provider
        value={{
          api,
          warning: "",
          loadingError: error?.message,
          retryLoading: error?.retryable ? () => setRetry((value) => value + 1) : undefined,
        }}
      >
        {children}
      </Context.Provider>
    );
  return loaded.changeSet ? (
    <LoadedChangeSet
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
      }}
    >
      {children}
    </Context.Provider>
  );
}

function LoadedChangeSet({
  initial,
  model: initialModel,
  activeModelReleaseId: initialActiveId,
  activeModelReleaseLabel: initialActiveLabel,
  children,
}: {
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
        const runtime = await api.modelRuntimeState();
        const activeLabel = await differingReleaseLabel(runtime.activeReleaseId, refreshed.modelReleaseId);
        if (nextModel) {
          setModel(nextModel);
          loadedReleaseId = refreshed.modelReleaseId;
        }
        setActiveModelReleaseId(runtime.activeReleaseId);
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
  if (isApiError(cause, "unsupported_pinned_model_schema")) {
    const details = cause.details as { schemaVersion?: string } | undefined;
    return {
      message: `This ${label}'s pinned model uses schema ${details?.schemaVersion ?? "an unsupported version"}. The ${label} is preserved and was not interpreted; return to Live.`,
      retryable: false,
    };
  }
  if (
    isApiError(cause, "pinned_model_invalid") ||
    isApiError(cause, "pinned_model_unavailable") ||
    isApiError(cause, "workspace_context_mismatch")
  ) {
    return {
      message: `${errorMessage(cause)} The ${label} was not interpreted; return to Live.`,
      retryable: false,
    };
  }
  return { message: errorMessage(cause), retryable: true };
}
