import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { createDraftClient } from "@/api/draftClient";
import { createHistoryClient } from "@/api/historyClient";
import { errorMessage } from "@/api/errors";
import type { EngineModel, WorkspaceDraft, WorkspaceRevision } from "@/types";
import { allowNavigation } from "@/routing/navigationGuard";
import { InlineError } from "@/ui/InlineError";

interface DataContext {
  api: typeof api;
  draft?: WorkspaceDraft;
  revision?: WorkspaceRevision;
  model?: EngineModel;
  activeModelReleaseId?: string;
  warning: string;
  refresh?: () => Promise<WorkspaceDraft>;
  reloadDraftModel?: () => Promise<void>;
}
const Context = createContext<DataContext>({ api, warning: "" });
export const useWorkspaceData = () => useContext(Context);
export const useDataApi = () => useContext(Context).api;

export function WorkspaceDataProvider({
  draftId,
  revisionId,
  workspaceKey,
  model,
  children,
}: {
  draftId?: string;
  revisionId?: string;
  workspaceKey: string;
  model: EngineModel;
  children: ReactNode;
}) {
  const [loaded, setLoaded] = useState<{
    draft?: WorkspaceDraft;
    revision?: WorkspaceRevision;
    model: EngineModel;
    activeModelReleaseId?: string;
  }>();
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!draftId && !revisionId) return;
    let active = true;
    async function load() {
      const [context, runtime] = await Promise.all([
        draftId ? api.workspaceDraft(draftId) : api.workspaceRevision(revisionId!),
        api.modelRuntimeState().catch(() => undefined),
      ]);
      const label = draftId ? "draft" : "revision";
      if (context.workspaceKey !== workspaceKey)
        throw new Error(`This ${label} belongs to another workspace. Return to Live and select its workspace.`);
      const release = await api.modelRelease(context.modelReleaseId, true);
      if (!release.model || release.schemaVersion !== model.schemaVersion)
        throw new Error(
          `This ${label}'s pinned model schema ${release.schemaVersion} is unsupported. The ${label} is preserved and has not been interpreted with the current model.`,
        );
      if (active) {
        setLoaded({
          ...(draftId ? { draft: context as WorkspaceDraft } : { revision: context as WorkspaceRevision }),
          model: release.model as unknown as EngineModel,
          activeModelReleaseId: runtime?.activeReleaseId,
        });
        setError("");
      }
    }
    load().catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [draftId, revisionId, workspaceKey, model.schemaVersion, retry]);
  if (!draftId && !revisionId) return children;
  if (!loaded)
    return (
      <div>
        {error ? (
          <InlineError message={error} onRetry={() => setRetry((value) => value + 1)} />
        ) : (
          <p>Loading {draftId ? "draft" : "historical revision"}…</p>
        )}
        <a
          href={`/apps/${encodeURIComponent(model.applications[0].key)}/views/${encodeURIComponent(model.applications[0].defaultView)}?workspaceKey=${encodeURIComponent(workspaceKey)}`}
        >
          Return to Live
        </a>
      </div>
    );
  return loaded.draft ? (
    <LoadedDraft initial={loaded.draft} model={loaded.model} activeModelReleaseId={loaded.activeModelReleaseId}>
      {children}
    </LoadedDraft>
  ) : (
    <Context.Provider
      value={{
        api: createHistoryClient(loaded.revision!.id),
        revision: loaded.revision,
        model: loaded.model,
        activeModelReleaseId: loaded.activeModelReleaseId,
        warning: "",
      }}
    >
      {children}
    </Context.Provider>
  );
}

function LoadedDraft({
  initial,
  model: initialModel,
  activeModelReleaseId: initialActiveId,
  children,
}: {
  initial: WorkspaceDraft;
  model: EngineModel;
  activeModelReleaseId?: string;
  children: ReactNode;
}) {
  const [draft, setDraft] = useState(initial);
  const [model, setModel] = useState(initialModel);
  const [activeModelReleaseId, setActiveModelReleaseId] = useState(initialActiveId);
  const [warning, setWarning] = useState("");
  const [controller] = useState(() => {
    let loadedReleaseId = initial.modelReleaseId;
    return createDraftClient(
      initial,
      async (refreshed) => {
        let nextModel: EngineModel | undefined;
        if (refreshed.modelReleaseId !== loadedReleaseId) {
          if (!allowNavigation())
            throw new Error(
              "The draft's model changed. Your input is preserved; saving is blocked until you accept a model refresh.",
            );
          const release = await api.modelRelease(refreshed.modelReleaseId, true);
          if (!release.model || release.schemaVersion !== initialModel.schemaVersion)
            throw new Error(
              "The draft's pinned model could not be loaded or is unsupported. Saving is blocked; retry the refresh or return to Live.",
            );
          nextModel = release.model as unknown as EngineModel;
        }
        const runtime = await api.modelRuntimeState();
        if (nextModel) {
          setModel(nextModel);
          loadedReleaseId = refreshed.modelReleaseId;
        }
        setActiveModelReleaseId(runtime.activeReleaseId);
        setDraft(refreshed);
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
  async function reloadDraftModel() {
    await refresh();
  }
  return (
    <Context.Provider
      value={{
        api: controller.client,
        draft,
        model,
        activeModelReleaseId,
        warning,
        refresh,
        reloadDraftModel,
      }}
    >
      {children}
    </Context.Provider>
  );
}
