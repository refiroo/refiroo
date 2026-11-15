import { useEffect, useState } from "react";
import { allWorkspaces } from "@/api/allWorkspaces";
import type { Workspace } from "@/types";

/**
 * The workspace the editor previews and loads into (0.11 D55): the one the user came from when it
 * runs the draft's model (`release.key`), else the first active workspace that does, in key order,
 * else the one the user came from, whose records the preview then does not read.
 */
export function useEditorWorkspace(modelKey: string | undefined, preferred: string): string {
  const [workspaces, setWorkspaces] = useState<Workspace[]>();
  useEffect(() => {
    let active = true;
    allWorkspaces({ status: "active" })
      .then((items) => active && setWorkspaces(items))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);
  if (!modelKey || !workspaces) return preferred;
  const running = workspaces.filter((item) => item.model.releaseKey === modelKey);
  if (running.some((item) => item.key === preferred) || !running.length) return preferred;
  return [...running].sort((a, b) => a.key.localeCompare(b.key))[0].key;
}
