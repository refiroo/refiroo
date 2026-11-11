/**
 * The workspace the person works in, remembered for the pages the application does not render: the
 * documentation site and the API reference are opened from plain links, so they read it from storage
 * (same origin) and list that workspace's consumer APIs. The key is JSON, a workspace key. The
 * reference page's inline script reads the same key: `_WORKSPACE_REDIRECT` in
 * `backend/app/management/reference/__init__.py`.
 */

import { useEffect } from "react";
import { writeLocalPreference } from "@/lib/localPreference";

export const SHARED_WORKSPACE_STORAGE_KEY = "refiroo.workspace";

/** Remembers `workspaceKey` (the default workspace too, which ends the effect of another). */
export function useRememberedWorkspace(workspaceKey: string) {
  useEffect(() => {
    if (workspaceKey) writeLocalPreference(SHARED_WORKSPACE_STORAGE_KEY, workspaceKey);
  }, [workspaceKey]);
}
