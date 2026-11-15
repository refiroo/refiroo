/**
 * Edit a workspace's model from the workspace (0.16 WM1): opens the editor on the draft of the model
 * it runs, for the workspace's ⋯ menu and its Settings page. Not offered without Model authoring and
 * Model release there, and Browse, which Apply reads the workspace's model with, where model
 * administration is off, or for a retired workspace (D323).
 */

import { api } from "@/api/client";
import { errorMessage } from "@/api/errors";
import { useHoldsGroup } from "@/state/useMe";
import { holds, useWorkspacePermissions } from "@/state/permissions";
import { useCapabilities } from "@/state/useSystem";
import type { RouteState } from "@/types";
import { useToast } from "@/ui/Toast";

export function useEditModel(
  workspaceKey: string,
  status: string | undefined,
  onNavigate: (route: RouteState) => void,
): (() => void) | undefined {
  const toast = useToast();
  const { capabilities } = useCapabilities();
  const authors = useHoldsGroup("model-authoring");
  const permissions = useWorkspacePermissions(workspaceKey);
  const releases = holds(permissions, "model-release") && holds(permissions, "browse");
  if (!authors || !releases || status !== "active" || !capabilities?.modelAdmin.activate) return undefined;
  return () => {
    api
      .openWorkspaceModelDraft(workspaceKey)
      .then((draft) =>
        onNavigate({ kind: "settings", page: "model", draftId: draft.id, editor: {}, forWorkspace: workspaceKey }),
      )
      .catch((cause) => toast(errorMessage(cause)));
  };
}
