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
  return aiOffer(system?.ai, permissions, true);
}

/**
 * The assistant, when its session may be offered in the workspace shown (AP-D38): `AI_AGENT_COMMAND`
 * is set, the send level is `values` and the person holds ai-proposals; whatever the provider.
 */
export function useWorkspaceAssistantOffer(): AiSystemInfo | undefined {
  const { system } = useSystem();
  const { permissions } = useWorkspaceData();
  return aiOffer(system?.ai, permissions, false);
}

/**
 * The provider, when a question in words may be asked of a list (0.16 AG4): a provider is set and the
 * person holds ai-proposals in this workspace. The question and the list's field names are the least
 * a send level allows, so any level offers it; otherwise nothing, and nothing is drawn.
 */
export function useQueryTranslationOffer(): AiSystemInfo | undefined {
  const { system } = useSystem();
  const { permissions } = useWorkspaceData();
  return queryTranslationOffer(system?.ai, permissions);
}

/** The rule alone: a provider is configured and ai-proposals is held. */
export function queryTranslationOffer(ai: AiSystemInfo | undefined, permissions: MyPermissions | undefined) {
  return ai?.configured && holds(permissions, "ai-proposals") ? ai : undefined;
}

/** The assistant's offer for a page outside the workspace data context, with the workspace's permissions. */
export function useAssistantOfferIn(workspaceKey: string | undefined, permissions: MyPermissions | undefined) {
  const { system } = useSystem();
  return workspaceKey ? aiOffer(system?.ai, permissions, false) : undefined;
}

/** One rule for both offers: the send level and the permission; the provider only for what calls it. */
function aiOffer(ai: AiSystemInfo | undefined, permissions: MyPermissions | undefined, needsProvider: boolean) {
  if (!ai || ai.sendLevel !== "values" || !holds(permissions, "ai-proposals")) return undefined;
  return (needsProvider ? ai.configured : ai.assistant) ? ai : undefined;
}
