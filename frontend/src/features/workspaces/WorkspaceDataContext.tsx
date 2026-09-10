import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { createDraftClient } from "@/api/draftClient";
import { createHistoryClient } from "@/api/historyClient";
import { errorMessage } from "@/api/errors";
import type { EngineModel, WorkspaceDraft, WorkspaceRevision } from "@/types";
import { InlineError } from "@/ui/InlineError";

interface DataContext {
  api: typeof api;
  draft?: WorkspaceDraft;
  revision?: WorkspaceRevision;
  model?: EngineModel;
  activeModelReleaseId?: string;
  warning: string;
  refresh?: () => Promise<WorkspaceDraft>;
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
  model,
  activeModelReleaseId,
  children,
}: {
  initial: WorkspaceDraft;
  model: EngineModel;
  activeModelReleaseId?: string;
  children: ReactNode;
}) {
  const [draft, setDraft] = useState(initial);
  const [warning, setWarning] = useState("");
  const [controller] = useState(() => createDraftClient(initial, setDraft, setWarning));
  return (
    <Context.Provider
      value={{ api: controller.client, draft, model, activeModelReleaseId, warning, refresh: controller.refresh }}
    >
      {children}
    </Context.Provider>
  );
}
