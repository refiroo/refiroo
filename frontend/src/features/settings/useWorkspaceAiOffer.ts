import type { MyPermissions } from "@/types";
import { holds } from "@/features/security/permissions";
import { useSystem } from "@/features/settings/useSystem";
import { useWorkspaceData } from "@/features/workspaces/WorkspaceDataContext";
import type { AiSystemInfo } from "@/types";

/**
 * The provider, when a feature that sends record names may be offered in the workspace shown (0.16
 * AP2): a provider is set, its send level is `values`, and the person holds ai-proposals in this
 * workspace; otherwise nothing, and nothing is drawn.
 */
export function useWorkspaceAiOffer(): AiSystemInfo | undefined {
  const { system } = useSystem();
  const { permissions } = useWorkspaceData();
  return aiOffer(system?.ai, permissions);
}

/** The same offer for a page outside the workspace data context, with the workspace's permissions. */
export function useAiOfferIn(workspaceKey: string | undefined, permissions: MyPermissions | undefined) {
  const { system } = useSystem();
  return workspaceKey ? aiOffer(system?.ai, permissions) : undefined;
}

function aiOffer(ai: AiSystemInfo | undefined, permissions: MyPermissions | undefined) {
  return ai?.configured && ai.sendLevel === "values" && holds(permissions, "ai-proposals") ? ai : undefined;
}
