/**
 * Each workspace's model, as the browser holds it (0.11 M5, D49): read once per workspace when
 * first needed, shared by the shell, Settings and the job pages, and forgotten after an activation
 * into that workspace so the next read loads its new release. A workspace that names no key reads
 * the default workspace's model, as the API does (D6).
 */

import { useEffect, useState } from "react";
import { api } from "@/api/client";
import type { EngineModel } from "@/types";

const loading = new Map<string, Promise<EngineModel>>();
const loaded = new Map<string, EngineModel>();

/** The workspace's model, loaded once; a failed read is not kept, so the next one retries. */
export function workspaceModel(workspaceKey: string): Promise<EngineModel> {
  let pending = loading.get(workspaceKey);
  if (!pending) {
    pending = api.model({ workspaceKey }).then(
      (model) => {
        loaded.set(workspaceKey, model);
        return model;
      },
      (cause: unknown) => {
        loading.delete(workspaceKey);
        throw cause;
      },
    );
    loading.set(workspaceKey, pending);
  }
  return pending;
}

/** The workspace's model if it has already loaded; for text that cannot wait, such as a toast. */
export function loadedWorkspaceModel(workspaceKey: string): EngineModel | undefined {
  return loaded.get(workspaceKey);
}

/** Forget one workspace's model (after an activation into it), or every one. */
export function forgetWorkspaceModel(workspaceKey?: string) {
  if (workspaceKey === undefined) {
    loading.clear();
    loaded.clear();
  } else {
    loading.delete(workspaceKey);
    loaded.delete(workspaceKey);
  }
}

/**
 * A workspace's model for a page about something of that workspace, such as a job of another
 * workspace than the one shown (D49): `fallback` until it has loaded, or when none is named or the
 * read fails.
 */
export function useWorkspaceModel(workspaceKey: string | null | undefined, fallback: EngineModel): EngineModel {
  const [found, setFound] = useState<{ key: string; model: EngineModel }>();
  useEffect(() => {
    if (!workspaceKey) return;
    let active = true;
    workspaceModel(workspaceKey)
      .then((model) => active && setFound({ key: workspaceKey, model }))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [workspaceKey]);
  return (workspaceKey && found?.key === workspaceKey ? found.model : undefined) ?? fallback;
}
