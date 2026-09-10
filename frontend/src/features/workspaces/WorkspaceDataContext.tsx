import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "@/api/client";
import { createDraftClient } from "@/api/draftClient";
import { errorMessage } from "@/api/errors";
import type { EngineModel, WorkspaceDraft } from "@/types";
import { InlineError } from "@/ui/InlineError";

interface DataContext {
  api: typeof api;
  draft?: WorkspaceDraft;
  model?: EngineModel;
  warning: string;
  refresh?: () => Promise<WorkspaceDraft>;
}
const Context = createContext<DataContext>({ api, warning: "" });
export const useWorkspaceData = () => useContext(Context);
export const useDataApi = () => useContext(Context).api;

export function WorkspaceDataProvider({
  draftId,
  workspaceKey,
  model,
  children,
}: {
  draftId?: string;
  workspaceKey: string;
  model: EngineModel;
  children: ReactNode;
}) {
  const [loaded, setLoaded] = useState<{ draft: WorkspaceDraft; model: EngineModel }>();
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!draftId) return;
    let active = true;
    async function load() {
      const draft = await api.workspaceDraft(draftId!);
      if (draft.workspaceKey !== workspaceKey)
        throw new Error("This draft belongs to another workspace. Return to Live and select its workspace.");
      const release = await api.modelRelease(draft.modelReleaseId, true);
      if (!release.model || release.schemaVersion !== model.schemaVersion)
        throw new Error("This draft's model schema is unsupported. The draft is preserved; use a compatible runtime.");
      if (active) {
        setLoaded({ draft, model: release.model as unknown as EngineModel });
        setError("");
      }
    }
    load().catch((cause) => active && setError(errorMessage(cause)));
    return () => {
      active = false;
    };
  }, [draftId, workspaceKey, model.schemaVersion, retry]);
  if (!draftId) return children;
  if (!loaded)
    return (
      <div>
        {error ? <InlineError message={error} onRetry={() => setRetry((value) => value + 1)} /> : <p>Loading draft…</p>}
        <a
          href={`/apps/${encodeURIComponent(model.applications[0].key)}/views/${encodeURIComponent(model.applications[0].defaultView)}?workspaceKey=${encodeURIComponent(workspaceKey)}`}
        >
          Return to Live
        </a>
      </div>
    );
  return (
    <LoadedDraft initial={loaded.draft} model={loaded.model}>
      {children}
    </LoadedDraft>
  );
}
function LoadedDraft({
  initial,
  model,
  children,
}: {
  initial: WorkspaceDraft;
  model: EngineModel;
  children: ReactNode;
}) {
  const [draft, setDraft] = useState(initial);
  const [warning, setWarning] = useState("");
  const [controller] = useState(() => createDraftClient(initial, setDraft, setWarning));
  return (
    <Context.Provider value={{ api: controller.client, draft, model, warning, refresh: controller.refresh }}>
      {children}
    </Context.Provider>
  );
}
